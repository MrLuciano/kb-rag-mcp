"""
Unit tests for kb_server/vector_store.py — targeting >=80% branch coverage.

Covers the branches missed by test_vector_store.py:
  connect() modes: embedded / gRPC / HTTP
  _ensure_collection: create vs. skip
  _create_payload_indexes: success and exception paths
  search() filter combinations
  search_sparse() empty / results / exception / filters
  upsert_chunks() batching, empty list, raises
  delete_document()
  list_documents() filters + pagination
  get_chunk_with_context()
  get_stats() full path
  upsert_chunks_parallel() empty / connected / not-connected
  close()
"""

import asyncio
import types
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ── Bootstrap stubs (idempotent — safe if test_vector_store.py ran first) ────

def _ensure_stubs():
    """Register lightweight stubs so vector_store can be imported without
    real qdrant / embed-server running.  Uses setdefault so we never clobber
    a real module that was already imported."""

    # Import real qdrant_client before stubs so real model classes (Distance,
    # PointStruct, etc.) are used — fixes enum comparisons broken by anonymous
    # type(name, (), {})() stubs.  setdefault below preserves real modules.
    import qdrant_client  # noqa: F401

    # kb_server.embed_client
    ec_name = "kb_server.embed_client"
    if ec_name not in sys.modules:
        ec = types.ModuleType(ec_name)
        ec.get_embed_dim = lambda: 4
        ec.get_embedding = None
        ec.BACKEND = "test-backend"
        ec.MODEL = "test-model"
        sys.modules[ec_name] = ec

    # qdrant_client was imported at the top of _ensure_stubs(), so all sub-modules
    # are the real package — no model stubs needed.  Override AsyncQdrantClient
    # so from qdrant_client import AsyncQdrantClient returns object (safe default)
    # before the session-scoped conftest fixture patches it.
    qc = sys.modules["qdrant_client"]
    qc.AsyncQdrantClient = object


_ensure_stubs()

# Make sure the project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kb_server.vector_store import VectorStore  # noqa: E402

# qdrant_client was imported earlier by _ensure_stubs(), so all model classes
# are real — no MagicMock fix-ups needed.  _vs_mod references are used by
# some tests that access VectorStore module internals.
import kb_server.vector_store as _vs_mod  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_point(chunk_id="abc", score=0.9, **extra_payload):
    """Build a mock ScoredPoint / Record with a .payload dict."""
    p = MagicMock()
    p.id = chunk_id
    p.score = score
    p.payload = {
        "text": "hello world",
        "source_file": "doc.md",
        "file_type": "md",
        "product": "my-product",
        "doc_type": "guide",
        "page": None,
        "chunk_index": 0,
        **extra_payload,
    }
    return p


def _make_query_response(points):
    """Wrap a list of mock points in an object with .points attribute
    (as returned by client.query_points)."""
    r = MagicMock()
    r.points = points
    return r


@pytest.fixture
def store():
    """Return (VectorStore, mock_client) with the mock injected."""
    vs = VectorStore()
    mock_client = AsyncMock()
    vs.client = mock_client
    return vs, mock_client


# ── connect() ─────────────────────────────────────────────────────────────────

class TestConnect:

    def test_connect_embedded_mode(self):
        """Lines 67-72: QDRANT_PATH set → embedded client created."""
        vs = VectorStore()
        fake_client = AsyncMock()

        with patch("kb_server.vector_store.QDRANT_PATH", "/data/qdrant"), \
             patch("kb_server.vector_store.AsyncQdrantClient",
                   return_value=fake_client) as MockClient, \
             patch.object(vs, "_ensure_collection", new=AsyncMock()):
            _run(vs.connect())

        called_kwargs = MockClient.call_args[1]
        assert called_kwargs.get("path") == "/data/qdrant"

    def test_connect_grpc_mode(self):
        """Lines 73-82: QDRANT_GRPC set → gRPC client created."""
        vs = VectorStore()
        fake_client = AsyncMock()

        with patch("kb_server.vector_store.QDRANT_PATH", ""), \
             patch("kb_server.vector_store.QDRANT_GRPC", True), \
             patch("kb_server.vector_store.AsyncQdrantClient",
                   return_value=fake_client) as MockClient, \
             patch.object(vs, "_ensure_collection", new=AsyncMock()):
            _run(vs.connect())

        called_kwargs = MockClient.call_args[1]
        assert "grpc_port" in called_kwargs
        assert called_kwargs.get("prefer_grpc") is True

    def test_connect_http_mode(self):
        """Lines 83-89: default → HTTP client created."""
        vs = VectorStore()
        fake_client = AsyncMock()

        with patch("kb_server.vector_store.QDRANT_PATH", ""), \
             patch("kb_server.vector_store.QDRANT_GRPC", False), \
             patch("kb_server.vector_store.AsyncQdrantClient",
                   return_value=fake_client) as MockClient, \
             patch.object(vs, "_ensure_collection", new=AsyncMock()):
            _run(vs.connect())

        called_kwargs = MockClient.call_args[1]
        assert "host" in called_kwargs
        assert "port" in called_kwargs


