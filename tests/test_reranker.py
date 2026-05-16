"""
Tests for cross-encoder reranker (FASE 12).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))


class TestCrossEncoderReranker:
    @pytest.fixture
    def reranker(self):
        from server.retrieval.reranker import CrossEncoderReranker
        return CrossEncoderReranker()

    @pytest.mark.asyncio
    @patch("server.retrieval.reranker.CrossEncoder")
    async def test_rerank_updates_scores(self, mock_cross_encoder, reranker):
        """Test that reranker updates result scores."""
        # Mock cross-encoder model
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.7, 0.5]
        mock_cross_encoder.return_value = mock_model
        
        results = [
            {"id": "1", "text": "doc 1", "score": 0.5},
            {"id": "2", "text": "doc 2", "score": 0.6},
            {"id": "3", "text": "doc 3", "score": 0.8},
        ]
        
        reranked = await reranker.rerank("test query", results)
        
        # Should return all results with new scores
        assert len(reranked) == 3
        
        # Scores should be updated from cross-encoder
        assert reranked[0]["score"] == 0.9
        assert reranked[1]["score"] == 0.7
        assert reranked[2]["score"] == 0.5
        
        # Results should be marked as reranked
        assert all(r["reranked"] for r in reranked)

    @pytest.mark.asyncio
    @patch("server.retrieval.reranker.CrossEncoder")
    async def test_rerank_reorders_results(self, mock_cross_encoder, reranker):
        """Test that reranker reorders results by new scores."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5, 0.9, 0.7]
        mock_cross_encoder.return_value = mock_model
        
        results = [
            {"id": "1", "text": "doc 1"},
            {"id": "2", "text": "doc 2"},
            {"id": "3", "text": "doc 3"},
        ]
        
        reranked = await reranker.rerank("test query", results)
        
        # Should be reordered by cross-encoder scores
        assert reranked[0]["id"] == "2"
        assert reranked[1]["id"] == "3"
        assert reranked[2]["id"] == "1"

    @pytest.mark.asyncio
    @patch("server.retrieval.reranker.CrossEncoder")
    async def test_rerank_respects_top_k(self, mock_cross_encoder, reranker):
        """Test that reranker respects top_k parameter."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        mock_cross_encoder.return_value = mock_model
        
        results = [{"id": str(i), "text": f"doc {i}"} for i in range(5)]
        
        reranked = await reranker.rerank("test query", results, top_k=3)
        
        # Should only return top 3
        assert len(reranked) == 3
        assert reranked[0]["score"] == 0.9
        assert reranked[2]["score"] == 0.7

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self, reranker):
        """Test that reranker handles empty results gracefully."""
        reranked = await reranker.rerank("test query", [])
        assert reranked == []

    @pytest.mark.asyncio
    @patch("server.retrieval.reranker.CrossEncoder")
    async def test_rerank_lazy_loads_model(self, mock_cross_encoder, reranker):
        """Test that model is lazy loaded on first use."""
        assert reranker.model is None
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9]
        mock_cross_encoder.return_value = mock_model
        
        await reranker.rerank("query", [{"id": "1", "text": "doc"}])
        
        # Model should be loaded
        assert mock_cross_encoder.called
        assert reranker.model is not None


class TestRerankerIntegration:
    @pytest.mark.asyncio
    async def test_search_kb_with_rerank(self):
        """Test that search_kb properly invokes reranker."""
        from server.server import _search_kb
        from unittest.mock import AsyncMock, patch
        
        # Mock dependencies
        with patch("server.server.get_embedding", return_value=[0.1] * 768):
            with patch("server.server.store") as mock_store:
                mock_store.search = AsyncMock(return_value=[
                    {"id": "1", "text": "result 1", "score": 0.8, 
                     "source_file": "test.pdf", "file_type": "pdf",
                     "chunk_id": "1"},
                ])
                
                with patch("server.retrieval.reranker.CrossEncoder"):
                    result = await _search_kb({
                        "query": "test",
                        "top_k": 5,
                        "rerank": True,
                    })
                    
                    # Should return results
                    assert len(result) == 1
                    assert "Resultados" in result[0].text


pytestmark = pytest.mark.fase12
