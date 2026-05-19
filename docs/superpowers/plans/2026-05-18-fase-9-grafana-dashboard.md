# FASE 9 Gap — Grafana Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a Grafana dashboard JSON file for KB-RAG monitoring covering ingestion, caching, batch processing, and worker metrics — ready to import into any Grafana instance.

**Architecture:** A single `deployment/config/grafana-dashboard.json` file using Grafana dashboard JSON model (v7+ compatible). No code changes needed — all metrics are already emitted by `observability/metrics.py` and scraped by Prometheus via the existing `deployment/config/prometheus.yml`. The dashboard is imported manually into Grafana UI or provisioned via `deployment/config/grafana-provisioning/`.

**Tech Stack:** Grafana dashboard JSON, Prometheus metrics already defined in `observability/metrics.py`.

---

## Prometheus Metrics Available

These are already emitted by the system (from `observability/metrics.py`):

**Ingestion:**
- `kb_ingest_jobs_created_total`, `kb_ingest_jobs_completed_total`, `kb_ingest_jobs_active`
- `kb_ingest_job_duration_seconds` (histogram)
- `kb_ingest_files_processed_total`, `kb_ingest_file_processing_seconds`
- `kb_ingest_chunks_generated_total`

**Workers & Rate Limiter:**
- `kb_ingest_worker_pool_size`, `kb_ingest_worker_pool_queue_size`, `kb_ingest_worker_pool_utilization`
- `kb_ingest_rate_limiter_tokens`, `kb_ingest_rate_limiter_waits_total`, `kb_ingest_rate_limiter_wait_seconds`

**Embedding API:**
- `kb_ingest_api_requests_total`, `kb_ingest_api_latency_seconds`
- `kb_batch_embeddings_total`, `kb_batch_embedding_texts_total`, `kb_batch_embedding_duration_seconds`
- `kb_batch_processing_throughput_chunks_per_sec`

**Cache:**
- `kb_rag_cache_hits_total`, `kb_rag_cache_misses_total`, `kb_rag_cache_evictions_total`
- `kb_rag_cache_size_bytes`, `kb_rag_cache_entries`

**HTTP Pool:**
- `kb_http_pool_connections`

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `deployment/config/grafana-dashboard.json` | Create | Main dashboard JSON |
| `deployment/config/grafana-provisioning/dashboards/kb-rag.yaml` | Create | Grafana provisioning config |
| `deployment/config/grafana-provisioning/datasources/prometheus.yaml` | Create | Datasource provisioning |
| `tests/e2e/test_deployment_workflow.py` | Modify | Add test that dashboard file exists and is valid JSON |

---

## Task 1: Create Grafana dashboard JSON

**Files:**
- Create: `deployment/config/grafana-dashboard.json`

- [ ] **Step 1: Write the failing test**

Open `tests/e2e/test_deployment_workflow.py` and add:

```python
def test_grafana_dashboard_exists(self):
    """Grafana dashboard JSON file must exist and be valid."""
    import json
    dashboard_path = Path("deployment/config/grafana-dashboard.json")
    self.assertTrue(dashboard_path.exists(), "grafana-dashboard.json not found")
    with open(dashboard_path) as f:
        data = json.load(f)
    self.assertIn("panels", data, "Dashboard must have panels")
    self.assertIn("title", data, "Dashboard must have title")
    self.assertGreater(len(data["panels"]), 5, "Dashboard should have at least 6 panels")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. pytest tests/e2e/test_deployment_workflow.py -k "test_grafana_dashboard_exists" -v
```
Expected: FAIL — `grafana-dashboard.json not found`

- [ ] **Step 3: Create grafana-dashboard.json**

```bash
cat > deployment/config/grafana-dashboard.json << 'DASHBOARD_EOF'
```

