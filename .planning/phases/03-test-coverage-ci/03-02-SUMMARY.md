---
phase: "03"
plan: "02"
subsystem: "tests"
tags: [testing, unit-tests, mocking, server, embed_client, reranker]
key-files:
  created:
    - tests/test_server_tools.py
    - tests/test_embed_client_unit.py
    - tests/test_reranker_unit.py
decisions:
  - Stubbed `fastembed`/`tokenizers` in reranker tests to avoid missing-module errors without installing heavy deps
  - Injected mock model via `reranker.model = mock` (attribute is `self.model`, not `_model`)
  - Patched `kb_server.retrieval.hybrid_search.get_hybrid_searcher` and `kb_server.retrieval.reranker.get_reranker` in server tests using the module import path
metrics:
  duration: "~3 min"
  completed: "2026-05-19"
  tasks_completed: 4
  files_created: 3
---

# Phase 03 Plan 02: Unit Tests — Server Tools, Embed Client, Reranker

**One-liner:** Unit tests with AsyncMock patching for server tool handlers, embed_client HTTP backends, and CrossEncoderReranker lazy-load model.

## Test Counts

| File | Tests | Status |
|------|-------|--------|
| `tests/test_server_tools.py` | 12 | ✅ all pass |
| `tests/test_embed_client_unit.py` | 8 | ✅ all pass |
| `tests/test_reranker_unit.py` | 6 | ✅ all pass |
| **Total** | **26** | **✅ 26/26** |

## Pytest Exit Code

```
26 passed in 25.71s
```

Exit code: **0**

## What Was Tested

### test_server_tools.py (12 tests)
1. `_search_kb` basic: result text in TextContent
2. `_search_kb` zero results → "no results" message
3. `collection_router=None` → uses `store.collection` default
4. `CollectionNotFoundError` → error TextContent (no exception raised)
5. `hybrid=True` → routes to `get_hybrid_searcher()`
6. `rerank=True` → routes to `get_reranker()`
7. `query_logger.log_query()` called after search
8. `_list_documents` → listing with source_file
9. `_list_documents` empty → empty-state message
10. `_get_chunk` found → TextContent with chunk text
11. `_get_chunk` not found → error TextContent
12. `_kb_stats` → TextContent with document/chunk counts

### test_embed_client_unit.py (8 tests)
1. openai-compat: mocked HTTP → 768 floats
2. ollama: mocked HTTP → 768 floats
3. HTTP 500 → `HTTPStatusError` raised
4. `ConnectError` propagates
5. `get_embeddings_batch` returns same length as input
6. `use_cache=False` bypasses cache entirely
7. `use_cache=True` caches result; second call uses cache
8. `get_embed_dim()` returns positive integer

### test_reranker_unit.py (6 tests)
1. `rerank()` sorts results by cross-encoder score descending
2. `rerank()` with empty results returns `[]`
3. `rerank()` truncates to `top_k`
4. `_load_model()` is lazy (`model is None` after `__init__`)
5. `rerank_with_cache()` without cache returns same as `rerank()`
6. `_load_model` failure propagates from `rerank()`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tokenizers` module missing for fastembed import chain**
- **Found during:** test collection
- **Issue:** `kb_server/retrieval/__init__.py` imports `hybrid_search.py` which imports `fastembed` which requires `tokenizers`. Module not installed.
- **Fix:** Added `sys.modules` stubs for `tokenizers`, `fastembed` and submodules at top of `test_reranker_unit.py` before importing reranker.
- **Files modified:** `tests/test_reranker_unit.py`

## Self-Check: PASSED

- [x] `tests/test_server_tools.py` — exists, 12 tests
- [x] `tests/test_embed_client_unit.py` — exists, 8 tests
- [x] `tests/test_reranker_unit.py` — exists, 6 tests
- [x] Commit `b87cdb5` — confirmed in git log
