# Phase 50: SSE Test Process Consolidation - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor `test_smoke.py` to use per-function `@patch` decorators, allowing SSE tests to run in the same pytest process instead of requiring a separate process.

Requirements: T-05

</domain>

<decisions>
## Implementation Decisions

- **D-01:** Convert all module-level monkeypatch/sys.modules stubs in `test_smoke.py` to per-function `@patch` decorators or `with patch()` context managers.
- **D-02:** SSE tests (`test_sse_handler.py`) should run alongside smoke tests without import-order conflicts.
- **D-03:** No change in test behavior or pass/fail semantics — only how stubbing is applied.

### the agent's Discretion
- Whether to refactor `test_smoke.py` in-place or rewrite from scratch
- Whether the `_ensure_stubs()` in `test_vector_store_unit.py` also needs changes

</decisions>

<canonical_refs>
## Canonical References

- `tests/test_smoke.py` — 259 lines, uses module-level monkeypatch stubs that conflict with SSE imports
- `tests/test_sse_handler.py` — 92 lines, requires clean fastapi imports
- `tests/conftest.py` — Existing session-scoped fixtures using proper `patch()` pattern
- `tests/test_reranker_lazy.py` — Reference for per-function `@patch` with sys.modules

</canonical_refs>

---

*Phase: 50-sse-test-consolidation*
*Context gathered: 2026-06-15*