Write the file `deployment/config/grafana-dashboard.json` with this content:

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "description": "",
      "type": "datasource",
      "pluginId": "prometheus",
      "pluginName": "Prometheus"
    }
  ],
  "__requires": [
    {
      "type": "grafana",
      "id": "grafana",
      "name": "Grafana",
      "version": "9.0.0"
    },
    {
      "type": "datasource",
      "id": "prometheus",
      "name": "Prometheus",
      "version": "1.0.0"
    },
    {
      "type": "panel",
      "id": "stat",
      "name": "Stat",
      "version": ""
    },
    {
      "type": "panel",
      "id": "timeseries",
      "name": "Time series",
      "version": ""
    },
    {
      "type": "panel",
      "id": "gauge",
      "name": "Gauge",
      "version": ""
    }
  ],
  "annotations": {
    "list": []
  },
  "description": "KB-RAG MCP Server monitoring dashboard",
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 1,
  "id": null,
  "links": [],
  "panels": [
    {
      "collapsed": false,
      "gridPos": { "h": 1, "w": 24, "x": 0, "y": 0 },
      "id": 1,
      "title": "Ingestion Overview",
      "type": "row"
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": {
          "color": { "mode": "thresholds" },
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": null }
            ]
          },
          "unit": "short"
        }
      },
      "gridPos": { "h": 4, "w": 4, "x": 0, "y": 1 },
      "id": 2,
      "options": { "colorMode": "value", "graphMode": "area", "reduceOptions": { "calcs": ["lastNotNull"] } },
      "title": "Jobs Created (total)",
      "type": "stat",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_ingest_jobs_created_total",
          "legendFormat": "jobs"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": {
          "color": { "mode": "thresholds" },
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": null },
              { "color": "yellow", "value": 1 },
              { "color": "red", "value": 5 }
            ]
          },
          "unit": "short"
        }
      },
      "gridPos": { "h": 4, "w": 4, "x": 4, "y": 1 },
      "id": 3,
      "options": { "colorMode": "value", "graphMode": "none", "reduceOptions": { "calcs": ["lastNotNull"] } },
      "title": "Active Jobs",
      "type": "stat",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_ingest_jobs_active",
          "legendFormat": "active"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "short", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 4, "w": 4, "x": 8, "y": 1 },
      "id": 4,
      "options": { "colorMode": "value", "graphMode": "area", "reduceOptions": { "calcs": ["lastNotNull"] } },
      "title": "Files Processed (total)",
      "type": "stat",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_ingest_files_processed_total",
          "legendFormat": "files"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "short", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 4, "w": 4, "x": 12, "y": 1 },
      "id": 5,
      "options": { "colorMode": "value", "graphMode": "area", "reduceOptions": { "calcs": ["lastNotNull"] } },
      "title": "Chunks Generated (total)",
      "type": "stat",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_ingest_chunks_generated_total",
          "legendFormat": "chunks"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "s", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 5 },
      "id": 6,
      "title": "Job Duration (p50 / p95 / p99)",
      "type": "timeseries",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "histogram_quantile(0.50, rate(kb_ingest_job_duration_seconds_bucket[5m]))",
          "legendFormat": "p50"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "histogram_quantile(0.95, rate(kb_ingest_job_duration_seconds_bucket[5m]))",
          "legendFormat": "p95"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "histogram_quantile(0.99, rate(kb_ingest_job_duration_seconds_bucket[5m]))",
          "legendFormat": "p99"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "short", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 5 },
      "id": 7,
      "title": "Files Processed Rate",
      "type": "timeseries",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "rate(kb_ingest_files_processed_total[5m])",
          "legendFormat": "files/s"
        }
      ]
    },
    {
      "collapsed": false,
      "gridPos": { "h": 1, "w": 24, "x": 0, "y": 13 },
      "id": 8,
      "title": "Workers & Rate Limiter",
      "type": "row"
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "min": 0,
          "max": 1,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": null },
              { "color": "yellow", "value": 0.7 },
              { "color": "red", "value": 0.9 }
            ]
          }
        }
      },
      "gridPos": { "h": 8, "w": 6, "x": 0, "y": 14 },
      "id": 9,
      "title": "Worker Pool Utilization",
      "type": "gauge",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_ingest_worker_pool_utilization",
          "legendFormat": "utilization"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "short", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 8, "w": 9, "x": 6, "y": 14 },
      "id": 10,
      "title": "Worker Pool — Size / Queue",
      "type": "timeseries",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_ingest_worker_pool_size",
          "legendFormat": "pool size"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_ingest_worker_pool_queue_size",
          "legendFormat": "queue size"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "short", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 8, "w": 9, "x": 15, "y": 14 },
      "id": 11,
      "title": "Rate Limiter — Tokens / Waits",
      "type": "timeseries",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_ingest_rate_limiter_tokens",
          "legendFormat": "available tokens"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "rate(kb_ingest_rate_limiter_waits_total[5m])",
          "legendFormat": "waits/s"
        }
      ]
    },
    {
      "collapsed": false,
      "gridPos": { "h": 1, "w": 24, "x": 0, "y": 22 },
      "id": 12,
      "title": "Embedding API & Batch Processing",
      "type": "row"
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "s", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 23 },
      "id": 13,
      "title": "Embedding API Latency (p50 / p95)",
      "type": "timeseries",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "histogram_quantile(0.50, rate(kb_ingest_api_latency_seconds_bucket[5m]))",
          "legendFormat": "p50"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "histogram_quantile(0.95, rate(kb_ingest_api_latency_seconds_bucket[5m]))",
          "legendFormat": "p95"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "short", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 23 },
      "id": 14,
      "title": "Batch Processing Throughput (chunks/s)",
      "type": "timeseries",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_batch_processing_throughput_chunks_per_sec",
          "legendFormat": "throughput"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "rate(kb_batch_embeddings_total[5m])",
          "legendFormat": "embedding batches/s"
        }
      ]
    },
    {
      "collapsed": false,
      "gridPos": { "h": 1, "w": 24, "x": 0, "y": 31 },
      "id": 15,
      "title": "Cache",
      "type": "row"
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "min": 0,
          "max": 1,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "red", "value": null },
              { "color": "yellow", "value": 0.5 },
              { "color": "green", "value": 0.8 }
            ]
          }
        }
      },
      "gridPos": { "h": 8, "w": 6, "x": 0, "y": 32 },
      "id": 16,
      "title": "Cache Hit Rate",
      "type": "gauge",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "rate(kb_rag_cache_hits_total[5m]) / (rate(kb_rag_cache_hits_total[5m]) + rate(kb_rag_cache_misses_total[5m]) + 0.001)",
          "legendFormat": "hit rate"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "short", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 8, "w": 9, "x": 6, "y": 32 },
      "id": 17,
      "title": "Cache Hits / Misses / Evictions",
      "type": "timeseries",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "rate(kb_rag_cache_hits_total[5m])",
          "legendFormat": "hits/s"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "rate(kb_rag_cache_misses_total[5m])",
          "legendFormat": "misses/s"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "rate(kb_rag_cache_evictions_total[5m])",
          "legendFormat": "evictions/s"
        }
      ]
    },
    {
      "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
      "fieldConfig": {
        "defaults": { "unit": "bytes", "color": { "mode": "palette-classic" } }
      },
      "gridPos": { "h": 8, "w": 9, "x": 15, "y": 32 },
      "id": 18,
      "title": "Cache Size (bytes) / Entries",
      "type": "timeseries",
      "targets": [
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_rag_cache_size_bytes",
          "legendFormat": "size bytes"
        },
        {
          "datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" },
          "expr": "kb_rag_cache_entries",
          "legendFormat": "entries"
        }
      ]
    }
  ],
  "refresh": "30s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["kb-rag", "rag", "mcp"],
  "templating": { "list": [] },
  "time": { "from": "now-1h", "to": "now" },
  "timepicker": {},
  "timezone": "browser",
  "title": "KB-RAG MCP",
  "uid": "kb-rag-mcp-v1",
  "version": 1
}
```

- [ ] **Step 4: Run test**

```bash
PYTHONPATH=. pytest tests/e2e/test_deployment_workflow.py -k "test_grafana_dashboard_exists" -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add deployment/config/grafana-dashboard.json tests/e2e/test_deployment_workflow.py
git commit -m "feat(monitoring): add Grafana dashboard JSON with 18 panels covering ingestion, workers, cache, batching"
```

---

## Task 2: Grafana provisioning configs

**Files:**
- Create: `deployment/config/grafana-provisioning/dashboards/kb-rag.yaml`
- Create: `deployment/config/grafana-provisioning/datasources/prometheus.yaml`

- [ ] **Step 1: Create provisioning files**

```yaml
# deployment/config/grafana-provisioning/dashboards/kb-rag.yaml
apiVersion: 1

