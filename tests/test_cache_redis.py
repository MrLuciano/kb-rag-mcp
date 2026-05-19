"""Tests for kb_server/cache/redis.py — RedisCache (fully mocked)."""
from __future__ import annotations

import pickle
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_redis_cache(serialize_method="pickle", default_ttl=None):
    """Instantiate RedisCache with a fully mocked redis.Redis client."""
    mock_redis_module = MagicMock()
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_redis_module.Redis.return_value = mock_client

    with patch.dict("sys.modules", {"redis": mock_redis_module}):
        from kb_server.cache.redis import RedisCache

        cache = RedisCache(
            host="localhost",
            port=6379,
            default_ttl=default_ttl,
            serialize_method=serialize_method,
        )
    # Expose client for assertions
    cache._client = mock_client
    return cache


# ---------------------------------------------------------------------------
# 1. get() returns deserialized value on hit
# ---------------------------------------------------------------------------


def test_get_returns_deserialized_value_on_hit():
    cache = make_redis_cache()
    value = [1.0, 2.0, 3.0]
    serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    cache._client.get.return_value = serialized

    result = cache.get("my_key")
    assert result == value
    cache._client.get.assert_called_once_with("kb-rag:my_key")


# ---------------------------------------------------------------------------
# 2. get() returns None on miss
# ---------------------------------------------------------------------------


def test_get_returns_none_on_miss():
    cache = make_redis_cache()
    cache._client.get.return_value = None
    assert cache.get("missing") is None


# ---------------------------------------------------------------------------
# 3. put() calls _client.set() with correct key prefix (no TTL)
# ---------------------------------------------------------------------------


def test_put_calls_set_with_correct_key_prefix():
    cache = make_redis_cache()
    cache.put("abc", "hello")
    # No TTL → should call .set(), not .setex()
    cache._client.set.assert_called_once()
    call_args = cache._client.set.call_args[0]
    assert call_args[0] == "kb-rag:abc"


# ---------------------------------------------------------------------------
# 4. put() with ttl uses setex
# ---------------------------------------------------------------------------


def test_put_with_ttl_uses_setex():
    cache = make_redis_cache()
    cache.put("ttl_key", "value", ttl=60)
    cache._client.setex.assert_called_once()
    call_args = cache._client.setex.call_args[0]
    assert call_args[0] == "kb-rag:ttl_key"
    assert call_args[1] == 60


# ---------------------------------------------------------------------------
# 5. invalidate returns True when key deleted
# ---------------------------------------------------------------------------


def test_invalidate_returns_true_when_deleted():
    cache = make_redis_cache()
    cache._client.delete.return_value = 1
    assert cache.invalidate("k") is True
    cache._client.delete.assert_called_once_with("kb-rag:k")


# ---------------------------------------------------------------------------
# 6. clear calls scan + delete for prefix keys
# ---------------------------------------------------------------------------


def test_clear_calls_scan_and_delete():
    cache = make_redis_cache()
    # Return cursor=0 on first call so loop terminates
    cache._client.scan.return_value = (0, [b"kb-rag:a", b"kb-rag:b"])
    cache.clear()
    cache._client.scan.assert_called_once()
    cache._client.delete.assert_called_once_with(b"kb-rag:a", b"kb-rag:b")


# ---------------------------------------------------------------------------
# 7. stats() returns dict (smoke test)
# ---------------------------------------------------------------------------


def test_stats_returns_dict():
    cache = make_redis_cache()
    cache._client.info.return_value = {
        "used_memory": 1024 * 1024,
        "used_memory_peak": 2 * 1024 * 1024,
    }
    cache._client.scan.return_value = (0, [])
    result = cache.stats()
    assert isinstance(result, dict)
    assert "backend" in result
    assert result["backend"] == "redis"
