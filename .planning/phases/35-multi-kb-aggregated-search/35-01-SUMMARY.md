# Phase 35 SUMMARY: Multi-KB Aggregated Search

**Date:** 2026-06-11
**Type:** execute
**Status:** Complete

## Changes Made

### `kb_server/collections/router.py` — Multi-KB resolution
- Added `resolve_multi(kb_ids, allow_default)` — resolves multiple KB identifiers to collections, validates existence

### `kb_server/vector_store.py` — Multi-collection search
- Added `multi_search(queries, collections, top_k, ...)` — fans out searches across multiple collections in parallel
- Score normalization via min-max scaling per collection

### `kb_server/server.py` — `search_kb` handler
- Added `kb_ids: Optional[list[str]]` parameter to `search_kb`
- Dispatches to multi-collection search when `kb_ids` is provided
- Merges and deduplicates results using RRF fusion across collections
- Preserves backward compatibility (single-KB path unchanged)

### `kb_server/retrieval/hybrid_search.py` — Multi-collection hybrid support
- Added `merge_multi_collection_results()` — RRF fusion across collection results with provenance

### `tests/test_multi_kb_aggregated_search.py` — 23 new tests
- Multi-KB search parameter handling, provenance tracking, dedup, RRF ordering
- Invalid/duplicate kb_ids, collection not found, empty results
- Backward compatibility with single-KB path

## Verification Results

| Test Suite | Status |
|---|---|
| `test_multi_kb_aggregated_search.py` | 23 passed |
| `test_collection_router.py` | 9 passed |
| `test_server_tools.py` | 32 passed |
| `test_vector_store_unit.py` | 46 passed |
| Full suite | 1061 passed, 12 skipped, 0 failures |

## Fixes Applied

- `ingest/connectors/__init__.py` — Added eager imports for confluence, jira, git (commit `cb42dab`)
