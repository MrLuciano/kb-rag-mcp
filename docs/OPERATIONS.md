# KB-RAG Operations Guide

Quick reference for daily operations, maintenance, and monitoring.

> **Note:** This is a quick reference. For detailed guides, see:
> - [README.md](../README.md) - Complete setup and usage
> - [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Problem solving
> - [logging-audit.md](logging-audit.md) — Logging coverage report

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
curl http://localhost:8000/health

# Detailed health status
curl http://localhost:8000/health/detailed | jq

# Check specific component
curl http://localhost:8000/health/detailed | jq '.components.embedding'

# Health check script
./deployment/scripts/health-check.sh all
```

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
curl http://localhost:8000/health/detailed | jq '.healthy'

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
curl http://localhost:8000/health/detailed | jq '.components.cache.details.hit_rate'

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
curl http://localhost:8000/health/detailed
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

## Performance Monitoring

### Key Metrics

```bash
# Cache hit rate (target: >80%)
curl http://localhost:8000/health/detailed | \
  jq '.components.cache.details.hit_rate'

# Component latency (target: <100ms)
curl http://localhost:8000/health/detailed | \
  jq '.components | to_entries[] | {name: .key, latency: .value.latency_ms}'

# Memory usage
systemctl show kb-rag-server -p MemoryCurrent

# CPU usage
systemd-cgtop -1 | grep kb-rag
```

### Prometheus Metrics

```bash
# Scrape metrics
curl http://localhost:8000/metrics

# Key metrics to monitor:
# - kb_rag_health_status
# - kb_rag_cache_hits_total / kb_rag_cache_misses_total
# - kb_rag_jobs_failed_total
# - kb_rag_filesystem_free_bytes
```

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

**Dashboard panels (18 total, 4 sections):**
- **Ingestion Overview:** jobs created, active jobs, files processed, chunks generated, job duration p50/p95/p99, files/s rate
- **Workers & Rate Limiter:** pool utilization gauge, pool size/queue, token bucket tokens/waits
- **Embedding API & Batch:** latency p50/p95, throughput chunks/s, embedding batches/s
- **Cache:** hit rate gauge, hits/misses/evictions, cache size bytes/entries

---

## Common Tasks

### Restart Services After Config Change

```bash
# 1. Edit configuration
sudo nano /opt/kb-rag/config/kb-rag.env

# 2. Restart services
sudo systemctl restart kb-rag.target

# 3. Verify health
curl http://localhost:8000/health/detailed
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
curl http://localhost:8000/health/detailed
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

## Quick Command Reference

| Task | Command |
|------|---------|
| Start services | `sudo systemctl start kb-rag.target` |
| Stop services | `sudo systemctl stop kb-rag.target` |
| Check health | `curl localhost:8000/health` |
| View logs | `sudo journalctl -u kb-rag-server -f` |
| Create backup | `./deployment/scripts/backup.sh` |
| Restore backup | `sudo ./deployment/scripts/restore.sh <file>` |
| Update system | `sudo ./deployment/scripts/update.sh` |
| Check status | `python -m ingest.ingest --status` |
| Ingest docs | `python -m ingest.ingest --docs <path>` |
| Clear cache | `sudo systemctl restart kb-rag-server` |

---

## Support Resources

- **Detailed Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Complete Setup Guide:** [README.md](../README.md)
- **Deployment Details:** [archive/FASE9_COMPLETION.md](archive/FASE9_COMPLETION.md)
- **GitHub Issues:** https://github.com/MrLuciano/kb-rag-mcp/issues

---

*Quick reference for KB-RAG-MCP v1.1 operations*  
*Last updated: 2026-05-23*
