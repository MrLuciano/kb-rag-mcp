---
phase: 37-request-level-retrieval-cache
plan: 01
subsystem: cache
tags: retrieval-cache, lru, request-level, observability, metrics

# Dependency graph
requires:
  - phase: 14
    provides: query_logger, metrics framework
  - phase: 17
    provides: filter_terms_cache patterns
provides:
  - Request-level retrieval cache module (RetrievalCache)
  - Cache key generation covering all retrieval-affecting inputs
  - Cache integration in _search_kb with hit/miss/expiry/invalidation
  - Retrieval cache metrics (kb_rag_retrieval_cache_ops_total)
  - invalidate_retrieval_cache() external hook for ingest events

affects:
  - Any future ingest/reclassification code that needs to invalidate cache

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Request-level cache wrapping CacheManager/LRU with deterministic key
    - Cache-first check before resource-intensive embedding + vector search
    - Observable cached flows (metrics + query logging still active)

key-files:
  created:
    - kb_server/cache/request_cache.py
    - tests/test_request_retrieval_cache.py
  modified:
    - kb_server/server.py
    - observability/metrics.py
    - tests/test_server_tools.py
    - tests/test_server_extra.py

key-decisions:
  - "Wrap existing CacheManager rather than building new cache infra"
  - "Cache structured search results (list[dict]) before rendering, not rendered output — rendering is cheap and flexible"
  - "Include all retrieval-affecting inputs in cache key: query, filters, top_k, hybrid/rerank flags, collection, kb_ids"
  - "Use sorted JSON serialization for deterministic keys (same inputs regardless of parameter order)"
  - "Disable retrieval cache by default in tests to prevent cross-test state pollution"

requirements-completed:
  - RLCACHE-01
  - RLCACHE-02
  - RLCACHE-03

# Metrics
duration: 18min
completed: 2026-06-11
---

# Phase 37 Plan 01: Request-level Retrieval Cache Summary

**Request-level LRU retrieval cache wrapping existing CacheManager with deterministic cache-key generation, TTL expiry, explicit invalidation hooks, and observable cached flows preserving query logging and metrics.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-11T00:52:30Z
- **Completed:** 2026-06-11T01:10:46Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- **RetrievalCache module** (`kb_server/cache/request_cache.py`) wrapping existing CacheManager/LRU with deterministic cache-key generation covering all retrieval-affecting inputs: query, collection/KB scope, all metadata filters, top_k, hybrid/rerank flags, and kb_ids
- **Server integration** in `_search_kb`: cache hit skips embedding + vector search + reranking (full pipeline), caching structured results before rendering with no breakage
- **TTL-based expiry** via underlying LRUCache + explicit `invalidate_all()` hook exposed as `invalidate_retrieval_cache()` for ingest/state-change events
- **Preserved observability**: cached flows still log to `query_logger` and emit `record_query()` metrics; new `kb_rag_retrieval_cache_ops_total` counter with hit/miss labels added
- **Cross-test isolation fix**: `reset_server_globals` fixtures in both `test_server_tools.py` and `test_server_extra.py` now save/restore `retrieval_cache` and disable by default

## Task Commits

Each task was committed atomically:

1. **Task 1: Create retrieval-cache module** - `b61babd` (feat)
2. **Task 2: Integrate cache into search path** - `2dd8453` (feat)
3. **Task 3: Preserve observability** - `28517aa` (feat)

**Bug fixes (discovered during execution):**
- `0421c8a` - Fix cross-test retrieval cache pollution (test_server_extra.py)
- `6cc43b3` - Fix cross-test retrieval cache pollution (test_server_tools.py)

**Plan metadata:** Pending (orchestrator commits STATE.md/ROADMAP.md)

## Files Created/Modified

- `kb_server/cache/request_cache.py` - New module: RetrievalCache class wrapping CacheManager, make_cache_key() function with SHA-256 over sorted JSON of all retrieval parameters
- `kb_server/server.py` - Cache initialization in module scope, cache check in _search_kb before embedding/search, cache storage after search, invalidate_retrieval_cache() function, retrieval metrics import
- `observability/metrics.py` - New `retrieval_cache_ops` counter with operation="hit"/"miss" labels and `record_retrieval_cache_op()` helper
- `tests/test_request_retrieval_cache.py` - 22 new tests covering key determinism (14 scenarios), hit/miss, TTL expiry, invalidation, metrics, and multi-entry behavior
- `tests/test_server_tools.py` - 7 new cache integration tests + fixture fix for cross-test isolation  
- `tests/test_server_extra.py` - Fixture fix for cross-test isolation

## Decisions Made

- **Cache structured results, not rendered output** — caching the `list[dict]` before rendering preserves flexibility if format changes, keeps rendering logic unified
- **Wrap CacheManager** — reuses existing LRU + metrics infrastructure instead of building new from scratch
- **Deterministic key via sorted JSON** — avoids ordering bugs; all None/optional inputs are explicitly included so cache keys are stable
- **Disable cache by default in tests** — prevents cross-test contamination where real cache instance from module import leaks state between tests using identical query strings

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Cross-test cache state pollution**
- **Found during:** Task 3 verification (regression sweep)
- **Issue:** `reset_server_globals` fixtures in both test_server_tools.py and test_server_extra.py did not save/restore `retrieval_cache`. The real module-level cache instance leaked state between tests using the same query string, causing a test to receive stale cached results from an earlier test.
- **Fix:** Added `retrieval_cache` save/restore to both fixtures; disabled cache by default in tests
- **Files modified:** `tests/test_server_tools.py`, `tests/test_server_extra.py`
- **Verification:** `test_search_kb_result_with_page_includes_page_info` now passes; full suite at 1095 passing, 0 failing
- **Committed in:** `0421c8a`, `6cc43b3`

---

**Total deviations:** 1 auto-fixed (1 blocking cross-test pollution)
**Impact on plan:** Necessary for correct test isolation. No scope creep.

## Issues Encountered

- **Cross-test cache pollution** — The real `retrieval_cache` instance from module import was shared across tests, causing stale results from one test to leak into another. Fixed by adding `retrieval_cache` to the `reset_server_globals` fixture in both test files.

## Verification Results

All 3 plan-level verification commands pass:

| Command | Result |
|---------|--------|
| `pytest tests/test_cache_manager.py tests/test_request_retrieval_cache.py -q` | 38 passed |
| `pytest tests/test_request_retrieval_cache.py tests/test_server_tools.py -q` | 50 passed |
| `pytest tests/test_request_retrieval_cache.py tests/test_query_logger.py -q` | 33 passed |

Full regression: 1095 passed, 12 skipped, 0 failed (excluding Qdrant-dependent e2e tests)

## Self-Check: PASSED

All created files verified on disk, all 5 commits present in git history.

## Next Phase Readiness

- Request-level retrieval cache complete with deterministic keys, TTL expiry, invalidation hooks
- Cached flows remain observable through query logging and metrics
- Ready for next step: Phase 37 execution is complete
