---
phase: 40-config-backlog
plan: 02
subsystem: config
tags: [config, sqlite, fastapi, hot-reload, observer]

# Dependency graph
requires:
  - phase: 40-config-backlog
    provides: ConfigLoader, REST API router, SQLite config table
provides:
  - ConfigLoader singleton exposed on kb_server.config module
  - Config REST API mounted on health server
  - load_from_env() seeding from .env on startup
  - reload_if_changed() with synchronous observer callbacks
  - @config.on_change("KEY") decorator syntax
  - server.py migrated from os.getenv to config.get()
affects:
  - kb_server/server.py
  - kb_server/health_server.py
  - config/bootstrap_env.py

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-level ConfigLoader singleton via __init__.py
    - Synchronous observer callbacks for hot-reload
    - str(config.get()).lower() for bool normalization from typed DB values

key-files:
  created: []
  modified:
    - kb_server/config/__init__.py
    - kb_server/config/loader.py
    - config/bootstrap_env.py
    - kb_server/health_server.py
    - kb_server/server.py
    - tests/test_config_api.py

key-decisions:
  - "load_from_env() only seeds the default production DB (kb_metadata.db) to avoid polluting temporary test databases"
  - "reload_if_changed() is synchronous per D-03 to avoid races; it compares old vs new cache after _refresh_cache()"
  - "on_change() supports both direct registration and decorator syntax via Optional callback parameter"
  - "server.py uses str(config.get(...)).lower() for bool normalization to handle both string and bool typed values"
  - "Renamed local uvicorn.Config variable to _uvicorn_config to avoid shadowing the module-level config singleton"

requirements-completed:
  - CONF-03
  - CONF-04
  - CONF-05
  - CONF-06
  - CONF-07
  - CONF-08

# Metrics
duration: 24 min
completed: 2026-06-16
---

# Phase 40 Plan 02: Config Integration & Hot-reload Summary

**Config system wired into production server: health server mounts REST API, server.py replaces os.getenv with ConfigLoader.get(), and hot-reload callbacks log runtime config changes**

## Performance

- **Duration:** 24 min
- **Started:** 2026-06-16T14:47:23Z
- **Completed:** 2026-06-16T15:11:23Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Config REST API mounted on health server at `/api/v1/config` with periodic 5s reload loop
- `ConfigLoader` seeds ~18 known env keys from `.env` into SQLite on first startup
- `reload_if_changed()` detects version bumps and triggers matching observer callbacks synchronously
- `@config.on_change("KEY")` decorator syntax works for module-level callback registration
- All `os.getenv()` calls in `server.py` replaced with `config.get()` preserving exact defaults
- Hot-reload callbacks registered for `RATE_LIMIT_ENABLED`, `QUERY_LOG_ENABLED`, `RLCACHE_ENABLED`, `SSE_PORT`, `SSE_HOST`, `MCP_PORT`, `MCP_HOST`
- 28 config tests pass (21 existing + 7 new hot-reload tests)
- Full suite: 1335 passed, 0 regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Mount config router on health server and seed from .env** - `422c1f4` (feat)
2. **Task 2: Implement reload_if_changed() and @on_change decorator** - `1bc3524` (test)
3. **Task 3: Replace os.getenv calls in server.py with ConfigLoader.get()** - `4a385f4` (feat)

**Formatting/mypy fixes:** `d197205` (refactor)

**Plan metadata:** `SUMMARY.md` pending

## Files Created/Modified

- `kb_server/config/__init__.py` — Module-level `config = ConfigLoader()` singleton
- `kb_server/config/loader.py` — Added `load_from_env()`, `reload_if_changed()`, decorator support in `on_change()`, `_old_cache` for change detection
- `config/bootstrap_env.py` — Calls `config.load_from_env()` after `load_dotenv()`
- `kb_server/health_server.py` — Mounts config router, sets `app.state.config_loader`, adds `_config_reload_loop()` every 5s, replaces `os.getenv` with `config.get()`
- `kb_server/server.py` — Replaces all `os.getenv` calls with `config.get()`, registers `@config.on_change()` callbacks, renames local `uvicorn.Config` to `_uvicorn_config`
- `tests/test_config_api.py` — 7 new tests: reload, decorator, sync, wildcard, observer error, server import

## Decisions Made

- **load_from_env() DB guard:** Only seeds when `db_path.name == "kb_metadata.db"` to avoid polluting test temp databases.
- **Bool normalization:** `str(config.get(...)).lower() in (...)` pattern handles both string and bool typed values safely.
- **uvicorn variable rename:** Renamed local `config` to `_uvicorn_config` to prevent `UnboundLocalError` shadowing the module-level ConfigLoader singleton.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] test_config_loader_reset_all failed due to env seeding**
- **Found during:** Task 1
- **Issue:** `load_from_env()` in `__init__` seeded 4 env keys into temporary test databases, causing `reset_all` to return 6 instead of 2
- **Fix:** Added guard in `load_from_env()` to skip seeding when `db_path.name != "kb_metadata.db"`
- **Files modified:** `kb_server/config/loader.py`
- **Verification:** `pytest tests/test_config_api.py` passes
- **Committed in:** `422c1f4` (Task 1)

**2. [Rule 1 - Bug] UnboundLocalError in server.py main()**
- **Found during:** Task 3 (full suite regression check)
- **Issue:** `config = uvicorn.Config(...)` local variable shadowed the module-level `config` singleton, causing `UnboundLocalError` when `config.get()` was called in `main()`
- **Fix:** Renamed local `config` variable to `_uvicorn_config` in both SSE and streamable-http branches
- **Files modified:** `kb_server/server.py`
- **Verification:** `pytest tests/test_server_streamable_http.py` passes
- **Committed in:** `4a385f4` (Task 3)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- Pre-existing flake8 E402 (imports after bootstrap_env) and E501 (line too long) in `server.py` and `health_server.py` — these are inherited from the codebase and not introduced by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Config system is fully integrated and ready for Phase 41 (Provider Alias)
- `config.get()` and `config.on_change()` patterns established for future phases
- Health server serves config API on port 8000

## Self-Check: PASSED

- [x] All created/modified files exist on disk
- [x] All commits exist in git history
- [x] All tests pass (28 config tests, 1335 full suite)
- [x] Linting clean (black, isort, mypy pass; flake8 E402/E501 are pre-existing)

---
*Phase: 40-config-backlog*
*Completed: 2026-06-16*
