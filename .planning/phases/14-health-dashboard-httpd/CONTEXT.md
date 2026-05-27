# Phase 14: Health Dashboard - Planning Context

**Date:** 2026-05-26  
**Phase:** 14 - Health Dashboard  
**Milestone:** v1.3 Post-Ship Polish & Infrastructure

---

## Problem Statement

System administrators and power users need a unified, real-time view of all kb-rag-mcp subsystem health and performance metrics. Currently:

- Health checks exist but are CLI-only (`kb-rag check health`) or JSON endpoints (`/health/detailed`)
- Grafana dashboard JSON exists but is NOT deployed in Docker Compose or Kubernetes
- No `/metrics` endpoint for Prometheus scraping (metrics defined but not exposed)
- Monitoring infrastructure (Prometheus + Grafana) exists in config but not integrated into deployments

**User need:** "Consolidate health/status access to all subsystems (Qdrant health, kb-rag-mcp server, ingestion status) into a single beautiful dashboard page."

---

## User Requirements

### Primary Use Case
- **Who:** System administrators, DevOps/SRE teams, power users
- **Why:** Monitor system health, troubleshoot issues, validate deployments
- **When:** Continuous monitoring, incident response, post-deploy validation

### Visual Design
- **Style:** Modern web design (polished, professional)
- **Layout:** Tab-based UI with 6 sections:
  1. Server Metrics (health status, component latencies)
  2. Ingestion Metrics (files processed, chunks indexed, throughput)
  3. Jobs (active/completed/failed, durations)
  4. Embedding Health (backend status, API latency, cache)
  5. Cache Performance (hit rate, evictions, size)
  6. Qdrant Health (collection stats, vector counts)

### Refresh Rate
- Near real-time with user-selectable intervals: **5s, 15s, 30s, 1m**
- Grafana native feature (no custom code needed)

### Deployment Targets
- **Docker Compose:** Add Prometheus + Grafana services
- **Kubernetes:** Create Prometheus + Grafana deployments in Helm chart

---

## Technical Decision: Grafana-Centric Approach

After evaluating 3 options (Static HTML, FastAPI+Jinja2, Grafana-Centric), **Option C: Grafana-Centric Dashboard** was selected.

### Rationale

**Alignment with requirements:**
- ✅ User explicitly requested to "extend Grafana dashboard and Prometheus service"
- ✅ Leverages existing `deployment/config/grafana-dashboard.json` (425 lines)
- ✅ Leverages existing Prometheus metrics in `observability/metrics.py` (28 metrics)
- ✅ Tab-based UI = Grafana dashboard rows (native feature)
- ✅ Selectable refresh intervals = Grafana built-in (5s, 15s, 30s, 1m)
- ✅ Modern web design = Grafana's polished UI
- ✅ Production-grade monitoring stack (industry standard)

**Why NOT alternatives:**
- ❌ Static HTML or FastAPI+Jinja2 would create a SECOND dashboard → fragmented monitoring
- ❌ Building custom charts duplicates Grafana's rich visualization capabilities
- ❌ Does not leverage existing Grafana investment

### Architecture Components

**Core change:** Add `/metrics` endpoint to `kb_server/health_server.py`
- Exposes existing Prometheus metrics from `observability/metrics.py`
- Uses `prometheus_client.generate_latest()`
- Minimal code change (~30 lines)

**Dashboard updates:** Extend `deployment/config/grafana-dashboard.json`
- Reorganize into 6 rows (tab sections)
- Add panels for all 28 Prometheus metrics
- Configure refresh intervals and panel thresholds

**Docker Compose integration:**
- Add `prometheus` service (scrapes `kb-rag-mcp:8000/metrics`)
- Add `grafana` service (provisioned with dashboard + datasource)
- Total: 4 services (Qdrant, kb-rag-mcp, Prometheus, Grafana)

**Kubernetes integration:**
- Create `deployment/helm/kb-rag-mcp/templates/prometheus.yaml`
- Create `deployment/helm/kb-rag-mcp/templates/grafana.yaml`
- Add Ingress routes for Grafana UI access
- Optional: ServiceMonitor CRD for Prometheus Operator

---

## Metrics Inventory

### Health Check Components (from kb_server/health.py)
1. **Embedding service** - Backend, model, dims, latency
2. **Vector store (Qdrant)** - Total chunks, documents, collection name, latency
3. **Cache** - Backend, entries, size MB, hit rate, latency
4. **Database (SQLite)** - Total jobs, active jobs, total files, latency
5. **Filesystem** - Free GB, total GB, percent free, latency

### Prometheus Metrics (from observability/metrics.py)

**Jobs:**
- `kb_ingest_jobs_created_total` (by priority)
- `kb_ingest_jobs_completed_total` (by status: completed/failed/cancelled)
- `kb_ingest_jobs_active` (by status: pending/running/paused)
- `kb_ingest_job_duration_seconds` (histogram)

