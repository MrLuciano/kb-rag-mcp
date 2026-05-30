# Codebase Concerns

**Analysis Date:** 2026-05-30

## Tech Debt

**Ingest Pipeline Metrics Unwired**
- Issue: Metrics defined in `observability/metrics.py` are never emitted by the ingest pipeline. This includes job metrics (`kb_ingest_jobs_*`), file metrics (`kb_ingest_files_processed_total`, `kb_ingest_file_processing_seconds`), chunk metrics (`kb_ingest_chunks_generated_total`), worker pool metrics (`kb_ingest_worker_pool_*`), rate limiter metrics (`kb_ingest_rate_limiter_*`), API metrics (`kb_ingest_api_requests_total`), and HTTP pool metrics (`kb_http_pool_connections`).
- Files: `observability/metrics.py`, `ingest/ingest.py`, `ingest/worker/pool.py`, `ingest/job/manager.py`
- Impact: Grafana dashboard had to be rebuilt with 18 dead panels removed. Ingest activity is invisible to monitoring.
- Fix approach: Create a shared `MetricsCollector` instance in `ingest/cli/main.py` and pass it through to `ingest/ingest.py`, worker pool, and job scheduler. See `.planning/backlog.md` item #4.

**Grafana Dashboard Missing Ingest Panels**
- Issue: Dashboard was rebuilt to only show live metrics. When ingest metrics are wired, the removed panels (Files Processed, Chunks Generated, Worker Pool, Job Duration, Rate Limiter, Batch Throughput) must be restored.
- Files: `deployment/config/grafana-dashboard.json`, `deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json`
- Depends on: Ingest pipeline metrics wiring
- Fix approach: Restore removed panels from git history (`git show 3d0d74f:deployment/config/grafana-dashboard.json`) and update queries to match wired metric names.

**Broad Exception Swallowing in `ingest/classifier.py`**
- Issue: `except Exception: pass` at lines 672, 691, 843, 896 silently ignores all errors during content classification. Malformed or malicious input may cause silent failures, making the system think classification succeeded when it didn't.
- Files: `ingest/classifier.py:672`, `ingest/classifier.py:691`, `ingest/classifier.py:843`, `ingest/classifier.py:896`
- Impact: Classification errors are invisible. Reclassify engine may report success while silently failing.
- Fix approach: Log exceptions at WARNING level at minimum; re-raise if critical. Use specific exception types instead of bare `except Exception`.

**Broad Exception Swallowing in `ingest/ingest.py`**
- Issue: `except Exception:` blocks at lines 655+ swallow errors during file processing without adequate context.
- Files: `ingest/ingest.py:655`
- Impact: Ingestion failures may be silently logged without raising, making batch jobs appear successful when files were skipped.
- Fix approach: Catch specific exceptions (`IOError`, `ParseError`, etc.) and log with file path context. Re-raise unexpected exceptions.

**Broad Exception Swallowing in `ingest/reclassify_engine.py`**
- Issue: `except Exception:` at line 496 catches all errors during reclassification batch processing.
- Files: `ingest/reclassify_engine.py:496`
- Impact: Partial batch failures may be silently ignored, leaving chunks with stale metadata.
- Fix approach: Catch specific Qdrant/SQLite errors. Log the full traceback. Consider marking the batch as failed rather than continuing.

## Known Bugs

**Hybrid Search Always Falls Back to Dense-Only**
- Symptoms: `HybridSearcher` claims to perform sparse+dense RRF fusion but the sparse search code path is commented out. The function returns dense-only results even when `strategy="hybrid"`.
- Files: `kb_server/retrieval/hybrid_search.py:153-168`
- Trigger: Any call to `search_kb` with hybrid mode enabled.
- Workaround: Results are still correct dense results, just not hybrid.
- Status: Long-standing issue from before 2026-05-19. Feature is advertised in `docs/SEARCH_QUALITY.md` but not implemented.

