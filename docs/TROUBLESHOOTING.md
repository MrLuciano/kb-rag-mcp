# KB-RAG Troubleshooting Guide

Comprehensive troubleshooting guide for KB-RAG-MCP installation,
deployment, and operation issues.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Service Issues](#service-issues)
3. [Health Check Failures](#health-check-failures)
4. [Performance Issues](#performance-issues)
5. [Ingestion Problems](#ingestion-problems)
6. [Search Issues](#search-issues)
7. [Memory and Resource Issues](#memory-and-resource-issues)
8. [Network and Connectivity](#network-and-connectivity)
9. [Database Issues](#database-issues)
10. [Logging and Debugging](#logging-and-debugging)

---

## Installation Issues

### Installation Script Fails

**Symptom:** `install.sh` exits with error.

**Common Causes:**

1. **Insufficient permissions:**
   ```bash
   # Error: Permission denied
   # Solution: Run with sudo
   sudo ./deployment/scripts/install.sh
   ```

2. **Python version too old:**
   ```bash
   # Check Python version
   python3 --version  # Must be 3.11+
   
   # Install Python 3.11+ on Debian/Ubuntu
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3.11-dev
   ```

3. **Missing system dependencies:**
   ```bash
   # Install required packages
   sudo apt update
   sudo apt install -y \
     python3-pip \
     python3-venv \
     sqlite3 \
     git \
     curl
   ```

4. **Disk space insufficient:**
   ```bash
   # Check available space (need 20GB+)
   df -h /opt
   
   # Clean up space if needed
   sudo apt clean
   sudo apt autoremove
   ```

### Virtual Environment Creation Fails

**Symptom:** `python3 -m venv .venv` fails.

**Solutions:**

```bash
# Ensure python3-venv is installed
sudo apt install python3.11-venv

# Remove corrupted venv and recreate
rm -rf .venv
python3 -m venv .venv

# Activate and verify
source .venv/bin/activate
python --version
```

### Dependency Installation Fails

**Symptom:** `pip install -r requirements.txt` fails.

**Solutions:**

```bash
# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install with verbose output
pip install -r requirements.txt -v

# If specific package fails, install separately
pip install <failing-package>

# Check for compilation dependencies (needed for some packages)
sudo apt install -y \
  build-essential \
  python3-dev \
  libffi-dev \
  libssl-dev
```

---

## Service Issues

### Services Won't Start

**Symptom:** `systemctl start kb-rag.target` fails.

**Diagnosis Steps:**

```bash
# 1. Check service status
sudo systemctl status kb-rag-server
sudo systemctl status kb-rag-health

# 2. View recent logs
sudo journalctl -u kb-rag-server -n 50
sudo journalctl -u kb-rag-health -n 50

# 3. Check configuration
sudo cat /opt/kb-rag/config/kb-rag.env | grep -v "^#"

# 4. Verify user exists
id kb-rag

# 5. Check file permissions
ls -la /opt/kb-rag/
```

**Common Issues:**

1. **Configuration file missing:**
   ```bash
   # Copy from template
   sudo cp /opt/kb-rag/config/kb-rag.env.template \
           /opt/kb-rag/config/kb-rag.env
   
   # Edit configuration
   sudo nano /opt/kb-rag/config/kb-rag.env
   
   # Restart services
   sudo systemctl restart kb-rag.target
   ```

2. **Port already in use:**
   ```bash
   # Check if port 8000 is in use
   sudo lsof -i :8000
   
   # Kill conflicting process or change port
   sudo nano /opt/kb-rag/config/kb-rag.env
   # Set: HEALTH_PORT=8001
   
   sudo systemctl restart kb-rag-health
   ```

3. **Virtual environment corrupted:**
   ```bash
   # Recreate venv
   cd /opt/kb-rag
   sudo -u kb-rag rm -rf venv
   sudo -u kb-rag python3 -m venv venv
   sudo -u kb-rag venv/bin/pip install -r requirements.txt
   
   sudo systemctl restart kb-rag.target
   ```

### Service Keeps Restarting

**Symptom:** Service enters restart loop.

**Diagnosis:**

```bash
# Check restart count
systemctl show kb-rag-server -p NRestarts

# View crash logs
sudo journalctl -u kb-rag-server --since "10 minutes ago"

# Check for common errors:
# - Configuration errors
# - Missing dependencies
# - Permission issues
# - External service unavailable (Qdrant, embedding API)
```

**Solutions:**

```bash
# Stop auto-restart temporarily for debugging
sudo systemctl stop kb-rag.target

# Run manually to see full error
cd /opt/kb-rag
sudo -u kb-rag venv/bin/python -m kb_server.server

# Or use the health check CLI (if server is running)
kb-rag check health

# Fix issue, then restart services
sudo systemctl start kb-rag.target
```

### Service Won't Stop

**Symptom:** `systemctl stop` hangs or times out.

**Solutions:**

```bash
# Force kill after timeout
sudo systemctl kill kb-rag-server

# If still running, manual kill
ps aux | grep kb-rag
sudo kill -9 <PID>

# Check for zombie processes
ps aux | grep -E "defunct|<defunct>"

# Restart systemd if needed (last resort)
sudo systemctl daemon-reexec
```

---

## Health Check Failures

### Health Endpoint Not Responding

**Symptom:** `curl http://localhost:8000/health` fails.

**Diagnosis:**

```bash
# 1. Run health check CLI (comprehensive)
kb-rag check health

# 2. Check if health service is running
sudo systemctl status kb-rag-health

# 3. Check if port is listening
sudo netstat -tlnp | grep 8000

# 4. Check firewall
sudo ufw status
sudo iptables -L -n | grep 8000

# 5. Test with full curl output
curl -v http://localhost:8000/health
```

**Solutions:**

```bash
# Restart health service
sudo systemctl restart kb-rag-health

# Check health service logs
sudo journalctl -u kb-rag-health -f

# Verify health server is configured correctly
grep HEALTH_PORT /opt/kb-rag/config/kb-rag.env
```

### Component Health Check Failures

#### Embedding Service Unhealthy

**Symptom:** `/health/detailed` shows embedding as unhealthy.

**Solutions:**

```bash
# Check if LM Studio is running
curl http://localhost:1234/v1/models

# Or for Ollama
curl http://localhost:11434/api/tags

# Verify embedding URL in config
grep EMBED_URL /opt/kb-rag/config/kb-rag.env

# Test embedding manually
curl -X POST http://localhost:1234/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-nomic-embed-text-v1.5",
    "input": "test"
  }'

# Restart embedding service
# (LM Studio: restart application)
# (Ollama: sudo systemctl restart ollama)
```

#### Vector Store Unhealthy

**Symptom:** Qdrant connection fails.

**Solutions:**

```bash
# Check if Qdrant is running
docker ps | grep qdrant
curl http://localhost:6333/healthz

# If not running, start Qdrant
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Check Qdrant logs
docker logs qdrant

# Verify Qdrant URL in config
grep QDRANT_URL /opt/kb-rag/config/kb-rag.env

# Test connection manually
curl http://localhost:6333/collections
```

#### Database Unhealthy

**Symptom:** SQLite database issues.

**Solutions:**

```bash
# Check database files exist
ls -lh /opt/kb-rag/data/*.db

# Check file permissions
sudo chown kb-rag:kb-rag /opt/kb-rag/data/*.db
sudo chmod 644 /opt/kb-rag/data/*.db

# Verify database integrity
sqlite3 /opt/kb-rag/data/jobs.db "PRAGMA integrity_check;"
sqlite3 /opt/kb-rag/data/kb_metadata.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
sudo /opt/kb-rag/deployment/scripts/restore.sh \
  /path/to/backup.tar.gz
```

#### Cache Unhealthy

**Symptom:** Cache backend unavailable.

**Solutions:**

```bash
# For LRU cache (in-memory), restart fixes it
sudo systemctl restart kb-rag-server

# For Redis cache
sudo systemctl status redis
sudo systemctl restart redis

# Test Redis connection
redis-cli ping  # Should return PONG

# Check Redis logs
sudo journalctl -u redis -n 50

# Fall back to LRU if Redis unavailable
sudo nano /opt/kb-rag/config/kb-rag.env
# Set: CACHE_BACKEND=lru
sudo systemctl restart kb-rag-server
```

#### Filesystem Issues

**Symptom:** Disk space warnings or errors.

**Solutions:**

```bash
# Check disk space
df -h /opt/kb-rag

# Find large files
sudo du -h /opt/kb-rag | sort -hr | head -20

# Clean old logs
sudo journalctl --vacuum-time=7d
sudo find /opt/kb-rag/logs -name "*.gz" -mtime +14 -delete

# Clean old backups
sudo find /backups -name "kb-rag-*.tar.gz" -mtime +30 -delete

# Increase disk space (last resort)
# Add new disk or extend existing partition
```

---

## Performance Issues

### Slow Search Queries

**Symptom:** Search queries take >2 seconds.

**Diagnosis:**

```bash
# Check component latencies
curl http://localhost:8000/health/detailed | \
  jq '.components | to_entries[] | 
      {name: .key, latency: .value.latency_ms}'

# Check Qdrant collection size
curl http://localhost:6333/collections/kb_docs | \
  jq '.result.points_count'

# Check cache hit rate (should be >80%)
curl http://localhost:8000/health/detailed | \
  jq '.components.cache.details.hit_rate'
```

**Solutions:**

1. **Increase cache size:**
   ```bash
   sudo nano /opt/kb-rag/config/kb-rag.env
   # Set: CACHE_MAX_SIZE_MB=1024
   sudo systemctl restart kb-rag-server
   ```

2. **Optimize Qdrant (if >1M chunks):**
   ```bash
   # Enable HNSW index optimization
   curl -X PATCH http://localhost:6333/collections/kb_docs \
     -H "Content-Type: application/json" \
     -d '{
       "optimizer_config": {
         "indexing_threshold": 10000
       }
     }'
   ```

3. **Check embedding API latency:**
   ```bash
   # If >100ms, consider GPU acceleration
   # LM Studio: Enable GPU in settings
   # Ollama: Use GPU-enabled model
   ```

### Slow Ingestion

**Symptom:** File ingestion takes too long.

**Diagnosis:**

```bash
# Check ingestion status
python3 -m ingest.ingest --status

# Monitor resource usage during ingestion
systemd-cgtop | grep kb-rag

# Check worker pool utilization in logs
sudo journalctl -u kb-rag-server | grep "worker_pool"
```

**Solutions:**

1. **Tune batch sizes:**
   ```bash
   sudo nano /opt/kb-rag/config/kb-rag.env
   # For faster ingestion (if RAM available):
   # EMBED_BATCH_SIZE=64
   # FILE_BATCH_SIZE=100
   # QDRANT_BATCH_SIZE=200
   
   sudo systemctl restart kb-rag-server
   ```

2. **Increase workers (if multi-core CPU):**
   ```bash
   sudo nano /opt/kb-rag/config/kb-rag.env
   # Set: WORKER_POOL_SIZE=8
   sudo systemctl restart kb-rag-server
   ```

3. **Check embedding API is not overloaded:**
   ```bash
   # Monitor LM Studio/Ollama logs
   # Reduce worker_rate_limit if needed
   sudo nano /opt/kb-rag/config/kb-rag.env
   # Set: WORKER_RATE_LIMIT=5
   ```

### High CPU Usage

**Symptom:** CPU usage constantly >80%.

**Solutions:**

```bash
# Check which process is consuming CPU
top -u kb-rag

# Reduce worker pool size
sudo nano /opt/kb-rag/config/kb-rag.env
# Set: WORKER_POOL_SIZE=2
sudo systemctl restart kb-rag-server

# Limit CPU usage via systemd
sudo systemctl edit kb-rag-server
# Add:
# [Service]
# CPUQuota=150%

sudo systemctl daemon-reload
sudo systemctl restart kb-rag-server
```

---

## Ingestion Problems

### Files Not Being Ingested

**Symptom:** Files present but not indexed.

**Diagnosis:**

```bash
# Check ingestion status
python3 -m ingest.ingest --status --list

# Check for errors
python3 -m ingest.ingest --status --errors

# Check file permissions
ls -la /path/to/docs

# Check supported formats
# Supported: pdf, docx, xlsx, pptx, txt, py, js, java, etc.
```

**Solutions:**

```bash
# Force re-ingestion
python3 -m ingest.ingest --docs /path/to/docs --clean

# Check logs for specific errors
sudo journalctl -u kb-rag-server | grep ERROR

# Verify file is readable
file /path/to/document.pdf
```

### Ingestion Errors

**Symptom:** Files show status ERROR in registry.

**Common Errors:**

1. **PDF parsing errors:**
   ```bash
   # Try alternative PDF library
   pip install pdfplumber
   
   # Or convert to text first
   pdftotext document.pdf document.txt
   ```

2. **Encoding errors:**
   ```bash
   # Check file encoding
   file -i document.txt
   
   # Convert to UTF-8
   iconv -f ISO-8859-1 -t UTF-8 document.txt > document_utf8.txt
   ```

3. **Large file timeout:**
   ```bash
   # Increase timeout in config
   sudo nano /opt/kb-rag/config/kb-rag.env
   # Set: FILE_PROCESSING_TIMEOUT=600
   ```

### Duplicate Documents

**Symptom:** Same document appears multiple times.

**Solutions:**

```bash
# Clean and re-ingest
python3 -m ingest.ingest --docs /path/to/docs --clean

# Or manually remove duplicates from Qdrant
curl -X POST http://localhost:6333/collections/kb_docs/points/delete \
  -H "Content-Type: application/json" \
  -d '{"filter": {"must": [{"key": "file_path", 
       "match": {"value": "/path/to/duplicate.pdf"}}]}}'
```

---

## Search Issues

### No Search Results

**Symptom:** Searches return empty results.

**Diagnosis:**

```bash
# 0. Run health check CLI to verify overall system status
kb-rag check health

# 1. Check documents are indexed
curl http://localhost:6333/collections/kb_docs | \
  jq '.result.points_count'

# 2. Check score threshold (may be too strict)
grep SCORE_THRESHOLD /opt/kb-rag/config/kb-rag.env

# 3. Test with simple query
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 10}'
```

**Solutions:**

```bash
# Lower score threshold
sudo nano /opt/kb-rag/config/kb-rag.env
# Set: SCORE_THRESHOLD=0.3  # Default: 0.5
sudo systemctl restart kb-rag-server

# Check query language matches document language
# English embeddings won't match Portuguese documents well
```

### Poor Search Quality

**Symptom:** Irrelevant results or missing relevant documents.

**Solutions:**

1. **Verify embedding model is loaded:**
   ```bash
   curl http://localhost:1234/v1/models
   # Should show your embedding model
   ```

2. **Check chunk size (may be too large or small):**
   ```bash
   # Optimal: 500-1000 tokens
   grep CHUNK_SIZE /opt/kb-rag/config/kb-rag.env
   ```

3. **Increase top_k to see more results:**
   ```bash
   # In search query, set top_k=20
   ```

4. **Re-index with better chunking:**
   ```bash
   # Adjust chunk size and re-ingest
   sudo nano /opt/kb-rag/config/kb-rag.env
   # Set: CHUNK_SIZE=800
   # Set: CHUNK_OVERLAP=200
   
   python3 -m ingest.ingest --docs /path/to/docs --clean
   ```

---

## Memory and Resource Issues

### Out of Memory (OOM) Errors

**Symptom:** Service killed with OOM error.

**Diagnosis:**

```bash
# Check memory limits
systemctl show kb-rag-server -p MemoryMax -p MemoryCurrent

# Check system memory
free -h

# Check OOM killer logs
sudo journalctl -k | grep -i "killed process"
```

**Solutions:**

1. **Reduce cache size:**
   ```bash
   sudo nano /opt/kb-rag/config/kb-rag.env
   # Set: CACHE_MAX_SIZE_MB=256
   sudo systemctl restart kb-rag-server
   ```

2. **Reduce batch sizes:**
   ```bash
   sudo nano /opt/kb-rag/config/kb-rag.env
   # EMBED_BATCH_SIZE=16
   # FILE_BATCH_SIZE=25
   sudo systemctl restart kb-rag-server
   ```

3. **Increase systemd memory limit:**
   ```bash
   sudo systemctl edit kb-rag-server
   # Add:
   # [Service]
   # MemoryMax=4G
   
   sudo systemctl daemon-reload
   sudo systemctl restart kb-rag-server
   ```

4. **Add swap space (temporary fix):**
   ```bash
   # Create 4GB swap file
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### Memory Leak Suspected

**Symptom:** Memory usage grows continuously.

**Diagnosis:**

```bash
# Monitor memory over time
watch -n 5 'systemctl show kb-rag-server -p MemoryCurrent'

# Check for growing cache
curl http://localhost:8000/health/detailed | \
  jq '.components.cache.details.size_bytes'
```

**Solutions:**

```bash
# Restart service daily (temporary)
sudo systemctl edit kb-rag-server
# Add:
# [Service]
# RuntimeMaxSec=86400

# Enable periodic restart
echo '0 3 * * * systemctl restart kb-rag-server' | \
  sudo crontab -u root -

# Report issue with memory profile
pip install memory_profiler
python -m memory_profiler kb_server/server.py
```

---

## Network and Connectivity

### Cannot Connect to External Services

**Symptom:** Cannot reach Qdrant, LM Studio, or other services.

**Diagnosis:**

```bash
# Test network connectivity
ping localhost
ping 127.0.0.1

# Check service ports
sudo netstat -tlnp | grep -E "1234|6333|11434"

# Check firewall rules
sudo ufw status verbose
sudo iptables -L -n

# Test with telnet
telnet localhost 6333
```

**Solutions:**

```bash
# Allow ports in firewall
sudo ufw allow 6333/tcp  # Qdrant
sudo ufw allow 1234/tcp  # LM Studio

# Check service binds to correct interface
# Qdrant should bind to 0.0.0.0 or 127.0.0.1

# Verify URLs in config
grep -E "QDRANT_URL|EMBED_URL" /opt/kb-rag/config/kb-rag.env
```

### Timeout Errors

**Symptom:** Connection timeouts to external services.

**Solutions:**

```bash
# Increase timeouts
sudo nano /opt/kb-rag/config/kb-rag.env
# Set: REQUEST_TIMEOUT=60
# Set: EMBED_TIMEOUT=30

sudo systemctl restart kb-rag-server
```

---

## Database Issues

### Database Locked

**Symptom:** SQLite database locked errors.

**Solutions:**

```bash
# Check for lingering connections
sudo lsof /opt/kb-rag/data/jobs.db

# Stop services and clear lock
sudo systemctl stop kb-rag.target
rm -f /opt/kb-rag/data/*.db-journal
sudo systemctl start kb-rag.target

# Enable WAL mode for better concurrency
sqlite3 /opt/kb-rag/data/jobs.db "PRAGMA journal_mode=WAL;"
sqlite3 /opt/kb-rag/data/kb_metadata.db "PRAGMA journal_mode=WAL;"
```

### Database Corruption

**Symptom:** Database integrity check fails.

**Solutions:**

```bash
# Backup corrupted database
sudo cp /opt/kb-rag/data/jobs.db \
        /opt/kb-rag/data/jobs.db.corrupted

# Try to recover
sqlite3 /opt/kb-rag/data/jobs.db ".recover" | \
  sqlite3 /opt/kb-rag/data/jobs.db.recovered

# If recovery succeeds, replace
sudo mv /opt/kb-rag/data/jobs.db.recovered \
        /opt/kb-rag/data/jobs.db

# If recovery fails, restore from backup
sudo /opt/kb-rag/deployment/scripts/restore.sh \
  /path/to/latest-backup.tar.gz
```

---

## Logging and Debugging

### Enable Debug Logging

```bash
# Enable debug level
sudo nano /opt/kb-rag/config/kb-rag.env
# Set: LOG_LEVEL=DEBUG

sudo systemctl restart kb-rag.target

# View debug logs
sudo journalctl -u kb-rag-server -f
```

### Structured Log Queries

```bash
# View as JSON
sudo journalctl -u kb-rag-server -o json-pretty

# Filter by severity
sudo journalctl -u kb-rag-server -p err  # Errors only
sudo journalctl -u kb-rag-server -p warning  # Warnings+

# Search by component
sudo journalctl -u kb-rag-server | grep '"component":"cache"'

# Extract error messages
sudo journalctl -u kb-rag-server -o json | \
  jq -r 'select(.PRIORITY=="3") | .MESSAGE'
```

### Running Audit Scripts

```bash
# English audit (checks for Portuguese in source files)
python scripts/docstring-audit.py --check-inline

# Logging coverage audit
python scripts/logging-audit.py

# Coverage report
pytest --cov=kb_server --cov=ingest --cov-branch --cov-report=term-missing
```

### Save Logs for Support

```bash
# Export recent logs
sudo journalctl -u kb-rag-server --since "1 hour ago" > \
  kb-rag-debug.log

# Include health status
curl http://localhost:8000/health/detailed > \
  kb-rag-health.json

# Include configuration (remove secrets first)
sudo cat /opt/kb-rag/config/kb-rag.env | \
  grep -v -E "PASSWORD|SECRET|TOKEN" > \
  kb-rag-config.txt

# Create support bundle
tar czf kb-rag-support-$(date +%Y%m%d-%H%M%S).tar.gz \
  kb-rag-debug.log \
  kb-rag-health.json \
  kb-rag-config.txt
```

---

## Getting Help

### Before Reporting Issues

1. ✅ Check this troubleshooting guide
2. ✅ Search existing GitHub issues
3. ✅ Gather diagnostic information:
   - Service status: `systemctl status kb-rag.target`
   - Recent logs: `journalctl -u kb-rag-server -n 100`
   - Health status: `kb-rag check health` or `curl localhost:8000/health/detailed`
   - System info: `uname -a`, `free -h`, `df -h`

### Reporting Issues

**Include in issue report:**

- KB-RAG version: `git describe --tags`
- OS and version: `cat /etc/os-release`
- Python version: `python3 --version`
- Error logs (sanitized)
- Steps to reproduce
- Expected vs actual behavior

**GitHub Issues:** https://github.com/MrLuciano/kb-rag-mcp/issues

---

## Quick Reference

### Most Common Issues

| Issue | Quick Fix |
|-------|-----------|
| Service won't start | `sudo journalctl -u kb-rag-server -n 50` |
| Health check fails | `sudo systemctl restart kb-rag-health` |
| No search results | Lower `SCORE_THRESHOLD` in config |
| Slow performance | Check cache hit rate, increase cache size |
| Out of memory | Reduce `CACHE_MAX_SIZE_MB`, batch sizes |
| Files not ingesting | Check file permissions, run with `--clean` |
| High CPU usage | Reduce `WORKER_POOL_SIZE` |

### Emergency Recovery

```bash
# Complete service restart
sudo systemctl stop kb-rag.target
sleep 5
sudo systemctl start kb-rag.target

# If restart doesn't work, restore from backup
sudo /opt/kb-rag/deployment/scripts/restore.sh \
  /path/to/backup.tar.gz

# Nuclear option: reinstall
sudo /opt/kb-rag/deployment/scripts/uninstall.sh
sudo ./deployment/scripts/install.sh
```

---

*Last updated: v1.3 - 2026-05-25*
