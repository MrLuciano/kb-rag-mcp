"""Unit tests for chunking strategies and ChunkingEngine.

FASE 25: Optimization Experiments
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kb_server.optimization.chunking_experiments import (
    ChunkingEngine,
    ChunkingStrategy,
    FixedStrategy,
    RecursiveStrategy,
    SemanticStrategy,
    create_strategy,
)

pytestmark = pytest.mark.fase25


# ── FixedStrategy tests ────────────────────────────────────────────


class TestFixedStrategy:
    def test_fixed_strategy_basic(self):
        """100-char text with chunk_size=30, overlap=10."""
        text = "a" * 100
        strategy = FixedStrategy(chunk_size=30, chunk_overlap=10)
        chunks = strategy.split(text)
        assert len(chunks) == 4
        assert all(len(c) >= 30 for c in chunks)
        assert chunks[0] == "a" * 30
        assert chunks[1] == "a" * 30

    def test_fixed_strategy_small_chunks_dropped(self):
        """Chunks shorter than 30 characters are dropped."""
        text = "short"
        strategy = FixedStrategy(chunk_size=30, chunk_overlap=10)
        chunks = strategy.split(text)
        assert chunks == []


# ── RecursiveStrategy tests ────────────────────────────────────────


class TestRecursiveStrategy:
    def test_recursive_strategy_split(self):
        """Paragraph boundaries are preserved with \\n\\n separator."""
        p1 = "Paragraph one. " * 10
        p2 = "Paragraph two. " * 10
        text = f"{p1}\n\n{p2}"
        strategy = RecursiveStrategy(chunk_size=100, chunk_overlap=10)
        chunks = strategy.split(text, "txt")
        assert len(chunks) >= 2
        assert "Paragraph one." in chunks[0]

    def test_recursive_strategy_fallback_on_import_error(self):
        """Manual fallback when RecursiveCharacterTextSplitter is
        unavailable.
        """
        with patch(
            "kb_server.optimization.chunking_experiments.log"
        ) as mock_log:
            with patch(
                "langchain_text_splitters.RecursiveCharacterTextSplitter",
                side_effect=ImportError("not available"),
            ):
                strategy = RecursiveStrategy(chunk_size=30, chunk_overlap=10)
                text = "a" * 100
                chunks = strategy.split(text)
                assert len(chunks) == 4
                assert all(len(c) >= 30 for c in chunks)
                mock_log.warning.assert_called_once()


# ── SemanticStrategy tests ─────────────────────────────────────────


class TestSemanticStrategy:
    def test_semantic_strategy_fallback(self):
        """Fallback to RecursiveStrategy when HybridChunker is unavailable."""
        with patch(
            "kb_server.optimization.chunking_experiments.log"
        ) as mock_log:
            with patch(
                "docling.chunking.HybridChunker",
                side_effect=ImportError("no docling"),
            ):
                strategy = SemanticStrategy(max_tokens=512)
                text = "a" * 100
                chunks = strategy.split(text)
                assert len(chunks) == 1
                assert chunks[0] == "a" * 100
                mock_log.warning.assert_called_once()


# ── create_strategy tests ──────────────────────────────────────────


class TestCreateStrategy:
    def test_create_strategy_fixed(self):
        """create_strategy returns FixedStrategy."""
        s = create_strategy("fixed", chunk_size=256)
        assert isinstance(s, FixedStrategy)
        assert s.chunk_size == 256

    def test_create_strategy_recursive(self):
        """create_strategy returns RecursiveStrategy."""
        s = create_strategy("recursive", chunk_size=512)
        assert isinstance(s, RecursiveStrategy)
        assert s.chunk_size == 512

    def test_create_strategy_semantic(self):
        """create_strategy returns SemanticStrategy."""
        s = create_strategy("semantic", max_tokens=256)
        assert isinstance(s, SemanticStrategy)
        assert s.max_tokens == 256

    def test_create_strategy_invalid(self):
        """Unknown strategy name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            create_strategy("invalid")


# ── ChunkingEngine tests ─────────────────────────────────────────────


class TestChunkingEngine:
    def test_chunking_engine_init(self):
        """Engine stores strategy, vector_store, and dataset."""
        strategy = FixedStrategy()
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        engine = ChunkingEngine(strategy, mock_store, mock_dataset)
        assert engine.strategy is strategy
        assert engine.vector_store is mock_store
        assert engine.dataset is mock_dataset

    def test_experiment_collection_suffix(self):
        """Experiment collection has _experiment suffix."""
        strategy = FixedStrategy()
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        engine = ChunkingEngine(strategy, mock_store, mock_dataset)
        assert engine._experiment_collection().endswith("_experiment")

    def test_run_experiment_empty_dataset(self):
        """Empty dataset returns zero metrics."""
        strategy = FixedStrategy()
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        mock_dataset.examples = []
        engine = ChunkingEngine(strategy, mock_store, mock_dataset)
        with patch("kb_server.collections.manager.CollectionManager"):
            with patch(
                "kb_server.embed_client.get_embedding",
            ):
                result = asyncio.run(
                    engine.run_experiment(Path("/tmp/empty"), clean=False)
                )
        assert result["recall_at_k"] == 0.0
        assert result["mrr"] == 0.0
        assert result["chunk_count"] == 0

    def test_run_experiment_with_results(self):
        """Dataset with one query produces metrics."""
        strategy = FixedStrategy()
        mock_store = MagicMock()
        mock_store.dim = 384
        mock_store.collection = "kb_docs"
        mock_dataset = MagicMock()
        mock_dataset.examples = [
            {
                "query": "test query",
                "expected_docs": ["doc1.txt"],
            }
        ]
        engine = ChunkingEngine(strategy, mock_store, mock_dataset)
        with patch("kb_server.collections.manager.CollectionManager"):
            with patch(
                "kb_server.embed_client.get_embedding",
                return_value=[0.1] * 384,
            ):
                mock_store.search.return_value = [{"source_file": "doc1.txt"}]
                result = asyncio.run(
                    engine.run_experiment(Path("/tmp/empty"), clean=False)
                )
        assert "recall_at_k" in result
        assert "mrr" in result
        assert "chunk_count" in result


# ── ChunkingStrategy ABC ─────────────────────────────────────────────


class TestChunkingStrategy:
    def test_chunking_strategy_abc(self):
        """ChunkingStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ChunkingStrategy()
