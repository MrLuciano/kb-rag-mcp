# Plan 06-02: Classifier Tests + kb_server Integration Tagging — Execution Summary

## Tasks Executed

### Task 1: Write tests/test_classifier.py ✅
- Created `tests/test_classifier.py` with 26 unit tests across 4 test classes:
  - `TestInferDocType` (13 tests) — admin_guide, standard, training, release_notes, install_guide, user_guide, api_guide, howto, reference, fallback, zip artifact, empty path, case insensitivity
  - `TestInferProduct` (6 tests) — directory name, override, alias, filename, fallback "geral", unknown dir name
  - `TestClassify` (4 tests) — basic, override, classify_document wrapper, unknown file
  - `TestModuleConstants` (3 tests) — DOC_TYPE_RULES, PRODUCT_ALIASES, PRODUCT_FROM_NAME structure validation
- All tests target public API: `infer_doc_type`, `infer_product`, `classify`, `classify_document`
- Test file is 135 lines; 26/26 passing

### Task 2: Audit kb_server test files for @pytest.mark.integration ✅
**Result: No integration tags needed.** All 9 audited files already use full mocking:
- `test_search_integration.py` — mocked VectorStore, docstring says "no live Qdrant required"
- `test_collection_routing_integration.py` — AsyncMock + @patch throughout
- `test_server_extra.py` — all mocks (AsyncMock, MagicMock, patch)
- `test_server_tools.py` — all mocks
- `test_vector_store.py` — _stub_modules() at import time
- `test_health.py` — TestClient only, no live dependencies
- `test_hybrid_search.py` — mocks throughout
- `test_reranker.py` — sys.modules injection for sentence_transformers
- `test_hybrid_search_minimal.py` — placeholder

The only existing `@pytest.mark.integration` markers (in `test_payload_indexes.py:154`) are correct.

## Changes from Plan
- `mock_embed_client` and `mock_redis_cache` fixtures changed from `autouse=True` to explicit opt-in — they conflicted with `test_batch.py`, `test_cache_redis.py`, and `test_embed_client_unit.py` which manage their own mocking internally. `mock_qdrant_client` remains `autouse=True` as the critical safety guard.
- `test_classifier.py` tests use correct filenames matching actual classifier priority rules (e.g., "Troubleshooting-" for howto, not "How-To-" which matches higher-priority "config_guide").

## Verification
- `pytest tests/test_classifier.py -v` — 26/26 passed
- `pytest tests/ -m "not integration" -x --tb=short` — 0 failures, 518 passed

## Changed Files
- `tests/test_classifier.py` — NEW, 135 lines, 26 tests
- `tests/conftest.py` — mock_embed_client/mock_redis_cache changed to non-autouse
