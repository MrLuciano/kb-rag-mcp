"""Chunking parameter optimization experiments.

PHASE 25: Optimization Experiments

Provides strategy abstractions for fixed, recursive, and semantic
chunking, plus a ChunkingEngine that orchestrates re-ingest and
metric computation against a golden dataset.
"""

import logging
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

from kb_server.evaluation.dataset import GoldenDataset
from kb_server.optimization.metric_computer import MetricComputer

log = logging.getLogger("kb-mcp.optimization")


# ── Chunking strategies ─────────────────────────────────────────────


class ChunkingStrategy(ABC):
    """Abstract base class for document chunking strategies."""

    @abstractmethod
    def split(self, text: str, file_type: str = "txt") -> List[str]:
        """Split *text* into chunks and return a list of chunk strings.

        Args:
            text: Raw text to split.
            file_type: Document type hint (e.g. ``txt``, ``pdf``).

        Returns:
            List of chunk strings.
        """
        ...


class FixedStrategy(ChunkingStrategy):
    """Fixed-size sliding-window chunking."""

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 80) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, file_type: str = "txt") -> List[str]:
        """Manual sliding-window split.

        Chunks shorter than 30 characters are dropped.
        """
        size = self.chunk_size
        overlap = self.chunk_overlap
        step = max(1, size - overlap)
        chunks = [
            text[i : i + size]
            for i in range(0, len(text), step)
            if len(text[i : i + size]) >= 30
        ]
        return chunks


class RecursiveStrategy(ChunkingStrategy):
    """Recursive character text splitting via LangChain."""

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 80,
        separators: Optional[List[str]] = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ]

    def split(self, text: str, file_type: str = "txt") -> List[str]:
        """Use :class:`RecursiveCharacterTextSplitter` if available.

        Falls back to manual fixed-size split on ImportError.
        """
        try:
            from langchain_text_splitters import (
                RecursiveCharacterTextSplitter,
            )

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
            )
            return splitter.split_text(text)
        except Exception:
            log.warning(
                "RecursiveCharacterTextSplitter unavailable; "
                "falling back to fixed-size split"
            )
            return FixedStrategy(self.chunk_size, self.chunk_overlap).split(
                text
            )


class SemanticStrategy(ChunkingStrategy):
    """Semantic chunking via docling HybridChunker."""

    def __init__(self, max_tokens: int = 512) -> None:
        self.max_tokens = max_tokens

    def split(self, text: str, file_type: str = "txt") -> List[str]:
        """Use :class:`HybridChunker` if available.

        Falls back to :class:`RecursiveStrategy` with ``chunk_size=512``
        and logs a warning.
        """
        try:
            from docling.chunking import HybridChunker

            chunker = HybridChunker(max_tokens=self.max_tokens)  # type: ignore[call-arg]
            chunks = chunker.chunk(text)  # type: ignore[arg-type]
            return [c.text for c in chunks]
        except Exception:
            log.warning("HybridChunker unavailable; falling back to recursive")
            return RecursiveStrategy(chunk_size=512).split(text)


# ── Factory ─────────────────────────────────────────────────────────


def create_strategy(name: str, **kwargs: Any) -> ChunkingStrategy:
    """Create a :class:`ChunkingStrategy` by name.

    Args:
        name: One of ``fixed``, ``recursive``, ``semantic``.
        **kwargs: Constructor arguments (``chunk_size``, ``overlap``,
            ``max_tokens``, etc.).

    Returns:
        ChunkingStrategy instance.

    Raises:
        ValueError: For unknown strategy names.
    """
    if name == "fixed":
        return FixedStrategy(
            chunk_size=kwargs.get("chunk_size", 600),
            chunk_overlap=kwargs.get(
                "chunk_overlap", kwargs.get("overlap", 80)
            ),
        )
    elif name == "recursive":
        return RecursiveStrategy(
            chunk_size=kwargs.get("chunk_size", 600),
            chunk_overlap=kwargs.get(
                "chunk_overlap", kwargs.get("overlap", 80)
            ),
        )
    elif name == "semantic":
        return SemanticStrategy(max_tokens=kwargs.get("max_tokens", 512))
    else:
        raise ValueError(f"Unknown strategy: {name}")


# ── ChunkingEngine ────────────────────────────────────────────────────


