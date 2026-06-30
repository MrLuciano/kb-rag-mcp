# KB-RAG MCP Backlog

Backlog of fixes and improvements from the Grafana "No data" metrics investigation session.

---

## Session Context

**Date**: 2026-05-30
**Trigger**: Grafana dashboard showing "No data" on most panels after full reclassification completed successfully.
**Environment**: AMD Ryzen 7 PRO 8845HS (WSL2), Docker Compose stack (kb-rag-mcp, Qdrant, Prometheus, Grafana)

---

## Pending / Known Issues

### 1. Pre-existing Test Failures — `test_list_tools_returns_five_tools`
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

### 2. Pre-existing Test Failures — E2E Ingestion & Health Workflows
**Status**: Known / Low Priority
**Files**: `tests/e2e/test_ingestion_workflow.py`, `tests/e2e/test_health_workflow.py`

**Problem**: 44 tests fail when run outside Docker because they require Qdrant, embedding backend, and filesystem paths not available in host test environment.

**Note**: These are environment-dependent, not code regressions. They pass when the full stack is available.

---

### 3. Ingest Pipeline Metrics Still Unwired
**Status**: Known / Backlog
**Severity**: Medium

**Problem**: Even after Phase 39 (Observability), the following ingest metrics remain defined but unpopulated:
- `kb_ingest_jobs_created_total` — needs wiring into job scheduler (`ingest/job/`)
- `kb_ingest_jobs_completed_total` / `kb_ingest_job_duration_seconds` — needs wiring into job completion
- `kb_ingest_files_processed_total` / `kb_ingest_file_processing_seconds` — needs wiring into `ingest/ingest.py` per-file loop
- `kb_ingest_chunks_generated_total` — needs wiring after chunking
- `kb_ingest_worker_pool_*` — needs wiring into `ingest/worker/pool.py`
- `kb_ingest_rate_limiter_*` — needs wiring if rate limiter is used
- `kb_ingest_api_requests_total` / `kb_ingest_api_latency_seconds` — health server does not use these
- `kb_http_pool_connections` — needs wiring from `httpx.AsyncClient` connection pool stats
- `kb_batch_processing_throughput_chunks_per_sec` — needs wiring into ingest orchestrator

**Decision**: These were intentionally left out because the immediate priority was Grafana usability for the query path. Ingest metrics can be wired when the ingest CLI (`kb-rag reclassify`) is actively used.

**Tracked in**: Phase 47 (LM Studio Dependency Handling) and future observability work.

---

### 4. Grafana Dashboard — Add Ingest Panels Back When Metrics Are Wired
**Status**: Backlog
**Depends on**: #3 above

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

## Operations Tasks

### 5. KB Has Zero Documents
**Status**: Ops task — not a development phase
**Effort**: ~30 min

**Problem**: OTCS documentation never ingested. Server returns empty results.
**Remediation**: `kb-ingest ingest --docs /mnt/c/Recebedor/learning/`

---

## Test Baseline

**Current passing tests**: 666 passed (excluding E2E environment-dependent failures)
**Known failing**: 44 E2E tests (require Docker stack), 1 unit test (`test_list_tools_returns_five_tools`)
**Regressions introduced**: None
**New tests needed**: None (existing tests cover the wired paths via `test_server_extra.py`)

---

## Tracked in ROADMAP

All critical/security/DB/quality items and feature work are now formally tracked in `.planning/ROADMAP.md` as phases:

| Backlog Item | ROADMAP Phase |
|--------------|---------------|
| CR-01/CR-03 (Auth gaps) | Phase 28c-fixes (done), Phase 44 (remaining) |
| CR-02/CR-05/CR-06/CR-07/CR-08 | Done in previous phases |
| CR-09 (Coverage 72% vs 90%) | Phase 46 |
| HW-01–HW-07 (Security) | Phase 44 |
| DB-01–DB-04 (Database) | Phase 45 |
| Q-01–Q-04 (Quality) | Phase 46 |
| M-02 (LM Studio fallback) | Phase 47 |
| S-01 (Cross-encoder lazy) | Phase 48 (done) |
| S-03 (Qdrant mock) | Phase 49 (done) |
| N-03 (SSE tests) | Phase 50 |
| Document Tag Management | Phase 51 |

---

## References

- `.planning/ROADMAP.md` — Current development roadmap (phases 43–51)
- `REVIEW.md` — Full audit with scores by dimension
- `.planning/reports/TECH_DEBT.md` — Consolidated technical debt from v0.1.0/v0.1.1
- `docs/AMDGPURESEARCH.md` — AMD GPU docling acceleration research