**Test Failure: `test_list_tools_returns_five_tools`**
- Symptoms: Test asserts `len(tools) == 5`, but `list_filter_options` tool (PHASE 17) makes it 6 tools.
- Files: `tests/test_server_extra.py:110`
- Fix: Update assertion to expect 6 tools including `list_filter_options`.
- Status: Known since 2026-05-30. Low priority — does not affect runtime behavior.

**E2E Tests Fail Outside Docker (44 tests)**
- Symptoms: `tests/e2e/test_ingestion_workflow.py` and `tests/e2e/test_health_workflow.py` require Qdrant, embedding backend, and filesystem paths not available in host test environment.
- Status: Environment-dependent, not code regressions. Pass when full Docker stack is available.
- Fix: Either run E2E tests only in Docker, or add `@pytest.mark.skipif` guards for missing services.

**Module Filter Tests Failing (4 tests)**
- Symptoms: `tests/test_vector_store_module_filter.py` assertions fail because mocked `store.search()` returns `AsyncMock` instead of `list`.
- Files: `tests/test_vector_store_module_filter.py`
- Root cause: Tests mock the coroutine return but do not `await` it, or mock setup is incomplete.
- Status: New failures not present in earlier test runs. May be related to recent `search()` signature changes.

**Filter Terms Cache Test Failing**
- Symptoms: `TestFilterTermsCache::test_cache_needs_refresh_no_marker` fails.
- Files: `tests/test_vector_store_terms.py`
- Status: New failure. Possibly related to recent filter terms cache initialization changes.

## Security Considerations

**No Authentication on MCP Server or Health Server**
- Risk: `kb_server/server.py` and `kb_server/health_server.py` expose MCP tools (search, ingest) with no authentication layer. The health server also exposes system information without auth.
- Files: `kb_server/server.py`, `kb_server/health_server.py`
- Current mitigation: Default binds to `127.0.0.1` (`SSE_HOST` default). Acceptable for local use, risky if `SSE_HOST=0.0.0.0`.
- Recommendations: Document that SSE mode must not be exposed publicly without a reverse proxy + auth layer. Add `WARNING` log if `SSE_HOST=0.0.0.0` without `AUTH_TOKEN` set.

## Performance Bottlenecks

**No CI/CD Pipeline — Tests Run Manually**
- Problem: No `.github/workflows/` directory exists. Tests must be run manually.
- Files: Entire `tests/` directory lacks automation.
- Cause: Explicit deferral to focus on feature development.
- Improvement path: Add GitHub Actions workflow running `pytest tests/ -x --ignore=tests/e2e` on push/PR.

**SQLite Used for Job Queue Under Concurrent Worker Load**
- Problem: `ingest/job/manager.py` uses SQLite (`kb_metadata.db`) as the job queue backend. Under concurrent batch processing (`ingest/worker/pool.py` spawns multiple workers), SQLite write contention becomes a bottleneck.
- Files: `ingest/job/manager.py`, `ingest/worker/pool.py`, `ingest/worker/batch_processor.py`
- Cause: SQLite has a single-writer limitation; WAL mode helps but doesn't eliminate contention.
- Improvement path: Enable WAL mode explicitly (`PRAGMA journal_mode=WAL`); or migrate to PostgreSQL/Redis for job queue at scale.

## Fragile Areas

**Test Suite Heavily Relies on `sys.modules` Monkey-Patching**
- Files: `tests/test_smoke.py`, `tests/test_hybrid_search.py`, `tests/test_payload_indexes.py`, `tests/test_reranker.py`, `tests/test_hybrid_rrf.py`
- Why fragile: Tests inject stub modules into `sys.modules` before imports. If import order changes, or test isolation between files is broken, stubs from one test file bleed into another.
- Safe modification: Always run tests in fresh subprocess isolation (`pytest-xdist` with `--forked`) rather than relying on manual `sys.modules` patching.
- Test coverage: Core MCP server logic (`kb_server/server.py`) has minimal unit test coverage; most tests cover auxiliary components.