**Files & Chunks:**
- `kb_ingest_files_processed_total` (by status)
- `kb_ingest_file_processing_seconds` (histogram)
- `kb_ingest_chunks_generated_total`

**Workers:**
- `kb_ingest_worker_pool_size`
- `kb_ingest_worker_pool_queue_size`
- `kb_ingest_worker_pool_utilization`

**Rate Limiter:**
- `kb_ingest_rate_limiter_tokens`
- `kb_ingest_rate_limiter_waits_total`
- `kb_ingest_rate_limiter_wait_seconds`

**API & Embeddings:**
- `kb_ingest_api_requests_total` (by endpoint)
- `kb_ingest_api_latency_seconds` (histogram)
- `kb_batch_embeddings_total`
- `kb_batch_embedding_texts_total`
- `kb_batch_embedding_duration_seconds`
- `kb_batch_processing_throughput_chunks_per_sec`

**Cache:**
- `kb_rag_cache_hits_total`
- `kb_rag_cache_misses_total`
- `kb_rag_cache_evictions_total`
- `kb_rag_cache_size_bytes`
- `kb_rag_cache_entries`

**Upserts:**
- `kb_batch_upserts_total`
- `kb_batch_upsert_points`
- `kb_batch_upsert_duration`

**HTTP Pool:**
- `kb_http_pool_connections`

---

## Dashboard Tab Structure

### Tab 1: Server Metrics
- Overall system health status (healthy/degraded)
- Component health badges (embedding, vector_store, cache, database, filesystem)
- Component latencies (gauge panels)
- Timestamp of last health check

### Tab 2: Ingestion Metrics
- Files processed total (counter)
- Files processing rate (rate over time)
- Chunks generated total (counter)
- Chunks per second (gauge)
- File processing duration (histogram → p50, p95, p99)

### Tab 3: Jobs
- Active jobs gauge (by status: pending/running/paused)
- Jobs created rate (by priority)
- Jobs completed rate (by status: completed/failed/cancelled)
- Job duration histogram (p50, p95, p99)
- Worker pool size, queue size, utilization

### Tab 4: Embedding Health
- Embedding backend status (text panel: backend name, model)
- API request rate (by endpoint)
- API latency histogram (p50, p95, p99)
- Batch embeddings rate
- Batch processing throughput (chunks/sec)

### Tab 5: Cache Performance
- Cache hit rate percentage (gauge)
- Cache hits vs misses (time-series)
- Cache evictions rate
- Cache size (MB)
- Cache entries count

### Tab 6: Qdrant Health
- Qdrant collection name (text panel)
- Total documents count
- Total chunks/vectors count
- Index size (from Qdrant metrics if exposed)
- Query latency (if available)

---

## Deployment Configuration

### Docker Compose Services

**prometheus:**
- Image: `prom/prometheus:latest`
- Config: Mount `deployment/config/prometheus.yml`
- Scrape target: `kb-rag-mcp:8000/metrics`
- Scrape interval: 15s
- Port: 9090 (Prometheus UI)

**grafana:**
- Image: `grafana/grafana:latest`
- Config: Mount `deployment/config/grafana-provisioning/`
- Provisioned dashboard: `deployment/config/grafana-dashboard.json`
- Provisioned datasource: Prometheus at `http://prometheus:9090`
- Port: 3000 (Grafana UI)
- Default credentials: admin/admin

### Kubernetes Deployments

**Prometheus StatefulSet:**
- 1 replica
- PersistentVolumeClaim for time-series data (10Gi, adjustable)
- ConfigMap for `prometheus.yml`
- Service: ClusterIP, port 9090

**Grafana Deployment:**
- 1 replica
- ConfigMap for provisioning configs
- ConfigMap for dashboard JSON
- Service: ClusterIP, port 3000
- Ingress: `/grafana` path (configurable)

**ServiceMonitor (optional):**
- If Prometheus Operator is installed
- Auto-discover kb-rag-mcp pods with label selector
- Scrape `/metrics` endpoint

---

## Success Criteria

### Functional Requirements
- [ ] `/metrics` endpoint on health_server returns Prometheus format
- [ ] Prometheus scrapes kb-rag-mcp successfully (no errors in Prometheus logs)
- [ ] Grafana dashboard displays all 6 tabs with panels
- [ ] All 28 metrics are visible in Grafana (no "No data" panels)
- [ ] Dashboard refresh intervals work (5s, 15s, 30s, 1m)
- [ ] Docker Compose brings up all 4 services (Qdrant, kb-rag, Prometheus, Grafana)
- [ ] Kubernetes Helm chart deploys all services including Prometheus + Grafana

### Quality Requirements
- [ ] Dashboard is responsive (works on mobile/tablet)
- [ ] Panels load in <2s with default data retention
- [ ] Documentation updated (OPERATIONS.md with dashboard access instructions)
- [ ] Screenshots added to `docs/assets/grafana-dashboard.png`

