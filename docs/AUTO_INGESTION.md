# Automatic Ingestion with File Watcher

Automatically detect file changes and trigger ingestion without manual intervention.

---

## Overview

The KB-RAG file watcher monitors your documentation directory for changes and automatically triggers ingestion jobs when files are created or modified. This eliminates the need to manually run `kb-rag ingest` after updating documentation.

### Key Features

- **Real-time monitoring**: Detects file create/modify events within 30 seconds
- **Smart batching**: Debounces multiple changes to avoid duplicate jobs
- **Selective watching**: Ignores temp files and unsupported formats
- **Automatic job creation**: Integrates with existing job system
- **systemd service**: Runs as a background service with auto-restart

---

## Connector-Based Ingestion (Phase 29)

In addition to the file watcher, the system supports ingestion from remote enterprise sources via the connector framework.

### Supported Sources

| Connector | Type | Auth Methods | Env Vars Required |
|-----------|------|-------------|-------------------|
| Confluence | Documentation | Basic (Server/DC) or Bearer (Cloud) | CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_TOKEN |
| JIRA | Issue Tracking | Basic (Server/DC) or Bearer (Cloud) | JIRA_URL, JIRA_USERNAME, JIRA_TOKEN |
| Git | Code/Config | HTTPS token or SSH key | GIT_REPO_URL, GIT_REPO_PATH |

### How It Works

Connectors follow a three-phase lifecycle:
1. **Stage** — Configure the source via `kb-rag connectors stage --type <type> --source-key <name>`
2. **Sync** — The connector fetches documents (full or incremental) and writes them to a staging directory
3. **Ingest** — Staged documents are processed through the normal ingest pipeline (chunk → embed → upsert)

### Connector vs File Watcher

| Feature | File Watcher | Connector |
|---------|-------------|-----------|
| Source | Local filesystem | Remote API (Confluence, JIRA, Git) |
| Trigger | File change event | Manual or scheduled sync |
| Sync type | Real-time (event-driven) | Pull-based (full/incremental) |
| Auth | Filesystem permissions | API tokens / SSH keys |
| Content | Any supported format | HTML (Confluence), ADF JSON (JIRA), files (Git) |

### Listing Available Connectors

```bash
python -m ingest.cli.main connectors list
```

Expected output:
```
Supported connector types:
  confluence
  jira
  git
```

### Staging a Connector

```bash
python -m ingest.cli.main connectors stage \
  --type confluence \
  --source-key "engineering-wiki" \
  --endpoint "https://confluence.example.com/rest/api"
```

This creates a staging area and fetches available documents. Staged documents are ready for standard ingestion.

---

## Quick Start

### 1. Configure Watch Path

Add to your `.env` or environment:

```bash
# Directory to monitor (defaults to DOCS_PATH)
WATCH_PATH=/path/to/docs

# Debounce window in seconds (default: 30)
WATCH_DEBOUNCE_SECONDS=30

# Monitor subdirectories recursively (default: true)
WATCH_RECURSIVE=true

# Additional patterns to ignore (comma-separated)
WATCH_IGNORE_PATTERNS=.tmp,.swp,.~,~$*
```

### 2. Start the Watcher

**As a systemd service (recommended for production):**

```bash
# Start the watcher
sudo systemctl start kb-rag-watcher

# Enable auto-start on boot
sudo systemctl enable kb-rag-watcher

# Check status
sudo systemctl status kb-rag-watcher

# View logs
sudo journalctl -u kb-rag-watcher -f
```

**As a standalone process (development):**

```bash
# From project root
python -m ingest.watcher.file_watcher

# Or with custom config
WATCH_PATH=/custom/path python -m ingest.watcher.file_watcher
```

### 3. Test It

Add or modify a document in your watched directory:

```bash
# Copy a new file
cp manual.pdf /path/to/docs/

# Wait ~30 seconds
# Check job queue
kb-rag job list

# You should see a new job created automatically
```

---

## How It Works

### Event Detection

The watcher uses the `watchdog` library to monitor filesystem events:

1. **File Created**: New file detected → schedule ingestion
2. **File Modified**: Existing file changed → schedule re-ingestion
3. **File Deleted**: Logged (deletion from Qdrant not yet implemented)

### Debouncing

Multiple changes within the debounce window (default: 30s) are batched into a single job:

