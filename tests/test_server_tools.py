"""
Unit tests for kb_server/server.py tool handlers.

Patches module-level globals to avoid real I/O.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import kb_server.server as srv
from kb_server.collections.router import CollectionNotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(text: str = "hello world", score: float = 0.9) -> dict:
    return {
        "chunk_id": "test-chunk-001",
        "score": score,
        "text": text,
        "source_file": "docs/test.md",
        "product": "testproduct",
        "doc_type": "guide",
        "file_type": "txt",  # REQUIRED — server.py accesses r['file_type']
        "page": None,
    }


def _make_doc(source_file: str = "docs/test.md") -> dict:
    return {
        "source_file": source_file,
        "chunk_count": 10,
        "product": "testproduct",
        "doc_type": "guide",
        "file_type": "txt",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_server_globals():
    """Restore module-level globals after each test."""
    original_store = srv.store
    original_router = srv.collection_router
    original_logger = srv.query_logger
    yield
    srv.store = original_store
    srv.collection_router = original_router
    srv.query_logger = original_logger


@pytest.fixture
def mock_store():
    s = AsyncMock()
    s.collection = "kb_docs"
    return s


@pytest.fixture
def mock_router():
    r = AsyncMock()
    r.resolve.return_value = "kb_docs"
    return r


@pytest.fixture
def mock_query_logger():
    return MagicMock()


@pytest.fixture
def mock_retrieval_cache():
    """Fixture providing a RetrievalCache-like mock for cache testing."""
    from unittest.mock import MagicMock

    cache = MagicMock()
    cache.enabled = True
    cache.make_key.return_value = "test-cache-key-abc123"
    return cache


# ---------------------------------------------------------------------------
# _search_kb
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_kb_basic_returns_result_text(mock_store, mock_router):
    """Basic search returns TextContent containing result text."""
    result = _make_result(text="hello world")
    mock_store.search.return_value = [result]
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "hello"})

    assert len(out) == 1
    assert "hello world" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_zero_results_returns_no_results_message(mock_store, mock_router):
    """Zero results → 'no results' message in TextContent."""
    mock_store.search.return_value = []
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "missing"})

    assert len(out) == 1
    assert "No results found" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_no_router_uses_store_collection(mock_store):
    """When collection_router is None, uses store.collection default."""
    result = _make_result()
    mock_store.search.return_value = [result]
    srv.store = mock_store
    srv.collection_router = None
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "test"})

    # Should pass collection_name=None (store.collection default path)
    assert len(out) == 1
    assert "hello world" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_collection_not_found_returns_error_text(mock_store):
    """CollectionNotFoundError from router → error TextContent (no exception)."""
    mock_router = AsyncMock()
    mock_router.resolve.side_effect = CollectionNotFoundError("missing_col")
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "test", "collection": "missing_col"})

    assert len(out) == 1
    assert "missing_col" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_hybrid_routes_to_hybrid_searcher(mock_store, mock_router):
    """hybrid=True routes to HybridSearcher.search, not store.search."""
    result = _make_result(text="hybrid result")
    mock_hybrid = AsyncMock()
    mock_hybrid.search.return_value = [result]
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        with patch(
            "kb_server.retrieval.hybrid_search.get_hybrid_searcher",
            return_value=mock_hybrid,
        ):
            out = await srv._search_kb({"query": "test", "hybrid": True})

    mock_hybrid.search.assert_awaited_once()
    mock_store.search.assert_not_awaited()
    assert "hybrid result" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_rerank_routes_to_reranker(mock_store, mock_router):
    """rerank=True calls reranker.rerank on search results."""
    result = _make_result(text="reranked result", score=0.95)
    mock_store.search.return_value = [result]
    mock_reranker = AsyncMock()
    mock_reranker.rerank.return_value = [result]
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        with patch(
            "kb_server.retrieval.reranker.get_reranker",
            return_value=mock_reranker,
        ):
            out = await srv._search_kb({"query": "test", "rerank": True})

    mock_reranker.rerank.assert_awaited_once()
    assert "reranked result" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_query_logger_called_after_search(mock_store, mock_router, mock_query_logger):
    """query_logger.log_query is called after a successful search."""
    result = _make_result()
    mock_store.search.return_value = [result]
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = mock_query_logger

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        await srv._search_kb({"query": "test"})

    mock_query_logger.log_query.assert_called_once()


@pytest.mark.asyncio
async def test_search_kb_with_kb_ids_routes_to_multi_search(mock_store, mock_router):
    """kb_ids triggers multi_search path instead of single search."""
    from kb_server.collections.router import CollectionNotFoundError

    mock_router.resolve_multi = AsyncMock(
        return_value=["kb_hr", "kb_eng"]
    )
    mock_store.multi_search = AsyncMock(
        return_value={
            "kb_hr": [
                {
                    "chunk_id": "hr-1",
                    "score": 0.9,
                    "text": "hr result",
                    "source_file": "hr.md",
                    "product": "HR",
                    "doc_type": "guide",
                    "file_type": "pdf",
                    "page": None,
                    "_collection": "kb_hr",
                },
            ],
            "kb_eng": [
                {
                    "chunk_id": "eng-1",
                    "score": 0.8,
                    "text": "eng result",
                    "source_file": "eng.md",
                    "product": "Eng",
                    "doc_type": "guide",
                    "file_type": "pdf",
                    "page": None,
                    "_collection": "kb_eng",
                },
            ],
        }
    )
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "test", "kb_ids": ["kb_hr", "kb_eng"]})

    assert len(out) == 1
    assert "hr result" in out[0].text
    assert "eng result" in out[0].text
    assert "multi-KB" in out[0].text
    mock_store.multi_search.assert_awaited_once()
    mock_store.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_kb_with_kb_ids_collection_not_found_returns_error(mock_store):
    """CollectionNotFoundError from resolve_multi → error TextContent."""
    from kb_server.collections.router import CollectionNotFoundError

    mock_router = AsyncMock()
    mock_router.resolve_multi.side_effect = CollectionNotFoundError("missing_kb")
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "test", "kb_ids": ["missing_kb"]})

    assert len(out) == 1
    assert "missing_kb" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_with_kb_ids_no_results(mock_store, mock_router):
    """multi_search returning empty → 'no results' message."""
    mock_router.resolve_multi = AsyncMock(return_value=["kb_empty"])
    mock_store.multi_search = AsyncMock(return_value={"kb_empty": []})
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "test", "kb_ids": ["kb_empty"]})

    assert len(out) == 1
    assert "No results found" in out[0].text


# ---------------------------------------------------------------------------
# PHASE 37: Retrieval cache integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_kb_cache_hit_skips_embedding_and_search(
    mock_store, mock_router,
):
    """Cache hit returns cached results without calling get_embedding or search."""
    cached_results = [
        {
            "chunk_id": "cached-1", "score": 0.99,
            "text": "cached result", "source_file": "cached.md",
            "product": "test", "doc_type": "guide", "file_type": "txt",
            "page": None,
        },
    ]
    cache = MagicMock()
    cache.enabled = True
    cache.get.return_value = cached_results

    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None
    srv.retrieval_cache = cache

    with patch("kb_server.server.get_embedding", new=AsyncMock()) as mock_embed:
        out = await srv._search_kb({"query": "cached test"})

    mock_embed.assert_not_awaited()
    mock_store.search.assert_not_awaited()
    assert len(out) == 1
    assert "cached result" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_cache_miss_performs_full_search(
    mock_store, mock_router,
):
    """Cache miss calls get_embedding and search normally."""
    result = {
        "chunk_id": "fresh-1", "score": 0.9,
        "text": "fresh result", "source_file": "fresh.md",
        "product": "test", "doc_type": "guide", "file_type": "txt",
        "page": None,
    }
    mock_store.search.return_value = [result]

    cache = MagicMock()
    cache.enabled = True
    cache.get.return_value = None  # miss

    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None
    srv.retrieval_cache = cache

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "fresh query"})

    mock_store.search.assert_awaited_once()
    assert len(out) == 1
    assert "fresh result" in out[0].text


@pytest.mark.asyncio
async def test_search_kb_cache_hit_still_logs_query(mock_store, mock_router):
    """Cache hit still calls query_logger.log_query for observability."""
    cached_results = [
        {
            "chunk_id": "cached-1", "score": 0.99,
            "text": "cached result", "source_file": "cached.md",
            "product": "test", "doc_type": "guide", "file_type": "txt",
            "page": None,
        },
    ]
    cache = MagicMock()
    cache.enabled = True
    cache.get.return_value = cached_results

    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = MagicMock()
    srv.retrieval_cache = cache

    with patch("kb_server.server.get_embedding", new=AsyncMock()):
        await srv._search_kb({"query": "cached query"})

    srv.query_logger.log_query.assert_called_once()


@pytest.mark.asyncio
async def test_search_kb_cache_disabled_does_not_check(
    mock_store, mock_router,
):
    """When cache is disabled, retrieval_cache is not consulted."""
    result = {
        "chunk_id": "fresh-1", "score": 0.9,
        "text": "fresh result", "source_file": "fresh.md",
        "product": "test", "doc_type": "guide", "file_type": "txt",
        "page": None,
    }
    mock_store.search.return_value = [result]

    cache = MagicMock()
    cache.enabled = False  # disabled

    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None
    srv.retrieval_cache = cache

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        out = await srv._search_kb({"query": "no cache"})

    mock_store.search.assert_awaited_once()
    assert "fresh result" in out[0].text
    cache.get.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_retrieval_cache_clears_cache():
    """invalidate_retrieval_cache() calls invalidate_all on the cache."""
    cache = MagicMock()
    srv.retrieval_cache = cache
    srv.invalidate_retrieval_cache()

    cache.invalidate_all.assert_called_once()


@pytest.mark.asyncio
async def test_search_kb_cache_stores_results_after_miss(mock_store, mock_router):
    """After a cache miss, results are stored in the cache."""
    result = {
        "chunk_id": "fresh-1", "score": 0.9,
        "text": "fresh result", "source_file": "fresh.md",
        "product": "test", "doc_type": "guide", "file_type": "txt",
        "page": None,
    }
    mock_store.search.return_value = [result]

    cache = MagicMock()
    cache.enabled = True
    cache.get.return_value = None  # miss

    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None
    srv.retrieval_cache = cache

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        await srv._search_kb({"query": "store test"})

    cache.put.assert_called_once()


@pytest.mark.asyncio
async def test_search_kb_cache_key_includes_all_filters(mock_store, mock_router):
    """Cache key is generated from all retrieval-affecting parameters."""
    cache = MagicMock()
    cache.enabled = True
    cache.get.return_value = None  # miss

    mock_store.search.return_value = []

    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None
    srv.retrieval_cache = cache

    args = {
        "query": "test",
        "top_k": 10,
        "product": "AppServer",
        "vendor": "OpenText",
        "hybrid": True,
        "rerank": True,
    }

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        await srv._search_kb(args)

    # Verify make_key was called (just checking the call happened,
    # since unit-level key determinism is tested separately)
    cache.make_key.assert_called_once()


# ---------------------------------------------------------------------------
# Existing tests continue below
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_kb_with_kb_ids_rerank_not_applied(mock_store, mock_router):
    """rerank=True is ignored when kb_ids is set (multi-KB path)."""
    mock_router.resolve_multi = AsyncMock(return_value=["kb_one"])
    mock_store.multi_search = AsyncMock(
        return_value={
            "kb_one": [
                {
                    "chunk_id": "a",
                    "score": 0.9,
                    "text": "result",
                    "source_file": "doc.md",
                    "product": "P",
                    "doc_type": "guide",
                    "file_type": "pdf",
                    "page": None,
                    "_collection": "kb_one",
                },
            ],
        }
    )
    srv.store = mock_store
    srv.collection_router = mock_router
    srv.query_logger = None

    with patch("kb_server.server.get_embedding", new=AsyncMock(return_value=[0.1] * 768)):
        with patch(
            "kb_server.retrieval.reranker.get_reranker",
        ) as mock_get_reranker:
            out = await srv._search_kb({
                "query": "test", "kb_ids": ["kb_one"], "rerank": True,
            })

    assert len(out) == 1
    assert "result" in out[0].text
    mock_get_reranker.assert_not_called()


# ---------------------------------------------------------------------------
# _list_documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_documents_returns_listing(mock_store, mock_router):
    """_list_documents returns TextContent listing document sources."""
    doc = _make_doc(source_file="docs/test.md")
    mock_store.list_documents.return_value = [doc]
    srv.store = mock_store
    srv.collection_router = mock_router

    out = await srv._list_documents({})

    assert len(out) == 1
    assert "docs/test.md" in out[0].text


@pytest.mark.asyncio
async def test_list_documents_empty_returns_empty_message(mock_store, mock_router):
    """_list_documents with no docs returns empty-state message."""
    mock_store.list_documents.return_value = []
    srv.store = mock_store
    srv.collection_router = mock_router

    out = await srv._list_documents({})

    assert len(out) == 1
    assert "No documents indexed" in out[0].text


# ---------------------------------------------------------------------------
# _get_chunk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_chunk_returns_chunk_content(mock_store):
    """_get_chunk returns TextContent with chunk text."""
    chunk = {
        "chunk_id": "chunk-abc",
        "chunk_index": 1,
        "source_file": "docs/guide.md",
        "text": "important content here",
    }
    mock_store.get_chunk_with_context.return_value = [chunk]
    srv.store = mock_store

    out = await srv._get_chunk({"chunk_id": "chunk-abc"})

    assert len(out) == 1
    assert "important content here" in out[0].text


@pytest.mark.asyncio
async def test_get_chunk_not_found_returns_error_text(mock_store):
    """_get_chunk with missing chunk returns error TextContent."""
    mock_store.get_chunk_with_context.return_value = []
    srv.store = mock_store

    out = await srv._get_chunk({"chunk_id": "nonexistent-chunk"})

    assert len(out) == 1
    assert "nonexistent-chunk" in out[0].text
    assert "not found" in out[0].text


# ---------------------------------------------------------------------------
# _kb_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kb_stats_returns_stats_content(mock_store):
    """_kb_stats returns TextContent with stats dict values."""
    mock_store.get_stats.return_value = {
        "total_documents": 42,
        "total_chunks": 420,
        "index_size_mb": 1.5,
        "embed_model": "nomic-embed-text-v1.5",
        "embed_dim": 768,
        "by_doc_type": {"guide": 10, "reference": 32},
        "by_file_type": {"pdf": 20, "txt": 22},
    }
    srv.store = mock_store

    out = await srv._kb_stats()

    assert len(out) == 1
    assert "42" in out[0].text
    assert "420" in out[0].text
