"""
Request-level retrieval cache for repeated search queries.

PHASE 37: Wraps the existing CacheManager and LRU primitives with
retrieval-specific cache-key generation, TTL management, and
explicit invalidation hooks.

Usage:
    cache = RetrievalCache(ttl=300)
    key = cache.make_key(query="ssl", top_k=5, ...)
    results = cache.get(key)
    if results is None:
        results = await perform_search(...)
        cache.put(key, results)
"""

import hashlib
import json
import logging
import os
from typing import Any, Optional

from kb_server.cache.manager import CacheManager

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────
_RLCACHE_ENABLED = os.getenv("RLCACHE_ENABLED", "true").lower() in (
    "true", "1", "yes"
)
_RLCACHE_TTL = int(os.getenv("RLCACHE_TTL", "300"))
_RLCACHE_MAX_ENTRIES = int(os.getenv("RLCACHE_MAX_ENTRIES", "1000"))


def make_cache_key(
    query: str,
    top_k: int = 5,
    filter_type: Optional[str] = None,
    product: Optional[str] = None,
    doc_type: Optional[str] = None,
    version: Optional[str] = None,
    vendor: Optional[str] = None,
    subsystem: Optional[str] = None,
    module: Optional[str] = None,
    hybrid: bool = False,
    rerank: bool = False,
    collection_param: Optional[str] = None,
    kb_ids: Optional[list[str]] = None,
) -> str:
    """Build a deterministic cache key from all retrieval-affecting inputs.

    Every argument that influences the search result must be included
    so that two requests produce the same key only when all retrieval
    parameters match exactly.

    Returns:
        A 64-character hex digest (SHA-256).
    """
    # Canonicalise filters as sorted JSON so equivalent dicts produce
    # the same key regardless of key order.
    filters = {
        "query": query,
        "top_k": top_k,
        "filter_type": filter_type,
        "product": product,
        "doc_type": doc_type,
        "version": version,
        "vendor": vendor,
        "subsystem": subsystem,
        "module": module,
        "hybrid": hybrid,
        "rerank": rerank,
        "collection": collection_param,
        "kb_ids": sorted(kb_ids) if kb_ids else None,
    }
    canonical = json.dumps(filters, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest


class RetrievalCache:
    """Request-level retrieval cache backed by CacheManager.

    Wraps the existing CacheManager (LRU or Redis) with
    retrieval-specific key generation and a simplified API.
    """

    def __init__(
        self,
        max_entries: int = _RLCACHE_MAX_ENTRIES,
        ttl: int = _RLCACHE_TTL,
        metrics: Any = None,
    ):
        """Initialise the retrieval cache.

        Args:
            max_entries: Approximate maximum number of entries (used to
                derive a size budget for the underlying LRU).
            ttl: Default TTL in seconds for cached entries.
            metrics: Optional MetricsCollector instance.
        """
        # Size budget: estimate ~1 KB per entry for result metadata.
        size_budget_mb = max(10, (max_entries * 1024) // (1024 * 1024))
        self._manager = CacheManager(
            backend="lru",
            metrics=metrics,
            max_size_mb=size_budget_mb,
        )
        self._default_ttl = float(ttl)
        log.info(
            "RetrievalCache initialised: max_entries=%d ttl=%ds "
            "size_budget_mb=%d",
            max_entries,
            ttl,
            size_budget_mb,
        )

    # ── Public API ───────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached results.

        Args:
            key: Cache key from make_cache_key().

        Returns:
            Cached search results (list[dict]) or None if not found/expired.
        """
        return self._manager.get(key)

    def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """Store search results in cache.

        Args:
            key: Cache key from make_cache_key().
            value: Data to cache (typically list[dict] of search results).
            ttl: TTL in seconds (defaults to instance default).
        """
        self._manager.put(key, value, ttl=ttl or self._default_ttl)

    def invalidate(self, key: str) -> bool:
        """Remove a single entry from the cache.

        Args:
            key: Cache key to remove.

        Returns:
            True if the key existed and was removed.
        """
        return self._manager.invalidate(key)

    def invalidate_all(self) -> None:
        """Clear all entries from the retrieval cache."""
        self._manager.clear()
        log.info("RetrievalCache fully invalidated")

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return self._manager.stats()

    @property
    def enabled(self) -> bool:
        """Whether the retrieval cache is active."""
        return _RLCACHE_ENABLED

    @staticmethod
    def make_key(
        query: str,
        top_k: int = 5,
        filter_type: Optional[str] = None,
        product: Optional[str] = None,
        doc_type: Optional[str] = None,
        version: Optional[str] = None,
        vendor: Optional[str] = None,
        subsystem: Optional[str] = None,
        module: Optional[str] = None,
        hybrid: bool = False,
        rerank: bool = False,
        collection_param: Optional[str] = None,
        kb_ids: Optional[list[str]] = None,
    ) -> str:
        """Build a deterministic cache key (delegates to module-level function).

        See :func:`make_cache_key` for details.
        """
        return make_cache_key(
            query=query,
            top_k=top_k,
            filter_type=filter_type,
            product=product,
            doc_type=doc_type,
            version=version,
            vendor=vendor,
            subsystem=subsystem,
            module=module,
            hybrid=hybrid,
            rerank=rerank,
            collection_param=collection_param,
            kb_ids=kb_ids,
        )
