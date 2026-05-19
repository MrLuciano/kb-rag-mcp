# 01-02 Summary: bootstrap_env() replaces load_dotenv blocks

## What was done

- Created `config/bootstrap_env.py` with a single `bootstrap_env()` function that centralizes all `.env` loading
- Created `config/__init__.py` (empty package marker)
- Replaced `load_dotenv` blocks in 9 entry point files:
  - `ingest/cli/legacy.py`
  - `ingest/cli/main.py`
  - `ingest/ingest.py`
  - `ingest/watcher/file_watcher.py`
  - `kb_server/health_server.py`
  - `kb_server/server.py`
  - `qa/run_qa.py`
  - `scripts/health_check.py`
  - `scripts/migrations/create_payload_indexes.py`

## Result

- Zero `load_dotenv` calls in source files outside `config/bootstrap_env.py`
- `tests/conftest.py` retains its own test-fixture loader (intentionally not changed)
- Test suite: 287 passed (up from 268 baseline), no new failures introduced
- Committed as: `refactor: single bootstrap_env() replaces 9 load_dotenv blocks (CLEAN-03)`
