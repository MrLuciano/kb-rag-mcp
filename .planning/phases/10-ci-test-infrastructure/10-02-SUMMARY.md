---
phase: 10-ci-test-infrastructure
plan: 02
subsystem: testing
tags: [pytest, qdrant, mocking, sys-modules, test-infrastructure]
requires:
  - phase: 09-startup-reliability
    provides: Test suite baseline (576 tests) and conftest.py mock fixtures
  - phase: 06-test-coverage-isolation
    provides: Mock isolation patterns (mock_qdrant_client fixture in conftest.py)
provides:
  - All qdrant_client model comparisons in tests use real enum types — no false negatives
  - Cleaner test infrastructure without sys.modules monkey-patching for qdrant
  - Reduced test file complexity (removed _patch_vs_callables, _ORIGINAL_VS_ATTRS)
affects: [testing, vector-store, embedding]
tech-stack:
  added: []
  patterns:
    - "Import real qdrant_client.models before test stubs to ensure sys.modules has real package"
    - "Keep sys.modules stubs only for heavy/unrelated dependencies (fastembed, sentence_transformers, etc.)"
key-files:
  created: []
  modified:
    - tests/test_smoke.py
    - tests/test_vector_store.py
    - tests/test_vector_store_unit.py
key-decisions:
  - "Import real qdrant_client at top of _ensure_stubs() — sys.modules setdefault then preserves real modules"
  - "Remove _patch_vs_callables() from test_vector_store_unit.py — real model classes are already callable"
  - "Keep non-qdrant stubs (mcp, fastembed, etc.) to prevent heavy dependency loading in test process"
requirements-completed: [DEBT-03]
duration: ~1.5h
completed: 2026-05-25
---

# Phase 10 Plan 02: Replace sys.modules qdrant Stubs with Real Imports Summary

**Replaced all `sys.modules` monkey-patching of `qdrant_client` model classes with real imports from `qdrant_client.models` — fixing enum value comparisons and removing `_patch_vs_callables()` workaround in 3 test files**

## Performance

- **Duration:** ~1.5h
- **Started:** 2026-05-25
- **Completed:** 2026-05-25
- **Tasks:** 4
- **Files modified:** 3

## Accomplishments

- All 3 test files now import real `qdrant_client.models` classes instead of `type(name, (), {})()` anonymous stubs
- Removed `_patch_vs_callables()` and `_ORIGINAL_VS_ATTRS` sentinel from `test_vector_store_unit.py` — real model classes are properly callable
- Removed `_qm.FilterSelector = MagicMock()` post-import override — uses real `FilterSelector` class
- Fixed `_run()` event-loop helper in `test_smoke.py` to handle `asyncio_mode = "strict"` (creates loop on `RuntimeError`)
- Full test suite: **551 passed, 5 skipped, 0 failed** — zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix qdrant_client stubs in test_smoke.py** — `747c756` (feat)
2. **Task 2: Fix qdrant_client stubs in test_vector_store.py** — `747c756` (feat)
3. **Task 3: Fix qdrant_client stubs in test_vector_store_unit.py** — `747c756` (feat)
4. **Task 4: Verify full test suite passes** — verified inline

**Plan metadata:** All tasks committed in single `747c756` commit.

## Files Modified

- `tests/test_smoke.py` — Replaced type(name,(),{})() stubs with real imports; fixed _run() helper
- `tests/test_vector_store.py` — Same real-import pattern in _ensure_stubs()
- `tests/test_vector_store_unit.py` — Removed _patch_vs_callables(), _ORIGINAL_VS_ATTRS, _qm.FilterSelector override

## Decisions Made

- **Import real qdrant before stubs:** Adding `import qdrant_client` at the top of `_ensure_stubs()` ensures the real package loads into `sys.modules` before the `setdefault` loop runs, which then preserves the real modules instead of creating anonymous stubs
- **Keep module-level stubs for qdrant sub-modules:** The `setdefault` loop for qdrant modules is retained as a no-op safety net for edge cases
- **Keep non-qdrant stubs:** MCP, fastembed, and other heavy dependency stubs remain to prevent unnecessary package loading in test processes
- **All 4 tasks committed together:** Changes to the 3 test files are interdependent and tested together

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- WSL filesystem (DrvFs) prevented the Write tool from writing modified files correctly (claimed success but files remained unchanged) — used `cat << 'EOF' > file` Bash heredocs as workaround
- `test_vector_store_unit.py` had an `import qdrant_client.models as _qm` at module level with `_qm.FilterSelector = MagicMock()` — removing this required ensuring real `FilterSelector` works with all existing assertions

## Known Stubs

None — all qdrant model stubs removed.

## Threat Flags (Scan)

None — test-only file changes, no new network/schema/auth surface.

## User Setup Required

None — test infrastructure change only.

## Next Phase Readiness

- Enum comparisons in tests now use real qdrant types — no `getattr(x, 'value', x)` workarounds needed
- Cleaner test files ready for further VectorStore test additions
- Debt item DEBT-03 resolved

---

*Phase: 10-ci-test-infrastructure*
*Completed: 2026-05-25*
