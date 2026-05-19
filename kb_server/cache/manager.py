"""Unified cache manager with metrics and fallback logic.

Provides a single interface for LRU and Redis backends with:
- Automatic fallback to LRU if Redis unavailable
- Prometheus metrics integration
- Hit/miss/eviction tracking
"""

import logging
from typing import Any, Literal, Optional

from observability.metrics import MetricsCollector
from kb_server.cache.lru import LRUCache

logger = logging.getLogger(__name__)


class CacheManager:
    """Unified cache interface with metrics and fallback.

    Args:
        backend: 'lru' or 'redis'
        metrics: MetricsCollector instance (optional)
        **backend_kwargs: Passed to LRUCache or RedisCache
    """

    def __init__(
        self,
        backend: Literal["lru", "redis"] = "lru",
        metrics: Optional[MetricsCollector] = None,
        **backend_kwargs: Any,
    ):
        self._metrics = metrics
        self._backend_type = backend
        self._cache: Any = None

        if backend == "lru":
            self._cache = LRUCache(on_evict=self._on_evict, **backend_kwargs)
            logger.info("CacheManager using LRU backend")
        elif backend == "redis":
            try:
                from kb_server.cache.redis import RedisCache

                self._cache = RedisCache(**backend_kwargs)
                logger.info("CacheManager using Redis backend")
            except ImportError:
                logger.warning("Redis not available, falling back to LRU")
                self._cache = LRUCache(
                    on_evict=self._on_evict, **backend_kwargs
                )
                self._backend_type = "lru"
            except Exception as e:
                logger.error("Redis init failed (%s), falling back to LRU", e)
                self._cache = LRUCache(
                    on_evict=self._on_evict, **backend_kwargs
                )
                self._backend_type = "lru"
        else:
            raise ValueError(f"Unknown cache backend: {backend}")

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache.

        Returns:
            Cached value or None if not found
        """
        value = self._cache.get(key)
        if self._metrics:
            if value is not None:
                self._metrics.cache_hits.labels(
                    backend=self._backend_type
                ).inc()
            else:
                self._metrics.cache_misses.labels(
                    backend=self._backend_type
                ).inc()
        return value

    def put(
        self,
        key: str,
        value: Any,
        size_bytes: Optional[int] = None,
        ttl: Optional[float] = None,
    ) -> None:
        """Insert or update cache entry.

        Args:
            key: Cache key
            value: Value to cache
            size_bytes: Size in bytes (LRU only, estimated if None)
            ttl: TTL in seconds
        """
        self._cache.put(key, value, size_bytes=size_bytes, ttl=ttl)

    def invalidate(self, key: str) -> bool:
        """Remove entry from cache.

        Returns:
            True if key was present and removed
        """
        return self._cache.invalidate(key)

    def clear(self) -> None:
        """Remove all entries from cache."""
        self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        base_stats = self._cache.stats()
        base_stats["backend"] = self._backend_type
        return base_stats

    def _on_evict(self, key: str, value: Any, reason: str) -> None:
        """Eviction callback for LRU cache."""
        if self._metrics:
            self._metrics.cache_evictions.labels(
                backend=self._backend_type, reason=reason
            ).inc()
        logger.debug("Cache eviction: key=%s reason=%s", key, reason)

    @property
    def backend_type(self) -> str:
        """Return backend type ('lru' or 'redis')."""
        return self._backend_type

    @staticmethod
    def hash_key(*parts: Any) -> str:
        """Create cache key from parts using SHA256."""
        return LRUCache.hash_key(*parts)
