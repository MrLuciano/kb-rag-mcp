"""Tests for kb_server/cache/request_cache.py — RetrievalCache."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from kb_server.cache.request_cache import (
    RetrievalCache,
    make_cache_key,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_metrics():
    m = MagicMock()
    m.cache_hits.labels.return_value = MagicMock()
    m.cache_misses.labels.return_value = MagicMock()
    m.cache_evictions.labels.return_value = MagicMock()
    return m


# ---------------------------------------------------------------------------
# make_cache_key — determinism and coverage of inputs
# ---------------------------------------------------------------------------


class TestMakeCacheKey:
    """Deterministic key generation covers all retrieval-affecting inputs."""

    def test_deterministic_identical_inputs(self):
        """Same inputs always produce the same key."""
        k1 = make_cache_key(query="ssl config", top_k=5)
        k2 = make_cache_key(query="ssl config", top_k=5)
        assert k1 == k2
        assert len(k1) == 64

    def test_different_query_different_key(self):
        """Different queries produce different keys."""
        k1 = make_cache_key(query="ssl")
        k2 = make_cache_key(query="proxy")
        assert k1 != k2

    def test_different_top_k_different_key(self):
        """Different top_k produces a different key."""
        k1 = make_cache_key(query="test", top_k=5)
        k2 = make_cache_key(query="test", top_k=10)
        assert k1 != k2

    def test_filters_affect_key(self):
        """Metadata filter parameters are part of the key."""
        k1 = make_cache_key(query="test", product="AppServer")
        k2 = make_cache_key(query="test", product="DataSync")
        assert k1 != k2

    def test_hybrid_flag_affects_key(self):
        """Boolean flags (hybrid/rerank) are part of the key."""
        k1 = make_cache_key(query="test")
        k2 = make_cache_key(query="test", hybrid=True)
        assert k1 != k2

    def test_rerank_flag_affects_key(self):
        k1 = make_cache_key(query="test")
        k2 = make_cache_key(query="test", rerank=True)
        assert k1 != k2

    def test_collection_param_affects_key(self):
        k1 = make_cache_key(query="test")
        k2 = make_cache_key(query="test", collection_param="kb_hr")
        assert k1 != k2

    def test_kb_ids_affects_key(self):
        k1 = make_cache_key(query="test")
        k2 = make_cache_key(query="test", kb_ids=["kb_hr", "kb_eng"])
        assert k1 != k2

    def test_kb_ids_order_independent(self):
        """kb_ids order should not affect the key (sorted internally)."""
        k1 = make_cache_key(query="test", kb_ids=["kb_eng", "kb_hr"])
        k2 = make_cache_key(query="test", kb_ids=["kb_hr", "kb_eng"])
        assert k1 == k2

    def test_filter_type_affects_key(self):
        k1 = make_cache_key(query="test", filter_type="pdf")
        k2 = make_cache_key(query="test", filter_type="txt")
        assert k1 != k2

    def test_version_affects_key(self):
        k1 = make_cache_key(query="test", version="22.3")
        k2 = make_cache_key(query="test", version="24.4")
        assert k1 != k2

    def test_vendor_affects_key(self):
        k1 = make_cache_key(query="test", vendor="OpenText")
        k2 = make_cache_key(query="test", vendor="Adobe")
        assert k1 != k2

    def test_subsystem_affects_key(self):
        k1 = make_cache_key(query="test", subsystem="API")
        k2 = make_cache_key(query="test", subsystem="Admin")
        assert k1 != k2

    def test_module_affects_key(self):
        k1 = make_cache_key(query="test", module="Security")
        k2 = make_cache_key(query="test", module="Configuration")
        assert k1 != k2

    def test_unicode_handling(self):
        """Unicode characters in queries do not break key generation."""
        key = make_cache_key(
            query="café configuratiön",
            product="Prüf",
        )
        assert len(key) == 64
        assert isinstance(key, str)


# ---------------------------------------------------------------------------
# RetrievalCache — hit / miss / expiry / invalidation
# ---------------------------------------------------------------------------


class TestRetrievalCache:
    """Request-level retrieval cache wraps CacheManager correctly."""

    def test_miss_returns_none(self):
        """Cache miss on empty cache returns None."""
        cache = RetrievalCache(max_entries=100, ttl=300)
        key = cache.make_key(query="missing")
        assert cache.get(key) is None

    def test_hit_returns_stored_value(self):
        """Cache hit returns the previously stored value."""
        cache = RetrievalCache(max_entries=100, ttl=300)
        key = cache.make_key(query="ssl")
        results = [
            {
                "chunk_id": "1",
                "score": 0.95,
                "text": "SSL config",
                "source_file": "doc.md",
            },
        ]
        cache.put(key, results)
        assert cache.get(key) == results

    def test_put_get_round_trip(self):
        """Multiple entries round-trip correctly."""
        cache = RetrievalCache(max_entries=100, ttl=300)
        k1 = cache.make_key(query="ssl")
        k2 = cache.make_key(query="proxy")
        cache.put(k1, [{"id": "a"}])
        cache.put(k2, [{"id": "b"}])
        assert cache.get(k1) == [{"id": "a"}]
        assert cache.get(k2) == [{"id": "b"}]

    def test_invalidate_removes_entry(self):
        """invalidate() removes a specific key."""
        cache = RetrievalCache(max_entries=100, ttl=300)
        key = cache.make_key(query="ssl")
        cache.put(key, ["data"])
        assert cache.invalidate(key) is True
        assert cache.get(key) is None

    def test_invalidate_nonexistent_returns_false(self):
        cache = RetrievalCache(max_entries=100, ttl=300)
        assert cache.invalidate("nonexistent") is False

    def test_invalidate_all_clears_cache(self):
        """invalidate_all() removes all entries."""
        cache = RetrievalCache(max_entries=100, ttl=300)
        k1 = cache.make_key(query="ssl")
        k2 = cache.make_key(query="proxy")
        cache.put(k1, ["a"])
        cache.put(k2, ["b"])
        cache.invalidate_all()
        assert cache.get(k1) is None
        assert cache.get(k2) is None

    def test_ttl_expiry(self):
        """Entries expire after TTL elapses."""
        cache = RetrievalCache(max_entries=100, ttl=0.01)
        key = cache.make_key(query="ssl")
        cache.put(key, ["expires_soon"])
        # Should be present immediately
        assert cache.get(key) == ["expires_soon"]
        # Wait for expiry
        time.sleep(0.02)
        assert cache.get(key) is None

    def test_ttl_extended_works(self):
        """Entry with explicit longer TTL outlives the default."""
        cache = RetrievalCache(max_entries=100, ttl=0.01)
        key = cache.make_key(query="ssl")
        # Put with explicit ttl that is longer than default
        cache.put(key, ["long_lived"], ttl=60)
        # Should be present immediately
        assert cache.get(key) == ["long_lived"]
        # Wait for default TTL to expire but custom TTL should keep it alive
        time.sleep(0.02)
        assert cache.get(key) == ["long_lived"]

    def test_make_key_delegates_correctly(self):
        """RetrievalCache.make_key matches module-level make_cache_key."""
        cache = RetrievalCache(max_entries=100, ttl=300)
        instance_key = cache.make_key(
            query="test",
            top_k=5,
            product="AppServer",
        )
        module_key = make_cache_key(
            query="test",
            top_k=5,
            product="AppServer",
        )
        assert instance_key == module_key

    def test_stats_contains_backend(self):
        """stats() returns at least the backend key."""
        cache = RetrievalCache(max_entries=100, ttl=300)
        s = cache.stats()
        assert "backend" in s
        assert s["backend"] == "lru"

    def test_metrics_are_recorded(self):
        """CacheManager metrics are wired through RetrievalCache."""
        m = make_metrics()
        cache = RetrievalCache(max_entries=100, ttl=300, metrics=m)
        key = cache.make_key(query="ssl")

        # Miss
        cache.get(key)
        # Hit
        cache.put(key, ["data"])
        cache.get(key)

        # Metrics calls happened
        m.cache_misses.labels.assert_called()
        m.cache_hits.labels.assert_called()

    def test_max_entries_does_not_break(self):
        """Creating a cache with various max_entries values works."""
        for n in [10, 100, 1000]:
            cache = RetrievalCache(max_entries=n, ttl=300)
            assert cache.stats()["backend"] == "lru"
