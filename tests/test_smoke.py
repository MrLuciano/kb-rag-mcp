"""
Integration tests for the core _search_kb -> VectorStore -> TextContent path.

These tests mock Qdrant and embedding to verify that:
1. Results flow correctly from store.search() into TextContent output.
2. Zero-result case returns the expected "no results" TextContent.
3. Filters (product, doc_type, file_type) are passed through to store.search().

Relies on conftest.py's mock_qdrant_client fixture (session-scoped) for Qdrant isolation.
"""
import asyncio

import pytest


def _run(coro):
    """Run a coroutine synchronously, creating an event loop if needed."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# -- Helpers ----------------------------------------------------------------


def _make_chunk(
    text="hello world",
    source="doc.md",
    score=0.9,
    product="acme",
    doc_type="guide",
    file_type="md",
):
    return {
        "chunk_id": "abc-123",
        "text": text,
        "source_file": source,
        "score": score,
        "product": product,
        "doc_type": doc_type,
        "file_type": file_type,
        "chunk_index": 0,
    }


# -- Tests -------------------------------------------------------------------


@pytest.mark.integration
def test_search_kb_returns_text_content_on_results(monkeypatch):
    """_search_kb returns list[TextContent] containing result text."""
    import importlib

    srv = importlib.import_module("kb_server.server")

    fake_vector = [0.1] * 768

    async def fake_embed(query):
        return fake_vector

    monkeypatch.setattr(srv, "get_embedding", fake_embed)
    monkeypatch.setattr(srv, "query_logger", None)

    class FakeStore:
        async def search(
            self, vector, top_k, filter_type, product,
            doc_type, version, vendor=None,
            subsystem=None, module=None, **kw
        ):
            return [_make_chunk()]

    monkeypatch.setattr(srv, "store", FakeStore())

    results = _run(
        srv._search_kb({"query": "test query", "hybrid": False})
    )

    assert results, "Expected at least one TextContent"
    assert all(r.type == "text" for r in results)
    combined = "\n".join(r.text for r in results)
    assert "hello world" in combined


@pytest.mark.integration
def test_search_kb_returns_no_results_message_when_store_empty(
    monkeypatch,
):
    """_search_kb returns 'no results' TextContent when store returns []."""
    import importlib

    srv = importlib.import_module("kb_server.server")

    async def fake_embed(query):
        return [0.0] * 768

    monkeypatch.setattr(srv, "get_embedding", fake_embed)
    monkeypatch.setattr(srv, "query_logger", None)

    class FakeStore:
        async def search(self, **kw):
            return []

    monkeypatch.setattr(srv, "store", FakeStore())

    results = _run(
        srv._search_kb({"query": "nothing", "hybrid": False})
    )

    assert len(results) == 1
    assert "No results found" in results[0].text


@pytest.mark.integration
def test_search_kb_passes_filters_to_store(monkeypatch):
    """Filters (product, doc_type, filter_type) are forwarded to store.search()."""
    import importlib

    srv = importlib.import_module("kb_server.server")

    async def fake_embed(query):
        return [0.0] * 768

    monkeypatch.setattr(srv, "get_embedding", fake_embed)
    monkeypatch.setattr(srv, "query_logger", None)

    captured = {}

    class FakeStore:
        async def search(
            self, vector, top_k, filter_type, product,
            doc_type, version, vendor=None,
            subsystem=None, module=None, **kw
        ):
            captured["filter_type"] = filter_type
            captured["product"] = product
            captured["doc_type"] = doc_type
            return []

    monkeypatch.setattr(srv, "store", FakeStore())

    _run(
        srv._search_kb({
            "query": "q",
            "hybrid": False,
            "product": "acme",
            "doc_type": "guide",
            "filter_type": "md",
        })
    )

    assert captured["product"] == "acme"
    assert captured["doc_type"] == "guide"
    assert captured["filter_type"] == "md"
