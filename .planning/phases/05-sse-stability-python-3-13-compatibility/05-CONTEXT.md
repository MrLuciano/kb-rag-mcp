# Phase 5: SSE Stability & Python 3.13 Compatibility - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a stable MCP SSE server on starlette 1.0.0 / Python 3.13 with comprehensive regression tests, a multi-version CI matrix, and validated dependency compatibility.

The fix for the `handle_sse NoneType` crash is already applied in `server.py` (returns `Response()`, trailing-slash consistency). This phase adds the surrounding quality infrastructure: tests, CI, version policy.

Requirements: SSE-01, SSE-02, COMPAT-01, COMPAT-02

</domain>

<decisions>
## Implementation Decisions

### SSE Test Strategy
- **D-01:** Write both unit tests AND integration tests for the SSE handler fix
- **D-02:** Unit test: mock `SseServerTransport.connect_sse`, invoke `handle_sse` with a fake Starlette Request, verify `Response()` is returned (not `None`)
- **D-03:** Integration test: use Starlette `TestClient` against the app, open a `GET /sse` connection, disconnect the client, verify no crash/exception propagates

### CI Matrix Design
- **D-04:** Use GitHub Actions `strategy.matrix.python-version` to test Python 3.11, 3.12, and 3.13 in parallel
- **D-05:** Matrix runs on push/PR to master (same triggers as current single-version CI)
- **D-06:** No separate nightly cron — push/PR coverage is sufficient

### Starlette Version Policy
- **D-07:** Pin minimum starlette version `>=1.0.0` in `requirements.in`
- **D-08:** Document the known compatible version in `.planning/codebase/STACK.md`

### Compatibility Audit Scope
- **D-09:** No proactive grep scan for 3.11-only patterns — let the CI matrix catch failures
- **D-10:** Run `pip-compile --python-version 3.13` (or equivalent) to check dependency compatibility with Python 3.13 proactively
- **D-11:** Fix only what the CI matrix or dependency audit surfaces

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### SSE Handler
- `kb_server/server.py` (lines 649–686) — The SSE transport block; fix already applied
- `.planning/codebase/STACK.md` — Framework versions (starlette 1.0.0, uvicorn 0.47.0)
- `.planning/codebase/ARCHITECTURE.md` — MCP server layer and entry points

### CI & Testing
- `.github/workflows/ci.yml` — Current single-version CI; must be extended to matrix
- `.planning/codebase/TESTING.md` — Test patterns, mocking approach, coverage setup
- `pyproject.toml` — pytest config, asyncio_mode = strict

### Dependencies
- `requirements.in` — Where starlette version pin is managed
- `requirements.txt` — Compiled lockfile for current versions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_smoke.py` — Already stubs `SseServerTransport` for testing; pattern can be reused/extended
- `tests/conftest.py` — Session-scoped fixture loads `.env`; shared by all tests

### Established Patterns
- **Mocking**: `unittest.mock` with `@patch` decorators and `AsyncMock` for async methods (see TESTING.md)
- **Test markers**: `@pytest.mark.asyncio` mandatory for async tests; `@pytest.mark.integration` for integration tests
- **Starlette TestClient**: Used in `test_health.py` for endpoint testing — pattern reusable for SSE integration test

### Integration Points
- `kb_server/server.py:main()` — Where SSE transport is initialized; tests must exercise the `TRANSPORT == "sse"` branch
- `.github/workflows/ci.yml` — Must be updated with matrix strategy
- `requirements.in` — Must pin starlette >=1.0.0

</code_context>

<specifics>
## Specific Ideas

No specific references — open to standard approaches for test implementation and CI configuration.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 5-SSE Stability & Python 3.13 Compatibility*
*Context gathered: 2026-05-21*
