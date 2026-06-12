# KB-RAG Operations Guide

Quick reference for daily operations, maintenance, and monitoring.

> **Note:** This is a quick reference. For detailed guides, see:
> - [README.md](../README.md) - Complete setup and usage
> - [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Problem solving
> - [logging-audit.md](logging-audit.md) — Logging coverage report

---

## Common

Content in this file applies to all deployment modes unless noted.
For mode-specific guidance:

- **Docker Compose** → [↓ Docker Compose](#docker-compose)
- **Helm (Kubernetes)** → [↓ Helm](#helm)
- **Systemd (Bare Metal)** → [↓ Systemd](#systemd)
- **Manual (Source)** → [↓ Manual](#manual)

---

## Daily Operations

### Service Management

```bash
# Start all services
sudo systemctl start kb-rag.target

# Stop all services
sudo systemctl stop kb-rag.target

# Restart all services
sudo systemctl restart kb-rag.target

# Check status
sudo systemctl status kb-rag.target

# Individual services
sudo systemctl restart kb-rag-server    # MCP server
sudo systemctl restart kb-rag-health    # Health check server
sudo systemctl restart kb-rag-scheduler # Job scheduler
```

### Health Monitoring

```bash
# Quick health check
curl http://localhost:8080/health

# Detailed health status
curl http://localhost:8080/health/detailed | jq

# Check specific component
curl http://localhost:8080/health/detailed | jq '.components.embedding'

# Health check script
./deployment/scripts/health-check.sh all

# Via CLI (requires kb-ingest on PATH)
kb-ingest check health
```

### Embedding Backend (LM Studio / Ollama)

KB-RAG requires an embedding service to convert text into vector
representations for semantic search. The server does not perform
embedding natively — it delegates to one of these backends:

| Backend | Env Value | Description |
|---------|-----------|-------------|
| LM Studio (SDK) | `lmstudio-sdk` | **Default.** Uses LM Studio's local inference server via SDK (port 1234) |
| LM Studio (REST) | `lmstudio-rest` | REST API to LM Studio (port 1234) |
| Ollama | `ollama` | Local Ollama instance (recommended for Docker/K8s) |
| OpenAI-compatible | `openai-compat` | Any OpenAI-compatible API |

### Ollama Deployment (Optional)

For Docker Compose and Kubernetes deployments, Ollama can be deployed as a
self-contained embedding backend. The model `nomic-embed-text:v1.5` is used:

- **Size:** 274MB (137M parameters, 768-dim)
- **Memory:** ~1Gi runtime (274MB weights + 500MB overhead)
- **GPU:** Optional — works on CPU
- **Model:** `nomic-embed-text:v1.5` (2K context window)

**Docker Compose:**
```bash
# Start Ollama alongside the main stack
docker compose -f docker-compose.yml -f deployment/docker-compose/ollama.yml up -d

# Pull model
docker compose exec ollama ollama pull nomic-embed-text:v1.5

# Configure .env
export OLLAMA_HOST=http://localhost:11434
export EMBED_BACKEND=ollama
export EMBED_MODEL=nomic-embed-text:v1.5
```

**Kubernetes / Helm:**
```bash
helm install kb-rag-mcp ./deployment/helm/kb-rag-mcp \
  --set ollama.enabled=true \
  --set ollama.model=nomic-embed-text:v1.5
```

See [KUBERNETES.md](KUBERNETES.md) for full Helm configuration.

**Configuration:**
```bash
# Set the backend
export EMBED_BACKEND=ollama
export OLLAMA_HOST=http://localhost:11434
export EMBED_MODEL=nomic-embed-text:v1.5

# Or via .env file (see config/.env.template)
```

#### Startup Requirements

Before starting the KB-RAG server, ensure the embedding backend is
running and reachable on the expected host:port.

#### Configuration

Set the backend via the `EMBED_BACKEND` environment variable:

```bash
# Default (LM Studio SDK)
export EMBED_BACKEND=lmstudio-sdk

# Ollama
export EMBED_BACKEND=ollama
export EMBED_BASE_URL=http://127.0.0.1:11434
export EMBED_MODEL=nomic-embed-text

# OpenAI-compatible (any OpenAI API proxy)
export EMBED_BACKEND=openai-compat
export EMBED_BASE_URL=https://api.openai.com/v1
export EMBED_API_KEY=sk-...
export EMBED_MODEL=text-embedding-3-small
```

#### Startup Requirements

Before starting the KB-RAG server, ensure the embedding backend is
running and reachable on the expected host:port.

**Checking backend health:**
```bash
# Via health check endpoint
curl http://localhost:8080/health/detailed | jq '.components.embedding'

# Via CLI (requires kb-ingest on PATH)
kb-ingest check health
```

The server logs a warning at startup if the embedding backend is
unreachable. The server will still start — queries will fail at
runtime with embedding errors until the backend is available.

#### Troubleshooting

**"Embedding backend unreachable" at startup:**
1. Verify LM Studio is running: `curl http://127.0.0.1:1234/v1/models`
2. Check which port LM Studio is serving on (Settings → Server)
3. Verify `EMBED_BASE_URL` matches LM Studio's listening address
4. If using LM Studio, ensure the model is loaded (not just downloaded)
5. Try a different backend type (e.g., `ollama`) as a fallback

#### Fallback Options

If LM Studio is not available (e.g., on resource-constrained servers),
use one of these alternatives:

1. **Ollama** — Lightweight local inference. Install via:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull nomic-embed-text
   ```
   Then set `EMBED_BACKEND=ollama`.

2. **OpenAI API** — No local hardware required. Requires an API key.
   Set `EMBED_BACKEND=openai-compat` with your API endpoint and key.

### Viewing Logs

```bash
# Follow all logs
sudo journalctl -u kb-rag-server -u kb-rag-health -f

# Last 100 lines
sudo journalctl -u kb-rag-server -n 100

# Since 1 hour ago
sudo journalctl -u kb-rag-server --since "1 hour ago"

# Errors only
sudo journalctl -u kb-rag-server -p err

# Save logs for analysis
sudo journalctl -u kb-rag-server --since today > kb-rag.log
```

---

## Routine Maintenance

### Daily Tasks

**Morning Checks:**
```bash
# 1. Check service status
sudo systemctl status kb-rag.target

# 2. Check health
curl http://localhost:8080/health/detailed | jq '.healthy'

# 3. Check disk space
df -h /opt/kb-rag

# 4. Review overnight errors
sudo journalctl -u kb-rag-server --since "24 hours ago" -p err
```

### Weekly Tasks

**Every Monday:**
```bash
# 1. Create backup
./deployment/scripts/backup.sh /backups/weekly-$(date +%Y%m%d).tar.gz

# 2. Check resource usage
systemd-cgtop -1 | grep kb-rag

# 3. Review cache hit rate (should be >80%)
curl http://localhost:8080/health/detailed | jq '.components.cache.details.hit_rate'

# 4. Clean old logs (if not auto-rotating)
sudo journalctl --vacuum-time=30d
```

### Monthly Tasks

**First of each month:**
```bash
# 1. Update system
sudo ./deployment/scripts/update.sh

# 2. Clean old backups (keep 3 months)
find /backups -name "kb-rag-*.tar.gz" -mtime +90 -delete

# 3. Review Prometheus alerts
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing")'

# 4. Verify test suite passes
pytest tests/ -v
```

---

## Backup and Restore

### Creating Backups

```bash
# Manual backup
./deployment/scripts/backup.sh

# Custom location
./deployment/scripts/backup.sh /path/to/backup.tar.gz

# Scheduled backup (add to cron)
0 3 * * * /opt/kb-rag/deployment/scripts/backup.sh /backups/daily-$(date +\%Y\%m\%d).tar.gz
```

### Restoring Backups

```bash
# Restore from backup (stops services automatically)
sudo ./deployment/scripts/restore.sh /path/to/backup.tar.gz

# Verify after restore
curl http://localhost:8080/health/detailed
```

### Backup Strategy

**Recommended schedule:**
- **Daily:** Automated backup at 3 AM
- **Weekly:** Copy backup to off-site storage
- **Monthly:** Test restore procedure
- **Retention:** 30 days daily, 12 weeks weekly, 12 months monthly

---

## Document Ingestion

### Single File Ingestion

```bash
cd /opt/kb-rag
source venv/bin/activate

# Ingest single file
python -m ingest.ingest --file /path/to/document.pdf

# Check status
python -m ingest.ingest --status
```

### Bulk Ingestion

```bash
# Ingest entire directory (incremental)
python -m ingest.ingest --docs /path/to/docs

# With specific product
python -m ingest.ingest --docs /path/to/docs --product MyProduct

# Clean and re-ingest everything
python -m ingest.ingest --docs /path/to/docs --clean

# More workers (if resources available)
python -m ingest.ingest --docs /path/to/docs --workers 8
```

### Monitoring Ingestion

```bash
# Check ingestion status
python -m ingest.ingest --status

# List all files
python -m ingest.ingest --status --list

# Show errors only
python -m ingest.ingest --status --errors

# Count documents by product
sqlite3 /opt/kb-rag/data/kb_metadata.db \
  "SELECT product, COUNT(*) FROM file_registry GROUP BY product"
```

---

## Health Dashboard

KB-RAG includes an integrated Grafana dashboard for real-time monitoring of all subsystems.

### Overview

The health dashboard provides 6 tab sections:

1. **Server Metrics** - Overall system health, component status, HTTP request rates
2. **Ingestion Metrics** - Files processed, chunks generated, processing throughput
3. **Jobs** - Active jobs, completion rates, duration histograms
4. **Embedding Health** - API latency, batch processing, throughput
5. **Cache Performance** - Hit rates, evictions, memory usage
6. **Qdrant Health** - Collection stats, vector counts, query latency

All metrics update in near real-time with selectable refresh intervals (5s, 15s, 30s, 1m).

<!-- TODO: Add dashboard screenshots showing:
     - Server Metrics tab (component health badges)
     - Ingestion Metrics tab (file processing rates)
     - Cache Performance tab (hit rate gauge)
     See GitHub issue for screenshot capture task -->

### Accessing the Dashboard

#### Docker Compose Deployments

1. Configure environment variables (optional):
   ```bash
   # Edit .env to customize ports and paths
   SSE_PORT=8765              # MCP SSE endpoint port
   DATA_DIR=./data            # Application data directory
   LOGS_DIR=./logs            # Log files directory
   QDRANT_DATA_PATH=./data/qdrant  # Qdrant storage path
   ```

2. Start the full stack:
   ```bash
   docker-compose up -d
   ```

3. Verify all services are healthy:
   ```bash
   docker-compose ps
   # Expected: All services show "healthy" status
   # Startup time: ~60-90 seconds for full health
   ```

4. Verify Grafana is running:
   ```bash
   docker-compose ps grafana
   # Expected: State = Up (healthy)
   ```

5. Open Grafana UI:
   ```
   http://localhost:3000
   ```

6. Default credentials: `admin` / `admin` (change on first login)

7. Navigate to: **Dashboards → KB-RAG Dashboards → KB-RAG MCP Monitoring**

#### Kubernetes Deployments

1. Verify monitoring components are deployed:
   ```bash
   kubectl get pods -l app.kubernetes.io/component=grafana
   kubectl get pods -l app.kubernetes.io/component=prometheus
   ```

2. Port-forward to Grafana:
   ```bash
   kubectl port-forward svc/<release-name>-grafana 3000:3000
   ```

3. Open Grafana UI:
   ```
   http://localhost:3000
   ```

4. Credentials: Set via Helm values (`monitoring.grafana.adminPassword`)

5. Dashboard auto-loads from ConfigMap provisioning

**Production Ingress:** Enable external access via Helm values:
```bash
helm install kb-rag ./deployment/helm/kb-rag-mcp \
  --set monitoring.grafana.ingress.enabled=true \
  --set monitoring.grafana.ingress.hosts[0].host=grafana.example.com
```

### Prometheus Metrics

All metrics are exposed at `/metrics` endpoint on the health server (port 8080, NOT SSE_PORT).

#### Job Metrics
- `kb_ingest_jobs_created_total{priority}` - Total jobs created by priority
- `kb_ingest_jobs_completed_total{status}` - Completed jobs (completed/failed/cancelled)
- `kb_ingest_jobs_active{status}` - Active jobs (pending/running/paused)
- `kb_ingest_job_duration_seconds` - Job execution duration histogram

#### Ingestion Metrics
- `kb_ingest_files_processed_total{status}` - Files processed by status
- `kb_ingest_chunks_generated_total` - Total chunks indexed
- `kb_ingest_file_processing_seconds` - File processing duration histogram

#### Cache Metrics
- `kb_rag_cache_hits_total` - Cache hits
- `kb_rag_cache_misses_total` - Cache misses
- `kb_rag_cache_size_bytes` - Cache size in bytes
- `kb_rag_cache_entries` - Number of cached entries

#### Provider Resilience Metrics
- kb_provider_requests_total{provider}
- kb_provider_errors_total{provider}
- kb_provider_circuit_state{provider,state}
- kb_provider_fallbacks_total{from_provider,to_provider}
- kb_provider_skipped_circuit_open_total{provider}
- kb_provider_skipped_budget_exhausted_total{provider}
- kb_provider_circuit_opened_total{provider}

#### Retrieval Cache Metrics
- kb_retrieval_cache_hits_total
- kb_retrieval_cache_misses_total

### Common Queries

#### Cache Hit Rate (%)
```promql
(rate(kb_rag_cache_hits_total[5m]) / (rate(kb_rag_cache_hits_total[5m]) + rate(kb_rag_cache_misses_total[5m]))) * 100
```

#### Files Processed per Minute
```promql
rate(kb_ingest_files_processed_total[1m]) * 60
```

#### Job Duration p95 (seconds)
```promql
histogram_quantile(0.95, rate(kb_ingest_job_duration_seconds_bucket[5m]))
```

#### Active Jobs by Status
```promql
sum by (status) (kb_ingest_jobs_active)
```

#### Embedding API Latency p99 (seconds)
```promql
histogram_quantile(0.99, rate(kb_ingest_api_latency_seconds_bucket[5m]))
```

### Customizing the Dashboard

The dashboard JSON is version-controlled at:
- **Docker Compose:** `deployment/config/grafana-dashboard.json`
- **Kubernetes:** Embedded in ConfigMap via Helm chart

To customize:

1. Edit dashboard in Grafana UI
2. Export JSON: **Dashboard Settings → JSON Model → Copy to clipboard**
3. Save to `deployment/config/grafana-dashboard.json`
4. Commit changes
5. Restart Grafana to reload:
   - Docker Compose: `docker-compose restart grafana`
   - Kubernetes: `kubectl rollout restart deployment/<release-name>-grafana`

### Disabling Monitoring

#### Docker Compose
Comment out `prometheus` and `grafana` services in `docker-compose.yml`:
```bash
docker-compose up -d qdrant kb-rag-mcp
```

#### Kubernetes
Disable via Helm values:
```bash
helm install kb-rag ./deployment/helm/kb-rag-mcp \
  --set monitoring.enabled=false
```

Or disable individual components:
```bash
--set monitoring.prometheus.enabled=false
--set monitoring.grafana.enabled=false
```

### Storage Configuration

#### Prometheus Data Retention

**Docker Compose:** Edit `docker-compose.yml` command args:
```yaml
- '--storage.tsdb.retention.time=30d'  # Default: 15d
```

**Kubernetes:** Set via Helm values:
```bash
--set monitoring.prometheus.retention=30d
--set monitoring.prometheus.storage.size=50Gi  # Default: 10Gi
```

#### Persistent Storage Location

- **Docker Compose:** Named volume `prometheus-data` (managed by Docker)
- **Kubernetes:** PersistentVolumeClaim (uses cluster default StorageClass)

To use a specific StorageClass in Kubernetes:
```bash
--set monitoring.prometheus.storage.storageClass=fast-ssd
```

### Troubleshooting

#### Grafana Shows "No Data"

1. Verify Prometheus is scraping successfully:
   ```bash
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[0].health'
   # Expected: "up"
   ```

2. Check kb-rag-mcp `/metrics` endpoint:
   ```bash
   curl http://localhost:8080/metrics | grep kb_ingest
   # Should return multiple metrics
   ```

3. Verify Grafana datasource:
   - Grafana UI → Configuration → Data Sources → Prometheus
   - Click "Test" button → Should show "Data source is working"

#### Prometheus Not Scraping Targets

**Docker Compose:**
```bash
# Verify service networking
docker-compose exec prometheus wget -O- http://kb-rag-mcp:8080/metrics
```

**Kubernetes:**
```bash
# Verify service discovery
kubectl exec -it <prometheus-pod> -- wget -O- http://<kb-rag-service>:8080/metrics
```

Check Prometheus logs:
```bash
docker-compose logs prometheus | grep ERROR  # Docker Compose
kubectl logs <prometheus-pod> | grep ERROR   # Kubernetes
```

#### High Memory Usage

Prometheus memory usage scales with:
- Number of time series (metrics × label combinations)
- Data retention period
- Scrape interval

To reduce:
1. Increase scrape interval: `--set monitoring.prometheus.scrapeInterval=30s`
2. Reduce retention: `--set monitoring.prometheus.retention=7d`
3. Increase memory limits: `--set monitoring.prometheus.resources.limits.memory=2Gi`

---

## Reclassification Management

### Overview

The reclassification system allows operators to update document metadata in Qdrant without re-ingesting or re-embedding documents. This is useful when:
- Classification rules improve (e.g., better vendor/subsystem detection)
- Documents were misclassified during initial ingest
- Metadata standards change (e.g., new product taxonomy)

### CLI Installation

The `kb-rag` command is installed as a console script via `setup.py`:

```bash
# Install in editable mode (development)
pip install -e .

# Verify command is available
kb-rag --help
kb-rag reclassify --help
```

> **Note:** `kb-ingest` is the legacy CLI entrypoint (`kb-ingest-legacy`).
> The modern CLI uses `kb-rag` for all operations including reclassification.

### Quick Reference

| Subcommand | Purpose | Example |
|-----------|---------|---------|
| `run` | Apply classification changes | `kb-rag reclassify run "docs/**/*.pdf"` |
| `verify` | Preview changes without applying | `kb-rag reclassify verify "docs/**/*.pdf"` |
| `sessions` | List backup sessions | `kb-rag reclassify sessions` |
| `rollback` | Restore from backup | `kb-rag reclassify rollback --session <ts>` |

### Architecture

**Components:**
- `kb_server/vector_store.py:update_chunk_metadata()` — In-place Qdrant payload updates
- `ingest/reclassify_engine.py` — Detection, backup, audit logic
- `ingest/cli/reclassify.py` — CLI commands (reclassify, verify, sessions, rollback)
- `data/registry.db` — SQLite tables: `reclassify_backups`, `reclassify_history`

**Data Flow:**
1. Scan Qdrant for documents matching pattern/filter
2. Run `classify()` on each source file
3. Compare current metadata vs. expected
4. Backup old metadata to SQLite
5. Update Qdrant payloads via `set_payload()`
6. Log changes to audit table

### Safety Mechanisms

#### 1. Interactive Confirmation

All reclassify operations show aggregated preview before applying changes:

```bash
kb-rag reclassify run "docs/**/*.pdf"

# Output:
# Found 47 documents with classification changes:
#
# Field      Documents  Change
# vendor     47         (empty) → 'OpenText'
# subsystem  23         (empty) → 'Admin'
#
# Apply these changes? [y/N]:
```

Use `--yes` flag only in automated scripts after testing interactively.

#### 2. Automatic Backup

Before updating Qdrant, old metadata is written to `reclassify_backups` table:

```sql
CREATE TABLE reclassify_backups (
    session_timestamp TEXT NOT NULL,
    source_file TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    chunk_index INTEGER,
    PRIMARY KEY (session_timestamp, source_file, field_name, chunk_index)
);
```

Each reclassify operation creates a session (timestamp: `2026-05-26T15-30-00`) linking all backups for that run.

#### 3. Audit Trail

All changes logged to `reclassify_history` table:

```sql
CREATE TABLE reclassify_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source_file TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    session_timestamp TEXT NOT NULL,
    FOREIGN KEY (session_timestamp) REFERENCES reclassify_backups(session_timestamp)
);
```

Query audit history:

```bash
sqlite3 data/registry.db
sqlite> SELECT * FROM reclassify_history WHERE source_file LIKE '%WebReports%';
```

#### 4. Backup Retention

Backups are kept for 30 days by default, auto-cleaned on each reclassify run. Configure:

```bash
export RECLASSIFY_BACKUP_RETENTION_DAYS=90
```

Disable auto-cleanup: `export RECLASSIFY_BACKUP_RETENTION_DAYS=0`

### Operational Procedures

#### Procedure 1: Verify Before Reclassify

Always verify changes before applying:

```bash
# 1. Check what would change
kb-rag reclassify verify "docs/**/*.pdf" > /tmp/verify-before.txt

# 2. Review output
less /tmp/verify-before.txt

# 3. Apply changes
kb-rag reclassify run "docs/**/*.pdf"

# 4. Verify applied
kb-rag reclassify verify "docs/**/*.pdf" > /tmp/verify-after.txt

# 5. Compare
diff /tmp/verify-before.txt /tmp/verify-after.txt
```

#### Procedure 2: Rollback Session

If reclassification produces incorrect results:

```bash
# 1. List recent sessions
kb-rag reclassify sessions

# Output:
# Session               Documents  Fields Changed  Date
# 2026-05-26T15-30-00   47         70              2026-05-26 15:30:00

# 2. Rollback session
kb-rag reclassify rollback --session 2026-05-26T15-30-00

# 3. Verify rollback
kb-rag reclassify verify "docs/**/*.pdf"
```

#### Procedure 3: Selective Rollback

Rollback specific documents to state before timestamp:

```bash
# Rollback only OpenText docs to state before 16:00
kb-rag reclassify rollback "docs/OT*.pdf" --before 2026-05-26T16-00-00
```

#### Procedure 4: Bulk Reclassification (Large Datasets)

For datasets with 10,000+ documents:

```bash
# Disable progress bar for faster processing
kb-rag reclassify run "**/*" --no-progress --yes > /tmp/reclassify.log 2>&1

# Monitor progress in separate terminal
watch -n 5 'tail -20 /tmp/reclassify.log'
```

### Monitoring

**Check reclassification activity:**

```sql
-- Recent reclassifications
SELECT 
    session_timestamp,
    COUNT(DISTINCT source_file) as docs,
    COUNT(*) as fields_changed
FROM reclassify_history
WHERE timestamp > datetime('now', '-7 days')
GROUP BY session_timestamp
ORDER BY timestamp DESC;

-- Most frequently reclassified documents
SELECT 
    source_file,
    COUNT(*) as reclassify_count
FROM reclassify_history
GROUP BY source_file
HAVING COUNT(*) > 1
ORDER BY reclassify_count DESC
LIMIT 20;
```

**Prometheus metrics (Phase 14 integration):**

```prometheus
# Reclassified documents total (counter)
reclassified_documents_total

# Reclassified chunks total (counter)
reclassified_chunks_total

# Backup sessions total (gauge)
reclassify_backup_sessions_total
```

### Troubleshooting

#### Issue: Reclassify slow for large collections

**Symptom:** `kb-rag reclassify run "**/*"` takes >10 minutes

**Cause:** Running `classify()` on thousands of files is I/O-bound

**Solution:**
1. Use metadata filters to reduce scope: `--filter 'vendor=""'`
2. Process in batches: `kb-rag reclassify run "docs/batch-1/*.pdf"`
3. Disable progress bar: `--no-progress`

#### Issue: Rollback fails with "Qdrant update error"

**Symptom:** `kb-rag reclassify rollback --session <timestamp>` fails mid-restore

**Cause:** Qdrant connection issues or collection deleted

**Solution:**
1. Check Qdrant health: `curl http://localhost:6333/healthz`
2. Verify collection exists: `kb-ingest db collections`
3. Manual restore from SQLite backup:

```python
import sqlite3
from kb_server.vector_store import VectorStore

conn = sqlite3.connect("data/registry.db")
session = "2026-05-26T15-30-00"

backups = conn.execute(
    "SELECT source_file, field_name, old_value FROM reclassify_backups WHERE session_timestamp=?",
    (session,)
).fetchall()

# Manually restore using VectorStore API
store = VectorStore()
await store.connect()
# ... restore logic ...
```

#### Issue: Backup session missing (auto-cleaned)

**Symptom:** `kb-rag reclassify sessions` doesn't show expected session

**Cause:** Session older than retention period (default 30 days)

**Solution:**
- No automatic recovery — backups are deleted
- Prevention: Set longer retention: `export RECLASSIFY_BACKUP_RETENTION_DAYS=90`
- For critical operations, export backups before cleanup:

```bash
# Export backups to JSON before cleanup
sqlite3 data/registry.db -json "SELECT * FROM reclassify_backups" > backups.json
```

### Best Practices

1. **Test on small subset first:** Before reclassifying thousands of documents, test on small pattern: `kb-rag reclassify run "docs/test/*.pdf"`

2. **Use verify workflow:** Always run `verify` before and after reclassification to confirm changes

3. **Document classification rule changes:** When updating `ingest/classifier.py`, document rationale in commit message for future reference

4. **Monitor audit history:** Regularly review `reclassify_history` table to identify frequently-reclassified documents (may indicate unstable classification rules)

5. **Backup before major changes:** Export `reclassify_backups` table before bulk reclassification:

```bash
sqlite3 data/registry.db ".dump reclassify_backups" > /backups/reclassify-$(date +%Y%m%d).sql
```

6. **Set retention based on change frequency:** If classification rules change often, increase retention: `export RECLASSIFY_BACKUP_RETENTION_DAYS=90`

### Integration with CI/CD

**Automated reclassification after classifier updates:**

```yaml
# .github/workflows/reclassify-on-classifier-update.yml
name: Auto-reclassify on classifier update

on:
  push:
    paths:
      - 'ingest/classifier.py'
    branches:
      - main

jobs:
  reclassify:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      
      - name: Verify changes
        run: |
          kb-rag reclassify verify "**/*" --filter 'vendor=""' > verify-before.txt
          
      - name: Reclassify if changes detected
        run: |
          if grep -q "Found.*documents with mismatches" verify-before.txt; then
              kb-rag reclassify run "**/*" --filter 'vendor=""' --yes
          fi
          
      - name: Verify applied
        run: |
          kb-rag reclassify verify "**/*" --filter 'vendor=""'
```

**Safety check:** Only auto-reclassify with narrow filters (e.g., `vendor=""`) to avoid unintended changes.

---

## Connector Operations (Phase 29)

### Managing Remote Sources

```bash
# List available connector types
python -m ingest.cli.main connectors list

# Stage a connector for sync
python -m ingest.cli.main connectors stage --type confluence \
  --source-key "my-docs" \
  --endpoint "https://confluence.example.com/rest/api"
```

### Confluence Connector
- Env vars: CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_TOKEN
- Supports Cloud (Bearer) and Server/DC (Basic) auth
- Uses CQL for query building, pagination for large spaces

### JIRA Connector
- Env vars: JIRA_URL, JIRA_USERNAME, JIRA_TOKEN
- JQL builder with project and incremental sync filters
- ADF to Markdown extraction

### Git Connector
- Env vars: GIT_REPO_URL, GIT_REPO_PATH
- Full sync: clone + ls-tree; incremental: pull + diff
- Support for HTTPS token and SSH auth

## Auth Operations (Phase 32)

```bash
# Create a new API key
python -m ingest.cli.main auth create --scope global --description "CI key"

# List existing keys (shows only prefixes)
python -m ingest.cli.main auth list

# Revoke a key
python -m ingest.cli.main auth revoke <8-char-prefix>
```

Keys are stored as SHA-256 hashes. Enable with AUTH_ENABLED=true in .env.

## Quota Operations (Phase 34)

```bash
# View current limits and usage
python -m ingest.cli.main quota show

# Set limits
python -m ingest.cli.main quota set --max-files 50000 --max-bytes 1073741824

# Reset usage counters
python -m ingest.cli.main quota reset
```

## Provider Resilience (Phase 36)

Circuit breaker and budget system protects against cascading provider failures:
- CLOSED → OPEN after CIRCUIT_BREAKER_THRESHOLD failures
- OPEN → HALF_OPEN after cooldown (exponential backoff: 30s, 60s, 120s...)
- HALF_OPEN → CLOSED on success, → OPEN on failure

Fallback chain: semicolon-separated EMBED_BACKEND (e.g., "lmstudio;ollama")

---

## Common Tasks

### Restart Services After Config Change

```bash
# 1. Edit configuration
sudo nano /opt/kb-rag/config/kb-rag.env

# 2. Restart services
sudo systemctl restart kb-rag.target

# 3. Verify health
curl http://localhost:8080/health/detailed
```

### Clear Cache

```bash
# Restart server (clears in-memory cache)
sudo systemctl restart kb-rag-server

# For Redis cache
redis-cli FLUSHDB
```

### Re-index Documents

```bash
cd /opt/kb-rag
source venv/bin/activate

# Clean and re-ingest
python -m ingest.ingest --docs /path/to/docs --clean
```

### Update to Latest Version

```bash
# Automated update (with backup)
sudo ./deployment/scripts/update.sh

# Manual update
cd /opt/kb-rag
sudo -u kb-rag git pull
sudo -u kb-rag venv/bin/pip install -r requirements.txt
sudo systemctl restart kb-rag.target
```

### Remote Deployment (acemagic/LXC)

Deploy on a remote Ubuntu 22.04+ server without Docker.

#### Prerequisites

```bash
# Install system dependencies
sudo apt update
sudo apt install -y git python3.11 python3.11-venv build-essential curl

# Verify Python version
python3.11 --version
```

#### Clone and Setup

```bash
# Clone repository
git clone https://github.com/MrLuciano/kb-rag-mcp.git /opt/kb-rag
cd /opt/kb-rag

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Configure

```bash
# Copy LXC config template
cp config/.env.lxc .env

# Edit environment variables
nano .env
```

Key variables to adjust for remote deployment:

| Variable | Description | Typical Value |
|----------|-------------|---------------|
| `QDRANT_HOST` | Qdrant server address | `localhost` or remote IP |
| `QDRANT_PORT` | Qdrant gRPC port | `6334` |
| `EMBED_BACKEND` | Embedding backend | `lmstudio-rest` |
| `LM_STUDIO_HOST` | LM Studio API host | `localhost` or remote IP |
| `LM_STUDIO_PORT` | LM Studio API port | `1234` |
| `SSE_HOST` | MCP SSE bind address | `0.0.0.0` (required for remote access) |
| `SSE_PORT` | MCP SSE port | `8765` |

#### Run with systemd

```bash
# Copy systemd service file
sudo cp scripts/kb-mcp.service /etc/systemd/system/

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable kb-mcp.service
sudo systemctl start kb-mcp.service

# Check status
sudo systemctl status kb-mcp.service
```

#### Health Check

```bash
# HTTP health endpoint
curl http://localhost:8080/health

# MCP server info
python scripts/health_check.py

# Check logs
sudo journalctl -u kb-mcp.service -n 50 -f
```

#### Verify Ingestion

```bash
source .venv/bin/activate

# Check ingest status
kb-ingest status

# Ingest documents
kb-ingest ingest --docs /path/to/docs
```

## Windows Firewall Management

### Overview

When running kb-rag-mcp on Windows (WSL2 + Docker), services are accessible from `localhost` by default. To enable access from other machines on your network (e.g., for remote monitoring, LAN-based MCP clients), Windows Firewall rules must be configured.

### Automatic Configuration

The `start-kb-rag.ps1` script includes built-in firewall configuration:

```powershell
# Requires Administrator privileges
.\scripts\start-kb-rag.ps1 -ConfigureFirewall
```

This creates inbound TCP rules for:
- **Qdrant:** 6333 (REST), 6334 (gRPC)
- **MCP SSE:** 8765
- **Health/Metrics:** 8080
- **Prometheus:** 9090
- **Grafana:** 3000

**Profiles enabled:** Domain, Private (not Public for security)

**Idempotency:** Safe to run multiple times — existing rules are skipped.

### Manual Configuration

If you prefer manual control or need custom profiles:

```powershell
# Create a single rule (example: MCP SSE)
New-NetFirewallRule `
    -DisplayName "KB-RAG-MCP-SSE" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8765 `
    -Action Allow `
    -Profile Domain,Private `
    -Description "Model Context Protocol (MCP) SSE endpoint" `
    -Group "KB-RAG-MCP" `
    -Enabled True

# List all KB-RAG rules
Get-NetFirewallRule -Group "KB-RAG-MCP" | Select-Object DisplayName, Enabled, Profile

# Disable a rule (without deleting)
Set-NetFirewallRule -DisplayName "KB-RAG-MCP-SSE" -Enabled False

# Remove all KB-RAG rules
Get-NetFirewallRule -Group "KB-RAG-MCP" | Remove-NetFirewallRule
```

### Enabling Public Profile (Internet-Facing)

**⚠️ Security Warning:** Only enable Public profile if you understand the security implications. Consider using VPN or SSH tunneling instead.

```powershell
# Enable Public profile for a specific rule
Set-NetFirewallRule -DisplayName "KB-RAG-MCP-SSE" -Profile Domain,Private,Public
```

### Troubleshooting

#### Problem: Cannot access services from LAN despite firewall rules

**Diagnostic Steps:**

1. **Verify firewall rule is active:**
   ```powershell
   Get-NetFirewallRule -DisplayName "KB-RAG-*" | Select-Object DisplayName, Enabled, Profile
   ```
   - Ensure `Enabled: True`
   - Ensure `Profile` includes `Private` or `Domain`

2. **Check Windows network profile:**
   ```powershell
   Get-NetConnectionProfile
   ```
   - If `NetworkCategory: Public`, firewall rules with `Domain,Private` profiles won't apply
   - Change to Private: `Set-NetConnectionProfile -Name "Network" -NetworkCategory Private`

3. **Verify WSL IP forwarding:**
   ```powershell
   netsh interface portproxy show v4tov4
   ```
   - Windows 11 22H2+ does automatic port forwarding from `0.0.0.0` to WSL IP
   - Older versions may require manual portproxy rules (not needed if using `0.0.0.0` bind in Docker)

4. **Confirm Docker port binding:**
   ```bash
   docker ps --format "table {{.Names}}\t{{.Ports}}"
   ```
   - Verify ports show `0.0.0.0:xxxx->xxxx/tcp` (not `127.0.0.1:xxxx`)

5. **Find Windows IP and test from remote machine:**
   ```powershell
   # On Windows host
   ipconfig | Select-String "IPv4"
   
   # From remote machine
   curl http://<WINDOWS_IP>:8080/health
   ```

#### Problem: Elevation prompt doesn't appear

**Cause:** Script run from non-elevated PowerShell, UAC settings may block prompt.

**Solution:**
1. Right-click PowerShell → "Run as Administrator"
2. Run script again: `.\scripts\start-kb-rag.ps1 -ConfigureFirewall`

#### Problem: Corporate firewall/VPN blocks access

**Solution:**
- Contact IT to whitelist ports 6333, 6334, 8765, 8080, 9090, 3000
- Alternative: Use SSH tunneling or WireGuard VPN to access services

### Group Policy Deployment (Enterprise)

For deploying to multiple Windows machines via GPO:

1. **Export rules after configuration:**
   ```powershell
   Get-NetFirewallRule -Group "KB-RAG-MCP" | Export-Csv -Path kb-rag-firewall-rules.csv
   ```

2. **Import via GPO:**
   - Computer Configuration → Policies → Windows Settings → Security Settings → Windows Defender Firewall with Advanced Security → Inbound Rules
   - Right-click → Import Policy → Select exported rules

3. **Deploy via GPO:**
   - Link GPO to target OU
   - Run `gpupdate /force` on target machines

### Security Best Practices

1. **Use Domain/Private profiles only** (default in script)
2. **Restrict source IPs if possible:**
   ```powershell
   Set-NetFirewallRule -DisplayName "KB-RAG-MCP-SSE" -RemoteAddress 192.168.1.0/24
   ```
3. **Audit firewall rules quarterly:**
   ```powershell
   Get-NetFirewallRule -Group "KB-RAG-MCP" | Format-Table DisplayName, Enabled, Profile, Action
   ```
4. **Disable rules when not needed:**
   ```powershell
   Get-NetFirewallRule -Group "KB-RAG-MCP" | Set-NetFirewallRule -Enabled False
   ```

### References

- [New-NetFirewallRule (Microsoft Docs)](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule)
- [WSL Networking (Microsoft Docs)](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [Windows Firewall with Advanced Security](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/)

### Check Service Resource Limits

```bash
# View current limits
systemctl show kb-rag-server -p MemoryMax -p CPUQuota

# Edit limits
sudo systemctl edit kb-rag-server
# Add:
# [Service]
# MemoryMax=4G
# CPUQuota=200%

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart kb-rag-server
```

---

## Emergency Procedures

### Service Won't Start

```bash
# 1. Check logs
sudo journalctl -u kb-rag-server -n 50

# 2. Check configuration
sudo cat /opt/kb-rag/config/kb-rag.env | grep -v "^#"

# 3. Verify external services
curl http://localhost:6333/healthz  # Qdrant
curl http://localhost:1234/v1/models  # LM Studio

# 4. Manual start for debugging
cd /opt/kb-rag
sudo -u kb-rag venv/bin/python -m kb_server.server
```

### Out of Disk Space

```bash
# 1. Check usage
df -h /opt/kb-rag
du -h /opt/kb-rag | sort -hr | head -20

# 2. Clean old logs
sudo journalctl --vacuum-time=7d
find /opt/kb-rag/logs -name "*.gz" -mtime +7 -delete

# 3. Clean old backups
find /backups -name "kb-rag-*.tar.gz" -mtime +30 -delete

# 4. Reduce cache size
sudo nano /opt/kb-rag/config/kb-rag.env
# Set: CACHE_MAX_SIZE_MB=256
sudo systemctl restart kb-rag-server
```

### Complete Service Restart

```bash
# Nuclear option - complete restart
sudo systemctl stop kb-rag.target
sleep 5
sudo systemctl start kb-rag.target
sudo systemctl status kb-rag.target
curl http://localhost:8080/health/detailed
```

### Rollback After Failed Update

```bash
# Restore from pre-update backup
sudo ./deployment/scripts/restore.sh /opt/kb-rag/data/backup-*.tar.gz

# Or manual rollback
cd /opt/kb-rag
sudo -u kb-rag git reset --hard <previous-commit>
sudo systemctl restart kb-rag.target
```

---

## Security Operations

### Review Access Logs

```bash
# Check who accessed the system (systemd logs)
sudo journalctl -u kb-rag-server | grep "connection"

# Check file access
sudo find /opt/kb-rag -type f -name "*.db" -exec ls -lh {} \;
```

### Verify Permissions

```bash
# All files should be owned by kb-rag user
ls -la /opt/kb-rag/

# Fix permissions if needed
sudo chown -R kb-rag:kb-rag /opt/kb-rag/
sudo chmod 755 /opt/kb-rag
sudo chmod 640 /opt/kb-rag/config/kb-rag.env
```

### Update Dependencies

```bash
# Check for security updates
cd /opt/kb-rag
sudo -u kb-rag venv/bin/pip list --outdated

# Update specific package
sudo -u kb-rag venv/bin/pip install --upgrade <package>

# Recompile requirements (for production)
sudo -u kb-rag venv/bin/pip-compile requirements.in
sudo -u kb-rag venv/bin/pip install -r requirements.txt
```

---

## Monitoring Checklist

### Daily
- [ ] Check service status
- [ ] Review error logs
- [ ] Verify health endpoints respond
- [ ] Check disk space >20%

### Weekly
- [ ] Create backup
- [ ] Review cache hit rate >80%
- [ ] Check resource usage <80%
- [ ] Review Prometheus alerts

### Monthly
- [ ] Update system
- [ ] Clean old backups
- [ ] Test restore procedure
- [ ] Run test suite
- [ ] Review security logs

---

## Docker Compose

See the following sections for Docker Compose-specific operations:

- **Accessing the dashboard** → [Health Dashboard → Docker Compose](#accessing-the-dashboard) (lines starting with "Docker Compose Deployments")
- **Customizing dashboards** → [Health Dashboard → Customizing](#customizing-the-dashboard) (`deployment/config/grafana-dashboard.json`)
- **Disabling monitoring** → [Health Dashboard → Disabling](#disabling-monitoring)
- **Prometheus retention** → [Health Dashboard → Storage Configuration](#storage-configuration)

For complete Docker Compose setup: [INSTRUCTIONS.md → Docker Compose](INSTRUCTIONS.md#docker-compose)

> **See also:** [TROUBLESHOOTING.md → Docker Compose](TROUBLESHOOTING.md#docker-compose), [INSTRUCTIONS.md → Docker Compose](INSTRUCTIONS.md#docker-compose)

---

## Helm

Helm (Kubernetes) deployments have dedicated operational guidance:

- **Dashboard access via port-forward** → [Health Dashboard → Kubernetes Deployments](#kubernetes-deployments)
- **Customizing via Helm values** → [Health Dashboard → Customizing](#customizing-the-dashboard) (Helm paths)
- **Monitoring toggle** → [Health Dashboard → Disabling](#disabling-monitoring) (Helm flags)
- **Storage configuration** → [Health Dashboard → Storage Configuration](#storage-configuration) (Helm values)

For complete Helm deployment: [KUBERNETES.md](../KUBERNETES.md)

> **See also:** [TROUBLESHOOTING.md → Helm](TROUBLESHOOTING.md#helm), [INSTRUCTIONS.md → Helm](INSTRUCTIONS.md#helm)

---

## Systemd

Systemd (bare metal) operations appear in the following sections:

- **Service management** → [Daily Operations → Service Management](#service-management) (`systemctl` commands)
- **Viewing logs** → [Viewing Logs](#viewing-logs) (`journalctl` commands)
- **Routine maintenance** → [Routine Maintenance](#routine-maintenance) (morning/weekly/monthly checks)
- **Emergency procedures** → [Emergency Procedures](#emergency-procedures)

Systemd unit files: `scripts/kb-mcp.service`, `scripts/kb-rag.target`

> **See also:** [TROUBLESHOOTING.md → Systemd](TROUBLESHOOTING.md#systemd), [INSTRUCTIONS.md → Systemd](INSTRUCTIONS.md#systemd)

---

## Manual

Manual (source-based) deployment operations:

- **Windows Firewall** → [Windows Firewall Management](#windows-firewall-management)
- **Direct `python -m` ingestion** → [Document Ingestion](#document-ingestion)
- **Embedding backend configuration** → [Embedding Backend (LM Studio)](#embedding-backend-lm-studio) (applies to all modes, but manual setup offers most flexibility)

For manual setup instructions: [INSTRUCTIONS.md → Manual](INSTRUCTIONS.md#manual)

> **See also:** [TROUBLESHOOTING.md → Manual](TROUBLESHOOTING.md#manual), [INSTRUCTIONS.md → Manual](INSTRUCTIONS.md#manual)

---

## Quick Command Reference

| Task | Command |
|------|---------|
| Start services | `sudo systemctl start kb-rag.target` |
| Stop services | `sudo systemctl stop kb-rag.target` |
| Check health | `curl localhost:8080/health` |
| View logs | `sudo journalctl -u kb-rag-server -f` |
| Create backup | `./deployment/scripts/backup.sh` |
| Restore backup | `sudo ./deployment/scripts/restore.sh <file>` |
| Update system | `sudo ./deployment/scripts/update.sh` |
| Check status | `python -m ingest.ingest --status` |
| Ingest docs | `python -m ingest.ingest --docs <path>` |
| Clear cache | `sudo systemctl restart kb-rag-server` |
| List connectors | `python -m ingest.cli.main connectors list` |
| Stage connector | `python -m ingest.cli.main connectors stage --type confluence` |
| Create API key | `python -m ingest.cli.main auth create --scope global` |
| List API keys | `python -m ingest.cli.main auth list` |
| Revoke API key | `python -m ingest.cli.main auth revoke <prefix>` |
| Show quotas | `python -m ingest.cli.main quota show` |
| Set quota | `python -m ingest.cli.main quota set --max-files 1000` |
| Reset quota | `python -m ingest.cli.main quota reset` |

---

## Support Resources

- **Detailed Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Complete Setup Guide:** [README.md](../README.md)
- **Deployment Details:** [archive/PHASE9_COMPLETION.md](archive/PHASE9_COMPLETION.md)
- **GitHub Issues:** https://github.com/MrLuciano/kb-rag-mcp/issues

---

*Quick reference for KB-RAG-MCP v0.1.1 operations*  
*Last updated: 2026-06-11*