class ChunkingEngine:
    """Orchestrate chunking experiments with re-ingest and metrics.

    The engine uses a temporary collection (``_experiment`` suffix) to
    avoid polluting production indexes.
    """

    def __init__(
        self,
        strategy: ChunkingStrategy,
        vector_store: Any,
        dataset: GoldenDataset,
    ) -> None:
        self.strategy = strategy
        self.vector_store = vector_store
        self.dataset = dataset
        self.metric_computer = MetricComputer()

    def _experiment_collection(self) -> str:
        """Return the temporary experiment collection name."""
        base = os.getenv("QDRANT_COLLECTION", "kb_docs")
        return f"{base}_experiment"

    async def _ingest_with_strategy(self, docs_path: Path) -> int:
        """Re-ingest documents using the configured chunking strategy.

        Args:
            docs_path: Directory containing documents to ingest.

        Returns:
            Number of chunks upserted.
        """
        # Lazy import to avoid heavy startup dependencies
        from ingest.ingest import parse_document
        from kb_server.embed_client import get_embeddings_batch

        docs_path = Path(docs_path)
        if not docs_path.exists():
            log.warning("Docs path does not exist: %s", docs_path)
            return 0

        all_chunks: List[dict] = []
        file_index = 0

        for file_path in docs_path.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                sections = parse_document(file_path)
            except Exception as exc:
                log.warning("Skipping %s: %s", file_path, exc)
                continue

            if not sections:
                continue

            for section in sections:
                text = section.get("text", "")
                if not text:
                    continue

                file_type = file_path.suffix.lower().lstrip(".") or "txt"
                chunks = self.strategy.split(text, file_type)

                for chunk_index, chunk_text in enumerate(chunks):
                    if len(chunk_text.strip()) < 30:
                        continue
                    all_chunks.append(
                        {
                            "text": chunk_text,
                            "source_file": str(file_path),
                            "file_type": file_type,
                            "product": "experiment",
                            "chunk_index": chunk_index,
                            "page": section.get("page"),
                            "chunk_id": str(uuid.uuid4()),
                        }
                    )

            file_index += 1

        if not all_chunks:
            log.warning("No chunks produced from %s", docs_path)
            return 0

        # Batch embeddings
        texts = [c["text"] for c in all_chunks]
        try:
            vectors = await get_embeddings_batch(texts)
        except Exception as exc:
            log.error("Embedding batch failed: %s", exc)
            return 0

        for chunk, vector in zip(all_chunks, vectors):
            chunk["vector"] = vector

        # Upsert to vector store
        try:
            await self.vector_store.upsert_chunks(all_chunks)
        except Exception as exc:
            log.error("Upsert failed: %s", exc)
            return 0

        log.info(
            "Ingested %d chunks from %d files into %s",
            len(all_chunks),
            file_index,
            self._experiment_collection(),
        )
        return len(all_chunks)

    async def run_experiment(
        self, docs_path: Path, top_k: int = 5, clean: bool = True
    ) -> dict:
        """Run a chunking experiment and return IR metrics.

        Args:
            docs_path: Directory containing documents to index.
            top_k: Number of top results to evaluate.
            clean: If True, clear the experiment collection before
                re-ingesting.

        Returns:
            Dictionary with keys ``recall_at_k``, ``mrr``,
            ``ndcg_at_k``, ``chunk_count``, ``strategy_name``.
        """
        from kb_server.collections.manager import CollectionManager
        from kb_server.embed_client import get_embedding

        experiment_collection = self._experiment_collection()

        # Clean experiment collection if requested
        if clean:
            try:
                manager = CollectionManager(
                    client=self.vector_store.client,
                    vector_size=self.vector_store.dim,
                )
                await manager.delete_collection(experiment_collection)
                await manager.create_collection(experiment_collection)
                # Temporarily override collection for upsert
                original_collection = self.vector_store.collection
                self.vector_store.collection = experiment_collection
                chunk_count = await self._ingest_with_strategy(docs_path)
                self.vector_store.collection = original_collection
            except Exception as exc:
                log.error("Failed to clean experiment collection: %s", exc)
                return {
                    "recall_at_k": 0.0,
                    "mrr": 0.0,
                    "ndcg_at_k": 0.0,
                    "chunk_count": 0,
                    "strategy_name": self.strategy.__class__.__name__,
                }
        else:
            original_collection = self.vector_store.collection
            self.vector_store.collection = experiment_collection
            chunk_count = await self._ingest_with_strategy(docs_path)
            self.vector_store.collection = original_collection

        # Run queries against experiment collection
        query_results = []
        for example in self.dataset.examples:
            query_text = example.get("query", "")
            if not query_text:
                continue

            try:
                vector = await get_embedding(query_text)
                results = await self.vector_store.search(
                    vector=vector,
                    top_k=top_k,
                    collection_name=experiment_collection,
                )
                retrieved_docs = [r.get("source_file", "") for r in results]
            except Exception as exc:
                log.warning("Query failed: %s", exc)
                retrieved_docs = []

            query_results.append(
                {
                    "query": query_text,
                    "retrieved_docs": retrieved_docs,
                    "expected_docs": example.get("expected_docs", []),
                }
            )

        metrics = self.metric_computer.compute_all(query_results, k=top_k)
        metrics["chunk_count"] = chunk_count
        metrics["strategy_name"] = self.strategy.__class__.__name__

        return metrics
