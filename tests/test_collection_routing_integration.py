"""Integration tests for multi-collection routing (TEST-03)."""
import pytest
from unittest.mock import AsyncMock, patch

import kb_server.server as server_module
from kb_server.collections.router import CollectionRouter, CollectionNotFoundError
from kb_server.collections.manager import CollectionManager
from kb_server.server import _search_kb


def _fake_result(text="collection routing test"):
    return {
        "chunk_id": "col-abc-456",
        "score": 0.88,
        "text": text,
        "source_file": "docs/collection.md",
        "product": "myproduct",
        "doc_type": "guide",
        "file_type": "txt",  # REQUIRED
    }


@pytest.fixture
def mock_store():
    store = AsyncMock()
    store.collection = "kb_docs"
    store.search.return_value = [_fake_result()]
    return store


@pytest.fixture
def two_collection_router():
    """CollectionRouter backed by a mock manager that knows col_a, col_b,
    and kb_docs."""
    manager = AsyncMock(spec=CollectionManager)

    async def collection_exists(name: str) -> bool:
        return name in ("col_a", "col_b", "kb_docs")

    manager.collection_exists.side_effect = collection_exists
    return CollectionRouter(manager, default_collection="kb_docs")


@pytest.fixture(autouse=True)
def patch_server_globals(mock_store):
    """Patch common server module globals."""
    with (
        patch.object(server_module, "store", mock_store),
        patch.object(server_module, "get_embedding", new=AsyncMock(
            return_value=[0.1] * 384
        )),
        patch.object(server_module, "query_logger", None),
    ):
        yield mock_store


@pytest.mark.asyncio
async def test_search_routes_to_correct_collection(
    patch_server_globals, two_collection_router
):
    """When collection='col_a' is specified, store.search must be called
    with collection_name='col_a'."""
    with patch.object(server_module, "collection_router", two_collection_router):
        await _search_kb({"query": "some query", "collection": "col_a"})

    call_kwargs = patch_server_globals.search.call_args
    assert call_kwargs.kwargs.get("collection_name") == "col_a"


@pytest.mark.asyncio
async def test_search_routes_to_default_when_no_collection_param(
    patch_server_globals, two_collection_router
):
    """When no collection is specified, store.search should use the default
    collection (kb_docs)."""
    with patch.object(server_module, "collection_router", two_collection_router):
        await _search_kb({"query": "default collection query"})

    call_kwargs = patch_server_globals.search.call_args
    assert call_kwargs.kwargs.get("collection_name") == "kb_docs"


@pytest.mark.asyncio
async def test_search_graceful_fallback_on_missing_collection(
    patch_server_globals, two_collection_router
):
    """Requesting a non-existent collection should return a TextContent with
    an error message — not raise an exception."""
    with patch.object(server_module, "collection_router", two_collection_router):
        results = await _search_kb(
            {"query": "some query", "collection": "missing_col"}
        )

    assert len(results) == 1
    assert results[0].type == "text"
    # Should contain some indication of the missing collection
    assert "missing_col" in results[0].text or "not exist" in results[0].text.lower()


@pytest.mark.asyncio
async def test_multi_collection_isolation(
    patch_server_globals, two_collection_router
):
    """Searching col_a should call store.search exactly once with
    collection_name='col_a'."""
    with patch.object(server_module, "collection_router", two_collection_router):
        await _search_kb({"query": "isolation query", "collection": "col_a"})

    patch_server_globals.search.assert_called_once()
    call_kwargs = patch_server_globals.search.call_args
    assert call_kwargs.kwargs.get("collection_name") == "col_a"
