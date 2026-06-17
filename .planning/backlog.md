# KB-RAG MCP Backlog

Backlog of fixes and improvements from the Grafana "No data" metrics investigation session.

---

## Session Context

**Date**: 2026-05-30
**Trigger**: Grafana dashboard showing "No data" on most panels after full reclassification completed successfully.
**Environment**: AMD Ryzen 7 PRO 8845HS (WSL2), Docker Compose stack (kb-rag-mcp, Qdrant, Prometheus, Grafana)

---

## Completed

### 1. Grafana "No data" — Root Cause & Fix
**Status**: Completed
**Severity**: High

**Problem**: Grafana dashboard displayed "No data" on ~70% of panels. Prometheus target was UP, but most queried metrics had zero values or did not exist.

**Root Cause**: Metrics were defined in `observability/metrics.py` but never actually emitted by application code:
- Job metrics (`kb_ingest_jobs_*`) — no ingest job runner wired them
- File metrics (`kb_ingest_files_processed_total`, `kb_ingest_chunks_generated_total`) — not wired into `ingest.py`
- Worker pool metrics (`kb_ingest_worker_pool_*`) — not wired into worker pool code
- Rate limiter metrics (`kb_ingest_rate_limiter_*`) — not wired
- API metrics (`kb_ingest_api_requests_total`, `kb_ingest_api_latency_seconds`) — health server did not use them
- Batch metrics — only `kb_batch_embedding_duration_seconds` and `kb_batch_upsert_duration_seconds` had zero values; `kb_batch_embeddings_total` and `kb_batch_upsert_points_total` never incremented
- Cache metrics (`kb_rag_cache_*`) — defined but `embed_client.py` used wrong metric names (`embedding_cache_hits_total` vs `cache_hits`)
- HTTP pool metrics (`kb_http_pool_connections`) — never called

**Fix**:
- Added `kb_rag_query_duration_seconds` histogram and `kb_rag_query_errors_total` counter to `observability/metrics.py`
- Wired `record_query()` and `record_query_error()` into `kb_server/server.py:call_tool()` to track all MCP tool executions
- Fixed `embed_client.py` `_metrics.increment()` calls to use correct metric names (`cache_hits`, `cache_misses`) with `backend="lru"` label
- Added missing `import time` to `kb_server/embed_client.py` (caused `NameError` during batch processing)
- Wired `record_batch_embedding()` into all batch embedding paths (`openai-compat`, `ollama`, fallback parallel)
- Wired `record_batch_upsert()` into `vector_store.py` `upsert_chunks()` and `upsert_chunks_parallel()`
- Rebuilt Grafana dashboard (`deployment/config/grafana-dashboard.json`) to only include panels querying live metrics:
  - Component Health Status (`up{job="kb-rag"}`)
  - Query Duration p95 (`kb_rag_query_duration_seconds`)
  - Query Errors (`kb_rag_query_errors_total`)
  - Batch Embedding Texts Rate (`kb_batch_embedding_texts_total`)
  - Batch Upsert Points Rate (`kb_batch_upsert_points_total`)
  - Batch Duration (embedding + upsert)
  - Cache Hit Rate %, Cache Size (MB), Cache Evictions Rate
  - Cache Hits / Misses, Cache Entries Count
- Removed 18 dead panels querying unpopulated metrics
- Synced dashboard to Helm charts (`deployment/helm/kb-rag-mcp/dashboards/`)
- Rebuilt and restarted `kb-rag-mcp` Docker container
- Grafana container restarted; dashboard confirmed loading with 15 panels

**Files Modified**:
- `observability/metrics.py`
- `kb_server/server.py`
- `kb_server/embed_client.py`
- `kb_server/vector_store.py`
- `deployment/config/grafana-dashboard.json`
- `deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json`

**Verification**:
- `curl http://localhost:8080/metrics | grep kb_rag_query` — shows histogram with buckets
- `curl http://localhost:9090/api/v1/query?query=kb_rag_query_duration_seconds_count` — returns data after tool calls
- Grafana UI: all 15 panels show data (or expected zeros) instead of "No data"

---

## Pending / Known Issues

