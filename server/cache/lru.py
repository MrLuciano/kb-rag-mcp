"""In-memory LRU cache with automatic RAM-based sizing.

Features:
- Thread-safe OrderedDict-based LRU eviction
- Auto-tunes max_size based on available system RAM
- TTL support for cache entries
- Size tracking and eviction callbacks
"""

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""

    key: str
    value: Any
    size_bytes: int
    created_at: float
    last_accessed: float
    ttl: Optional[float] = None  # seconds, None = never expires

    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL."""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl


class LRUCache:
    """Thread-safe LRU cache with TTL and RAM auto-tuning.

    Auto-sizing:
    - If max_size_mb is None, auto-tunes to 10% of available RAM
    - Minimum: 100 MB
    - Maximum: 4 GB

    Args:
        max_size_mb: Maximum cache size in MB (None = auto)
        default_ttl: Default TTL in seconds (None = no expiry)
        on_evict: Callback (key, value, reason) when entry evicted
    """

    def __init__(
        self,
        max_size_mb: Optional[int] = None,
        default_ttl: Optional[float] = None,
        on_evict: Optional[Callable[[str, Any, str], None]] = None,
    ):
        self._lock = RLock()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._default_ttl = default_ttl
        self._on_evict = on_evict

        # Auto-tune max size
        if max_size_mb is None:
            max_size_mb = self._auto_tune_size_mb()
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._current_size_bytes = 0

        logger.info(
            "LRUCache initialized: max_size_mb=%d, default_ttl=%s",
            max_size_mb,
            default_ttl,
        )

    def _auto_tune_size_mb(self) -> int:
        """Auto-tune cache size based on available RAM."""
        try:
            import psutil

            available_mb = psutil.virtual_memory().available // (1024 * 1024)
            # Use 10% of available RAM
            auto_mb = max(100, min(4096, available_mb // 10))
            logger.info(
                "Auto-tuned cache size: %d MB (available RAM: %d MB)",
                auto_mb,
                available_mb,
            )
            return auto_mb
        except ImportError:
            logger.warning("psutil not available, using default 512 MB cache")
            return 512
        except Exception as e:
            logger.error("Failed to auto-tune cache size: %s, using 512 MB", e)
            return 512

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache, updating LRU order.

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            # Check expiry
            if entry.is_expired():
                self._evict(key, "expired")
                return None

            # Update LRU order
            self._cache.move_to_end(key)
            entry.last_accessed = time.time()
            return entry.value

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
            size_bytes: Size in bytes (estimated if None)
            ttl: TTL in seconds (uses default_ttl if None)
        """
        if ttl is None:
            ttl = self._default_ttl

        if size_bytes is None:
            size_bytes = self._estimate_size(value)

        with self._lock:
            # Remove old entry if exists
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_size_bytes -= old_entry.size_bytes

            # Create new entry
            now = time.time()
            entry = CacheEntry(
                key=key,
                value=value,
                size_bytes=size_bytes,
                created_at=now,
                last_accessed=now,
                ttl=ttl,
            )

            # Evict until we have space
            while self._current_size_bytes + size_bytes > self._max_size_bytes:
                if not self._cache:
                    logger.warning(
                        "Cannot cache %s: size %d exceeds max %d",
                        key,
                        size_bytes,
                        self._max_size_bytes,
                    )
                    return
                # Evict LRU (first item in OrderedDict)
                lru_key = next(iter(self._cache))
                self._evict(lru_key, "size_limit")

            # Insert
            self._cache[key] = entry
            self._current_size_bytes += size_bytes
            self._cache.move_to_end(key)

    def invalidate(self, key: str) -> bool:
        """Remove entry from cache.

        Returns:
            True if key was present and removed
        """
        with self._lock:
            if key in self._cache:
                self._evict(key, "manual")
                return True
            return False

    def clear(self) -> None:
        """Remove all entries from cache."""
        with self._lock:
            keys = list(self._cache.keys())
            for key in keys:
                self._evict(key, "clear")

    def _evict(self, key: str, reason: str) -> None:
        """Internal: evict entry and update size."""
        entry = self._cache.pop(key)
        self._current_size_bytes -= entry.size_bytes
        if self._on_evict:
            try:
                self._on_evict(key, entry.value, reason)
            except Exception as e:
                logger.error("Eviction callback error for %s: %s", key, e)

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        import sys

        if isinstance(value, (list, tuple)):
            # Embedding vector
            if value and isinstance(value[0], (int, float)):
                return len(value) * 8  # 8 bytes per float64
            return sys.getsizeof(value)
        return sys.getsizeof(value)

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            return {
                "size_bytes": self._current_size_bytes,
                "size_mb": self._current_size_bytes / (1024 * 1024),
                "max_size_bytes": self._max_size_bytes,
                "max_size_mb": self._max_size_bytes / (1024 * 1024),
                "entries": len(self._cache),
                "utilization_pct": (
                    (100.0 * self._current_size_bytes / self._max_size_bytes)
                    if self._max_size_bytes > 0
                    else 0.0
                ),
            }

    @staticmethod
    def hash_key(*parts: Any) -> str:
        """Create cache key from parts using SHA256.

        Args:
            *parts: Key components (will be str() converted)

        Returns:
            Hex digest of concatenated parts
        """
        combined = "|".join(str(p) for p in parts)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