### Testing Requirements
- [ ] Manual test: `curl localhost:8000/metrics` returns valid Prometheus format
- [ ] Manual test: Open Grafana at `localhost:3000`, verify all panels load
- [ ] Manual test: Trigger ingestion job, verify metrics update in dashboard
- [ ] Manual test: Stop Qdrant, verify health status shows "degraded" in dashboard
- [ ] E2E test: Verify `deployment/config/grafana-dashboard.json` is valid JSON

---

## Constraints & Non-Goals

### In Scope
- ✅ Prometheus + Grafana deployment in Docker Compose
- ✅ Prometheus + Grafana deployment in Kubernetes/Helm
- ✅ `/metrics` endpoint on health_server
- ✅ Extend existing Grafana dashboard JSON with 6-tab structure
- ✅ Documentation and screenshots

### Out of Scope (Future Work)
- ❌ Log aggregation (would require Loki)
- ❌ Distributed tracing (would require Tempo)
- ❌ Alerting rules (Prometheus alertmanager config exists but not configured)
- ❌ Authentication (Grafana anonymous access OK for internal deployments)
- ❌ Custom landing page (Grafana IS the dashboard)
- ❌ Real-time WebSocket updates (Grafana polling sufficient)

### Project Constraints
- **No breaking changes** - Existing health endpoints must remain unchanged
- **No new dependencies** - `prometheus_client` already in `requirements.txt`
- **Python 3.11+ only** - Standard project requirement
- **Test baseline** - 585 tests passing, no regressions allowed
- **Coverage baseline** - 90% coverage maintained

---

## Implementation Phases

### Phase 1: Metrics Endpoint (1 day)
Add `/metrics` route to `kb_server/health_server.py`
- Import `prometheus_client.generate_latest, CONTENT_TYPE_LATEST`
- Add `@app.get("/metrics")` route
- Return `Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)`
- Test: `curl localhost:8000/metrics | grep kb_ingest`

### Phase 2: Dashboard Design (2 days)
Extend `deployment/config/grafana-dashboard.json`
- Open in Grafana UI for visual editing
- Create 6 dashboard rows (collapsible sections)
- Add panels for each metric (28 panels total)
- Configure panel thresholds, colors, units
- Export JSON, commit to repo

### Phase 3: Docker Compose Integration (1 day)
Update `docker-compose.yml`
- Add `prometheus` service with volume mounts
- Add `grafana` service with provisioning mounts
- Configure network connectivity
- Test: `docker-compose up -d && curl localhost:3000`

### Phase 4: Kubernetes Integration (2 days)
Update Helm chart
- Create `templates/prometheus.yaml` (StatefulSet, Service, ConfigMap)
- Create `templates/grafana.yaml` (Deployment, Service, ConfigMap, Ingress)
- Update `values.yaml` with toggles and config
- Test: `helm install kb-rag ./deployment/helm/kb-rag-mcp`

### Phase 5: Documentation (1 day)
Update documentation
- `docs/OPERATIONS.md` - Add "Health Dashboard" section
- `README.md` - Add dashboard screenshot and link
- Capture screenshots with `docs/assets/grafana-dashboard-*.png`
- Document Prometheus query examples

**Total Estimated Effort:** 7 days

---

## Open Questions (Resolved)

1. ~~Should we add a custom landing page at `/`?~~  
   **Decision:** No. Grafana IS the dashboard. Health server `/health` endpoints remain for programmatic access.

2. ~~Should we support both anonymous and authenticated Grafana access?~~  
   **Decision:** Anonymous access sufficient for v1 (internal deployments). Add auth in future if needed.

3. ~~Should we configure Prometheus alerting rules?~~  
   **Decision:** Out of scope for Phase 14. Alert config exists in `kb-rag-alerts.yml` but not activated.

4. ~~Should we add ServiceMonitor for Prometheus Operator?~~  
   **Decision:** Optional. Add if Prometheus Operator detected, otherwise use standard Service scraping.

5. ~~Historical data retention for Prometheus?~~  
   **Decision:** Default 15 days, configurable via `values.yaml` for Kubernetes.

---

## References

**Existing Assets:**
- `deployment/config/grafana-dashboard.json` - Current dashboard (425 lines)
- `deployment/config/prometheus.yml` - Prometheus scrape config
- `deployment/config/grafana-provisioning/` - Grafana provisioning configs
- `observability/metrics.py` - All 28 Prometheus metrics definitions
- `kb_server/health.py` - Health check system (5 components)
- `kb_server/health_server.py` - FastAPI health HTTP server

**Documentation:**
- `docs/superpowers/plans/2026-05-18-fase-9-grafana-dashboard.md` - Prior Grafana dashboard plan
- `docs/OPERATIONS.md` - Operations guide (to be updated)

**Tech Stack:**
- Prometheus: Latest stable (v2.x)
- Grafana: Latest stable (v10.x or v11.x)
- FastAPI: 0.136.1 (current)
- prometheus_client: 0.25.0 (current)

---

## Next Step

Return to planning workflow to break down implementation into executable plans.
