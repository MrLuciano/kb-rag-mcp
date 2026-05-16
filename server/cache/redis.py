"""Optional Redis cache backend.

Requires redis package. Falls back to LRU if unavailable.

Features:
- Distributed caching across multiple server instances
- Persistent cache across restarts
- TTL support via Redis EXPIRE
- Atomic operations
"""

import json
import logging
import pickle
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-backed cache with TTL and serialization.

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password (optional)
        default_ttl: Default TTL in seconds (None = no expiry)
        key_prefix: Prefix for all keys (namespace isolation)
        serialize_method: 'json' or 'pickle'
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: Optional[int] = None,
        key_prefix: str = "kb-rag:",
        serialize_method: str = "pickle",
    ):
        try:
            import redis
        except ImportError:
            raise ImportError(
                "redis package required for RedisCache. "
                "Install with: pip install redis"
            )

        self._client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=False,  # Binary mode
        )
        self._default_ttl = default_ttl
        self._key_prefix = key_prefix
        self._serialize_method = serialize_method

        # Test connection
        try:
            self._client.ping()
            logger.info(
                "RedisCache connected: %s:%d db=%d prefix=%s",
                host,
                port,
                db,
                key_prefix,
            )
        except Exception as e:
            logger.error("Redis connection failed: %s", e)
            raise

    def _make_key(self, key: str) -> str:
        """Prepend namespace prefix to key."""
        return f"{self._key_prefix}{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value to bytes."""
        if self._serialize_method == "json":
            return json.dumps(value).encode("utf-8")
        elif self._serialize_method == "pickle":
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            raise ValueError(
                f"Unknown serialize method: {self._serialize_method}"
            )

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to value."""
        if self._serialize_method == "json":
            return json.loads(data.decode("utf-8"))
        elif self._serialize_method == "pickle":
            return pickle.loads(data)
        else:
            raise ValueError(
                f"Unknown serialize method: {self._serialize_method}"
            )

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from Redis.

        Returns:
            Cached value or None if not found
        """
        try:
            redis_key = self._make_key(key)
            data = self._client.get(redis_key)
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error("Redis GET error for %s: %s", key, e)
            return None

    def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Insert or update cache entry in Redis.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default_ttl if None)
            **kwargs: Ignored (for interface compatibility)
        """
        if ttl is None:
            ttl = self._default_ttl

        try:
            redis_key = self._make_key(key)
            data = self._serialize(value)
            if ttl is not None:
                self._client.setex(redis_key, ttl, data)
            else:
                self._client.set(redis_key, data)
        except Exception as e:
            logger.error("Redis PUT error for %s: %s", key, e)

    def invalidate(self, key: str) -> bool:
        """Remove entry from Redis.

        Returns:
            True if key was present and removed
        """
        try:
            redis_key = self._make_key(key)
            deleted = self._client.delete(redis_key)
            return deleted > 0
        except Exception as e:
            logger.error("Redis DELETE error for %s: %s", key, e)
            return False

    def clear(self) -> None:
        """Remove all entries with this cache's prefix."""
        try:
            pattern = f"{self._key_prefix}*"
            cursor = 0
            while True:
                cursor, keys = self._client.scan(
                    cursor, match=pattern, count=100
                )
                if keys:
                    self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.error("Redis CLEAR error: %s", e)

    def stats(self) -> dict[str, Any]:
        """Return Redis cache statistics."""
        try:
            info = self._client.info("memory")
            pattern = f"{self._key_prefix}*"
            cursor, keys = self._client.scan(0, match=pattern, count=1000)
            entry_count = len(keys)
            # Approximate count if scan incomplete
            if cursor != 0:
                entry_count = f"~{entry_count}+"

            return {
                "backend": "redis",
                "entries": entry_count,
                "used_memory_mb": (info.get("used_memory", 0) / (1024 * 1024)),
                "used_memory_peak_mb": (
                    info.get("used_memory_peak", 0) / (1024 * 1024)
                ),
            }
        except Exception as e:
            logger.error("Redis STATS error: %s", e)
            return {"backend": "redis", "error": str(e)}

    @staticmethod
    def hash_key(*parts: Any) -> str:
        """Create cache key from parts (delegates to LRU)."""
        from server.cache.lru import LRUCache

        return LRUCache.hash_key(*parts)
