---
phase: 35-multi-kb-aggregated-search
plan: 01
subsystem: retrieval
tags: multi-kb, aggregated-search, rrf, fusion, backward-compatible
requires:
  - phase: 27-kb-registry
    provides: CollectionRouter.resolve(), KB identifier resolution
  - phase: 12-search-quality
    provides: Hybrid search with BM25 + dense, RRF fusion pattern
provides:
  - Multi-KB aggregated search via `search_kb(kb_ids=[...])`
  - CollectionRouter.resolve_multi() for resolving KB ID lists to collections
  - VectorStore.multi_search() for parallel collection search with provenance
  - merge_multi_collection_results() with min-max normalization, RRF fusion, dedup
affects:
  - Phase 37 request cache (cache keys include kb_ids)
  - Any future multi-collection or cross-KB features

tech-stack:
  added: []
  patterns:
    - Parallel collection dispatch with asyncio.gather
    - Per-collection score normalization before RRF fusion
    - Provenance tagging with `_collection` field in results
    - Filter propagation across all collections from single filter spec

key-files:
  created: []
  modified:
    - kb_server/server.py
    - kb_server/collections/router.py
    - kb_server/vector_store.py
    - kb_server/retrieval/hybrid_search.py
    - tests/test_collection_router.py
    - tests/test_hybrid_search.py
    - tests/test_server_tools.py
    - tests/test_vector_store_unit.py

key-decisions:
  - "CollectionRouter.resolve_multi() reuses existing resolve_kb_id() from Phase 27"
  - "Min-max score normalization per collection prevents high-score collections from dominating RRF"
  - "chunk_id deduplication — same chunk in multiple KBs appears once (highest score wins)"
  - "Fail fast on invalid KB IDs — error returned, no silent skipping"
  - "Empty kb_ids defaults to single-KB behavior (backward compatible)"
  - "Reranking disabled for multi-KB searches — cross-collection score distributions make reranking impractical"

patterns-established:
  - "Parallel collection dispatch: multi_search() gathers per-collection searches concurrently"
  - "Score normalization before fusion: _min_max_normalize() transforms per-collection scores to [0,1] before RRF"
  - "Provenance annotation with _collection tag: each result carries its source KB/collection name"

requirements-completed:
  - MULTIKB-01
  - MULTIKB-02
  - MULTIKB-03

duration: 26min
completed: 2026-06-10
---

# Phase 35: Multi-KB Aggregated Search Summary

**`search_kb` tool accepts `kb_ids` list parameter, fans out search across multiple collections in parallel, normalizes scores per collection, fuses via RRF, deduplicates by chunk_id, and returns merged results with provenance**

## Performance

- **Duration:** 26 min (implementation) + 6 min (tests)
- **Started:** 2026-06-10T23:21:24Z
- **Completed:** 2026-06-10T23:27:37Z
- **Tasks:** 2 (feat + tests)
- **Files modified:** 8

## Accomplishments

- `CollectionRouter.resolve_multi()` validates and resolves a list of KB IDs to collection names
- `VectorStore.multi_search()` executes parallel search across multiple collections with provenance tagging
- `merge_multi_collection_results()` normalizes scores per collection, applies RRF fusion, deduplicates by chunk_id
- `search_kb` handler dispatches to multi-KB path when `kb_ids` is provided, single-KB path unchanged
- 22 regression tests across 4 test files covering all edge cases (empty, missing, invalid, provenance, dedup, backward compat)

## Task Commits

Each task was committed atomically:

1. **Task 1: Multi-KB aggregated search implementation** - `086efb0` (feat)
2. **Task 2: Tests for multi-KB aggregated search** - `50a068b` (test)

## Files Created/Modified

- `kb_server/server.py` - Added `kb_ids` parameter to `search_kb`, multi-KB dispatch with error handling
- `kb_server/collections/router.py` - Added `resolve_multi()` for KB ID list resolution
- `kb_server/vector_store.py` - Added `multi_search()` with parallel collection search and `_collection` provenance tag
- `kb_server/retrieval/hybrid_search.py` - Added `_min_max_normalize()` and `merge_multi_collection_results()` with RRF fusion and dedup
- `tests/test_collection_router.py` - 5 tests: all-existing, empty, missing, single, None
- `tests/test_hybrid_search.py` - 9 tests: normalize identity/single/identical/empty, merge empty/single/dedup/top-k/RRF
- `tests/test_server_tools.py` - 4 tests: routes-to-multi, not-found, no-results, rerank-disabled
- `tests/test_vector_store_unit.py` - 4 tests: no-client, empty-collections, parallel-tag, filters-passthrough

## Decisions Made

- Reused existing `CollectionRouter.resolve_kb_id()` from Phase 27 for per-ID resolution
- Min-max normalization per collection before RRF fusion prevents score-bias toward collections with wider score distributions
- chunk_id deduplication handles the case where the same document was indexed into multiple KBs
- Reranking disabled for multi-KB — cross-collection score distributions make cross-encoder reranking unreliable
- Invalid KB IDs produce a `CollectionNotFoundError` response rather than silently excluding them
- Cache keys in Phase 37's retrieval cache include `kb_ids` parameter for proper cache isolation

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encounterated

None.

## User Setup Required

None — no external service configuration required. Feature is opt-in via `kb_ids` parameter on `search_kb`.

## Next Phase Readiness

- Multi-KB search integrated with Phase 37 retrieval cache (cache keys include kb_ids)
- Pattern ready for future multi-collection features

---
*Phase: 35-multi-kb-aggregated-search*
*Completed: 2026-06-10*
