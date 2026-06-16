"""
Tests for cross-encoder reranker (FASE 12).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

# sentence_transformers may not be fully installed in CI (missing 'transformers'
# backend dependency). Inject a stub into sys.modules so that
# `from sentence_transformers import CrossEncoder` inside _load_model() resolves
# to our mock without triggering the real import chain.
_mock_st = MagicMock()
_mock_cross_encoder_cls = MagicMock()
_mock_st.CrossEncoder = _mock_cross_encoder_cls
sys.modules.setdefault("sentence_transformers", _mock_st)


def _make_mock_model(scores):
    """Return a fresh mock model that returns the given scores."""
    mock_model = MagicMock()
    mock_model.predict.return_value = scores
    return mock_model


class TestCrossEncoderReranker:
    @pytest.fixture
    def reranker(self):
        from kb_server.retrieval.reranker import CrossEncoderReranker

        r = CrossEncoderReranker()
        r.model = None  # ensure clean state
        return r

    @pytest.mark.asyncio
    async def test_rerank_updates_scores(self, reranker):
        """Test that reranker updates result scores."""
        mock_model = _make_mock_model([0.9, 0.7, 0.5])
        _mock_cross_encoder_cls.return_value = mock_model

        results = [
            {"id": "1", "text": "doc 1", "score": 0.5},
            {"id": "2", "text": "doc 2", "score": 0.6},
            {"id": "3", "text": "doc 3", "score": 0.8},
        ]

        reranked = await reranker.rerank("test query", results)

        assert len(reranked) == 3
        assert reranked[0]["score"] == 0.9
        assert reranked[1]["score"] == 0.7
        assert reranked[2]["score"] == 0.5
        assert all(r["reranked"] for r in reranked)

    @pytest.mark.asyncio
    async def test_rerank_reorders_results(self, reranker):
        """Test that reranker reorders results by new scores."""
        mock_model = _make_mock_model([0.5, 0.9, 0.7])
        _mock_cross_encoder_cls.return_value = mock_model

        results = [
            {"id": "1", "text": "doc 1"},
            {"id": "2", "text": "doc 2"},
            {"id": "3", "text": "doc 3"},
        ]

        reranked = await reranker.rerank("test query", results)

        assert reranked[0]["id"] == "2"
        assert reranked[1]["id"] == "3"
        assert reranked[2]["id"] == "1"

    @pytest.mark.asyncio
    async def test_rerank_respects_top_k(self, reranker):
        """Test that reranker respects top_k parameter."""
        mock_model = _make_mock_model([0.9, 0.8, 0.7, 0.6, 0.5])
        _mock_cross_encoder_cls.return_value = mock_model

        results = [{"id": str(i), "text": f"doc {i}"} for i in range(5)]

        reranked = await reranker.rerank("test query", results, top_k=3)

        assert len(reranked) == 3
        assert reranked[0]["score"] == 0.9
        assert reranked[2]["score"] == 0.7

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self, reranker):
        """Test that reranker handles empty results gracefully."""
        reranked = await reranker.rerank("test query", [])
        assert reranked == []

    @pytest.mark.asyncio
    async def test_rerank_lazy_loads_model(self, reranker):
        """Test that model is lazy loaded on first use."""
        assert reranker.model is None

        mock_model = _make_mock_model([0.9])
        _mock_cross_encoder_cls.reset_mock()
        _mock_cross_encoder_cls.return_value = mock_model

        await reranker.rerank("query", [{"id": "1", "text": "doc"}])

        assert _mock_cross_encoder_cls.called
        assert reranker.model is not None


class TestRerankerIntegration:
    @pytest.mark.asyncio
    async def test_search_kb_with_rerank(self):
        """Test that search_kb properly invokes reranker."""
        from kb_server.server import _search_kb
        from unittest.mock import AsyncMock, patch

        # Mock dependencies
        with patch("kb_server.server.get_embedding", return_value=[0.1] * 768):
            with patch("kb_server.server.store") as mock_store:
                mock_store.search = AsyncMock(
                    return_value=[
                        {
                            "id": "1",
                            "text": "result 1",
                            "score": 0.8,
                            "source_file": "test.pdf",
                            "file_type": "pdf",
                            "chunk_id": "1",
                        },
                    ]
                )

                result = await _search_kb(
                    {
                        "query": "test",
                        "top_k": 5,
                        "rerank": True,
                    }
                )

                assert len(result) == 1
                assert "Results for:" in result[0].text


pytestmark = pytest.mark.fase12
