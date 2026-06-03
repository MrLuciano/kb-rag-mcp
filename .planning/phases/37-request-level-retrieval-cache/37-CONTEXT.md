# Phase 37: Request-level Retrieval Cache

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** Medium
**Code:** RLCACHE-01
**Competitive Reference:** [kalicyh/mcp-rag](https://github.com/kalicyh/mcp-rag) — request-level retrieval cache
**Promoted from:** `.planning/ROADMAP.md` Backlog (Medium Priority)

## Objective

Add an in-memory LRU cache for identical search queries with configurable `max_entries` and TTL. Reduces redundant embedding + vector search for repeated queries (e.g., polling dashboards, repeated user queries).

## Expected Deliverables

- LRU cache implementation with TTL and max_entries
- Cache key: hash of (query_text + kb_id + filter_params + top_k)
- Cache invalidation: TTL expiry + config-change invalidation (embedding model, filter schema changes)
- Optional Redis backend (disabled by default, enabled via `REDIS_URL` env)
- Prometheus metrics: `cache_hits_total`, `cache_misses_total`, `cache_evictions_total`
- `RLCACHE_ENABLED=true/false` env var to disable (for debugging)

## Cache Key Design

```python
cache_key = hashlib.sha256(
    f"{query_text}|{kb_id}|{filters_json}|{top_k}|{rerank_enabled}".encode()
).hexdigest()
```

Where `filters_json` is sorted canonical JSON of all filter parameters (module, vendor, doc_type, etc.).

## Key Design Decisions

- **Storage:** Python `collections.OrderedDict` for in-memory LRU (simple, no external deps)
- **Redis option:** Optional Redis backend for multi-instance deployments (shared cache across instances)
- **Invalidation:** TTL-based + manual invalidation on config changes (embedding model change, schema change)
- **Cache warming:** No automatic cache warming (cold start is fine — cache builds up on first queries)
- **Scope:** Per-kb_id cache (same query to different KBs is a different cache entry)
- **Memory bound:** `RLCACHE_MAX_ENTRIES=1000` limits memory (LRU eviction when full)

## Implementation Scope

1. LRU cache class in `kb_server/cache/retrieval_cache.py`
2. Redis backend option (use existing `diskcache` pattern from embed cache as reference)
3. Integration into `search_kb` handler: check cache before embedding + search, store result after
4. Config via env: `RLCACHE_ENABLED=true`, `RLCACHE_MAX_ENTRIES=1000`, `RLCACHE_TTL=300`
5. Prometheus metrics for hit rate, eviction rate
6. Cache invalidation on relevant config changes (embedding backend change, filter schema change)

## Open Questions

1. Should cached results be returned directly (skip reranking) or still pass through reranker?
2. How to handle cache stampede (many simultaneous identical requests)?
3. Should we differentiate cache by user/API key (same query from different users = different entries)?

## See Also

- `kalicyh/mcp-rag` retrieval cache (GitHub: kalicyh/mcp-rag)
- `kb_server/cache/` — existing cache patterns
- `kb_server/server.py` — `search_kb` handler
- `observability/metrics.py` — existing Prometheus metrics