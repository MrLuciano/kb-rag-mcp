# Query Analysis and Logging Guide

## Overview

KB-RAG automatically logs all search queries to support:
- **Performance monitoring** - Track latency and result quality
- **Usage analytics** - Understand query patterns
- **System improvement** - Identify optimization opportunities

All queries are stored in SQLite with 90-day auto-rotation.

## Quick Start

### Enable Query Logging

Query logging is **enabled by default**. To disable:

```bash
# .env or environment
QUERY_LOG_ENABLED=false
```

### View Query Log

```bash
# Connect to database
sqlite3 data/kb_metadata.db

# Recent queries
SELECT timestamp, query_text, result_count, latency_ms 
FROM query_log 
ORDER BY id DESC 
LIMIT 10;

# Queries with zero results
SELECT query_text, filters, version_filter
FROM query_log 
WHERE result_count = 0
ORDER BY timestamp DESC;
```

## What Gets Logged

### Query Information
- **query_text**: The search query
- **timestamp**: ISO 8601 UTC timestamp
- **top_k**: Number of results requested
- **score_threshold**: Minimum score filter (if used)

### Filters Applied
- **filters**: JSON object with product, doc_type, file_type
- **version_filter**: Version constraint (FASE 13)

### Results
- **result_count**: Number of results returned
- **max_score**: Highest relevance score
- **min_score**: Lowest relevance score
- **avg_score**: Average relevance score

### Performance
- **latency_ms**: Query execution time in milliseconds

## Database Schema

```sql
CREATE TABLE query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    query_text TEXT NOT NULL,
    top_k INTEGER,
    score_threshold REAL,
    filters TEXT,              -- JSON: {"product": "X", "doc_type": "Y"}
    version_filter TEXT,       -- e.g., "23.4" or ">=1.0.0"
    result_count INTEGER,
    max_score REAL,
    min_score REAL,
    avg_score REAL,
    latency_ms REAL
);
```

## Query Analysis

### 1. Performance Analysis

**Average latency by query type:**

```sql
SELECT 
    CASE 
        WHEN filters IS NOT NULL THEN 'filtered'
        ELSE 'unfiltered'
    END as query_type,
    AVG(latency_ms) as avg_latency,
    MAX(latency_ms) as max_latency,
    COUNT(*) as query_count
FROM query_log
GROUP BY query_type;
```

**Slow queries (>1 second):**

```sql
SELECT timestamp, query_text, latency_ms, result_count
FROM query_log
WHERE latency_ms > 1000
ORDER BY latency_ms DESC;
```

### 2. Result Quality Analysis

**Queries with low max scores:**

```sql
SELECT query_text, max_score, result_count
FROM query_log
WHERE max_score < 0.7
ORDER BY timestamp DESC
LIMIT 20;
```

**Zero-result queries:**

```sql
SELECT query_text, filters, version_filter, COUNT(*) as occurrences
FROM query_log
WHERE result_count = 0
GROUP BY query_text
ORDER BY occurrences DESC;
```

### 3. Usage Patterns

**Most common queries:**

```sql
SELECT query_text, COUNT(*) as frequency
FROM query_log
GROUP BY query_text
HAVING frequency > 1
ORDER BY frequency DESC
LIMIT 20;
```

**Most used filters:**

```sql
SELECT 
    json_extract(filters, '$.product') as product,
    COUNT(*) as usage_count
FROM query_log
WHERE filters IS NOT NULL
GROUP BY product
ORDER BY usage_count DESC;
```

**Version filter usage:**

```sql
SELECT 
    version_filter,
    COUNT(*) as count,
    AVG(result_count) as avg_results
FROM query_log
WHERE version_filter IS NOT NULL
GROUP BY version_filter
ORDER BY count DESC;
```

### 4. Time-Based Analysis

**Queries per hour (last 24h):**

```sql
SELECT 
    strftime('%Y-%m-%d %H:00', timestamp) as hour,
    COUNT(*) as query_count,
    AVG(latency_ms) as avg_latency
FROM query_log
WHERE timestamp > datetime('now', '-24 hours')
GROUP BY hour
ORDER BY hour;
```

## Statistics API

Use the QueryLogger API for programmatic access:

```python
from server.telemetry.query_logger import QueryLogger
from pathlib import Path

logger = QueryLogger(db_path=Path("data/kb_metadata.db"))

# Get aggregate statistics
stats = logger.get_query_stats()
print(f"Total queries: {stats['total_queries']}")
print(f"Avg latency: {stats['avg_latency_ms']:.1f}ms")
print(f"Avg results: {stats['avg_results']:.1f}")
```

## Data Retention

### Auto-Rotation

Query logs are automatically cleaned up:
- **Retention**: 90 days (configurable)
- **Frequency**: On each query (lightweight check)
- **Method**: DELETE queries older than cutoff

### Manual Cleanup

```python
from server.telemetry.query_logger import QueryLogger
from pathlib import Path

logger = QueryLogger(db_path=Path("data/kb_metadata.db"))

# Clean up queries older than 30 days
deleted_count = logger.cleanup_old_queries(retention_days=30)
print(f"Deleted {deleted_count} old queries")
```

