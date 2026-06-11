# Testing Policy for KB-RAG-MCP

## Test Strategy

- Use **pytest** for all unit, integration, and system tests
- All tests live in the `tests/` directory
- Async tests use `@pytest.mark.asyncio` with strict mode (`asyncio_mode = "strict"` in `pyproject.toml`)
- Pytest markers are defined in `pyproject.toml`:
  - `integration` — tests requiring live infrastructure (Qdrant, LM Studio, Redis); skipped via `pytest -m 'not integration'`
  - `fase12` — tests targeting Phase 12 features (hybrid search, reranking)
  - `cli` — CLI integration tests that exercise click commands end-to-end
  - `fase29` — tests targeting Phase 29 features (enterprise connectors)
  - `fase30` — tests targeting Phase 30 features (knowledge graph)
  - `fase36` — tests targeting Phase 36 features (circuit breaker, provider budget)
- All new features require tests for main success and common failure cases
- Test names must describe scenario and expected result
- Use fixtures via `conftest.py` for common test data/setup

## Coverage Requirements

- **90% branch coverage** minimum for `kb_server/` and `ingest/` (enforced via `pyproject.toml` `[tool.coverage.report] fail_under = 90`)
- Run coverage with:
  ```bash
  pytest --cov=kb_server --cov=ingest --cov-branch --cov-report=term-missing
  ```

## Test Count

- **1095** core unit tests (in `tests/`, excluding e2e and SSE handler)
- **12** skipped (require Qdrant — integration/e2e)
- Run all tests:
  ```bash
  pytest tests/ -v
  ```
- Run unit tests only:
  ```bash
  pytest tests/ -m "not integration" -v
  ```

## Code Quality

| Tool       | Purpose          | Configuration                          |
|------------|------------------|----------------------------------------|
| **black**  | Code formatting  | Line-length 79, target py311           |
| **isort**  | Import sorting   | Black profile, line-length 79          |
| **flake8** | Linting          | Max line-length 79, extends-ignore E203/W503 |
| **mypy**   | Type checking    | Python 3.11, lenient (`disallow_untyped_defs=false`) |

## Running Tests

```bash
# Full test suite (excluding e2e)
pytest tests/ -x -q --ignore=tests/e2e --ignore=tests/test_sse_handler.py

# With coverage
pytest --cov=kb_server --cov=ingest --cov-branch --cov-report=term-missing

# Continuous runs (fast feedback)
pytest --maxfail=3 --disable-warnings -v

# Integration tests only
pytest tests/ -m integration -v
```

## Audit Scripts

```bash
# English audit — checks for Portuguese text in source files
python scripts/docstring-audit.py --check-inline

# Logging coverage audit — validates logging coverage across modules
python scripts/logging-audit.py
```

## CI Enforcement

- **Coverage gate** — enforced on PR-to-master via `pytest --cov --cov-branch --cov-fail-under=90`
- **English audit** — runs on every push/PR; fails if Portuguese detected in source
- **Logging audit** — runs with `--fail-under` threshold; validates logging statements
- **Helm lint** — runs on every push/PR via `helm lint --strict`
- **Formatting/linting** — black, isort, flake8, mypy run in CI

## Contribution

- All code must pass tests, type checks, format/lint, English audit, and coverage gate before merge
- Failing or missing tests must be explained in PR description
- New features must include tests matching coverage thresholds

---

*Last updated: 2026-06-11 for v1.4*
