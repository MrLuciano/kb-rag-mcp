# Phase 6: Test Coverage & Isolation - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver comprehensive test coverage across all `kb_server/` and `ingest/` Python modules with proper isolation mocking, clearly marked integration tests, and no external service requirements for unit tests.

Requirements: TEST-01, TEST-02, TEST-03

</domain>

<decisions>
## Implementation Decisions

### Module-to-Test-File Mapping
- **D-01:** Hybrid approach — strict 1:1 mapping for modules with zero dedicated test coverage; per-subject grouping for well-covered functional areas
- **D-02:** ALL modules without a dedicated test file need one (not just `classifier.py`). This includes `kb_server/telemetry/query_logger.py`, `kb_server/analytics/query_analyzer.py`, `kb_server/optimization/chunking_experiments.py`, `kb_server/optimization/scoring_experiments.py`, `kb_server/ui/app.py`, `kb_server/ui/routes.py`, and any `ingest/` submodules without direct test files
- **D-03:** New test files use a mix of unit tests (with full mocking per TEST-02) and `@pytest.mark.integration` markers where mocking is impractical

### Test Isolation & Mocking
- **D-04:** Integration marker policy: `@pytest.mark.integration` only for tests needing EXTERNAL RUNNING SERVICES (Qdrant container, LM Studio process, Redis server). Tests loading local models (sentence_transformers cross-encoder) are "unit tests" for tagging purposes
- **D-05:** Cross-encoder model: mock `sentence_transformers.CrossEncoder` with `unittest.mock.patch` in unit tests for Phase 6
- **D-06:** Lazy-loading the cross-encoder model in `kb_server/retrieval/reranker.py` is DEFERRED to post-Phase 6. Phase 6 uses mocking only

### Test Infrastructure
- **D-07:** New mock fixtures go into `tests/conftest.py` for shared use (Qdrant, LM Studio, Redis mocks)
- **D-08:** All pytest custom markers registered in `pyproject.toml` under `[tool.pytest.ini_options].markers`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §"Test Coverage & Isolation" — TEST-01, TEST-02, TEST-03 definitions

### Codebase Maps
- `.planning/codebase/TESTING.md` — Test framework setup, mocking patterns, run commands
- `.planning/codebase/STRUCTURE.md` — Module directory layout for all files needing test coverage
- `.planning/codebase/CONVENTIONS.md` — Naming and style conventions for tests

### Existing Test Infrastructure
- `tests/conftest.py` — Shared session fixtures
- `tests/test_smoke.py` — Reference for test_smoke.py's module-level stubbing pattern
- `pyproject.toml` — pytest config (asyncio_mode = strict, markers, coverage)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_smoke.py` — Module-level stubbing pattern for Qdrant, MCP, starlette. Reusable for new test files that need isolated imports
- `tests/conftest.py` — Session-scoped .env loader. Extension point for shared Qdrant/LM Studio/Redis mock fixtures
- `unittest.mock` (stdlib) — AsyncMock, MagicMock, patch all widely used (104 mock usages across test files)

### Established Patterns
- Imports inside test functions (avoids collection-time circular imports)
- `@pytest.mark.asyncio` mandatory for all async tests (strict mode)
- `pytest.raises` with `match=` parameter for error testing
- Class-based test grouping for shared fixtures; top-level functions for independent tests

### Integration Points
- New test files go in `tests/` named `test_<module>.py`
- `pyproject.toml` `[tool.pytest.ini_options]` — marker registration and coverage config
- `tests/conftest.py` — shared fixture registration
- `.github/workflows/ci.yml` — potential `-m "not integration"` filtering

### Identified Coverage Gaps
- `ingest/classifier.py` — zero direct test coverage (primary gap)
- `kb_server/telemetry/query_logger.py` — no dedicated test file
- `kb_server/analytics/query_analyzer.py` — no dedicated test file
- `kb_server/optimization/chunking_experiments.py` — no dedicated test file
- `kb_server/optimization/scoring_experiments.py` — no dedicated test file
- `kb_server/ui/app.py` — no dedicated test file
- `kb_server/ui/routes.py` — no dedicated test file
- `ingest/core/meta_loader.py` — no dedicated test file
- `ingest/core/version_extractor.py` — no dedicated test file
- `ingest/job/models.py` — no dedicated test file
- `ingest/job/manager.py` — no dedicated test file
- `ingest/job/scheduler.py` — no dedicated test file
- `ingest/worker/limiter.py` — no dedicated test file
- `ingest/cli/db.py` — no dedicated test file
- `ingest/cli/progress.py` — no dedicated test file
- `ingest/cli/legacy.py` — no dedicated test file
- `ingest/parsers/legacy_office.py` — no dedicated test file
- `ingest/parsers/zip_handler.py` — no dedicated test file

</code_context>

<specifics>
## Specific Ideas

No specific references — open to standard approaches for test implementation and mocking strategy.

</specifics>

<deferred>
## Deferred Ideas

- **Lazy-load cross-encoder model** — Refactor `kb_server/retrieval/reranker.py` to defer model loading until first `predict()` call, enabling unit tests that never trigger the 500MB+ model load. Post-Phase 6 optimization.

</deferred>

---

*Phase: 6-Test Coverage & Isolation*
*Context gathered: 2026-05-22*