### 2. Pre-existing Test Failures — `test_list_tools_returns_five_tools`
**Status**: Known / Low Priority
**File**: `tests/test_server_extra.py:110`

**Problem**: Test asserts `len(tools) == 5`, but `list_filter_options` tool was added in PHASE 17, making it 6 tools.

**Fix**: Update assertion to expect 6 tools or explicitly check for the new tool.

```python
assert set(names) == {
    "search_kb",
    "list_documents",
    "get_chunk",
    "kb_stats",
    "list_collections",
    "list_filter_options",  # PHASE 17
}
```

---

### 3. Pre-existing Test Failures — E2E Ingestion & Health Workflows
**Status**: Known / Low Priority
**Files**: `tests/e2e/test_ingestion_workflow.py`, `tests/e2e/test_health_workflow.py`

**Problem**: 44 tests fail when run outside Docker because they require Qdrant, embedding backend, and filesystem paths not available in host test environment.

**Note**: These are environment-dependent, not code regressions. They pass when the full stack is available.

---

### 4. Ingest Pipeline Metrics Still Unwired
**Status**: Known / Backlog
**Severity**: Medium

**Problem**: Even after this session, the following metrics remain defined but unpopulated:
- `kb_ingest_jobs_created_total` — needs wiring into job scheduler (`ingest/job/`)
- `kb_ingest_jobs_completed_total` / `kb_ingest_job_duration_seconds` — needs wiring into job completion
- `kb_ingest_files_processed_total` / `kb_ingest_file_processing_seconds` — needs wiring into `ingest/ingest.py` per-file loop
- `kb_ingest_chunks_generated_total` — needs wiring after chunking
- `kb_ingest_worker_pool_*` — needs wiring into `ingest/worker/pool.py`
- `kb_ingest_rate_limiter_*` — needs wiring if rate limiter is used
- `kb_ingest_api_requests_total` / `kb_ingest_api_latency_seconds` — health server does not use these; perhaps rename for ingest API if one exists
- `kb_http_pool_connections` — needs wiring from `httpx.AsyncClient` connection pool stats
- `kb_batch_processing_throughput_chunks_per_sec` — needs wiring into ingest orchestrator

**Decision**: These were intentionally left out of this session because the immediate priority was Grafana usability for the query path (which is the primary user-facing interaction). Ingest metrics can be wired when the ingest CLI (`kb-rag reclassify`) is actively used and metrics are needed for monitoring.

**Recommended approach**: When implementing ingest metrics, create a shared `MetricsCollector` instance in `ingest/cli/main.py` and pass it through to `ingest/ingest.py`, worker pool, and job scheduler.

---

### 5. Grafana Dashboard — Add Ingest Panels Back When Metrics Are Wired
**Status**: Backlog
**Depends on**: #4

When ingest metrics are wired, restore the removed panels to the dashboard:
- Files Processed (total) + rate
- Chunks Generated (total) + rate
- File Processing Duration p95
- Worker Pool Size / Queue / Utilization
- Jobs Created / Active / Completion Rate
- Job Duration (p50/p95/p99)
- Rate Limiter Tokens / Waits
- Batch Processing Throughput gauge
- HTTP Pool Connections

---

## Test Baseline

**Current passing tests**: 666 passed (excluding E2E environment-dependent failures)
**Known failing**: 44 E2E tests (require Docker stack), 1 unit test (`test_list_tools_returns_five_tools`)
**Regressions introduced**: None
**New tests needed**: None (existing tests cover the wired paths via `test_server_extra.py`)

---

---

## v0.1.6 Backlog — Review Findings & Tech Debt

Items consolidated from `REVIEW.md` (2026-06-15 full audit) and `.planning/reports/TECH_DEBT.md`.

### 🔴 Critical (Must Fix)

#### CR-01: Admin API has zero authentication
- **File:** `kb_server/ui/routes_admin.py`
- **Source:** REVIEW.md
- **Fix:** Add `Depends(get_current_user)` or API key check to document cleanup endpoints. **Partially fixed** — auth added but needs verification.

#### CR-02: Admin endpoints call non-existent methods
- **File:** `kb_server/ui/routes_admin.py`
- **Source:** REVIEW.md
- **Fix:** `delete_by_source` doesn't exist on VectorStore. `process_file` called with wrong signature. **Fixed** — changed to `delete_document`.