# ── _ensure_collection() ──────────────────────────────────────────────────────

class TestEnsureCollection:

    def test_ensure_collection_creates_when_missing(self):
        """Lines 105-115: collection absent → create_collection called."""
        vs, mc = _make_store_with_mock()
        mc.get_collections.return_value = MagicMock(collections=[])
        mc.create_collection = AsyncMock()
        mc.create_payload_index = AsyncMock()

        _run(vs._ensure_collection())

        mc.create_collection.assert_called_once()

    def test_ensure_collection_skips_when_existing(self):
        """Lines 105: collection present → create_collection NOT called."""
        vs, mc = _make_store_with_mock()
        existing = MagicMock()
        existing.name = vs.collection
        mc.get_collections.return_value = MagicMock(collections=[existing])
        mc.create_collection = AsyncMock()

        _run(vs._ensure_collection())

        mc.create_collection.assert_not_called()

    def test_create_payload_indexes_called_for_three_fields(self):
        """Line 115: _create_payload_indexes called → 6 index creations."""
        vs, mc = _make_store_with_mock()
        mc.get_collections.return_value = MagicMock(collections=[])
        mc.create_collection = AsyncMock()
        mc.create_payload_index = AsyncMock()

        _run(vs._ensure_collection())

        assert mc.create_payload_index.call_count == 6

    def test_create_payload_indexes_ignores_exception(self):
        """Lines 137-141: exception in create_payload_index is swallowed."""
        vs, mc = _make_store_with_mock()
        mc.create_payload_index = AsyncMock(side_effect=Exception("boom"))

        # Should not raise
        _run(vs._create_payload_indexes())

    def test_ensure_collection_raises_if_not_connected(self):
        """Line 98-99: client None → RuntimeError."""
        vs = VectorStore()
        # client is already None by default
        with pytest.raises(RuntimeError, match="not connected"):
            _run(vs._ensure_collection())

    def test_create_payload_indexes_raises_if_not_connected(self):
        """Line 124-125: _create_payload_indexes with no client → RuntimeError."""
        vs = VectorStore()
        with pytest.raises(RuntimeError, match="not connected"):
            _run(vs._create_payload_indexes())


# ── search() ──────────────────────────────────────────────────────────────────

class TestSearch:

    def test_search_returns_flat_dicts(self, store):
        """Lines 195-208: results mapped to flat dicts."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([_make_point("id1", 0.9),
                                              _make_point("id2", 0.7)])
        )

        results = _run(vs.search(vector=[0.1, 0.2, 0.3, 0.4]))

        assert len(results) == 2
        assert results[0]["chunk_id"] == "id1"
        assert results[0]["score"] == 0.9
        assert "text" in results[0]

    def test_search_with_product_filter(self, store):
        """Lines 167-170: product filter added to query."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search(vector=[0.1] * 4, product="acme"))

        kwargs = mc.query_points.call_args[1]
        qf = kwargs.get("query_filter")
        assert qf is not None

    def test_search_with_doc_type_filter(self, store):
        """Lines 171-175: doc_type filter added."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search(vector=[0.1] * 4, doc_type="api"))

        kwargs = mc.query_points.call_args[1]
        assert kwargs.get("query_filter") is not None

    def test_search_with_version_filter(self, store):
        """Lines 177-182: version filter added (FASE 13)."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search(vector=[0.1] * 4, version="2.0"))

        kwargs = mc.query_points.call_args[1]
        assert kwargs.get("query_filter") is not None

    def test_search_with_filter_type(self, store):
        """Lines 161-166: file_type filter added."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search(vector=[0.1] * 4, filter_type="pdf"))

        kwargs = mc.query_points.call_args[1]
        assert kwargs.get("query_filter") is not None

    def test_search_collection_name_override(self, store):
        """Line 187: collection_name param overrides default."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search(vector=[0.1] * 4, collection_name="other_col"))

        kwargs = mc.query_points.call_args[1]
        assert kwargs["collection_name"] == "other_col"

    def test_search_no_filters_passes_none_filter(self, store):
        """Line 184: no conditions → query_filter=None."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search(vector=[0.1] * 4))

        kwargs = mc.query_points.call_args[1]
        assert kwargs.get("query_filter") is None

    def test_search_with_module_filter(self, store):
        """Phase 17: module filter condition built."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search(vector=[0.1] * 4, module="Administration"))

        kwargs = mc.query_points.call_args[1]
        assert kwargs.get("query_filter") is not None


