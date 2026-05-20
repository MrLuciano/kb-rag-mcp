"""
Unit tests for kb_server/retrieval/reranker.py — CrossEncoderReranker.

No real cross-encoder model is loaded; self.model is injected directly.
"""
from __future__ import annotations

# Stub out heavy optional deps that may be missing in CI
import sys
from unittest.mock import MagicMock

for _mod in (
    "tokenizers",
    "fastembed",
    "fastembed.sparse",
    "fastembed.sparse.bm25",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import numpy as np
import pytest

from kb_server.retrieval.reranker import CrossEncoderReranker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(i: int, score: float = 0.5) -> dict:
    return {
        "chunk_id": f"chunk-{i}",
        "score": score,
        "text": f"result {i}",
        "source_file": "doc.md",
        "product": "test",
        "doc_type": "guide",
        "file_type": "txt",
    }


def _make_mock_model(scores: list[float]):
    """Return a mock that mimics CrossEncoder.predict."""
    from unittest.mock import MagicMock
    m = MagicMock()
    m.predict.return_value = np.array(scores)
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rerank_sorts_by_score_descending():
    """rerank() returns results sorted by cross-encoder score descending."""
    reranker = CrossEncoderReranker()
    results = [_make_result(0), _make_result(1), _make_result(2)]
    # Assign scores: chunk-2 best, chunk-0 worst
    reranker.model = _make_mock_model([0.1, 0.5, 0.9])

    out = await reranker.rerank("query", results)

    assert out[0]["chunk_id"] == "chunk-2"
    assert out[1]["chunk_id"] == "chunk-1"
    assert out[2]["chunk_id"] == "chunk-0"
    assert out[0]["score"] == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_rerank_empty_results_returns_empty():
    """rerank() with empty input returns empty list."""
    reranker = CrossEncoderReranker()
    out = await reranker.rerank("query", [])
    assert out == []


@pytest.mark.asyncio
async def test_rerank_truncates_to_top_k():
    """rerank() with top_k truncates to top_k results."""
    reranker = CrossEncoderReranker()
    results = [_make_result(i) for i in range(5)]
    reranker.model = _make_mock_model([0.1, 0.2, 0.9, 0.5, 0.3])

    out = await reranker.rerank("query", results, top_k=3)

    assert len(out) == 3


@pytest.mark.asyncio
async def test_load_model_is_lazy():
    """_load_model() should NOT be called during __init__."""
    reranker = CrossEncoderReranker()
    # After __init__, model must still be None (lazy)
    assert reranker.model is None


@pytest.mark.asyncio
async def test_rerank_with_cache_returns_same_as_rerank():
    """rerank_with_cache() without a cache manager returns same results as rerank()."""
    reranker = CrossEncoderReranker()
    results = [_make_result(i) for i in range(3)]
    scores = [0.3, 0.7, 0.5]
    reranker.model = _make_mock_model(scores)

    direct = await reranker.rerank("query", results)
    # Reset model mock so predict returns same values
    reranker.model = _make_mock_model(scores)
    cached = await reranker.rerank_with_cache("query", results, cache_manager=None)

    assert [r["chunk_id"] for r in direct] == [r["chunk_id"] for r in cached]


@pytest.mark.asyncio
async def test_load_model_failure_propagates():
    """If CrossEncoder() raises, the exception propagates from rerank()."""
    reranker = CrossEncoderReranker()
    # model is None → _load_model will be called

    with pytest.raises(Exception):
        with pytest.MonkeyPatch().context() as mp:
            def bad_load(self):  # noqa: N803
                raise RuntimeError("model load failed")
            mp.setattr(CrossEncoderReranker, "_load_model", bad_load)
            await reranker.rerank("query", [_make_result(0)])


# ---------------------------------------------------------------------------
# _load_model (lines 53-69)
# ---------------------------------------------------------------------------


def test_load_model_sets_model_attribute():
    """_load_model() sets self.model when CrossEncoder is importable."""
    reranker = CrossEncoderReranker()
    assert reranker.model is None

    fake_ce = MagicMock()
    with pytest.MonkeyPatch().context() as mp:
        # Patch the sentence_transformers import inside _load_model
        fake_st = MagicMock()
        fake_st.CrossEncoder.return_value = fake_ce
        mp.setitem(sys.modules, "sentence_transformers", fake_st)
        reranker._load_model()

    assert reranker.model is fake_ce


def test_load_model_raises_import_error_when_missing():
    """_load_model() raises ImportError if sentence_transformers absent."""
    reranker = CrossEncoderReranker()

    with pytest.MonkeyPatch().context() as mp:
        # Remove sentence_transformers so import fails
        mp.setitem(sys.modules, "sentence_transformers", None)
        with pytest.raises((ImportError, Exception)):
            reranker._load_model()


# ---------------------------------------------------------------------------
# rerank_with_cache (lines 148-155)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rerank_with_cache_second_call_uses_cache():
    """rerank_with_cache() calls model.predict only once on cache hit."""
    reranker = CrossEncoderReranker()
    results = [_make_result(i) for i in range(3)]
    reranker.model = _make_mock_model([0.3, 0.7, 0.5])

    # Build a simple async cache
    _store: dict = {}

    async def cache_get(key):
        return _store.get(key)

    async def cache_set(key, value, ttl=None):
        _store[key] = value

    cache = MagicMock()
    cache.get = cache_get
    cache.set = cache_set

    # First call — model.predict should be called
    await reranker.rerank_with_cache("q", results, cache_manager=cache)
    first_call_count = reranker.model.predict.call_count

    # Second call with same query + results — should hit cache
    await reranker.rerank_with_cache("q", results, cache_manager=cache)
    second_call_count = reranker.model.predict.call_count

    assert first_call_count == 1
    assert second_call_count == 1  # no additional call on cache hit


@pytest.mark.asyncio
async def test_rerank_with_cache_stores_result():
    """rerank_with_cache() stores computed result in cache for future use."""
    reranker = CrossEncoderReranker()
    results = [_make_result(0), _make_result(1)]
    reranker.model = _make_mock_model([0.9, 0.1])

    _store: dict = {}

    async def cache_get(key):
        return _store.get(key)

    async def cache_set(key, value, ttl=None):
        _store[key] = value

    cache = MagicMock()
    cache.get = cache_get
    cache.set = cache_set

    out = await reranker.rerank_with_cache("q", results, cache_manager=cache)

    # Cache must have been populated
    assert len(_store) == 1
    cached_value = list(_store.values())[0]
    assert [r["chunk_id"] for r in out] == [r["chunk_id"] for r in cached_value]


# ---------------------------------------------------------------------------
# get_reranker singleton (lines 176-178)
# ---------------------------------------------------------------------------


def test_get_reranker_returns_singleton():
    """get_reranker() returns same instance on repeated calls."""
    import kb_server.retrieval.reranker as reranker_module

    reranker_module._reranker = None
    from kb_server.retrieval.reranker import get_reranker

    a = get_reranker()
    b = get_reranker()
    assert a is b


def test_get_reranker_creates_cross_encoder_instance():
    """get_reranker() returns a CrossEncoderReranker instance."""
    import kb_server.retrieval.reranker as reranker_module

    reranker_module._reranker = None
    from kb_server.retrieval.reranker import get_reranker

    result = get_reranker()
    assert isinstance(result, CrossEncoderReranker)
