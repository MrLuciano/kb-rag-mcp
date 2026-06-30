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
        dense_results = [
            {"id": "1", "chunk_id": "1", "score": 0.9, "text": "doc"}
        ]
        sparse_results = [
            {"id": "1", "chunk_id": "1", "score": 0.85, "text": "doc"}
        ]
        mock_vector_store.search = AsyncMock(return_value=dense_results)
        mock_vector_store.search_sparse = AsyncMock(
            return_value=sparse_results
        )

        sparse_vec = {42: 0.5, 99: 0.8}
        with patch.object(
            hybrid_searcher,
            "generate_sparse_vector",
            new=AsyncMock(return_value=sparse_vec),
        ):
            with patch.object(
                hybrid_searcher,
                "_rrf_fusion",
                wraps=hybrid_searcher._rrf_fusion,
            ) as mock_rrf:
                await hybrid_searcher.search(
                    vector_store=mock_vector_store,
                    query_vector=[0.1] * 768,
                    query_text="test query",
                    top_k=5,
                )
                mock_vector_store.search_sparse.assert_called_once()
                call_kwargs = mock_rrf.call_args
                assert (
                    len(call_kwargs.kwargs.get("sparse_results", [])) > 0
                ), "sparse_results passed to _rrf_fusion must be non-empty"

    @pytest.mark.asyncio
    async def test_falls_back_to_dense_when_sparse_empty(
        self, hybrid_searcher
    ):
        """When sparse vector is empty, only dense results are returned."""
        mock_vector_store = AsyncMock()
        dense_results = [
            {"id": "1", "chunk_id": "1", "score": 0.9, "text": "doc"}
        ]
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


class TestMergeMultiCollectionResults:
    """Tests for merge_multi_collection_results and _min_max_normalize."""

    def test_min_max_normalize_identity(self):
        from kb_server.retrieval.hybrid_search import _min_max_normalize

        results = [
            {"chunk_id": "a", "score": 0.5},
            {"chunk_id": "b", "score": 0.8},
            {"chunk_id": "c", "score": 0.3},
        ]
        normalized = _min_max_normalize(results)
        scores = [r["score"] for r in normalized]
        assert max(scores) == 1.0
        assert min(scores) == 0.0

    def test_min_max_normalize_single_result(self):
        from kb_server.retrieval.hybrid_search import _min_max_normalize

        results = [{"chunk_id": "a", "score": 0.7}]
        normalized = _min_max_normalize(results)
        assert normalized[0]["score"] == 1.0

    def test_min_max_normalize_identical_scores(self):
        from kb_server.retrieval.hybrid_search import _min_max_normalize

        results = [
            {"chunk_id": "a", "score": 0.5},
            {"chunk_id": "b", "score": 0.5},
        ]
        normalized = _min_max_normalize(results)
        assert all(r["score"] == 1.0 for r in normalized)

    def test_min_max_normalize_empty_list(self):
        from kb_server.retrieval.hybrid_search import _min_max_normalize

        assert _min_max_normalize([]) == []

    def test_merge_multi_empty_collections(self):
        from kb_server.retrieval.hybrid_search import (
            merge_multi_collection_results,
        )

        result = merge_multi_collection_results({}, top_k=5)
        assert result == []

    def test_merge_multi_single_collection(self):
        from kb_server.retrieval.hybrid_search import (
            merge_multi_collection_results,
        )

        per_collection = {
            "kb_main": [
                {"chunk_id": "a", "score": 0.9, "source_file": "doc1.md"},
                {"chunk_id": "b", "score": 0.7, "source_file": "doc1.md"},
            ],
        }
        result = merge_multi_collection_results(per_collection, top_k=5)
        assert len(result) == 2
        assert result[0]["chunk_id"] == "a"

    def test_merge_multi_dedup(self):
        from kb_server.retrieval.hybrid_search import (
            merge_multi_collection_results,
        )

        per_collection = {
            "kb_hr": [
                {"chunk_id": "c1", "score": 0.8, "source_file": "hr.md"},
                {"chunk_id": "c2", "score": 0.6, "source_file": "hr.md"},
            ],
            "kb_eng": [
                {"chunk_id": "c1", "score": 0.7, "source_file": "eng.md"},
            ],
        }
        result = merge_multi_collection_results(per_collection, top_k=5)
        chunk_ids = [r["chunk_id"] for r in result]
        assert chunk_ids.count("c1") == 1
        assert len(result) == 2

    def test_merge_multi_top_k_enforced(self):
        from kb_server.retrieval.hybrid_search import (
            merge_multi_collection_results,
        )

        per_collection = {
            "kb_a": [
                {
                    "chunk_id": f"c{i}",
                    "score": 0.9 - i * 0.1,
                    "source_file": f"doc{i}.md",
                }
                for i in range(5)
            ],
            "kb_b": [
                {
                    "chunk_id": f"d{i}",
                    "score": 0.8 - i * 0.1,
                    "source_file": f"doc{i}.md",
                }
                for i in range(5)
            ],
        }
        result = merge_multi_collection_results(per_collection, top_k=3)
        assert len(result) == 3

    def test_merge_multi_dedup_different_scores(self):
        from kb_server.retrieval.hybrid_search import (
            merge_multi_collection_results,
        )

        per_collection = {
            "kb_a": [
                {"chunk_id": "c1", "score": 0.5, "source_file": "a.md"},
            ],
            "kb_b": [
                {"chunk_id": "c1", "score": 0.9, "source_file": "b.md"},
            ],
        }
        result = merge_multi_collection_results(per_collection, top_k=5)
        assert len(result) == 1
        assert result[0]["chunk_id"] == "c1"

    def test_merge_multi_rrf_fusion_aggregates_scores(self):
        """Duplicate chunk_ids across collections accumulate RRF scores."""
        from kb_server.retrieval.hybrid_search import (
            merge_multi_collection_results,
        )

        per_collection = {
            "kb_x": [
                {"chunk_id": "c1", "score": 0.9, "source_file": "x.md"},
            ],
            "kb_y": [
                {"chunk_id": "c1", "score": 0.8, "source_file": "y.md"},
            ],
        }
        result = merge_multi_collection_results(per_collection, top_k=5)
        assert len(result) == 1
        # RRF scores should be aggregated: 1/(60+1) + 1/(60+1) = 2/61
        assert abs(result[0]["score"] - 2.0 / 61.0) < 1e-9


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
        assert (
            search_kb_tool.inputSchema["properties"]["hybrid"]["type"]
            == "boolean"
        )


pytestmark = pytest.mark.fase12
