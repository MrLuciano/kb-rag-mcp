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
    assert "Nenhum resultado" in out[0].text


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
    assert "Nenhum documento" in out[0].text


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
    assert "não encontrado" in out[0].text


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
