# Plan 46-01 SUMMARY: Code Quality & Coverage

## Objective

Fix code quality baseline: migrate deprecated datetime.utcnow(), tag pre-existing test failures as integration, remove unused imports.

## Verification

| Check | Result |
|-------|--------|
| Full non-Qdrant test suite (209 tests) | ✅ All pass, no regressions |
| Zero remaining `datetime.utcnow()` calls | ✅ 0 occurrences |
| `flake8 --select=F401` | ✅ Reduced from 17 to 0 |

## Tasks Executed

| # | Fix | Status |
|---|-----|--------|
| 1 | Replace 24 `datetime.utcnow()` calls with `datetime.now(timezone.utc).replace(tzinfo=None)` across 11 files | ✅ |
| 2 | Remove 16 unused imports (F401) across 12 files | ✅ |
| 3 | Tag 5 pre-existing Qdrant-dependent tests with `@pytest.mark.integration` | ✅ |

## Files Modified

- **utcnow migration (11 files):** `kb_server/evaluation/exporter.py`, `kb_server/analytics/query_analyzer.py`, `kb_server/health.py`, `kb_server/telemetry/query_logger.py`, `kb_server/optimization/result_store.py`, `kb_server/auth/models.py`, `kb_server/auth/erasure.py`, `kb_server/auth/service.py`, `kb_server/ui/routes_admin.py`, `ingest/reclassify_engine.py`, `tests/test_query_logger.py`
- **Unused import removal (12 files):** `ingest/cli/connectors.py`, `ingest/cli/evaluate.py`, `ingest/connectors/__init__.py`, `ingest/connectors/models.py`, `ingest/connectors/staging.py`, `ingest/graph_builder.py`, `kb_server/circuit_breaker.py`, `kb_server/prompts.py`, `kb_server/provider_budget.py`, `kb_server/ui/app.py`, `kb_server/ui/routes_admin.py`
- **Integration tagging:** `tests/test_smoke.py` (3 tests), `tests/test_server_terms.py` (2 tests)
