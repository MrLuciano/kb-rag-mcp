"""
Unit tests for kb_server/retrieval/hybrid_search.py — HybridSearcher.

Covers _load_sparse_model, generate_sparse_vector, search, _rrf_fusion,
and get_hybrid_searcher singleton.

fastembed / tokenizers are not installed in CI — stubbed before any import.
"""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Stub missing deps before any imports
for _mod in (
    "tokenizers",
    "fastembed",
    "fastembed.sparse",
    "fastembed.sparse.bm25",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import kb_server.retrieval.hybrid_search as hs_module
from kb_server.retrieval.hybrid_search import HybridSearcher, get_hybrid_searcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(chunk_id: str, score: float = 0.5) -> dict:
    return {
        "chunk_id": chunk_id,
        "score": score,
        "text": f"text for {chunk_id}",
        "source_file": "doc.md",
    }


def _make_store(
    dense_results: list[dict] | None = None,
    sparse_results: list[dict] | None = None,
) -> MagicMock:
    store = MagicMock()
    store.search = AsyncMock(return_value=dense_results or [])
    store.search_sparse = AsyncMock(return_value=sparse_results or [])
    return store


# ---------------------------------------------------------------------------
# _load_sparse_model (lines 51-62)
# ---------------------------------------------------------------------------


def test_load_sparse_model_initializes_bm25():
    """_load_sparse_model() sets sparse_model when called."""
    searcher = HybridSearcher()
    assert searcher.sparse_model is None

    fake_model = MagicMock()
    # Patch SparseTextEmbedding at the module level where it's used
    with patch.object(
        hs_module,
        "SparseTextEmbedding",
        return_value=fake_model,
    ):
        searcher._load_sparse_model()

    assert searcher.sparse_model is fake_model


def test_load_sparse_model_is_idempotent():
    """Second call to _load_sparse_model() is a no-op (already loaded)."""
    searcher = HybridSearcher()
    fake_model = MagicMock()
    searcher.sparse_model = fake_model  # pre-loaded

    with patch.object(hs_module, "SparseTextEmbedding") as mock_cls:
        searcher._load_sparse_model()
        mock_cls.assert_not_called()

    # Model unchanged
    assert searcher.sparse_model is fake_model


def test_load_sparse_model_propagates_exception():
    """If SparseTextEmbedding raises, _load_sparse_model re-raises."""
    searcher = HybridSearcher()
    with patch.object(
        hs_module, "SparseTextEmbedding", side_effect=RuntimeError("no model")
    ):
        with pytest.raises(RuntimeError, match="no model"):
            searcher._load_sparse_model()

    # Model must remain None after failure
    assert searcher.sparse_model is None


# ---------------------------------------------------------------------------
# get_hybrid_searcher singleton (lines 237-239)
# ---------------------------------------------------------------------------


def test_get_hybrid_searcher_returns_singleton():
    """get_hybrid_searcher() returns the same object on repeated calls."""
    # Reset module-level singleton
    hs_module._hybrid_searcher = None
    a = get_hybrid_searcher()
    b = get_hybrid_searcher()
    assert a is b


def test_get_hybrid_searcher_creates_instance():
    """get_hybrid_searcher() returns a HybridSearcher instance."""
    hs_module._hybrid_searcher = None
    result = get_hybrid_searcher()
    assert isinstance(result, HybridSearcher)


# ---------------------------------------------------------------------------
# generate_sparse_vector (lines 70-96)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_sparse_vector_returns_dict():
    """generate_sparse_vector returns a dict with int keys and float values."""
    searcher = HybridSearcher()

    sparse_embedding = MagicMock()
    sparse_embedding.indices = [1, 5, 10]
    sparse_embedding.values = [0.8, 0.3, 0.6]

    fake_model = MagicMock()
    fake_model.embed.return_value = [sparse_embedding]
    searcher.sparse_model = fake_model

    result = await searcher.generate_sparse_vector("hello world")

    assert isinstance(result, dict)
    assert result == {1: 0.8, 5: 0.3, 10: 0.6}


@pytest.mark.asyncio
async def test_generate_sparse_vector_empty_on_exception():
    """generate_sparse_vector returns {} when embed raises (non-fatal)."""
    searcher = HybridSearcher()

    fake_model = MagicMock()
    fake_model.embed.side_effect = RuntimeError("embed failed")
    searcher.sparse_model = fake_model

    result = await searcher.generate_sparse_vector("hello")
    assert result == {}


@pytest.mark.asyncio
async def test_generate_sparse_vector_accepts_dict_format():
    """generate_sparse_vector handles sparse vec already as dict."""
    searcher = HybridSearcher()

    fake_model = MagicMock()
    fake_model.embed.return_value = [{3: 0.5, 7: 0.9}]
    searcher.sparse_model = fake_model

    result = await searcher.generate_sparse_vector("test")
    assert result == {3: 0.5, 7: 0.9}


# ---------------------------------------------------------------------------
# search() (lines 98-169)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_combines_dense_and_sparse_results():
    """search() calls both dense and sparse search and returns fused list."""
    searcher = HybridSearcher()
    dense = [_make_result("d1"), _make_result("d2")]
    sparse = [_make_result("s1"), _make_result("d1")]
    store = _make_store(dense, sparse)

    # Patch generate_sparse_vector to return non-empty sparse vector
    searcher.generate_sparse_vector = AsyncMock(return_value={1: 0.5})

    results = await searcher.search(store, [0.1, 0.2], "query", top_k=10)

    store.search.assert_called_once()
    store.search_sparse.assert_called_once()
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_search_dense_only_when_sparse_empty():
    """search() skips sparse search when sparse vector is empty."""
    searcher = HybridSearcher()
    dense = [_make_result("d1"), _make_result("d2"), _make_result("d3")]
    store = _make_store(dense, [])

    searcher.generate_sparse_vector = AsyncMock(return_value={})

    results = await searcher.search(store, [0.1], "query", top_k=2)

    # search_sparse should NOT be called
    store.search_sparse.assert_not_called()
    # Dense results returned (up to top_k)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_rrf_fusion_deduplicates():
    """Same chunk_id in dense and sparse is not duplicated in output."""
    searcher = HybridSearcher()
    shared_id = "shared-chunk"
    dense = [_make_result(shared_id)]
    sparse = [_make_result(shared_id)]
    store = _make_store(dense, sparse)

    searcher.generate_sparse_vector = AsyncMock(return_value={1: 0.5})

    results = await searcher.search(store, [0.1], "query", top_k=10)

    chunk_ids = [r["chunk_id"] for r in results]
    assert chunk_ids.count(shared_id) == 1


@pytest.mark.asyncio
async def test_search_rrf_fusion_scores_are_float():
    """All score values in fused results are floats."""
    searcher = HybridSearcher()
    dense = [_make_result("d1"), _make_result("d2")]
    sparse = [_make_result("s1")]
    store = _make_store(dense, sparse)

    searcher.generate_sparse_vector = AsyncMock(return_value={1: 0.5})

    results = await searcher.search(store, [0.1], "query", top_k=10)

    for r in results:
        assert isinstance(r["score"], float)


@pytest.mark.asyncio
async def test_search_respects_top_k():
    """search() returns at most top_k results."""
    searcher = HybridSearcher()
    dense = [_make_result(f"d{i}") for i in range(10)]
    sparse = [_make_result(f"s{i}") for i in range(10)]
    store = _make_store(dense, sparse)

    searcher.generate_sparse_vector = AsyncMock(return_value={1: 0.5})

    results = await searcher.search(store, [0.1], "query", top_k=3)

    assert len(results) <= 3


@pytest.mark.asyncio
async def test_search_empty_sparse_results_returns_dense():
    """When search_sparse returns [], dense results still returned."""
    searcher = HybridSearcher()
    dense = [_make_result("d1"), _make_result("d2")]
    store = _make_store(dense, [])

    searcher.generate_sparse_vector = AsyncMock(return_value={1: 0.5})

    results = await searcher.search(store, [0.1], "query", top_k=10)

    assert len(results) == 2
    chunk_ids = {r["chunk_id"] for r in results}
    assert "d1" in chunk_ids
    assert "d2" in chunk_ids


@pytest.mark.asyncio
async def test_search_exception_in_sparse_returns_dense_only():
    """When generate_sparse_vector fails (returns {}), dense results returned."""
    searcher = HybridSearcher()
    dense = [_make_result("d1"), _make_result("d2")]
    store = _make_store(dense, [])

    # simulate sparse failure by returning empty dict
    searcher.generate_sparse_vector = AsyncMock(return_value={})

    results = await searcher.search(store, [0.1], "query", top_k=10)

    store.search_sparse.assert_not_called()
    assert len(results) == 2


# ---------------------------------------------------------------------------
# _rrf_fusion directly
# ---------------------------------------------------------------------------


def test_rrf_fusion_marks_results():
    """_rrf_fusion adds 'fusion' key to each result."""
    searcher = HybridSearcher()
    dense = [_make_result("a"), _make_result("b")]
    sparse = [_make_result("c")]

    fused = searcher._rrf_fusion(dense, sparse)

    for r in fused:
        assert r.get("fusion") == "rrf"


def test_rrf_fusion_empty_inputs():
    """_rrf_fusion with empty lists returns empty list."""
    searcher = HybridSearcher()
    assert searcher._rrf_fusion([], []) == []


def test_rrf_fusion_dedup():
    """_rrf_fusion deduplicates chunk_ids appearing in both lists."""
    searcher = HybridSearcher()
    dense = [_make_result("x")]
    sparse = [_make_result("x")]

    fused = searcher._rrf_fusion(dense, sparse)
    assert len(fused) == 1
    assert fused[0]["chunk_id"] == "x"