**`qa/embedder.py` and `qa/run_qa.py` Must Import `kb_server` Before `mcp`**
- Files: `qa/embedder.py:8`, `qa/run_qa.py:19`
- Why fragile: Comment reads "must be imported before mcp pollutes sys.modules". This ordering dependency is invisible to tooling and will silently break if import order is changed.
- Safe modification: Document the constraint; consider a module-level guard or import hook.

## Missing Critical Features

**Sparse Search Is Stubbed Out (Not Implemented)**
- Problem: The hybrid search feature advertised in documentation (`docs/SEARCH_QUALITY.md`) is not actually performing sparse vector search. Sparse search code is commented out in `kb_server/retrieval/hybrid_search.py`.
- Blocks: True BM25/hybrid RAG quality; claimed FASE features are incomplete.

**RAGAS Evaluation Pipeline Is Not Implemented**
- Problem: `kb_server/evaluation/ragas_pipeline.py:47-53` contains a TODO and `raise NotImplementedError`. The `docs/RAG_EVALUATION.md` references this pipeline.
- Blocks: Automated RAG quality measurement.

**Chunking and Scoring Experiment Runners Are Stubs**
- Problem: `kb_server/optimization/chunking_experiments.py` and `kb_server/optimization/scoring_experiments.py` immediately `raise NotImplementedError`.
- Blocks: Parameter tuning for retrieval quality.

## Resolved Since Last Audit (2026-05-19)

- ✅ **`.env` files removed from git** — Only `config/.env.template` is tracked now. `.env` and `config/.env.local`/`config/.env.lxc` are in `.gitignore`.
- ✅ **`server/` directory deleted** — Old `server/` package removed. All entry points and tests now use `kb_server/`.
- ✅ **`ingest/registry.py` (v1) removed** — Old v1 registry no longer exists. Migration handled by `ingest/core/metadata.py`.
- ✅ **`bootstrap_env()` centralized** — All entry points now import from `config.bootstrap_env` instead of copy-pasting `load_dotenv` blocks.
- ✅ **Batch checksum fixed** — `ingest/worker/batch_processor.py` now computes SHA-256 instead of using `checksum="batch"` placeholder.
- ✅ **File watcher deletion implemented** — `on_deleted` handler now calls `delete_handler` to remove vectors from Qdrant.
- ✅ **Query metrics wired** — `kb_rag_query_duration_seconds` and `kb_rag_query_errors_total` now tracked in `kb_server/server.py`.
- ✅ **Cache metric names fixed** — `embed_client.py` now uses correct metric names (`cache_hits`, `cache_misses`).
- ✅ **Batch embedding/upsert metrics wired** — `record_batch_embedding()` and `record_batch_upsert()` now called from `embed_client.py` and `vector_store.py`.

## Test Coverage Gaps

**`kb_server/collections/` (multi-collection routing):**
- What's not tested: `CollectionManager` and `CollectionRouter` behavior under missing collections, alias resolution, error propagation to MCP tools.
- Files: `kb_server/collections/manager.py`, `kb_server/collections/router.py`
- Risk: Multi-collection feature (PHASE 15) could fail silently.
- Priority: High

**Metrics emission paths:**
- What's not tested: The newly wired metrics (`record_query`, `record_batch_embedding`, `record_batch_upsert`) have no dedicated tests verifying they emit correct Prometheus labels and values.
- Files: `observability/metrics.py`, `kb_server/server.py`, `kb_server/embed_client.py`, `kb_server/vector_store.py`
- Risk: Metrics refactoring could break silently.
- Priority: Medium

---

*Concerns audit: 2026-05-30*
*Previous audit: 2026-05-19*
*Changes: 6 issues resolved, 4 new issues added, 2 updated*