providers:
  - name: 'KB-RAG'
    orgId: 1
    folder: 'KB-RAG'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

```yaml
# deployment/config/grafana-provisioning/datasources/prometheus.yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    jsonData:
      timeInterval: "15s"
    version: 1
    editable: true
```

- [ ] **Step 2: Verify files exist**

```bash
ls deployment/config/grafana-provisioning/dashboards/
ls deployment/config/grafana-provisioning/datasources/
```
Expected: both yaml files present

- [ ] **Step 3: Commit**

```bash
git add deployment/config/grafana-provisioning/
git commit -m "feat(monitoring): add Grafana provisioning configs for dashboard and datasource"
```

---

## Task 3: Update OPERATIONS.md with Grafana import instructions

**Files:**
- Modify: `docs/OPERATIONS.md`

- [ ] **Step 1: Check current OPERATIONS.md for Grafana section**

```bash
grep -n -i "grafana" docs/OPERATIONS.md | head -10
```

- [ ] **Step 2: Add Grafana section if missing**

Find the monitoring section in `docs/OPERATIONS.md` and add after the Prometheus section:

```markdown
### Grafana Dashboard

**Import manually:**
1. Open Grafana UI → Dashboards → Import
2. Upload `deployment/config/grafana-dashboard.json`
3. Select your Prometheus datasource
4. Click Import

**Provision automatically (Grafana 7+):**
```bash
# Copy provisioning configs to Grafana
sudo cp deployment/config/grafana-provisioning/datasources/prometheus.yaml \
  /etc/grafana/provisioning/datasources/
sudo cp deployment/config/grafana-provisioning/dashboards/kb-rag.yaml \
  /etc/grafana/provisioning/dashboards/
sudo cp deployment/config/grafana-dashboard.json \
  /etc/grafana/provisioning/dashboards/
sudo systemctl restart grafana-server
```

**Dashboard panels:**
- Ingestion Overview: jobs, files, chunks, job duration
- Workers & Rate Limiter: pool utilization, queue depth, token bucket
- Embedding API & Batch: latency p50/p95, throughput
- Cache: hit rate gauge, hits/misses/evictions, size
```

- [ ] **Step 3: Commit**

```bash
git add docs/OPERATIONS.md
git commit -m "docs: add Grafana dashboard import/provisioning instructions to OPERATIONS.md"
```
