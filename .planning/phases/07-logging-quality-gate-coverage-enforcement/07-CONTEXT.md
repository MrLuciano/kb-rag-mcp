# Phase 7: Logging, Quality Gate & Coverage Enforcement - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver structured logging coverage on every public method in `kb_server/`, a
logging coverage audit, and a CI-enforced 90% branch coverage quality gate on
both `kb_server/` and `ingest/`.

Requirements: LOG-01, LOG-02, QUAL-01, QUAL-02

</domain>

<decisions>
## Implementation Decisions

### Coverage Scope
- **D-01:** Quality gate applies to both `kb_server/` AND `ingest/` at 90%
  branch coverage. REQUIREMENTS.md says `kb_server/` only, but agreed that
  `ingest/` gets the same standard.
- **D-02:** `ingest/` target is 90% same as `kb_server/` — no gradual ramp.

### Uncovered Margin Handling
- **D-03:** Pragmatic approach — narrow, justified `# pragma: no cover`
  annotations allowed for defense-in-depth code (bare `except` blocks,
  third-party error paths, unreachable defensive checks).
- **D-04:** Each `# pragma: no cover` must have an inline comment explaining
  why it's excluded. No blanket `# pragma: no cover` on files or classes.
- **D-05:** Excludes are NOT centralized in `pyproject.toml` — inline only.

### Enforcement Mechanism
- **D-06:** Both mechanisms — `[tool.coverage.report] fail_under = 90` in
  `pyproject.toml` AND `--cov-fail-under=90` in CI step.
- **D-07:** Coverage enforcement runs on PR to master only (not every push).
- **D-08:** CI coverage step covers both `--cov=kb_server` and `--cov=ingest`.

### Areas Not Discussed (agent discretion)
- **Logging audit method** — Not selected for discussion. Recommendation:
  `pytest --co` style collect-all-functions script that greps for `log.` calls
  in `kb_server/` modules. One-time report, not automated CI gate.
- **Logging format** — Not selected for discussion. Recommendation: keep stdlib
  `logging` (no structlog), emit consistent key=value pairs in messages.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §"Logging Coverage" — LOG-01, LOG-02 definitions
- `.planning/REQUIREMENTS.md` §"Quality Gate" — QUAL-01, QUAL-02 definitions

### Codebase Maps
- `.planning/codebase/STRUCTURE.md` — Module layout for kb_server/ and ingest/
- `.planning/codebase/TESTING.md` — Test patterns, coverage setup, run commands
- `.planning/codebase/CONVENTIONS.md` — Naming and style conventions

### Current CI Configuration
- `.github/workflows/ci.yml` — Existing CI pipeline; coverage step to be added

### Prior Phase Context
- `.planning/phases/06-test-coverage-isolation/06-CONTEXT.md` — Phase 6 decisions
  on mocking, integration markers, conftest fixtures

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py` — Session-scoped `mock_qdrant_client` fixture (autouse)
  prevents accidental Qdrant connections during coverage-gap testing
- `.github/workflows/ci.yml` — Existing CI workflow with Python matrix; coverage
  step can be added as an additional job or step
- `pyproject.toml` — `[tool.pytest.ini_options]` already has testpaths, markers,
  filterwarnings; `[tool.coverage]` section exists but is empty

### Established Patterns
- **Logging:** stdlib `logging` with `kb-mcp.*` logger names. ~86 log calls
  across `kb_server/` already (server.py, vector_store.py, hybrid_search.py,
  embed_client.py, health.py, collections/manager.py, retrieval/reranker.py).
- **Logger naming:** `log = logging.getLogger("kb-mcp.{module}")` pattern
  established in all main modules.
- **Coverage run:** `pytest tests/ --cov=kb_server --cov=ingest --cov-report=term-missing`

### Integration Points
- `pyproject.toml` — Add `[tool.coverage.report]` with `fail_under = 90`
- `.github/workflows/ci.yml` — Add coverage job with `--cov=kb_server --cov=ingest`
- `kb_server/` — Add logging to `collections/router.py`, `cache/*`,
  `telemetry/query_logger.py`, `analytics/query_analyzer.py`,
  `evaluation/*.py`, `ui/*.py`, `optimization/*.py`
- Same for `ingest/` — audit and add logging where missing

### Targeting Identified
- 15+ kb_server submodules with zero logging calls need log entries added
- ingest/ coverage baseline unknown — first coverage run on ingest/ needed

</code_context>

<specifics>
## Specific Ideas

- Logging audit: a simple script that scans `kb_server/` for public functions
  and checks each has a `log.info()` or similar call. Outputs a report of
  gaps. One-time run, not CI enforcement.
- Coverage enforcement: `pytest --cov=kb_server --cov=ingest --cov-fail-under=90`
  in CI step on PR-to-master only.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 7-Logging, Quality Gate & Coverage Enforcement*
*Context gathered: 2026-05-23*
