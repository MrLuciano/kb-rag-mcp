"""
TDD tests for vector_store.py fixes:
  WR-01/02: assert guards → explicit RuntimeError
  WR-05:    doc_type in get_stats() scroll projection
  IN-07:    list_documents scroll loop must not exit early when len(batch) < limit
"""

import pytest
import sys
import os
import types
import asyncio

# Provide lightweight stubs to break the circular import chain before importing
# vector_store. We only need to prevent server.py / embed_client from being
# fully initialised — VectorStore itself doesn't depend on the full server.


def _stub_modules():
    # Import real qdrant_client before stubs so real model classes (Distance,
    # PointStruct, etc.) are used — fixes enum comparisons broken by anonymous
    # type(name, (), {})() stubs.  setdefault below preserves real modules.
    import qdrant_client  # noqa: F401

    # Stub embed_client
    ec = types.ModuleType("embed_client")
    ec.get_embed_dim = lambda: 768
    ec.get_embedding = None
    ec.BACKEND = "fastembed"
    ec.MODEL = "test-model"
    sys.modules.setdefault("embed_client", ec)

    # Stub server.cache.manager (pulled in by real embed_client)
    cm = types.ModuleType("kb_server.cache.manager")

    class FakeCM:
        pass

    cm.CacheManager = FakeCM
    sys.modules.setdefault("kb_server.cache.manager", cm)

    # Stub qdrant_client and sub-modules used at import time
    for mod in [
        "qdrant_client",
        "qdrant_client.async_qdrant_client",
        "qdrant_client.http",
        "qdrant_client.http.models",
        "qdrant_client.models",
    ]:
        sys.modules.setdefault(mod, types.ModuleType(mod))

    # qdrant_client was imported at the top of _stub_modules(), so all sub-modules
    # are the real package — no model stubs needed.  Override AsyncQdrantClient
    # so from qdrant_client import AsyncQdrantClient returns object (safe default)
    # before the session-scoped conftest fixture patches it.
    qc = sys.modules["qdrant_client"]
    qc.AsyncQdrantClient = object


_stub_modules()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

# Now import VectorStore — will use the stubs above
from kb_server.vector_store import VectorStore  # noqa: E402

# ── WR-01/02: assert → RuntimeError ─────────────────────────────────────────


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_connect_raises_if_already_connected():
    """WR-02: connect() raises RuntimeError (not AssertionError) if called twice."""
    vs = VectorStore()
    vs.client = object()  # simulate already-connected state

    with pytest.raises(RuntimeError, match="already connected"):
        _run(vs.connect())


def test_search_raises_if_not_connected():
    """WR-01: search() raises RuntimeError (not AssertionError) when client is None."""
    vs = VectorStore()
    with pytest.raises(RuntimeError, match="not connected"):
        _run(vs.search(vector=[0.0] * 768))


def test_list_documents_raises_if_not_connected():
    """WR-01: list_documents() raises RuntimeError when client is None."""
    vs = VectorStore()
    with pytest.raises(RuntimeError, match="not connected"):
        _run(vs.list_documents())


def test_get_stats_raises_if_not_connected():
    """WR-01: get_stats() raises RuntimeError when client is None."""
    vs = VectorStore()
    with pytest.raises(RuntimeError, match="not connected"):
        _run(vs.get_stats())


# ── WR-05: doc_type in get_stats() scroll projection ────────────────────────


def test_get_stats_includes_doc_type_in_scroll_projection():
    """WR-05: get_stats() scroll must request 'doc_type' in with_payload list."""
    vs = VectorStore()

    scroll_calls = []

    class FakeCollection:
        points_count = 0

    class FakeClient:
        async def get_collection(self, name):
            return FakeCollection()

        async def scroll(
            self, collection_name, limit, with_payload, with_vectors, **kw
        ):
            scroll_calls.append(with_payload)
            return [], None

    vs.client = FakeClient()

    _run(vs.get_stats())

    assert scroll_calls, "scroll() was never called"
    projection = scroll_calls[0]
    assert (
        "doc_type" in projection
    ), f"'doc_type' missing from scroll with_payload projection: {projection}"


# ── IN-07: list_documents scroll must not exit early ─────────────────────────


def test_list_documents_continues_scroll_when_batch_smaller_than_page():
    """IN-07: scroll loop must continue when batch size < page limit (500).

    Bug: old code broke when len(results) < 500 even though offset is non-None,
    meaning more pages exist. The loop should only stop when offset is None.
    """
    vs = VectorStore()

    def _make_record(name):
        r = types.SimpleNamespace()
        r.payload = {
            "source_file": name,
            "file_type": "md",
            "product": "p",
            "doc_type": "guide",
        }
        return r

    page1 = [_make_record(f"doc{i}.md") for i in range(3)]
    page2 = [_make_record(f"doc{i+10}.md") for i in range(2)]
    pages = [(page1, "fake-offset"), (page2, None)]
    call_count = [0]

    class FakeClient:
        async def scroll(self, **kw):
            result = pages[call_count[0]]
            call_count[0] += 1
            return result

    vs.client = FakeClient()

    docs = _run(vs.list_documents(limit=50))

    assert (
        call_count[0] == 2
    ), f"Expected 2 scroll calls (both pages), got {call_count[0]}"
    assert len(docs) == 5, f"Expected 5 docs (3+2), got {len(docs)}"