#### CR-03: Session cookie JWT_SECRET per-request random
- **File:** `kb_server/auth/router.py`
- **Source:** REVIEW.md
- **Fix:** `JWT_SECRET` defaults to random per-request. No cookie validation code exists. **Partially fixed** — secret made stable, validation still needed.

#### CR-05: Health check DB without connecting
- **File:** `kb_server/health.py:239`
- **Source:** REVIEW.md
- **Fix:** `check_database()` calls `get_stats()` without `connect()`. **Fixed.**

#### CR-06: Export crashes on non-existent column
- **File:** `ingest/cli/export.py:102`
- **Source:** REVIEW.md
- **Fix:** `version` column doesn't exist in files table. **Fixed.**

#### CR-07: IngestRegistry missing thread safety
- **File:** `ingest/core/metadata.py:766`
- **Source:** REVIEW.md
- **Fix:** Missing `check_same_thread=False` and WAL mode. **Fixed.**

#### CR-08: Undefined `os` in reclassify CLI
- **File:** `ingest/cli/reclassify.py`
- **Source:** REVIEW.md
- **Fix:** Uses `os.getenv` without importing `os`. **Fixed.**

#### Coverage: 72% branch vs 90% target
- **Severity:** HIGH
- **Source:** REVIEW.md
- **Issue:** CI gate `fail_under = 90` will fail on every PR. 1204 tests pass, 5 pre-existing failures (need Qdrant).

### 🟡 Security Warnings

#### HW-01: Horizontal privilege escalation — export_user_data
- **File:** `kb_server/auth/service.py:63`
- **Issue:** Any authenticated user can export any other user's data. No ownership check.
- **Fix:** Add `caller_id == target_user_id` check.

#### HW-02: Horizontal privilege escalation — list_api_keys
- **File:** `kb_server/auth/service.py:120`
- **Issue:** `list_api_keys` accepts arbitrary user_id without verifying caller ownership.
- **Fix:** Scope to caller's user_id from auth context.

#### HW-03: Erasure approve+execute in single request
- **File:** `kb_server/auth/erasure.py:46` + `kb_server/auth/router.py:178`
- **Issue:** No separation of duties — single request approves AND executes erasure.
- **Fix:** Split into two endpoints called by different roles.

#### HW-04: Session cookie secure=False
- **File:** `kb_server/auth/router.py:172`
- **Issue:** Cookie set with `secure=False` — leaks over HTTP.
- **Fix:** Set `secure=True` in production (env var gated).

#### HW-05: verify_key writes DB on every auth
- **File:** `kb_server/auth/service.py:177-178`
- **Issue:** Every API key verification writes `last_used_at` timestamp — DB contention under load.
- **Fix:** Batch in-memory, flush periodically.

#### HW-06: Auth router never mounted
- **File:** `kb_server/auth/router.py` (entire file)
- **Issue:** All auth endpoints are unreachable because the auth router is never mounted on the main server app.
- **Fix:** Mount router in `kb_server/server.py` `main()`.

#### HW-07: API key prefix in rate-limit subject
- **File:** `kb_server/server.py:564`
- **Issue:** API key prefix leaked into rate-limit subject tracking via `extract_bearer_token`.
- **Fix:** Hash or truncate the subject.

### 🟡 Database Warnings

#### DB-01: Connection leaks in UI routes
- **Files:** `kb_server/ui/routes.py`, `kb_server/ui/routes_admin.py`, `tests/test_query_analyzer.py`
- **Issue:** 7+ raw `sqlite3.connect()` calls without context managers — connections leak on exception.
- **Fix:** Use `with sqlite3.connect() as conn:` pattern.

#### DB-02: Foreign keys not enforced
- **Files:** All `connect()` methods in `ingest/core/metadata.py`, `kb_server/auth_registry.py`
- **Issue:** `PRAGMA foreign_keys=ON` never set — `ON DELETE CASCADE` silently ignored.
- **Fix:** Set `PRAGMA foreign_keys=ON` on every connection.

