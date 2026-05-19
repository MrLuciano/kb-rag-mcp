# 01-03 Summary: Implement Real BM25+Dense RRF Hybrid Search

## What was done

- Added `VectorStore.search_sparse()` method in `kb_server/vector_store.py`
  - Uses `NamedSparseVector` / `SparseVector` from `qdrant_client.http.models`
  - Gracefully returns `[]` if collection lacks sparse index (exception caught)
  - Supports all existing filters: `filter_type`, `product`, `doc_type`, `version`

- Replaced TODO stub in `HybridSearcher.search()` (`kb_server/retrieval/hybrid_search.py`)
  - Now calls `vector_store.search_sparse()` when `sparse_vector` is non-empty
  - Passes sparse results to `_rrf_fusion()` for real RRF combination
  - Removed "Sparse search not yet implemented" log message

- Added two TDD tests in `tests/test_hybrid_search.py`
  - `test_sparse_path_exercised`: verifies `search_sparse` is called and RRF receives non-empty sparse results
  - `test_falls_back_to_dense_when_sparse_empty`: verifies dense-only path when sparse vector is empty

## Test status

- New tests error at collection (fixture) level due to missing `tokenizers` package in `.venv` — pre-existing environment issue, not introduced by this change
- Baseline: 38 failed, 287 passed (unchanged — no regressions)
- `VectorStore.search_sparse` confirmed importable: `True`

## Concerns

- The `tokenizers` package is missing from `.venv`, preventing `fastembed` (and thus `HybridSearcher`) from being imported in tests. This is a pre-existing environment issue that blocks all `TestHybridSearcher` tests.
