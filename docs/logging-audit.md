# Logging Coverage Audit

Generated: 2026-06-11 | Phase 7, Plan 07-02 (updated for v0.1.4)

## Scope

One-time audit of all public methods in `kb_server/` and `ingest/` for
log calls (`log.info`, `log.debug`, `log.warning`, `log.error`, `log.exception`
or `logger.*` equivalents).

## Results Summary

| Metric | Value |
|--------|-------|
| Total functions scanned | 382 |
| Functions with log calls | 161 |
| Coverage | 42.1% |
| Functions without logs | 221 |

Coverage decreased from 50.6% (v0.1.3) due to new v0.1.4 modules (auth, connectors,
circuit breaker, provider budget, request cache, knowledge graph) that lack
logging instrumentation.

## Modules With Full Coverage (100%)

| Module | Methods |
|--------|---------|
| `kb_server/analytics/query_analyzer.py` | 4/4 |
| `kb_server/collections/manager.py` | 4/4 |
| `kb_server/collections/router.py` | 3/3 |
| `kb_server/evaluation/csv_loader.py` | 1/1 |
| `kb_server/evaluation/ragas_pipeline.py` | 2/2 |
| `kb_server/retrieval/hybrid_search.py` | 4/4 |
| `kb_server/retrieval/reranker.py` | 3/3 |
| `kb_server/telemetry/query_logger.py` | 3/3 |
| `ingest/parsers/legacy_office.py` | 7/7 |
| `ingest/parsers/zip_handler.py` | 1/1 |
| `ingest/reclassify_engine.py` | 5/5 |
| `ingest/cli/evaluate.py` | 1/1 |
| `ingest/utils.py` | 1/1 |
| `ingest/worker/batch_processor.py` | 1/1 |

## Modules With Lowest Coverage

| Module | Coverage | Methods |
|--------|----------|---------|
| `kb_server/auth.py` | 0% | 0/3 |
| `kb_server/auth_registry.py` | 0% | 0/6 |
| `kb_server/evaluation/dataset.py` | 0% | 0/4 |
| `kb_server/evaluation/llm_wrapper.py` | 0% | 0/4 |
| `kb_server/evaluation/metrics.py` | 0% | 0/4 |
| `kb_server/health_server.py` | 0% | 0/5 |
| `kb_server/optimization/chunking_experiments.py` | 0% | 0/1 |
| `kb_server/optimization/scoring_experiments.py` | 0% | 0/1 |
| `kb_server/prompts.py` | 0% | 0/3 |
| `kb_server/provider_budget.py` | 0% | 0/6 |
| `kb_server/rate_limiter.py` | 0% | 0/2 |
| `kb_server/ui/app.py` | 0% | 0/2 |
| `kb_server/ui/routes.py` | 0% | 0/4 |
| `ingest/cli/auth.py` | 0% | 0/4 |
| `ingest/cli/check.py` | 0% | 0/2 |
| `ingest/cli/connectors.py` | 0% | 0/3 |
| `ingest/cli/db.py` | 0% | 0/2 |
| `ingest/cli/export.py` | 0% | 0/2 |
| `ingest/cli/job.py` | 0% | 0/8 |
| `ingest/cli/main.py` | 0% | 0/2 |
| `ingest/cli/progress.py` | 0% | 0/3 |
| `ingest/cli/quota.py` | 0% | 0/4 |
| `ingest/cli/reclassify.py` | 0% | 0/5 |
| `ingest/cli/status.py` | 0% | 0/2 |
| `ingest/connectors/base.py` | 0% | 0/6 |
| `ingest/connectors/models.py` | 0% | 0/3 |
| `ingest/graph_builder.py` | 0% | 0/5 |
| `ingest/job/models.py` | 0% | 0/5 |
| `ingest/validation/base.py` | 0% | 0/3 |
| `ingest/validation/content.py` | 0% | 0/1 |
| `ingest/validation/format.py` | 0% | 0/1 |
| `ingest/validation/pipeline.py` | 0% | 0/9 |
| `ingest/validation/size.py` | 0% | 0/2 |

## New v0.1.4 Modules (added since v0.1.3)

| Module | Coverage | Status |
|--------|----------|--------|
| `kb_server/auth.py` | 0% | Needs logging |
| `kb_server/auth_registry.py` | 0% | Needs logging |
| `kb_server/cache/request_cache.py` | 12% | Partially covered |
| `kb_server/circuit_breaker.py` | 33% | Partially covered |
| `kb_server/prompts.py` | 0% | Needs logging |
| `kb_server/provider_budget.py` | 0% | Needs logging |
| `kb_server/rate_limiter.py` | 0% | Needs logging |
| `ingest/cli/auth.py` | 0% | Needs logging |
| `ingest/cli/connectors.py` | 0% | Needs logging |
| `ingest/cli/quota.py` | 0% | Needs logging |
| `ingest/connectors/base.py` | 0% | Needs logging |
| `ingest/connectors/confluence.py` | 50% | Partially covered |
| `ingest/connectors/git.py` | 25% | Partially covered |
| `ingest/connectors/jira.py` | 50% | Partially covered |
| `ingest/graph_builder.py` | 0% | Needs logging |

---

*Re-run with `python scripts/logging-audit.py` to regenerate.*
*Last updated: 2026-06-11 for v0.1.4*
