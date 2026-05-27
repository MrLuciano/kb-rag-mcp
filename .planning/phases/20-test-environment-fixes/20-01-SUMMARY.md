---
id: 20-01
phase: 20
status: complete
completed: 2026-05-27
task_count: 3
commits:
  - b381556 fix(20): ensure log directory exists before FileHandler init (TESTFIX-02)
  - 14a0ae2 fix(20): move module-level mocks to fixture scope in test_reranker_lazy (TESTFIX-01)
---

# Plan 20-01: Test Environment Fixes — Summary

## What was fixed

### TESTFIX-01: Fixture isolation
Moved module-level `MagicMock` objects in `tests/test_reranker_lazy.py` into `mock_objects` fixture — prevents mock state leakage when run alongside other test files in the same session.

### TESTFIX-02: LOG_PATH PermissionError
Added `os.makedirs(os.path.dirname(_log_path), exist_ok=True)` in `kb_server/server.py` before `logging.FileHandler` init. Previously, LOG_PATH from `.env` could point to a non-existent directory, causing PermissionError on module import.

### TESTFIX-03: Clean environment
Removed stale `.pyc`/`__pycache__` artifacts. Verified 31 tests across 5 test files pass together without issues.

## Self-Check: PASSED
- [x] PermissionError eliminated — `kb_server.server` imports cleanly with any LOG_PATH
- [x] Fixture isolation fixed — test files run together without interaction
- [x] Stale artifacts cleaned
- [x] 31 tests pass across server, reranker, and vector store test files