```
t=0s:   file.pdf created
t=5s:   file.pdf modified
t=10s:  file.pdf modified
t=30s:  → Single ingestion job created for file.pdf
```

This prevents:
- Duplicate ingestion during file copying
- Job queue overload during bulk file operations
- Unnecessary processing of intermediate states

### Ignore Patterns

Files matching these patterns are automatically ignored:

**Default patterns:**
- `.tmp` - Temporary files
- `.swp` - Vim swap files
- `.~` - Office temp files
- `~$*` - Office lock files
- `.git` - Git repository files
- `__pycache__` - Python cache

**Unsupported extensions:**
Any file not in: `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.md`

**Custom patterns:**
Add your own via `WATCH_IGNORE_PATTERNS`:

```bash
WATCH_IGNORE_PATTERNS=.tmp,.swp,backup_*,draft_*
```

### Job Creation

When a change is detected, the watcher creates an ingestion job with:

```python
{
    "docs_path": "/path/to/docs",  # Root directory
    "priority": "normal",           # Standard priority
    "force": True,                  # Force re-ingestion
    "workers": 1,                   # Single worker
    "clean": False,                 # Keep existing docs
    "sync": False                   # Async execution
}
```

Jobs are queued and processed by the worker pool according to priority.

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCH_PATH` | `$DOCS_PATH` | Directory to monitor |
| `WATCH_DEBOUNCE_SECONDS` | `30` | Batch changes within N seconds |
| `WATCH_RECURSIVE` | `true` | Monitor subdirectories |
| `WATCH_IGNORE_PATTERNS` | `.tmp,.swp,.~,~$*` | Patterns to ignore |

### systemd Service Options

**File:** `/etc/systemd/system/kb-rag-watcher.service`

```ini
[Service]
# Restart policy
Restart=always
RestartSec=10

# Resource limits
MemoryMax=512M
CPUQuota=50%

# Dependencies
After=kb-rag-server.service
Requires=kb-rag-server.service
```

**Modify and reload:**

```bash
# Edit service file
sudo systemctl edit kb-rag-watcher