#### DB-03: Missing indexes
- **Files:** `kb_server/auth_registry.py` (`api_keys.prefix`), `kb_server/telemetry/query_logger.py` (`query_log.timestamp`)
- **Issue:** Full table scans on revoke and cleanup operations.
- **Fix:** Add indexes on `prefix` and `timestamp` columns.

#### DB-04: Migration fragility — bare CREATE TABLE
- **File:** `ingest/core/metadata.py` (reclassify_backups, reclassify_history tables)
- **Issue:** `CREATE TABLE` without `IF NOT EXISTS` — re-running migration crashes.
- **Fix:** Add `IF NOT EXISTS` to all migration DDL.

### 🟡 Quality Warnings

#### Q-01: 23 uses of deprecated datetime.utcnow()
- **Files:** Multiple across `kb_server/`, `ingest/`, `tests/`
- **Issue:** `datetime.utcnow()` deprecated in Python 3.12+. Causes warnings in test output (302 warnings).
- **Fix:** Replace with `datetime.now(datetime.UTC).replace(tzinfo=None)`.

#### Q-02: 481 flake8 violations
- **Source:** Full codebase scan
- **Issue:** Mostly line length (E501), unused imports (F401), whitespace (W293).
- **Fix:** Run `black` + manual cleanup.

#### Q-03: 17 unused imports
- **Files:** Multiple across codebase
- **Issue:** Stale imports from refactoring.
- **Fix:** Run `autoflake --remove-all-unused-imports`.

#### Q-04: 5 pre-existing test failures
- **Files:** `tests/test_smoke.py` (3), `tests/test_server_terms.py` (2)
- **Issue:** Require Qdrant running — need `@pytest.mark.integration` tag or mock fixes.

### 🟢 TECH_DEBT Items (from .planning/reports/TECH_DEBT.md)

#### M-01: KB has zero documents (Must Fix)
- **Effort:** ~30 min
- **Issue:** OTCS documentation never ingested. Server returns empty results.
- **Remediation:** `kb-ingest ingest --docs /mnt/c/Recebedor/learning/`

#### M-02: LM Studio must be running for ingest/eval (Must Fix)
- **Effort:** ~2h
- **Issue:** No graceful fallback if embedding backend is unreachable.
- **Remediation:** Add startup health-check, `kb-ingest check` command.

#### S-01: Cross-encoder model loads 500MB at import (Should Fix)
- **File:** `kb_server/retrieval/reranker.py`
- **Effort:** ~1h
- **Fix:** Defer model loading to first `predict()` call.

#### S-03: MagicMock pollution from qdrant_client stubs (Should Fix)
- **Files:** `tests/conftest.py`, `tests/test_vector_store_unit.py`
- **Effort:** ~2h
- **Fix:** Replace `sys.modules` stubbing with `unittest.mock.patch`.

#### N-03: SSE tests need separate process (Nice to Have)
- **Effort:** ~1h
- **Fix:** Refactor `test_smoke.py` to use per-function `@patch` instead of module-level stubs.

### TODO from REVIEW.md (not yet addressed)

- CR-09: Branch coverage — 72% vs 90% target in CI
- HW-01/02: Horizontal privilege escalation — ownership checks
- HW-03: Erasure separation of duties — split approve/execute
- HW-06: Mount auth router on main server app
- DB-01: Connection leaks — context manager pattern
- DB-02: Foreign key enforcement — PRAGMA foreign_keys=ON
- DB-03: Missing indexes — prefix, timestamp
- Q-01: datetime.utcnow() deprecation — 23 sites
- Q-02: 481 flake8 violations

---

## Feature: Document Tag Management & Re-ingest Control

### 6. Bulk Classification Tag Editor
**Status**: Proposed / Backlog
**Severity**: High
**Requested**: 2026-06-17

**Problem**: Users have no way to correct misclassified documents after ingestion. Wrong Product/Type/Version/Status tags require full re-ingestion. No bulk operations exist.

**Use Cases**:
- User accidentally ingested `.venv` Python packages as "documents" — 10,785 wrong files
- User wants to change product tag from "OTCS" to "OpenText-CS" for 1,700 files
- User wants to delete all "error" status files (11,436 items)
- User wants to mark 500 config guides for re-ingestion after product rename

