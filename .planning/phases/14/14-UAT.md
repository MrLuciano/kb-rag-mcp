---
status: diagnosed
phase: 14-health-dashboard
source:
  - 14-01-SUMMARY.md
  - 14-02-SUMMARY.md
  - 14-03-SUMMARY.md
  - 14-04-SUMMARY.md
  - 14-05-SUMMARY.md
started: 2026-05-26T03:30:00Z
updated: 2026-05-26T10:35:00Z
---

## Current Test

[testing paused - 1 blocker issue found, 10 tests blocked pending fix]

## Tests

### 1. Cold Start - Docker Compose Stack
expected: Start the full monitoring stack from scratch. `docker-compose up -d` completes without errors. All 4 services start: qdrant, kb-rag-mcp, prometheus, grafana. `docker-compose ps` shows all services as "Up (healthy)". No error logs in any service.
result: issue
reported: "docker compose up -d fails with 'Error dependency qdrant failed to start'. Qdrant container healthcheck fails with 'curl: executable file not found in $PATH'. Also need configurable volume paths for Qdrant database files."
severity: blocker

### 2. Metrics Endpoint Accessibility
expected: Visit `http://localhost:8000/metrics` in browser or curl. Page loads successfully with HTTP 200. Content-Type header shows `text/plain; version=X.X.X; charset=utf-8`. Response body contains plain text with metric names starting with `kb_` (e.g., `kb_ingest_jobs_created_total`, `kb_rag_cache_hits_total`).
result: blocked
blocked_by: server
reason: "Cannot test - kb-rag-mcp container depends on qdrant health, which is failing due to Test 1 issues"

### 3. Prometheus Scraping kb-rag-mcp
expected: Open Prometheus UI at `http://localhost:9090`. Navigate to Status → Targets. See `kb-rag` target listed with health status "UP". Scrape endpoint shows `http://kb-rag-mcp:8000/metrics`. Last scrape shows recent timestamp (within last 15 seconds).
result: blocked
blocked_by: server
reason: "Cannot test - prometheus depends on kb-rag-mcp health"

### 4. Prometheus Metrics Query
expected: In Prometheus UI at `http://localhost:9090`, go to Graph tab. Type query: `kb_ingest_jobs_created_total`. Click Execute. See metric data or "No data" message (valid if no jobs have run yet). Metric is recognized (no "Unknown metric" error).
result: blocked
blocked_by: server
reason: "Cannot test - prometheus depends on kb-rag-mcp health"

### 5. Grafana UI Access
expected: Open Grafana at `http://localhost:3000`. Login page appears with username/password fields. Enter `admin` / `admin`. Login succeeds. Grafana home page loads showing dashboards and navigation menu.
result: blocked
blocked_by: server
reason: "Cannot test - grafana depends on prometheus health"

### 6. Grafana Dashboard Discovery
expected: In Grafana UI, click "Dashboards" menu (left sidebar). See "KB-RAG Dashboards" folder or "KB-RAG MCP Monitoring" dashboard listed. Click to open dashboard. Dashboard loads without errors.
result: blocked
blocked_by: server
reason: "Cannot test - grafana depends on prometheus health"

### 7. Dashboard Structure - 6 Row Sections
expected: Grafana dashboard shows 6 collapsible row sections at the top level: "Server Metrics", "Ingestion Metrics", "Jobs", "Embedding Health", "Cache Performance", "Qdrant Health". Clicking a row expands to show panels underneath. All rows expand without errors.
result: blocked
blocked_by: server
reason: "Cannot test - grafana depends on prometheus health"

### 8. Dashboard Panels - Server Metrics
expected: Expand "Server Metrics" row. See panels for: Component Health Status, HTTP Requests Rate, API Latency. Panels load (may show "No data" if no activity yet, which is valid). No "Panel plugin not found" or other errors.
result: blocked
blocked_by: server
reason: "Cannot test - grafana depends on prometheus health"

