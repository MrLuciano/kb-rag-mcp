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
            {"id": "1", "score": 0.9, "text": "result 1"},
            {"id": "2", "score": 0.8, "text": "result 2"},
        ]
        sparse_results = [
            {"id": "2", "score": 0.95, "text": "result 2"},
            {"id": "3", "score": 0.85, "text": "result 3"},
        ]
        
        fused = hybrid_searcher._rrf_fusion(dense_results, sparse_results)
        
        assert len(fused) == 3
        assert all(r.get("fusion") == "rrf" for r in fused)
        result_ids = [r["id"] for r in fused]
        assert result_ids[0] == "2"

    @pytest.mark.asyncio
    async def test_rrf_fusion_empty_sparse(self, hybrid_searcher):
        dense_results = [
            {"id": "1", "score": 0.9},
            {"id": "2", "score": 0.8},
        ]
        sparse_results = []
        
        fused = hybrid_searcher._rrf_fusion(dense_results, sparse_results)
        
        assert len(fused) == 2
        assert fused[0]["id"] == "1"


class TestHybridSearchCLI:
    @pytest.mark.asyncio
    async def test_search_kb_has_hybrid_parameter(self):
        from kb_server.server import app
        
        tools = await app.list_tools()
        search_kb_tool = next(t for t in tools if t.name == "search_kb")
        
        assert "hybrid" in search_kb_tool.inputSchema["properties"]
        assert search_kb_tool.inputSchema["properties"]["hybrid"]["type"] == "boolean"


pytestmark = pytest.mark.fase12
