"""Tests for HybridSearcher._rrf_fusion — CR-03 regression test."""
import pytest
import sys
from pathlib import Path

# hybrid_search imports fastembed at module level; stub it out before import
import types as _types
_fastembed = _types.ModuleType("fastembed")
class _SparseTextEmbedding:
    pass
_fastembed.SparseTextEmbedding = _SparseTextEmbedding
sys.modules.setdefault("fastembed", _fastembed)

from server.retrieval.hybrid_search import HybridSearcher


def make_result(chunk_id: str, score: float) -> dict:
    """Build a result dict matching VectorStore.search() output format."""
    return {
        "chunk_id": chunk_id,
        "score": score,
        "text": "sample",
        "source_file": "doc.pdf",
        "file_type": "pdf",
        "product": "prod-a",
        "doc_type": "document",
        "page": 1,
        "chunk_index": 0,
    }


class TestRRFFusion:
    def setup_method(self):
        self.hs = HybridSearcher()

    def test_rrf_fusion_uses_chunk_id_key(self):
        """_rrf_fusion must read 'chunk_id', not 'id', matching VectorStore output."""
        dense = [make_result("abc", 0.9), make_result("def", 0.7)]
        sparse = [make_result("def", 0.8), make_result("ghi", 0.6)]

        # Must not raise KeyError
        fused = self.hs._rrf_fusion(dense_results=dense, sparse_results=sparse)

        ids = [r["chunk_id"] for r in fused]
        assert "abc" in ids
        assert "def" in ids
        assert "ghi" in ids

    def test_rrf_fusion_higher_ranked_scores_more(self):
        """Result appearing in both lists gets higher fused score than result in one."""
        dense = [make_result("both", 0.9), make_result("dense_only", 0.8)]
        sparse = [make_result("both", 0.9), make_result("sparse_only", 0.7)]

        fused = self.hs._rrf_fusion(dense_results=dense, sparse_results=sparse)

        score_map = {r["chunk_id"]: r["score"] for r in fused}
        assert score_map["both"] > score_map["dense_only"]
        assert score_map["both"] > score_map["sparse_only"]

    def test_rrf_fusion_empty_sparse_returns_dense_order(self):
        """With empty sparse, fusion order matches dense order."""
        dense = [make_result("a", 0.9), make_result("b", 0.8), make_result("c", 0.7)]
        fused = self.hs._rrf_fusion(dense_results=dense, sparse_results=[])

        ids = [r["chunk_id"] for r in fused]
        assert ids == ["a", "b", "c"]

    def test_rrf_fusion_marks_results_as_fused(self):
        """Fused results have fusion='rrf' marker."""
        dense = [make_result("x", 0.9)]
        fused = self.hs._rrf_fusion(dense_results=dense, sparse_results=[])
        assert fused[0]["fusion"] == "rrf"