**SQL cleanup:**

```sql
-- Delete queries older than 90 days
DELETE FROM query_log 
WHERE timestamp < datetime('now', '-90 days');

-- Vacuum to reclaim space
VACUUM;
```

## Performance Impact

Query logging is designed for minimal overhead:

### Latency Impact
- **Target**: <5ms per query
- **Typical**: 1-2ms (SQLite insert)
- **Overhead**: <1% of total query time

### Storage
- **Per query**: ~200 bytes
- **1000 queries/day**: ~200KB/day, ~6MB/month
- **90-day retention**: ~18MB total

### CPU/Memory
- **Negligible**: Single INSERT per query
- **No indexes**: Simple append-only writes
- **Async-safe**: Non-blocking operation

## Export Query Logs

### JSON Export

```bash
# Export all queries
python3 -c "
from ingest.cli.export import export_registry_json
import sys
export_registry_json(sys.stdout)
" > queries.json

# Export filtered queries
python3 -c "
from ingest.cli.export import export_registry_json
import sys
export_registry_json(sys.stdout, product='ArchiveCenter')
" > archivecenter_queries.json
```

### CSV Export

```bash
# Export to CSV
python3 -c "
from ingest.cli.export import export_registry_csv
import sys
export_registry_csv(sys.stdout)
" > queries.csv
```

## Privacy Considerations

### What to Log
✅ Query text (for analysis)
✅ Filters and parameters
✅ Result metrics (count, scores)
✅ Performance data

### What NOT to Log
❌ User identifiers (no auth = no users)
❌ IP addresses
❌ Session tokens
❌ API keys

### Data Sharing
- **Internal only**: No external transmission
- **Local storage**: SQLite on same server
- **Read-only exports**: For analysis only

## Troubleshooting

### Logging Not Working

**Check if enabled:**
```bash
# Should see "Query logging enabled" in logs
sudo journalctl -u kb-rag-server | grep "Query logging"
```

**Verify database permissions:**
```bash
ls -l data/kb_metadata.db
# Should be writable by kb-rag user
```

**Test manually:**
```python
from server.telemetry.query_logger import QueryLogger
from pathlib import Path

logger = QueryLogger(db_path=Path("data/kb_metadata.db"))
logger.log_query(
    query_text="test query",
    top_k=5,
    score_threshold=None,
    filters=None,
    version_filter=None,
    result_count=1,
    scores=[0.9],
    latency_ms=10.5
)
print("Logged successfully")
```

### Database Locked

If writes fail with "database is locked":

```bash
# Check for long-running queries
sqlite3 data/kb_metadata.db "PRAGMA busy_timeout=5000;"

# Enable WAL mode for better concurrency
sqlite3 data/kb_metadata.db "PRAGMA journal_mode=WAL;"
```

### High Latency

If query logging adds >5ms overhead:

```bash
# Check database size
du -h data/kb_metadata.db

# Vacuum if large
sqlite3 data/kb_metadata.db "VACUUM;"

# Reduce retention
python3 -c "
from server.telemetry.query_logger import QueryLogger
from pathlib import Path
logger = QueryLogger(db_path=Path('data/kb_metadata.db'))
logger.cleanup_old_queries(retention_days=30)
"
```

## Use Cases

### 1. Identify Missing Content

Find queries with zero results to discover content gaps:

```sql
SELECT query_text, COUNT(*) as frequency
FROM query_log
WHERE result_count = 0
GROUP BY query_text
HAVING frequency > 2
ORDER BY frequency DESC;
```

**Action**: Add documents covering these topics.

### 2. Optimize Slow Queries

Find queries consistently >500ms:

```sql
SELECT query_text, AVG(latency_ms) as avg_latency
FROM query_log
GROUP BY query_text
HAVING avg_latency > 500
ORDER BY avg_latency DESC;
```

**Action**: Optimize indexes, tune chunking, cache results.

### 3. Validate Filters

Check if version filtering improves result quality:

```sql
SELECT 
    CASE WHEN version_filter IS NOT NULL THEN 'versioned' 
         ELSE 'unversioned' END as filter_type,
    AVG(max_score) as avg_top_score,
    AVG(result_count) as avg_results
FROM query_log
GROUP BY filter_type;
```

### 4. Monitor System Health

Daily query volume and performance:

```sql
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as queries,
    AVG(latency_ms) as avg_latency,
    SUM(CASE WHEN result_count = 0 THEN 1 ELSE 0 END) as zero_results
FROM query_log
WHERE timestamp > datetime('now', '-7 days')
GROUP BY date
ORDER BY date;
```

## Related Documentation

- [WEB_UI.md](WEB_UI.md) - Web UI for browsing queries
- [FASE14_PLAN.md](FASE14_PLAN.md) - Implementation details
- [OPERATIONS.md](OPERATIONS.md) - Deployment guide

## Future Enhancements

Potential improvements:
- Query clustering (group similar queries)
- Automatic alerting (zero results spike)
- Query suggestion (typo correction)
- Result caching (for common queries)
- A/B testing support (compare configurations)