# ── search_sparse() ───────────────────────────────────────────────────────────

class TestSearchSparse:

    def test_search_sparse_empty_vector_returns_empty(self, store):
        """Line 230-231: empty sparse_vector dict → [] immediately."""
        vs, mc = store
        result = _run(vs.search_sparse(sparse_vector={}))
        assert result == []
        mc.query_points.assert_not_called()

    def test_search_sparse_raises_if_not_connected(self):
        """Line 228-229: client None → RuntimeError."""
        vs = VectorStore()
        with pytest.raises(RuntimeError, match="not connected"):
            _run(vs.search_sparse(sparse_vector={1: 0.5}))

    def test_search_sparse_returns_flat_dicts(self, store):
        """Lines 275-288: results mapped to flat dicts."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([_make_point("sp1", 0.8)])
        )

        results = _run(vs.search_sparse(sparse_vector={0: 1.0, 5: 0.3}))

        assert len(results) == 1
        assert results[0]["chunk_id"] == "sp1"
        assert results[0]["score"] == 0.8

    def test_search_sparse_exception_returns_empty(self, store):
        """Lines 289-294: exception in query_points → returns []."""
        vs, mc = store
        mc.query_points = AsyncMock(side_effect=Exception("no sparse index"))

        result = _run(vs.search_sparse(sparse_vector={1: 0.5}))

        assert result == []

    def test_search_sparse_with_product_and_doctype_filters(self, store):
        """Lines 240-256: product + doc_type → filter built."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search_sparse(
            sparse_vector={1: 0.9},
            product="prod",
            doc_type="guide",
        ))

        kwargs = mc.query_points.call_args[1]
        assert kwargs.get("query_filter") is not None

    def test_search_sparse_with_filter_type(self, store):
        """Lines 234-239: filter_type → filter built."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search_sparse(
            sparse_vector={1: 0.9},
            filter_type="pdf",
        ))

        kwargs = mc.query_points.call_args[1]
        assert kwargs.get("query_filter") is not None

    def test_search_sparse_with_version_filter(self, store):
        """Lines 252-257: version → filter built."""
        vs, mc = store
        mc.query_points = AsyncMock(
            return_value=_make_query_response([])
        )

        _run(vs.search_sparse(
            sparse_vector={1: 0.9},
            version="3.0",
        ))

        kwargs = mc.query_points.call_args[1]
        assert kwargs.get("query_filter") is not None


# ── upsert_chunks() ───────────────────────────────────────────────────────────

class TestUpsertChunks:

    def test_upsert_raises_if_not_connected(self):
        """Line 299-300: client None → RuntimeError."""
        vs = VectorStore()
        with pytest.raises(RuntimeError, match="not connected"):
            _run(vs.upsert_chunks([{"vector": [0.1] * 4, "text": "x",
                                    "source_file": "a.md"}]))

    def test_upsert_empty_list_does_nothing(self, store):
        """Lines 314-316: empty list → early return, upsert not called."""
        vs, mc = store

        _run(vs.upsert_chunks([]))

        mc.upsert.assert_not_called()

    def test_upsert_calls_upsert_in_batches(self, store):
        """Lines 334-341: 5 chunks with batch_size=2 → ceil(5/2)=3 calls."""
        vs, mc = store
        vs.batch_size = 2
        mc.upsert = AsyncMock()

        chunks = [
            {"vector": [0.1, 0.2, 0.3, 0.4], "text": f"chunk {i}",
             "source_file": "doc.md"}
            for i in range(5)
        ]

        _run(vs.upsert_chunks(chunks))

        assert mc.upsert.call_count == 3

    def test_upsert_generates_uuid_when_chunk_id_missing(self, store):
        """Line 320: missing chunk_id → uuid generated."""
        vs, mc = store
        mc.upsert = AsyncMock()

        _run(vs.upsert_chunks([
            {"vector": [0.1] * 4, "text": "no id here", "source_file": "x"}
        ]))

        mc.upsert.assert_called_once()
        args_kwargs = mc.upsert.call_args[1]
        points = args_kwargs["points"]
        assert len(points) == 1
        # id should be a non-empty string (uuid)
        assert points[0].id


# ── delete_document() ─────────────────────────────────────────────────────────

class TestDeleteDocument:

    def test_delete_document_raises_if_not_connected(self):
        vs = VectorStore()
        with pytest.raises(RuntimeError, match="not connected"):
            _run(vs.delete_document("some/file.md"))

    def test_delete_document_calls_delete(self, store):
        """Lines 356-369: client.delete called with correct collection."""
        vs, mc = store
        mc.delete = AsyncMock()

        _run(vs.delete_document("docs/guide.md"))

        mc.delete.assert_called_once()
        kwargs = mc.delete.call_args[1]
        assert kwargs["collection_name"] == vs.collection


# ── list_documents() ──────────────────────────────────────────────────────────

class TestListDocuments:

    def test_list_documents_returns_docs(self, store):
        """Lines 406-430: scroll returns points → list of source dicts."""
        vs, mc = store
        mc.scroll = AsyncMock(
            return_value=([_make_point("p1"), _make_point("p2",
                           source_file="other.md")], None)
        )

        results = _run(vs.list_documents())

        assert isinstance(results, list)
        assert len(results) >= 1  # deduped by source_file
        assert "source_file" in results[0]
        assert "chunk_count" in results[0]

    def test_list_documents_with_filter_type(self, store):
        """Lines 383-389: filter_type → conditions built."""
        vs, mc = store
        mc.scroll = AsyncMock(return_value=([], None))

        _run(vs.list_documents(filter_type="pdf"))

        kwargs = mc.scroll.call_args[1]
        assert kwargs.get("scroll_filter") is not None

    def test_list_documents_with_product_filter(self, store):
        """Lines 390-393: product → conditions built."""
        vs, mc = store
        mc.scroll = AsyncMock(return_value=([], None))

        _run(vs.list_documents(product="myproduct"))

        kwargs = mc.scroll.call_args[1]
        assert kwargs.get("scroll_filter") is not None

    def test_list_documents_with_doc_type_filter(self, store):
        """Lines 394-399: doc_type → conditions built."""
        vs, mc = store
        mc.scroll = AsyncMock(return_value=([], None))

        _run(vs.list_documents(doc_type="api"))

        kwargs = mc.scroll.call_args[1]
        assert kwargs.get("scroll_filter") is not None

    def test_list_documents_collection_name_override(self, store):
        """Line 408: collection_name param overrides default."""
        vs, mc = store
        mc.scroll = AsyncMock(return_value=([], None))

        _run(vs.list_documents(collection_name="alt_col"))

        kwargs = mc.scroll.call_args[1]
        assert kwargs["collection_name"] == "alt_col"

    def test_list_documents_stops_when_limit_reached(self, store):
        """Line 406: loop exits when len(docs) >= limit."""
        vs, mc = store
        # Return 3 distinct docs with offset=None → only 1 page call needed
        points = [
            _make_point(f"p{i}", source_file=f"doc{i}.md") for i in range(3)
        ]
        mc.scroll = AsyncMock(return_value=(points, None))

        results = _run(vs.list_documents(limit=2))

        assert len(results) == 2

    def test_list_documents_with_module_filter(self, store):
        """Phase 17: module filter condition built."""
        vs, mc = store
        mc.scroll = AsyncMock(return_value=([], None))

        _run(vs.list_documents(module="Administration"))

        kwargs = mc.scroll.call_args[1]
        assert kwargs.get("scroll_filter") is not None


# ── get_chunk_with_context() ──────────────────────────────────────────────────

class TestGetChunkWithContext:

    def test_get_chunk_returns_empty_if_not_found(self, store):
        """Line 450-451: retrieve returns [] → return []."""
        vs, mc = store
        mc.retrieve = AsyncMock(return_value=[])

        result = _run(vs.get_chunk_with_context("nonexistent-id"))

        assert result == []

    def test_get_chunk_returns_context_window(self, store):
        """Lines 444-486: retrieve + scroll → returns sorted chunk list."""
        vs, mc = store
        target = _make_point("target", chunk_index=2, source_file="a.md")
        neighbor0 = _make_point("n0", chunk_index=1, source_file="a.md")
        neighbor1 = _make_point("n1", chunk_index=3, source_file="a.md")
        # Out-of-window neighbor
        far = _make_point("far", chunk_index=10, source_file="a.md")

        mc.retrieve = AsyncMock(return_value=[target])
        mc.scroll = AsyncMock(return_value=(
            [neighbor0, target, neighbor1, far], None
        ))

        result = _run(vs.get_chunk_with_context("target", context_window=1))

        chunk_indices = [c["chunk_index"] for c in result]
        # Should include indices 1, 2, 3 (window=1 around index 2)
        assert 2 in chunk_indices
        # far (index 10) should be excluded
        assert 10 not in chunk_indices
        # Should be sorted
        assert chunk_indices == sorted(chunk_indices)

    def test_get_chunk_raises_if_not_connected(self):
        """Line 437-438: client None → RuntimeError."""
        vs = VectorStore()
        with pytest.raises(RuntimeError, match="not connected"):
            _run(vs.get_chunk_with_context("some-id"))


# ── get_stats() ───────────────────────────────────────────────────────────────

class TestGetStats:

    def test_get_stats_returns_dict_with_expected_keys(self, store):
        """Lines 494-526: full stats path."""
        vs, mc = store
        fake_info = MagicMock()
        fake_info.points_count = 42
        mc.get_collection = AsyncMock(return_value=fake_info)

        sample_points = [
            _make_point("a", file_type="md", doc_type="guide",
                        source_file="doc1.md"),
            _make_point("b", file_type="pdf", doc_type="api",
                        source_file="doc2.pdf"),
        ]
        mc.scroll = AsyncMock(return_value=(sample_points, None))

        result = _run(vs.get_stats())

        assert result["total_chunks"] == 42
        assert "total_documents" in result
        assert "by_file_type" in result
        assert "by_doc_type" in result
        assert "embed_model" in result
        assert "embed_backend" in result


# ── upsert_chunks_parallel() ─────────────────────────────────────────────────

class TestUpsertChunksParallel:

    def test_parallel_upsert_empty_returns_immediately(self, store):
        """Line 543-544: empty list → early return."""
        vs, mc = store
        _run(vs.upsert_chunks_parallel([]))
        mc.upsert.assert_not_called()

    def test_parallel_upsert_raises_if_not_connected(self):
        """Line 546-547: client None → RuntimeError."""
        vs = VectorStore()
        chunks = [{"vector": [0.1] * 4, "text": "x", "source_file": "a.md"}]
        with pytest.raises(RuntimeError, match="not connected"):
            _run(vs.upsert_chunks_parallel(chunks))

    def test_parallel_upsert_calls_upsert(self, store):
        """Lines 583-590: 3 chunks, batch_size=2, max_parallel=2."""
        vs, mc = store
        vs.batch_size = 2
        mc.upsert = AsyncMock()

        chunks = [
            {"vector": [0.1] * 4, "text": f"t{i}", "source_file": "a.md"}
            for i in range(3)
        ]

        _run(vs.upsert_chunks_parallel(chunks, max_parallel=2))

        # 3 chunks / batch_size 2 → 2 batches → 2 upsert calls
        assert mc.upsert.call_count == 2


# ── close() ──────────────────────────────────────────────────────────────────

class TestClose:

    def test_close_calls_client_close_and_sets_none(self, store):
        """Lines 600-602: close() calls client.close() and nulls self.client."""
        vs, mc = store
        mc.close = AsyncMock()

        _run(vs.close())

        mc.close.assert_called_once()
        assert vs.client is None

    def test_close_is_noop_when_already_closed(self):
        """Line 600: client is None → no-op."""
        vs = VectorStore()
        # Should not raise
        _run(vs.close())


# ── Helper (defined after fixture to avoid forward-ref issues) ────────────────

def _make_store_with_mock():
    """Alternative to the pytest fixture for use in class methods."""
    vs = VectorStore()
    mc = AsyncMock()
    vs.client = mc
    return vs, mc