# Reload systemd
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart kb-rag-watcher
```

---

## Usage Scenarios

### Scenario 1: Documentation Updates

**Use case**: Regular updates to product documentation

**Setup:**
```bash
WATCH_PATH=/mnt/docs/products
WATCH_DEBOUNCE_SECONDS=30
WATCH_RECURSIVE=true
```

**Workflow:**
1. Documentation team updates files in `/mnt/docs/products`
2. Watcher detects changes within 30 seconds
3. Ingestion job queued automatically
4. Workers process files in background
5. Updated content available for search

**Benefits:**
- Zero manual intervention
- Always up-to-date knowledge base
- Team can focus on content, not tooling

### Scenario 2: Batch Document Import

**Use case**: Importing multiple documents at once

**Setup:**
```bash
WATCH_DEBOUNCE_SECONDS=60  # Longer window for batch
```

**Workflow:**
```bash
# Copy 50 files
cp -r /source/*.pdf /path/to/docs/

# Watcher detects all 50 files
# Batches changes over 60s window
# Creates single job for entire batch
```

**Benefits:**
- Efficient batch processing
- Single job instead of 50 separate jobs
- No queue overload

### Scenario 3: Network Share Monitoring

**Use case**: Monitor documents on network share

**Setup:**
```bash
WATCH_PATH=/mnt/network-docs
WATCH_DEBOUNCE_SECONDS=120  # Longer for network latency
WATCH_IGNORE_PATTERNS=.tmp,.swp,~$*,.DS_Store
```

**Considerations:**
- Network latency may require longer debounce
- Temporary files from Office apps must be ignored
- Monitor network connectivity for service health

---

## Troubleshooting

### Watcher Not Starting

**Symptom:** Service fails to start

**Check:**
```bash
# View detailed error
sudo journalctl -u kb-rag-watcher -n 50

# Common issues:
# 1. WATCH_PATH doesn't exist
ls -la $WATCH_PATH

# 2. Permission denied
sudo chown -R kb-rag:kb-rag /path/to/docs
sudo chmod -R 755 /path/to/docs

# 3. Missing watchdog library
pip install watchdog>=3.0.0
```

### Changes Not Detected

**Symptom:** Files created but no jobs triggered

**Check:**
```bash
# 1. Verify watcher is running
sudo systemctl status kb-rag-watcher

# 2. Check if file extension is supported
# Only: .pdf, .docx, .xlsx, .pptx, .txt, .md

# 3. Check ignore patterns
# View current patterns in logs
sudo journalctl -u kb-rag-watcher | grep "DocWatcher initialized"

# 4. Test with a known file
cp test.pdf /path/to/docs/
# Wait 35 seconds
kb-rag job list
```

### Too Many Jobs Created

**Symptom:** Job queue fills up with duplicate jobs

**Cause:** Debounce window too short

**Fix:**
```bash
# Increase debounce window
# Edit /opt/kb-rag/kb-rag.env
WATCH_DEBOUNCE_SECONDS=60

# Restart service
sudo systemctl restart kb-rag-watcher
```

### Temp Files Being Watched

**Symptom:** Ingestion errors on `.tmp` or `~$` files

**Fix:**
```bash
# Add patterns to ignore list
WATCH_IGNORE_PATTERNS=.tmp,.swp,.~,~$*,~lock*

# Restart watcher
sudo systemctl restart kb-rag-watcher
```

### High Memory Usage

**Symptom:** Watcher using >512MB RAM

**Cause:** Watching too many files or large directory tree

**Fix:**
```bash
# 1. Reduce watch scope
WATCH_RECURSIVE=false

# 2. Watch specific subdirectories
WATCH_PATH=/path/to/docs/specific-product

# 3. Increase resource limit
sudo systemctl edit kb-rag-watcher
# Add:
[Service]
MemoryMax=1G

sudo systemctl daemon-reload
sudo systemctl restart kb-rag-watcher
```

### Service Crashes Frequently

**Symptom:** Watcher restarts every few minutes

**Check:**
```bash
# View crash logs
sudo journalctl -u kb-rag-watcher --since "1 hour ago"

# Common causes:
# 1. Disk full
df -h

# 2. Too many open files
ulimit -n  # Should be >1024

# 3. Database locked
# Check job database isn't corrupted
sqlite3 kb_metadata.db "PRAGMA integrity_check;"
```

---

## Performance Characteristics

### Resource Usage

**Memory:**
- Baseline: ~50MB
- Per 1,000 watched files: +1MB
- Debouncer overhead: negligible

**CPU:**
- Idle: <1%
- During events: 5-10%
- Job creation: <1%

**Disk I/O:**
- Minimal (event-driven, not polling)
- No filesystem scanning after initial startup

### Latency

**Event Detection:**
- Local filesystem: <1 second
- Network share: 1-5 seconds (depends on network)

**Debounce Window:**
- Configurable: 10-300 seconds
- Default: 30 seconds
- Trade-off: lower = faster updates, higher = better batching

**Job Creation:**
- Overhead: <50ms per job
- Database write: <10ms

---

## Best Practices

### 1. Choose Appropriate Debounce Window

```bash
# Frequent small updates (wiki-style)
WATCH_DEBOUNCE_SECONDS=15

# Normal documentation updates
WATCH_DEBOUNCE_SECONDS=30

# Batch imports or network shares
WATCH_DEBOUNCE_SECONDS=120
```

### 2. Monitor Service Health

```bash
# Add to monitoring system
systemctl is-active kb-rag-watcher || alert

# Check logs daily
sudo journalctl -u kb-rag-watcher --since yesterday | grep ERROR
```

### 3. Exclude Unnecessary Directories

```bash
# Don't watch:
# - Source repositories (.git)
# - Build outputs (dist/, build/)
# - Archive directories

# Use specific paths:
WATCH_PATH=/docs/current-products
# Not:
WATCH_PATH=/docs  # Includes archives, temp, etc.
```

### 4. Test Before Production

```bash
# 1. Start watcher in foreground
python -m ingest.watcher.file_watcher

# 2. Add test file
cp test.pdf /path/to/docs/

# 3. Verify job created
kb-rag job list

# 4. Check job completes
kb-rag job show <job-id>

# 5. Enable systemd service
sudo systemctl enable kb-rag-watcher
```

### 5. Combine with Manual Ingestion

The watcher complements, but doesn't replace, manual ingestion:

**Use watcher for:**
- Ongoing updates
- Real-time sync
- Team collaboration

**Use manual ingestion for:**
- Initial bulk import
- Forced re-processing
- Troubleshooting specific files

```bash
# Force re-ingest everything
kb-rag ingest /path/to/docs --force

# Then enable watcher for updates
sudo systemctl start kb-rag-watcher
```

---

## Advanced Configuration

### Multiple Watch Paths

To watch multiple directories, create multiple service instances:

```bash
# Copy service file
sudo cp /etc/systemd/system/kb-rag-watcher.service \
       /etc/systemd/system/kb-rag-watcher-archive.service

# Edit new service
sudo systemctl edit kb-rag-watcher-archive.service
# Change:
Environment="WATCH_PATH=/archive/docs"

# Start both
sudo systemctl start kb-rag-watcher
sudo systemctl start kb-rag-watcher-archive
```

### Conditional Watching

Watch only during business hours using systemd timers:

```bash
# Create timer unit
sudo nano /etc/systemd/system/kb-rag-watcher.timer

[Unit]
Description=KB-RAG Watcher Schedule

[Timer]
OnCalendar=Mon-Fri 08:00-18:00
Persistent=false

[Install]
WantedBy=timers.target

# Enable timer instead of service
sudo systemctl enable kb-rag-watcher.timer
```

### Custom Event Handlers

For advanced use cases, extend `DocWatcher`:

```python
# custom_watcher.py
from ingest.watcher.file_watcher import DocWatcher

class CustomWatcher(DocWatcher):
    def on_created(self, event):
        # Custom logic before job creation
        if self.validate_file(event.src_path):
            super().on_created(event)
    
    def validate_file(self, path: str) -> bool:
        # Add custom validation
        return path.endswith(('.pdf', '.docx'))
```

---

## Migration Guide

### From Manual Ingestion

**Before (manual):**
```bash
# Update docs
cp new-manual.pdf /docs/

# Manually trigger ingestion
kb-rag ingest /docs
```

**After (automatic):**
```bash
# 1. Configure watcher (one-time)
echo "WATCH_PATH=/docs" >> .env

# 2. Start watcher service
sudo systemctl enable --now kb-rag-watcher

# 3. Just update docs - ingestion happens automatically
cp new-manual.pdf /docs/
# Done! No manual step needed
```

### From Cron Jobs

**Before (cron):**
```cron
# Ingest every hour
0 * * * * /usr/bin/kb-rag ingest /docs
```

**After (watcher):**
```bash
# 1. Disable cron job
crontab -e  # Comment out ingestion line

# 2. Enable watcher
sudo systemctl enable --now kb-rag-watcher

# Benefits:
# - Real-time updates (not hourly delay)
# - Only processes changed files (not full re-scan)
# - Automatic retry on failure
```

---

## FAQ

**Q: Does the watcher re-ingest unchanged files?**  
A: No. The watcher only triggers jobs when files are created or modified. The job system then checks file hashes to skip unchanged content.

**Q: What happens if the watcher is stopped?**  
A: Manual ingestion still works normally. Changes made while the watcher is stopped won't be detected, so run manual ingestion to catch up.

**Q: Can I watch multiple directories?**  
A: Yes, either set `WATCH_PATH` to a common parent directory with `WATCH_RECURSIVE=true`, or run multiple watcher instances with different configurations.

**Q: How do I exclude specific subdirectories?**  
A: Use `WATCH_IGNORE_PATTERNS` to exclude patterns, or set `WATCH_PATH` to specific subdirectories instead of the parent.

**Q: Does the watcher handle file deletions?**  
A: Currently, deletions are logged but not processed. Deletion from Qdrant will be added in a future phase.

**Q: What if a file changes multiple times quickly?**  
A: The debouncer batches changes within the window (default 30s) into a single job, preventing duplicate processing.

**Q: Can the watcher handle network shares (SMB/NFS)?**  
A: Yes, but increase `WATCH_DEBOUNCE_SECONDS` to account for network latency. Test thoroughly as network filesystems may have delayed events.

**Q: How do I know if the watcher is working?**  
A: Check logs: `sudo journalctl -u kb-rag-watcher -f` and verify jobs are created: `kb-rag job list`

---

## See Also

- [Metadata Overrides](METADATA_OVERRIDES.md) - Override classification with `_meta.json`
- [Version Filtering](VERSION_FILTERING.md) - Search by document version
- [Job Management](../README.md#job-management) - Monitor and control ingestion jobs
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

---

*Last updated: 2026-06-11 for v1.3*
