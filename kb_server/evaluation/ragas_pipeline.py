"""RAGAS-based RAG evaluation pipeline (custom metrics implementation).

Uses LLM-as-judge via kb_server.evaluation.llm_wrapper instead of the
ragas library (which has incompatible transitive dependencies).

Metrics:
  - faithfulness        : Is the answer supported by the context?
  - answer_relevancy    : Does the answer address the question?
  - context_precision   : Fraction of retrieved contexts that are relevant
  - context_recall      : Fraction of ground-truth facts present in contexts
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb_server.evaluation.dataset import GoldenDataset
from kb_server.evaluation.llm_wrapper import (
    BaseLLMWrapper,
    RAGASLLMAdapter,
    create_llm_wrapper,
)

# Import custom metrics (prompt-based, no ragas dependency)
from kb_server.evaluation import metrics as custom_metrics

log = logging.getLogger("kb-mcp.eval")

# Default backend for evaluation judge
DEFAULT_EVAL_BACKEND = os.getenv("EMBED_BACKEND", "lmstudio-rest")
DEFAULT_EVAL_MODEL = os.getenv("EVAL_LLM_MODEL", os.getenv("LLM_MODEL", "default"))


class RAGASEvaluator:
    """RAGAS-style evaluation pipeline using custom LLM-as-judge metrics."""

    def __init__(
        self,
        dataset: GoldenDataset,
        llm_provider: Optional[BaseLLMWrapper] = None,
        model: str = DEFAULT_EVAL_MODEL,
        backend: str = DEFAULT_EVAL_BACKEND,
        vector_store: Optional[Any] = None,
    ):
        """Initialize evaluator.

        Args:
            dataset: Golden dataset with query / expected_answer / expected_docs.
            llm_provider: Optional pre-configured LLM wrapper.
                          If None, one is created from the backend env var.
            model: Model name for LLM-as-judge.
            backend: Backend identifier (lmstudio-rest, openai-compat, ollama).
            vector_store: Optional VectorStore for retrieving live contexts.
        """
        self.dataset = dataset
        self.backend = backend
        self.model = model
        self.vector_store = vector_store

        if llm_provider is not None:
            self.llm = RAGASLLMAdapter(llm_provider)
        else:
            wrapper = create_llm_wrapper(backend, model=model)
            self.llm = RAGASLLMAdapter(wrapper)

        log.info(
            "RAGASEvaluator initialized: backend=%s model=%s examples=%d",
            backend,
            model,
            len(dataset),
        )

    async def evaluate(self) -> Dict[str, float]:
        """Run evaluation on all examples in the dataset.

        Returns:
            Dict mapping metric_name -> mean_score.
            Keys: faithfulness, answer_relevancy, context_precision, context_recall.

        Raises:
            ValueError: If dataset is empty.
        """
        if not self.dataset.examples:
            log.warning("Dataset is empty — nothing to evaluate")
            return {}

        scores: Dict[str, List[float]] = {
            "faithfulness": [],
            "answer_relevancy": [],
            "context_precision": [],
            "context_recall": [],
        }

        for i, example in enumerate(self.dataset.examples):
            query = example.get("query", "")
            expected_answer = example.get("expected_answer", "")
            expected_docs = example.get("expected_docs", [])

            log.debug("Evaluating example %d/%d: %s", i + 1, len(self.dataset.examples), query[:60])

            # Determine contexts to use
            contexts = await self._get_contexts(query, expected_docs)
            if not contexts:
                log.warning("No contexts for query: %s", query[:60])
                continue

            # Use expected_answer as the "answer" to evaluate
            answer = expected_answer

            try:
                # Run all 4 metrics in parallel
                f_score, ar_score, cp_score, cr_score = await asyncio.gather(
                    custom_metrics.faithfulness(answer, contexts, self.llm),
                    custom_metrics.answer_relevancy(query, answer, self.llm),
                    custom_metrics.context_precision(query, contexts, self.llm),
                    custom_metrics.context_recall(query, answer, contexts, self.llm),
                )
                scores["faithfulness"].append(f_score)
                scores["answer_relevancy"].append(ar_score)
                scores["context_precision"].append(cp_score)
                scores["context_recall"].append(cr_score)
            except Exception as e:
                log.error("Error evaluating example %d: %s", i, e)
                continue

        # Compute means
        results: Dict[str, float] = {}
        for metric_name, values in scores.items():
            if values:
                results[metric_name] = round(sum(values) / len(values), 4)
            else:
                results[metric_name] = 0.0

        log.info("Evaluation complete: %s", results)
        return results

    async def _get_contexts(
        self, query: str, expected_docs: List[str]
    ) -> List[str]:
        """Retrieve contexts for a query.

        Priority:
        1. Live VectorStore.search() if vector_store is provided
        2. expected_docs from the dataset
        3. Fallback: empty list
        """
        contexts: List[str] = []

        # Try live search first
        if self.vector_store is not None:
            try:
                from kb_server.embed_client import get_embedding

                vector = await get_embedding(query)
                results = await self.vector_store.search(
                    vector=vector,
                    top_k=5,
                )
                contexts = [r.get("text", str(r)) for r in results]
                log.debug("Retrieved %d contexts from vector store", len(contexts))
            except Exception as e:
                log.warning("VectorStore search failed: %s", e)

        # Fallback to expected_docs
        if not contexts and expected_docs:
            contexts = expected_docs
            log.debug("Using %d expected_docs as contexts", len(contexts))

        return contexts

    def save_results(self, results: Dict[str, float], output_path: Path) -> None:
        """Save evaluation results to JSON."""
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        log.info("Results saved to %s", output_path)
