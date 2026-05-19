"""Integration tests for ingest→search_kb MCP path (TEST-02).
Uses mocked VectorStore — no live Qdrant required.
"""
import pytest
from unittest.mock import AsyncMock, patch

import kb_server.server as server_module
from kb_server.server import _search_kb


def _fake_result(text="integration test document"):
    return {
        "chunk_id": "abc-123",
        "score": 0.92,
        "text": text,
        "source_file": "docs/guide.md",
        "product": "myproduct",
        "doc_type": "guide",
        "file_type": "txt",  # REQUIRED: server.py accesses r['file_type'] directly
    }


@pytest.fixture(autouse=True)
def patch_server_globals():
    """Patch all server module globals to isolate tests from live services."""
    mock_store = AsyncMock()
    mock_store.collection = "kb_docs"

    with (
        patch.object(server_module, "store", mock_store),
        patch.object(server_module, "get_embedding", new=AsyncMock(
            return_value=[0.1] * 384
        )),
        patch.object(server_module, "collection_router", None),
        patch.object(server_module, "query_logger", None),
    ):
        yield mock_store


@pytest.mark.asyncio
async def test_ingest_then_search_returns_document(patch_server_globals):
    """Mock store returns a fake result; _search_kb should return TextContent
    containing that document's text."""
    patch_server_globals.search.return_value = [_fake_result()]

    results = await _search_kb({"query": "integration test"})

    assert len(results) == 1
    assert "integration test document" in results[0].text


@pytest.mark.asyncio
async def test_search_with_product_filter(patch_server_globals):
    """Calling search_kb with product param should forward product to store.search."""
    patch_server_globals.search.return_value = [
        _fake_result("product filtered doc")
    ]

    await _search_kb({"query": "some query", "product": "myproduct"})

    call_kwargs = patch_server_globals.search.call_args
    assert call_kwargs.kwargs.get("product") == "myproduct"


@pytest.mark.asyncio
async def test_search_no_results_returns_empty_message(patch_server_globals):
    """When store returns no results, _search_kb should return a TextContent
    indicating no results without raising an exception."""
    patch_server_globals.search.return_value = []

    results = await _search_kb({"query": "query with no results"})

    assert len(results) == 1
    assert results[0].type == "text"
    # Should indicate no results found
    assert "Nenhum resultado" in results[0].text or "no result" in results[0].text.lower()


@pytest.mark.asyncio
async def test_search_kb_with_top_k(patch_server_globals):
    """Passing top_k should forward the value to store.search."""
    patch_server_globals.search.return_value = [_fake_result()]

    await _search_kb({"query": "some query", "top_k": 3})

    call_kwargs = patch_server_globals.search.call_args
    assert call_kwargs.kwargs.get("top_k") == 3
