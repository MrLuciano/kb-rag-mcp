"""
Tests for hybrid search (FASE 12).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHybridSearcher:
    @pytest.fixture
    def hybrid_searcher(self):
        from kb_server.retrieval.hybrid_search import HybridSearcher
        return HybridSearcher()

    @pytest.mark.asyncio
    async def test_rrf_fusion_combines_results(self, hybrid_searcher):
        dense_results = [
            {"id": "1", "chunk_id": "1", "score": 0.9, "text": "result 1"},
            {"id": "2", "chunk_id": "2", "score": 0.8, "text": "result 2"},
        ]
        sparse_results = [
            {"id": "2", "chunk_id": "2", "score": 0.95, "text": "result 2"},
            {"id": "3", "chunk_id": "3", "score": 0.85, "text": "result 3"},
        ]
        
        fused = hybrid_searcher._rrf_fusion(dense_results, sparse_results)
        
        assert len(fused) == 3
        assert all(r.get("fusion") == "rrf" for r in fused)
        result_ids = [r["chunk_id"] for r in fused]
        assert result_ids[0] == "2"

    @pytest.mark.asyncio
    async def test_rrf_fusion_empty_sparse(self, hybrid_searcher):
        dense_results = [
            {"id": "1", "chunk_id": "1", "score": 0.9},
            {"id": "2", "chunk_id": "2", "score": 0.8},
        ]
        sparse_results = []
        
        fused = hybrid_searcher._rrf_fusion(dense_results, sparse_results)
        
        assert len(fused) == 2
        assert fused[0]["chunk_id"] == "1"

    @pytest.mark.asyncio
    async def test_sparse_path_exercised(self, hybrid_searcher):
        """Proves sparse search is called and RRF receives non-empty sparse results."""
        mock_vector_store = AsyncMock()
        dense_results = [{"id": "1", "chunk_id": "1", "score": 0.9, "text": "doc"}]
        sparse_results = [{"id": "1", "chunk_id": "1", "score": 0.85, "text": "doc"}]
        mock_vector_store.search = AsyncMock(return_value=dense_results)
        mock_vector_store.search_sparse = AsyncMock(return_value=sparse_results)

        sparse_vec = {42: 0.5, 99: 0.8}
        with patch.object(
            hybrid_searcher,
            "generate_sparse_vector",
            new=AsyncMock(return_value=sparse_vec),
        ):
            with patch.object(
                hybrid_searcher, "_rrf_fusion", wraps=hybrid_searcher._rrf_fusion
            ) as mock_rrf:
                await hybrid_searcher.search(
                    vector_store=mock_vector_store,
                    query_vector=[0.1] * 768,
                    query_text="test query",
                    top_k=5,
                )
                mock_vector_store.search_sparse.assert_called_once()
                call_kwargs = mock_rrf.call_args
                assert len(call_kwargs.kwargs.get("sparse_results", [])) > 0, \
                    "sparse_results passed to _rrf_fusion must be non-empty"

    @pytest.mark.asyncio
    async def test_falls_back_to_dense_when_sparse_empty(self, hybrid_searcher):
        """When sparse vector is empty, only dense results are returned."""
        mock_vector_store = AsyncMock()
        dense_results = [{"id": "1", "chunk_id": "1", "score": 0.9, "text": "doc"}]
        mock_vector_store.search = AsyncMock(return_value=dense_results)
        mock_vector_store.search_sparse = AsyncMock(return_value=[])

        with patch.object(
            hybrid_searcher,
            "generate_sparse_vector",
            new=AsyncMock(return_value={}),
        ):
            results = await hybrid_searcher.search(
                vector_store=mock_vector_store,
                query_vector=[0.1] * 768,
                query_text="test query",
                top_k=5,
            )
            mock_vector_store.search_sparse.assert_not_called()
            assert results == dense_results[:5]


class TestHybridSearchCLI:
    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="app.list_tools() is a decorator factory, not a tools list; "
        "requires MCP server introspection API"
    )
    async def test_search_kb_has_hybrid_parameter(self):
        from kb_server.server import app

        tools = app.list_tools()
        search_kb_tool = next(t for t in tools if t.name == "search_kb")
        
        assert "hybrid" in search_kb_tool.inputSchema["properties"]
        assert search_kb_tool.inputSchema["properties"]["hybrid"]["type"] == "boolean"


pytestmark = pytest.mark.fase12
