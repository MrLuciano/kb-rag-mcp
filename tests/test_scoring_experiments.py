"""Unit tests for scoring variants and ScoringEngine.

FASE 25: Optimization Experiments
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from kb_server.optimization.scoring_experiments import (
    DenseOnlyVariant,
    HybridVariant,
    RerankedVariant,
    ScoringEngine,
    ScoringVariant,
    create_variant,
    _init_distance_metrics,
    DISTANCE_METRICS,
)

pytestmark = pytest.mark.fase25


# ── DenseOnlyVariant tests ────────────────────────────────────────


class TestDenseOnlyVariant:
    @pytest.mark.asyncio
    async def test_dense_only_variant_search(self):
        """Mock vector_store.search returns results, verify variant
        returns them unchanged."""
        mock_store = AsyncMock()
        mock_store.search.return_value = [
            {"chunk_id": "1", "source_file": "a.pdf"}
        ]
        variant = DenseOnlyVariant(distance_metric="COSINE")
        with patch(
            "kb_server.optimization.scoring_experiments.get_embedding",
            return_value=[0.1, 0.2],
        ):
            results = await variant.search(
                query="test", vector_store=mock_store, top_k=5
            )
        assert results == [{"chunk_id": "1", "source_file": "a.pdf"}]
        mock_store.search.assert_awaited_once()

    def test_dense_only_variant_distance_metric(self):
        """Verify distance_metric attribute is stored and reported."""
        variant = DenseOnlyVariant(distance_metric="DOT")
        assert variant.distance_metric == "DOT"


# ── HybridVariant tests ───────────────────────────────────────────


class TestHybridVariant:
    @pytest.mark.asyncio
    async def test_hybrid_variant_search(self):
        """Mock HybridSearcher.search returns results, verify variant
        calls it with correct weights."""
        mock_hybrid = MagicMock()
        mock_hybrid.search = AsyncMock(
            return_value=[{"chunk_id": "1", "source_file": "a.pdf"}]
        )
        mock_hybrid.dense_weight = 0.7
        mock_hybrid.sparse_weight = 0.3
        mock_hybrid.rrf_k = 60

        variant = HybridVariant(
            dense_weight=0.7, sparse_weight=0.3, rrf_k=60
        )
        with patch(
            "kb_server.optimization.scoring_experiments.get_hybrid_searcher",
            return_value=mock_hybrid,
        ), patch(
            "kb_server.optimization.scoring_experiments.get_embedding",
            return_value=[0.1, 0.2],
        ):
            results = await variant.search(
                query="test", vector_store=MagicMock(), top_k=5
            )
        assert results == [{"chunk_id": "1", "source_file": "a.pdf"}]
        mock_hybrid.search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_hybrid_variant_custom_weights(self):
        """dense_weight=0.8, sparse_weight=0.2 passed correctly."""
        captured = {}

        async def _search(*args, **kwargs):
            # Capture weights during search call (before finally restores)
            captured["dense"] = mock_hybrid.dense_weight
            captured["sparse"] = mock_hybrid.sparse_weight
            return []

        mock_hybrid = MagicMock()
        mock_hybrid.search = _search
        mock_hybrid.dense_weight = 0.7
        mock_hybrid.sparse_weight = 0.3
        mock_hybrid.rrf_k = 60

        variant = HybridVariant(
            dense_weight=0.8, sparse_weight=0.2, rrf_k=60
        )
        with patch(
            "kb_server.optimization.scoring_experiments.get_hybrid_searcher",
            return_value=mock_hybrid,
        ), patch(
            "kb_server.optimization.scoring_experiments.get_embedding",
            return_value=[0.1, 0.2],
        ):
            await variant.search(
                query="test", vector_store=MagicMock(), top_k=5
            )
        assert captured["dense"] == 0.8
        assert captured["sparse"] == 0.2


# ── RerankedVariant tests ─────────────────────────────────────────


class TestRerankedVariant:
    @pytest.mark.asyncio
    async def test_reranked_variant_search(self):
        """Mock base variant + mock reranker, verify results are reranked."""
        base = AsyncMock()
        base.search.return_value = [
            {"chunk_id": "1", "source_file": "a.pdf", "text": "foo"},
            {"chunk_id": "2", "source_file": "b.pdf", "text": "bar"},
        ]
        mock_reranker = MagicMock()
        mock_reranker.rerank = AsyncMock(
            return_value=[
                {"chunk_id": "2", "source_file": "b.pdf", "score": 0.9}
            ]
        )
        mock_reranker._load_model = MagicMock()

        variant = RerankedVariant(base_variant=base)
        with patch(
            "kb_server.optimization.scoring_experiments.get_reranker",
            return_value=mock_reranker,
        ):
            results = await variant.search(
                query="test", vector_store=MagicMock(), top_k=1
            )
        assert results == [
            {"chunk_id": "2", "source_file": "b.pdf", "score": 0.9}
        ]
        base.search.assert_awaited_once()
        mock_reranker.rerank.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reranked_variant_warmup(self):
        """Verify _warmup is called before experiment (check log or mock)."""
        mock_reranker = MagicMock()
        mock_reranker._load_model = MagicMock()
        base = AsyncMock()
        base.search.return_value = []

        variant = RerankedVariant(base_variant=base)
        with patch(
            "kb_server.optimization.scoring_experiments.get_reranker",
            return_value=mock_reranker,
        ):
            await variant.search(
                query="test", vector_store=MagicMock(), top_k=5
            )
        mock_reranker._load_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_reranked_variant_disabled(self):
        """Base variant results returned as-is if reranker fails."""
        base = AsyncMock()
        base.search.return_value = [
            {"chunk_id": "1", "source_file": "a.pdf"}
        ]
        mock_reranker = MagicMock()
        mock_reranker.rerank = AsyncMock(side_effect=RuntimeError("boom"))
        mock_reranker._load_model = MagicMock()

        variant = RerankedVariant(base_variant=base)
        with patch(
            "kb_server.optimization.scoring_experiments.get_reranker",
            return_value=mock_reranker,
        ):
            results = await variant.search(
                query="test", vector_store=MagicMock(), top_k=5
            )
        assert results == [{"chunk_id": "1", "source_file": "a.pdf"}]


# ── create_variant tests ──────────────────────────────────────────


class TestCreateVariant:
    def test_create_variant_dense_only(self):
        """create_variant('dense_only') returns DenseOnlyVariant."""
        v = create_variant("dense_only")
        assert isinstance(v, DenseOnlyVariant)

    def test_create_variant_hybrid(self):
        """create_variant('hybrid') returns HybridVariant."""
        v = create_variant("hybrid")
        assert isinstance(v, HybridVariant)
        assert v.dense_weight == 0.7
        assert v.sparse_weight == 0.3

    def test_create_variant_reranked(self):
        """create_variant('reranked', base='dense_only') returns
        RerankedVariant with DenseOnlyVariant base."""
        v = create_variant("reranked", base="dense_only")
        assert isinstance(v, RerankedVariant)
        assert isinstance(v.base_variant, DenseOnlyVariant)

    def test_create_variant_invalid(self):
        """create_variant('unknown') raises ValueError with 'unknown'."""
        with pytest.raises(ValueError) as exc_info:
            create_variant("unknown")
        assert "unknown" in str(exc_info.value).lower()


# ── ScoringEngine tests ─────────────────────────────────────────


class TestScoringEngine:
    def test_scoring_engine_init(self):
        """ScoringEngine(variant, mock_store, mock_dataset) stores
        dependencies."""
        variant = MagicMock(spec=ScoringVariant)
        store = MagicMock()
        dataset = MagicMock()
        engine = ScoringEngine(
            variant=variant, vector_store=store, dataset=dataset
        )
        assert engine.variant is variant
        assert engine.vector_store is store
        assert engine.dataset is dataset

    @pytest.mark.asyncio
    async def test_scoring_engine_run_experiment(self):
        """Mock dataset with 2 examples, mock search returns results,
        verify metrics dict returned with recall_at_k, mrr, ndcg_at_k."""
        variant = AsyncMock()
        variant.search.return_value = [
            {"chunk_id": "1", "source_file": "doc1.pdf"}
        ]
        variant.__class__.__name__ = "DenseOnlyVariant"

        store = MagicMock()
        dataset = MagicMock()
        dataset.examples = [
            {
                "query": "q1",
                "expected_docs": ["doc1.pdf"],
                "expected_answer": "a1",
            },
            {
                "query": "q2",
                "expected_docs": ["doc2.pdf"],
                "expected_answer": "a2",
            },
        ]

        engine = ScoringEngine(
            variant=variant, vector_store=store, dataset=dataset
        )
        with patch(
            "kb_server.optimization.scoring_experiments.get_embedding",
            return_value=[0.1, 0.2],
        ):
            result = await engine.run_experiment(top_k=5)

        assert "recall_at_k" in result
        assert "mrr" in result
        assert "ndcg_at_k" in result
        assert result["variant_name"] == "DenseOnlyVariant"
        assert result["distance_metric"] == "COSINE"
        assert result["reranker_enabled"] is False
        assert variant.search.await_count == 2


# ── DISTANCE_METRICS tests ────────────────────────────────────────


class TestDistanceMetrics:
    def test_distance_metrics_populated(self):
        """_init_distance_metrics populates DISTANCE_METRICS."""
        _init_distance_metrics()
        assert "COSINE" in DISTANCE_METRICS
        assert "DOT" in DISTANCE_METRICS
        assert "EUCLID" in DISTANCE_METRICS
        assert "MANHATTAN" in DISTANCE_METRICS

    def test_distance_metrics_idempotent(self):
        """Calling _init_distance_metrics twice is safe."""
        _init_distance_metrics()
        _init_distance_metrics()
        assert len(DISTANCE_METRICS) == 4