### 9. Dashboard Panels - Cache Performance
expected: Expand "Cache Performance" row. See panels for: Cache Hit Rate %, Cache Size (MB), Cache Evictions Rate. Panels use gauge or timeseries visualization. Panels load without errors.
result: blocked
blocked_by: server
reason: "Cannot test - grafana depends on prometheus health"

### 10. Dashboard Refresh Intervals
expected: In Grafana dashboard, click the refresh interval dropdown (top right, next to time range). Dropdown shows options: 5s, 15s, 30s, 1m, 5m, 15m. Current selection is 15s. Selecting a different interval changes the refresh rate (visible in UI or by watching panels update).
result: blocked
blocked_by: server
reason: "Cannot test - grafana depends on prometheus health"

### 11. Prometheus Datasource in Grafana
expected: In Grafana, go to Configuration → Data Sources (gear icon in left sidebar). See "Prometheus" datasource listed. Click it. Datasource settings show URL: `http://prometheus:9090`. Click "Test" button at bottom. Message shows "Data source is working" with green checkmark.
result: blocked
blocked_by: server
reason: "Cannot test - grafana depends on prometheus health"

### 12. Documentation - OPERATIONS.md Health Dashboard Section
expected: Open `docs/OPERATIONS.md` in text editor or markdown viewer. Search for "## Health Dashboard" section (around line 290). Section exists with subsections: Overview, Accessing the Dashboard, Prometheus Metrics, Common Queries, Troubleshooting. Content is comprehensive (~250 lines) with specific commands and URLs.
result: pending

### 13. Documentation - README Monitoring Link
expected: Open `README.md`. Search for "monitoring". See feature bullet mentioning "Real-time monitoring dashboard: Grafana + Prometheus". Technical Documentation section has link to OPERATIONS.md with inline mention of "health dashboard". Clicking link (if viewing in GitHub/web) navigates to OPERATIONS.md#health-dashboard.
result: pending

### 14. Helm Chart Validation
expected: Run `helm lint deployment/helm/kb-rag-mcp`. Command completes with exit code 0. Output shows "1 chart(s) linted, 0 chart(s) failed". No errors about monitoring templates.
result: pending

### 15. Helm Chart - Monitoring Disabled
expected: Run `helm template test-release deployment/helm/kb-rag-mcp --set monitoring.enabled=false | grep -c "kind: Service"`. Output shows count that does NOT include prometheus or grafana services. Monitoring stack is omitted when disabled via values.
result: pending

## Summary

total: 15
passed: 0
issues: 1
pending: 3
skipped: 0
blocked: 10

## Gaps

- truth: "Docker Compose stack starts all 4 services successfully with healthy status"
  status: failed
  reason: "User reported: docker compose up -d fails with 'Error dependency qdrant failed to start'. Qdrant container healthcheck fails with 'curl: executable file not found in $PATH'. Also need configurable volume paths for Qdrant database files."
  severity: blocker
  test: 1
  root_cause: "docker-compose.yml qdrant healthcheck uses CMD curl, but qdrant/qdrant:latest image (Alpine-based) does not include curl or wget. Healthcheck fails immediately, marking container unhealthy. kb-rag-mcp service has `depends_on: qdrant: condition: service_healthy`, so it never starts. Volume path `./data/qdrant` is hardcoded with no environment variable override."
  artifacts:
    - path: "docker-compose.yml"
      line: 11
      issue: "healthcheck uses 'curl' command not available in qdrant container"
    - path: "docker-compose.yml"
      line: 9
      issue: "volume path './data/qdrant' is hardcoded, not configurable via env var"
  missing:
    - "Replace curl-based healthcheck with wget (available in qdrant image) or HTTP endpoint test using sh + nc"
    - "Add QDRANT_DATA_PATH environment variable with default './data/qdrant'"
    - "Update volume binding to use ${QDRANT_DATA_PATH:-./data/qdrant}:/qdrant/storage"
    - "Document QDRANT_DATA_PATH in .env.example and OPERATIONS.md"
  debug_session: ""
