# Logging Coverage Audit

Generated: 2026-05-23 | Phase 7, Plan 07-02

## Scope

One-time audit of all public methods in `kb_server/` and `ingest/` for
log calls (`log.info`, `log.debug`, `log.warning`, `log.error`, `log.exception`
or `logger.*` equivalents).

## Results Summary

| Metric | Value |
|--------|-------|
| Total functions scanned | 235 |
| Functions with log calls | 119 |
| Coverage | 50.6% |
| Functions without logs | 116 |

## Modules With Full Coverage (100%)

| Module | Methods |
|--------|---------|
| `kb_server/analytics/query_analyzer.py` | 4/4 |
| `kb_server/collections/manager.py` | 4/4 |
| `kb_server/collections/router.py` | 2/2 |
| `kb_server/embed_client.py` | 7/7 |
| `kb_server/retrieval/hybrid_search.py` | 3/3 |
| `kb_server/retrieval/reranker.py` | 3/3 |
| `kb_server/telemetry/query_logger.py` | 3/3 |
| `ingest/parsers/legacy_office.py` | 7/7 |
| `ingest/parsers/zip_handler.py` | 1/1 |
| `ingest/worker/batch_processor.py` | 1/1 |

## Gap-Fill Summary (Plan 07-02)

The following modules received new log calls during this phase:

| Module | Before | After | Gaps Remaining |
|--------|--------|-------|----------------|
| `kb_server/collections/router.py` | 0% | 100% | 0 |
| `kb_server/telemetry/query_logger.py` | 0% | 100% | 0 |
| `kb_server/analytics/query_analyzer.py` | 0% | 100% | 0 |
| `kb_server/collections/manager.py` | 60% | 100% | 0 |
| `kb_server/retrieval/hybrid_search.py` | 67% | 100% | 0 |
| `kb_server/retrieval/reranker.py` | 67% | 100% | 0 |
| `kb_server/embed_client.py` | 57% | 100% | 0 |
| `ingest/core/metadata.py` | 0% | 70% | 6 |

Remaining gaps in gap-filled modules are simple utility/accessor methods
(`hash_key`, `backend_type`, `sha256`, `conn`, `get_stats`, etc.) where
adding log calls would add noise without value.

## Known Gaps (Out of Scope)

### `kb_server/` — remaining gaps

- `kb_server/cache/lru.py`: `hash_key` (static utility)
- `kb_server/cache/manager.py`: `backend_type` (property), `hash_key` (static)
- `kb_server/cache/redis.py`: `hash_key` (static utility)
- `kb_server/evaluation/dataset.py` (3 gaps) — not in scope
- `kb_server/evaluation/ragas_pipeline.py` (2 gaps) — not in scope
- `kb_server/health.py` (3 gaps) — not in scope
- `kb_server/health_server.py` (4 gaps) — not in scope
- `kb_server/optimization/chunking_experiments.py` (1 gap) — not in scope
- `kb_server/optimization/scoring_experiments.py` (1 gap) — not in scope
- `kb_server/server.py` (2 gaps) — hand-written framework handler
- `kb_server/ui/app.py` (2 gaps) — not in scope
- `kb_server/ui/routes.py` (4 gaps) — not in scope
- `kb_server/vector_store.py` (4 gaps) — not in scope

### `ingest/` — remaining gaps

- `ingest/classifier.py` (4 gaps)
- `ingest/cli/` (15 gaps across 4 CLI modules)
- `ingest/core/meta_loader.py` (3 gaps)
- `ingest/core/metadata.py` (6 gaps — utility methods)
- `ingest/core/version_extractor.py` (2 gaps)
- `ingest/ingest.py` (6 gaps)
- `ingest/job/manager.py` (4 gaps)
- `ingest/job/models.py` (5 gaps)
- `ingest/job/scheduler.py` (3 gaps)
- `ingest/validation/` (10 gaps across 4 validation modules)
- `ingest/watcher/file_watcher.py` (3 gaps)
- `ingest/worker/executor.py` (1 gap)
- `ingest/worker/limiter.py` (6 gaps)
- `ingest/worker/pool.py` (6 gaps)
- `ingest/worker/worker.py` (2 gaps)

## Verification

- Audit script runs from project root: `python3 scripts/logging-audit.py`
- No CI integration — one-time report
