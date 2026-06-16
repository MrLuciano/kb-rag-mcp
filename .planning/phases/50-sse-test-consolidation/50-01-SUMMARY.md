# Plan 50-01 SUMMARY: SSE Test Process Consolidation

## Objective

Refactor `test_smoke.py` to remove module-level `sys.modules` stubs that prevented SSE tests from running in the same pytest process.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_sse_handler.py tests/test_smoke.py -v` | ✅ 6/6 PASS (same process) |
| All existing tests | ✅ No regressions |

## Changes

- **`tests/test_smoke.py`** — Removed entire `_ensure_stubs()` function (120+ lines of module-level stubs for starlette, fastapi, uvicorn, mcp submodules, etc.). These stubs were vestigial — all packages are now installed in the environment, and `conftest.py`'s `mock_qdrant_client` fixture provides Qdrant isolation. Per-function `monkeypatch` in each test handles the remaining mocks. Removed stale `sys.path` entry for non-existent `server/` directory.

## Implementation Notes

- The module-level stubs were originally needed in v0.1.0 when packages like `fastapi` and `starlette` were optional. Now all packages are always installed, and `importlib.import_module("kb_server.server")` works cleanly without pre-stubbing.
- SSE tests previously required a separate pytest process (`pytest tests/test_sse_handler.py` run alone). Now they run alongside all other tests.
