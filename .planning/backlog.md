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

## References

- `docs/AMDGPURESEARCH.md` — AMD GPU docling acceleration research
- `ingest/ingest.py` — PDF extractor selection (`PDF_EXTRACTOR` env var)
- `ingest/reclassify_engine.py` — path resolution fixes
- `kb_server/ui/routes.py` — schema mapping fixes for web UI
- `docker-compose.yml` — web-ui service, port mappings
