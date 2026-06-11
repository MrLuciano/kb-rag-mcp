"""Scoring and reranking experiments with configurable distance metrics.

FASE 25: Optimization Experiments

Provides strategy abstractions for comparing dense-only, hybrid, and
reranked retrieval variants.  The ``ScoringEngine`` runs experiments
against an existing indexed collection without re-ingesting.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from kb_server.embed_client import get_embedding
from kb_server.evaluation.dataset import GoldenDataset
from kb_server.optimization.metric_computer import MetricComputer
from kb_server.retrieval.hybrid_search import get_hybrid_searcher
from kb_server.retrieval.reranker import get_reranker

log = logging.getLogger("kb-mcp.optimization")


# ── Distance metric mapping ───────────────────────────────────────


def _get_distance_enum():
    """Lazy-load qdrant_client.models.Distance."""
    from qdrant_client.models import Distance

    return Distance


DISTANCE_METRICS: Dict[str, Any] = {}


def _init_distance_metrics() -> None:
    """Populate ``DISTANCE_METRICS`` with qdrant distance enum values."""
    if DISTANCE_METRICS:
        return
    Distance = _get_distance_enum()
    DISTANCE_METRICS.update(
        {
            "COSINE": Distance.COSINE,
            "DOT": Distance.DOT,
            "EUCLID": Distance.EUCLID,
            "MANHATTAN": Distance.MANHATTAN,
        }
    )


# ── ScoringVariant ABC ────────────────────────────────────────────


class ScoringVariant(ABC):
    """Abstract base class for scoring strategy variants."""

    @abstractmethod
    async def search(
        self,
        query: str,
        vector_store: Any,
        top_k: int = 5,
    ) -> List[dict]:
        """Return search results for *query*.

        Args:
            query: Query text.
            vector_store: ``VectorStore`` instance.
            top_k: Number of results to return.

        Returns:
            List of result dicts.
        """


# ── DenseOnlyVariant ────────────────────────────────────────────────


class DenseOnlyVariant(ScoringVariant):
    """Dense vector search only, with configurable distance metric."""

    def __init__(self, distance_metric: str = "COSINE"):
        self.distance_metric = distance_metric

    async def search(
        self,
        query: str,
        vector_store: Any,
        top_k: int = 5,
    ) -> List[dict]:
        """Search using dense vector only.

        The distance metric is recorded for reporting but collection
        creation is the caller's responsibility.
        """
        log.info(
            "DenseOnlyVariant search: query='%s...', top_k=%d, "
            "metric=%s",
            query[:60],
            top_k,
            self.distance_metric,
        )
        query_vector = await get_embedding(query)
        return await vector_store.search(
            vector=query_vector,
            top_k=top_k,
        )


# ── HybridVariant ───────────────────────────────────────────────────


class HybridVariant(ScoringVariant):
    """Hybrid dense + sparse search with RRF fusion."""

    def __init__(
        self,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        rrf_k: int = 60,
    ):
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k

    async def search(
        self,
        query: str,
        vector_store: Any,
        top_k: int = 5,
    ) -> List[dict]:
        """Search using dense + sparse hybrid search with RRF fusion."""
        log.info(
            "HybridVariant search: query='%s...', top_k=%d, "
            "dense_weight=%.2f, sparse_weight=%.2f, rrf_k=%d",
            query[:60],
            top_k,
            self.dense_weight,
            self.sparse_weight,
            self.rrf_k,
        )
        query_vector = await get_embedding(query)
        hybrid_searcher = get_hybrid_searcher()
        # Temporarily override weights for this search
        original_dense = hybrid_searcher.dense_weight
        original_sparse = hybrid_searcher.sparse_weight
        original_rrf_k = hybrid_searcher.rrf_k
        try:
            hybrid_searcher.dense_weight = self.dense_weight
            hybrid_searcher.sparse_weight = self.sparse_weight
            hybrid_searcher.rrf_k = self.rrf_k
            return await hybrid_searcher.search(
                vector_store=vector_store,
                query_vector=query_vector,
                query_text=query,
                top_k=top_k,
            )
        finally:
            hybrid_searcher.dense_weight = original_dense
            hybrid_searcher.sparse_weight = original_sparse
            hybrid_searcher.rrf_k = original_rrf_k


# ── RerankedVariant ─────────────────────────────────────────────────


class RerankedVariant(ScoringVariant):
    """Wrap a base variant and apply cross-encoder reranking."""

    def __init__(
        self,
        base_variant: ScoringVariant,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        batch_size: int = 20,
    ):
        self.base_variant = base_variant
        self.model_name = model_name
        self.batch_size = batch_size
        self._warmed_up = False

    async def _warmup(self) -> None:
        """Warm up reranker to avoid non-deterministic first-run scores."""
        if self._warmed_up:
            return
        log.info("RerankedVariant: warming up cross-encoder model")
        reranker = get_reranker()
        reranker._load_model()
        self._warmed_up = True
        log.info("RerankedVariant: warmup complete")

    async def search(
        self,
        query: str,
        vector_store: Any,
        top_k: int = 5,
    ) -> List[dict]:
        """Run base search, then rerank results via cross-encoder."""
        log.info(
            "RerankedVariant search: query='%s...', top_k=%d, "
            "model=%s",
            query[:60],
            top_k,
            self.model_name,
        )
        if not self._warmed_up:
            await self._warmup()
        base_results = await self.base_variant.search(
            query=query,
            vector_store=vector_store,
            top_k=top_k,
        )
        if not base_results:
            return []
        reranker = get_reranker()
        try:
            return await reranker.rerank(
                query=query,
                results=base_results,
                top_k=top_k,
            )
        except Exception as e:
            log.warning(
                "Reranking failed (%s); returning base results", e
            )
            return base_results


# ── ScoringEngine ───────────────────────────────────────────────────


class ScoringEngine:
    """Run scoring experiments against an indexed collection.

    The engine does **not** re-ingest; it assumes the collection is
    already populated and runs queries at query time.
    """

    def __init__(
        self,
        variant: ScoringVariant,
        vector_store: Any,
        dataset: GoldenDataset,
    ):
        self.variant = variant
        self.vector_store = vector_store
        self.dataset = dataset

    async def _warmup_reranker(self) -> None:
        """Warm up reranker if the variant is a ``RerankedVariant``."""
        if isinstance(self.variant, RerankedVariant):
            await self.variant._warmup()

    async def run_experiment(self, top_k: int = 5) -> Dict[str, Any]:
        """Run the experiment and return IR metrics.

        For each example in the dataset, embeds the query, runs the
        scoring variant's search, and collects the retrieved source
        file names.

        Args:
            top_k: Number of results to retrieve per query.

        Returns:
            Dictionary with keys ``recall_at_k``, ``mrr``,
            ``ndcg_at_k``, plus metadata fields.
        """
        log.info(
            "ScoringEngine.run_experiment: top_k=%d, "
            "dataset_size=%d",
            top_k,
            len(self.dataset),
        )

        # Warm up reranker if needed
        await self._warmup_reranker()

        query_results = []
        for example in self.dataset.examples:
            query_text = example.get("query", "")
            expected_docs = example.get("expected_docs", [])
            if not query_text:
                log.warning("Skipping example with empty query")
                continue

            results = await self.variant.search(
                query=query_text,
                vector_store=self.vector_store,
                top_k=top_k,
            )
            retrieved_docs = [
                r.get("source_file", "") for r in results
            ]
            query_results.append(
                {
                    "query": query_text,
                    "retrieved_docs": retrieved_docs,
                    "expected_docs": expected_docs,
                }
            )

        computer = MetricComputer()
        metrics = computer.compute_all(query_results, k=top_k)

        # Add variant metadata
        metrics["variant_name"] = self.variant.__class__.__name__
        if isinstance(self.variant, DenseOnlyVariant):
            metrics["distance_metric"] = self.variant.distance_metric
        else:
            metrics["distance_metric"] = "COSINE"

        if isinstance(self.variant, HybridVariant):
            metrics["dense_weight"] = self.variant.dense_weight
            metrics["sparse_weight"] = self.variant.sparse_weight
        else:
            metrics["dense_weight"] = None
            metrics["sparse_weight"] = None

        metrics["reranker_enabled"] = isinstance(
            self.variant, RerankedVariant
        )

        log.info("ScoringEngine experiment complete: %s", metrics)
        return metrics


# ── Factory ─────────────────────────────────────────────────────────


def create_variant(name: str, **kwargs: Any) -> ScoringVariant:
    """Create a scoring variant by name.

    Args:
        name: Variant name — ``dense_only``, ``hybrid``, ``reranked``.
        **kwargs: Constructor arguments.

    Returns:
        ``ScoringVariant`` instance.

    Raises:
        ValueError: If *name* is unknown.
    """
    if name == "dense_only":
        return DenseOnlyVariant(
            distance_metric=kwargs.get("distance_metric", "COSINE")
        )
    elif name == "hybrid":
        return HybridVariant(
            dense_weight=kwargs.get("dense_weight", 0.7),
            sparse_weight=kwargs.get("sparse_weight", 0.3),
            rrf_k=kwargs.get("rrf_k", 60),
        )
    elif name == "reranked":
        base = kwargs.get("base", "hybrid")
        if isinstance(base, str):
            base_variant = create_variant(base)
        elif isinstance(base, ScoringVariant):
            base_variant = base
        else:
            raise ValueError(
                f"reranked base must be str or ScoringVariant, "
                f"got {type(base)}"
            )
        return RerankedVariant(
            base_variant=base_variant,
            model_name=kwargs.get(
                "model_name",
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
            ),
            batch_size=kwargs.get("batch_size", 20),
        )
    else:
        raise ValueError(f"Unknown variant name: {name}")