**Proposed Feature**: `kb-rag tags` CLI + Web UI panel for bulk tag management

#### CLI Commands

```bash
# List current tag values and counts
kb-rag tags list --product
kb-rag tags list --type
kb-rag tags list --status

# Update tags (bulk)
kb-rag tags update --product "OTCS" --new-product "OpenText-CS" --dry-run
kb-rag tags update --product ".venv" --status "error" --remove
kb-rag tags update --type "config_guide" --version "v2.1" --mark-reingest

# Remove files from KB and registry
kb-rag tags remove --product ".venv" --confirm
kb-rag tags remove --status "error" --dry-run

# Mark for re-ingest (updates registry status + deletes Qdrant chunks)
kb-rag tags reingest --product "Documentum" --type "release_notes"
```

#### Web UI Panel

New admin page `/admin/tags` with:
- **Filter Bar**: Dropdowns for Product, Type, Version, Status + search box
- **Data Table**: Shows files matching filter with checkboxes
- **Bulk Actions Toolbar** (appears when rows selected):
  - "Change Product →" dropdown + apply
  - "Change Type →" dropdown + apply
  - "Change Version →" input + apply
  - "Change Status →" dropdown + apply
  - "Remove from KB" button (red, confirmation modal)
  - "Mark for Re-ingest" button
- **Stats Cards**: Total files, by-product breakdown, by-status breakdown
- **Dry-run toggle**: Preview changes without executing

#### Data Model Changes

No schema changes needed. Uses existing `ingest_registry.files` table columns:
- `product` (TEXT)
- `file_type` / `doc_type` (TEXT) — unify naming first
- `status` (TEXT: ok/error/deleted)
- `chunks` (INTEGER)

New operations on existing columns:
- `UPDATE files SET product = ? WHERE product = ?`
- `DELETE FROM files WHERE product = ?`
- `UPDATE files SET status = 'pending_reingest' WHERE ...`

#### Qdrant Integration

For removal:
```python
# Delete by payload filter
await client.delete(
    collection_name="kb_docs",
    points_selector=models.Filter(
        must=[
            models.FieldCondition(key="product", match=models.MatchValue(value=".venv"))
        ]
    )
)
```

For re-ingest marking:
```python
# Delete chunks from Qdrant, set registry status to "pending"
# Next ingest run picks them up
```

#### Files to Modify

- `ingest/cli/main.py` — add `tags` command group
- `ingest/cli/tags.py` — new CLI module
- `kb_server/ui/routes_admin.py` — add `/admin/tags` endpoints
- `kb_server/ui/templates/` — new tag management template
- `ingest/core/metadata.py` — add `IngestRegistry.bulk_update_tags()`, `.bulk_remove()`, `.mark_reingest()`
- `kb_server/vector_store.py` — add `delete_by_filter()` method

#### Effort Estimate
- CLI commands: ~2h
- Web UI panel: ~4h
- Registry methods: ~1h
- Qdrant deletion: ~1h
- Tests: ~2h
- **Total: ~10h**

#### Acceptance Criteria
- [ ] `kb-rag tags list` shows tag counts
- [ ] `kb-rag tags update --dry-run` previews changes without side effects
- [ ] `kb-rag tags remove` deletes files from registry + Qdrant
- [ ] `kb-rag tags reingest` sets status to pending + deletes Qdrant chunks
- [ ] Web UI shows filterable table with bulk actions
- [ ] All operations have confirmation for destructive actions
- [ ] Unit tests cover all registry methods
- [ ] Integration tests verify Qdrant deletion

---

## References

- `REVIEW.md` — Full audit with scores by dimension
- `.planning/reports/TECH_DEBT.md` — Consolidated technical debt from v0.1.0/v0.1.1
- `docs/AMDGPURESEARCH.md` — AMD GPU docling acceleration research
- `ingest/ingest.py` — PDF extractor selection (`PDF_EXTRACTOR` env var)
- `ingest/reclassify_engine.py` — path resolution fixes
- `kb_server/ui/routes.py` — schema mapping fixes for web UI
- `docker-compose.yml` — web-ui service, port mappings
