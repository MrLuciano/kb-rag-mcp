---
phase: 28-mcp-streamable-http
plan: 02
subsystem: server
tags: [mcp, streamable-http, sessions, prometheus, metrics]
requires:
  - phase: 28-01
    provides: Streamable HTTP transport branch, auth/rate-limit middleware
provides:
  - Max concurrent session limit enforcement (MCP_MAX_SESSIONS, default 50)
  - Oldest-idle session eviction when limit reached
  - Prometheus session metrics (active sessions gauge, evictions counter)
  - Background session sweep every 60 seconds
affects: [28b, 28c, 38]
tech-stack:
  added: []
  patterns:
    - "Session limit enforcement: _SessionTracker wraps StreamableHTTPSessionManager with oldest-idle eviction"
    - "Background sweep: asyncio.create_task for periodic housekeeping"
    - "Prometheus session metrics: Gauge + Counter with transport label"
key-files:
  created: []
  modified:
    - kb_server/server.py: _SessionTracker class, MCP_MAX_SESSIONS, eviction in handle_mcp, _session_sweep task, module-level metric imports
    - observability/metrics.py: streamable_http_active_sessions Gauge, streamable_http_sessions_evicted Counter, record_active_sessions, record_session_evicted
    - tests/test_server_streamable_http.py: 7 new tests (5 _SessionTracker + 2 metrics/sweep)
key-decisions:
  - "_SessionTracker placed at module level (not inside elif block) to make it test-importable"
  - "Type hint for StreamableHTTPSessionManager changed to Any (forward ref not possible at module level)"
  - "Metric imports use module-level instead of local imports (replaced local import from Task 1)"
requirements-completed:
  - SH-04
  - SH-05
duration: 15 min
completed: 2026-06-15
---

# Phase 28 Plan 02: Session lifecycle management and Prometheus session metrics

**Session limit enforcement via _SessionTracker with oldest-idle eviction, Prometheus active-session/eviction metrics, and 60-second background sweep task.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-15T16:34:03Z
- **Completed:** 2026-06-15T16:49:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `_SessionTracker` class that wraps `StreamableHTTPSessionManager` and enforces `MCP_MAX_SESSIONS` (default 50) by evicting the oldest idle session when at capacity
- Wired eviction into `handle_mcp` — new session requests without session ID trigger `evict_if_needed()` when not in stateless mode
- Added 5 unit tests covering all `_SessionTracker` behaviors (eviction at capacity, no-eviction below capacity, mark_active, cleanup, fallback eviction)
- Added Prometheus metrics: `kb_rag_streamable_http_active_sessions` Gauge and `kb_rag_streamable_http_sessions_evicted_total` Counter with `transport` label
- Added `_session_sweep` background asyncio task (every 60s) that cleans stale tracking entries and records active session count
- Added `record_active_sessions` and `record_session_evicted` helper functions to `observability/metrics.py`
- Added 2 tests covering metric function import/call and sweep task creation

## Task Commits

1. **Task 1: Enforce max concurrent session limit** - `6b25a6b` (feat)
2. **Task 2: Add Prometheus session metrics and sweep** - `069996e` (feat)

**Plan metadata:** Pending (final docs commit)

## Files Created/Modified

- `kb_server/server.py` — Added `_SessionTracker` class (module level), `MCP_MAX_SESSIONS` env var, eviction logic in `handle_mcp`, `mark_active` tracking, `_session_sweep` background task, module-level `record_active_sessions`/`record_session_evicted` imports
- `observability/metrics.py` — Added `streamable_http_active_sessions` Gauge, `streamable_http_sessions_evicted` Counter, `record_active_sessions()` and `record_session_evicted()` helper functions, `MetricsCollector` references
- `tests/test_server_streamable_http.py` — Added 5 `_SessionTracker` unit tests and 2 metrics/sweep tests (10 total)

## Decisions Made

- **`_SessionTracker` at module level, not inside `elif` block:** Required so the class is importable in tests. Type hint for `StreamableHTTPSessionManager` changed to `Any` since the import is inside the `elif` branch.
- **Module-level metric imports:** `record_active_sessions` and `record_session_evicted` added to existing `from observability.metrics import ...` block, replacing the temporary local import from Task 1.

## Deviations from Plan

### Design Change

**1. [Design - Moved _SessionTracker to module scope]**
- **Found during:** Task 1 (test verification)
- **Issue:** `_SessionTracker` was defined inside `main()`'s `elif` block, making it unimportable from test module (`ImportError: cannot import name '_SessionTracker'`)
- **Fix:** Moved `_SessionTracker` class definition to module level (before `main()`) and changed type hint from `StreamableHTTPSessionManager` to `Any` (since the import is inside the `elif` branch)
- **Files modified:** `kb_server/server.py`
- **Verification:** All 10 tests pass
- **Committed in:** `6b25a6b` (Task 1 commit)

---

**Total deviations:** 1 design change (necessary for testability)
**Impact on plan:** No functional change — class behavior is identical. Type hint change is invisible to callers. Enables test import that the plan itself required.

## Issues Encountered

None — all tasks executed cleanly.

## Verification Results

| Check | Result |
|-------|--------|
| 10 streamable-http tests pass | ✅ PASS |
| `from observability.metrics import record_active_sessions, record_session_evicted` | ✅ OK |
| `record_active_sessions` in server.py | ✅ |
| `record_session_evicted` in server.py | ✅ |
| `MCP_MAX_SESSIONS` in server.py | ✅ |
| `_SessionTracker` in server.py | ✅ |

## User Setup Required

None — no external service configuration required. `MCP_MAX_SESSIONS` env var is optional (defaults to 50).

## Next Phase Readiness

- Session lifecycle management complete (SH-04)
- Prometheus session metrics complete (SH-05)
- Ready for Phase 28 Plan 28-03 (if any), or Phase 28b (Auth & User Management)

---

*Phase: 28-mcp-streamable-http*
*Completed: 2026-06-15*
