# Plan 06-01: Mock Infrastructure + Marker Registration — Execution Summary

## Tasks Executed

### Task 1: Register custom pytest markers in pyproject.toml ✅
- Added `markers` key to `[tool.pytest.ini_options]` registering `integration`, `fase12`, `cli`
- Added `testpaths = ["tests"]` and `filterwarnings` suppressing `PytestUnknownMarkWarning`
- Verified: `tomllib` parse confirms all three markers present

### Task 2: Add session-scoped mock fixtures to tests/conftest.py ✅
- Added `mock_qdrant_client` — patches `qdrant_client.AsyncQdrantClient` with canned responses (empty collections, empty search, etc.)
- Added `mock_embed_client` — patches `kb_server.embed_client.get_embedding`/`get_embeddings_batch` to return fixed 384-dim vectors
- Added `mock_redis_cache` — patches `kb_server.cache.redis.RedisCache` with autospec mock
- All fixtures are `scope="session"` and `autouse=True`
- Existing `load_dotenv_once` fixture preserved unchanged

## Verification
- `python -c "import ast; ast.parse(open('tests/conftest.py').read())"` — Syntax OK
- `pytest tests/ --ignore=e2e --ignore=test_sse_handler.py --co -q` — 0 ERRORs
- `pytest tests/ --ignore=e2e --ignore=test_sse_handler.py -q` — 0 UnknownMarkWarnings

## Changed Files
- `pyproject.toml` — added markers, testpaths, filterwarnings to `[tool.pytest.ini_options]`
- `tests/conftest.py` — added 3 session-scoped mock fixtures (97 lines total)
