"""Tests for terms table / distinct value methods."""

import sys
import types
import os

import pytest


def _ensure_stubs():
    import qdrant_client  # noqa: F401
    ec_name = "kb_server.embed_client"
    if ec_name not in sys.modules:
        ec = types.ModuleType(ec_name)
        ec.get_embed_dim = lambda: 4
        sys.modules[ec_name] = ec
    qc = sys.modules["qdrant_client"]
    qc.AsyncQdrantClient = object


_ensure_stubs()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kb_server.vector_store import VectorStore
from kb_server.filter_terms_cache import FilterTermsCache


def _run(coro):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def store():
    from unittest.mock import AsyncMock
    vs = VectorStore()
    mock_client = AsyncMock()
    vs.client = mock_client
    return vs, mock_client


class TestGetDistinctValues:

    def test_get_distinct_values_empty_when_no_client(self, store):
        vs, mc = store
        vs.client = None
        result = _run(vs.get_distinct_values(field="product"))
        assert result == []

    def test_get_distinct_values_returns_list(self, store):
        vs, mc = store
        mc.scroll.return_value = ([], None)
        result = _run(vs.get_distinct_values(
            field="product",
            collection_name="test_collection",
        ))
        assert isinstance(result, list)

    def test_get_distinct_values_with_limit(self, store):
        vs, mc = store
        mc.scroll.return_value = ([], None)
        result = _run(vs.get_distinct_values(
            field="product",
            top_n=3,
            collection_name="test_collection",
        ))
        assert isinstance(result, list)

    def test_get_distinct_values_with_counts(self, store):
        vs, mc = store
        mc.scroll.return_value = ([], None)
        result = _run(vs.get_distinct_values(
            field="product",
            with_counts=True,
            collection_name="test_collection",
        ))
        assert isinstance(result, list)


class TestFilterTermsCache:

    def test_cache_initialization(self, store):
        vs, mc = store
        cache = FilterTermsCache(store=vs)
        assert cache is not None
        assert cache.terms == {}
        assert cache.last_scan_mtime == 0

    def test_cache_get_formatted_empty(self):
        cache = FilterTermsCache(store=None)
        result = cache.get_formatted(field="product", top_n=20)
        assert result == ""

    def test_cache_needs_refresh_no_marker(self, store):
        vs, mc = store
        cache = FilterTermsCache(store=vs)
        assert cache._needs_refresh() is False
