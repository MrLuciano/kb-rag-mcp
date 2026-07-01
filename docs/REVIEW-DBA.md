---
phase: database-administrator-review
reviewed: 2026-06-15T12:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - ingest/core/metadata.py
  - ingest/cli/export.py
  - ingest/reclassify_engine.py
  - kb_server/config/db.py
  - kb_server/telemetry/query_logger.py
  - kb_server/auth_registry.py
  - kb_server/ui/routes.py
  - kb_server/ui/routes_admin.py
  - kb_server/analytics/query_analyzer.py
  - kb_server/health.py
findings:
  critical: 3
  warning: 8
  info: 6
  total: 17
status: issues_found
---

# Database Administrator Review: SQLite Usage Audit

**Reviewed:** 2026-06-15T12:00:00Z
**Depth:** deep — cross-file analysis with call-chain tracing
**Files Reviewed:** 10 source files spanning 5 independent SQLite databases
**Status:** issues_found

## Summary

This review covers all direct SQLite usage across the kb-rag-mcp codebase — 10 source files spanning 5 distinct SQLite databases (`kb_metadata.db`, `registry.db`, `query_log.db`, `auth.db`, and the shared multi-purpose `kb_metadata.db`). Three **CRITICAL** bugs were found: one causes the database health check to always report unhealthy, one makes the `export` CLI command crash when a `version` filter is supplied, and one allows concurrent ingest workers to throw `sqlite3.ProgrammingError` due to missing thread-safety configuration. Eight **WARNING** issues include connection leaks, missing indexes on auth and query-log tables, unenforced foreign keys, and unsafe SQL formatting. The migration system is mostly sound but lacks idempotency and reversibility.

---

## Critical Issues

### CR-01: Health check calls `get_stats()` without connecting — always reports unhealthy

**File:** `kb_server/health.py:239-240`
**Code:**
```python
store = MetadataStore()
stats = store.get_stats()  # <-- _conn is None, raises RuntimeError
```
**Risk:** The function claims to "Verify database file exists, can connect and query, schema is correct" but never calls `store.connect()`. `MetadataStore.__init__` sets `_conn = None` (line 44). The `conn` property raises `RuntimeError("Database not connected")` when `_conn` is `None` (line 75-78). This means `check_database()` always falls into the `except` branch and reports as unhealthy. Any deployment using the health endpoint for liveness/readiness probes will see a perpetually degraded database status, masking real issues.

**Fix:**
```python
store = MetadataStore()
store.connect()  # <-- missing call
try:
    stats = store.get_stats()
finally:
    store.close()
```

---

### CR-02: `export.py` version filter references non-existent column — crashes on use

**File:** `ingest/cli/export.py:102-103`
**Code:**
```python
if version:
    query += " AND version = ?"
    params.append(version)
```
**Risk:** The `files` table in both `MetadataStore._create_schema_v2()` (line 176-188) and `IngestRegistry._migrate()` (line 793-805) has **no `version` column**. When `version` is supplied, this query produces `SELECT * FROM files WHERE 1=1 AND version = ?`, which raises `sqlite3.OperationalError: no such column: version`. The test at `tests/test_export.py` created its own schema with a `version` column (line 36), masking this bug. Any user invoking `kb-ingest export` with `--version` will receive a database error.

**Fix — option A (remove non-functional filter):**
```python
if version:
    # Version column does not exist in the files table
    # For future use: ensure column is added to schema first
    pass
```

**Fix — option B (add the column, if semantically needed):**
```python
# In both _create_schema_v2 and IngestRegistry._migrate:
#   version TEXT DEFAULT ''
# Then uncomment the export filter
```

---

### CR-03: `IngestRegistry.connect()` missing `check_same_thread=False` and WAL mode — crashes in multi-threaded context

**File:** `ingest/core/metadata.py:771-773`
**Code:**
```python
def connect(self) -> None:
    self._conn = sqlite3.connect(self.db_path)
    self._conn.row_factory = sqlite3.Row
    self._migrate()
```
**Risk:** Unlike `MetadataStore.connect()` (lines 50-57) which sets `check_same_thread=False`, WAL journal mode, and `synchronous=NORMAL`, the `IngestRegistry` has none of these. The default `check_same_thread=True` means sqlite3 will raise `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread` if the connection is used from a different thread. The ingest pipeline uses async workers (see `ingest/ingest.py` and `ingest/worker/`), so multi-threaded access is expected. Also missing WAL mode means concurrent readers will block each other — writes block all readers.

**Fix:**
```python
def connect(self) -> None:
    self._conn = sqlite3.connect(
        self.db_path,
        check_same_thread=False,
        timeout=30.0,
    )
    self._conn.row_factory = sqlite3.Row
    self._conn.execute("PRAGMA journal_mode=WAL")
    self._conn.execute("PRAGMA synchronous=NORMAL")
    self._migrate()
```

---

## Warnings

### WR-01: Connection leak in `routes.py` — no context manager, only closed on success

**File:** `kb_server/ui/routes.py:48-112`, `190-208`
**Code:**
```python
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
# ... queries that can throw ...
conn.close()  # Only reached if no exception
```
**Risk:** If any exception occurs between `connect()` and `close()`, the connection is leaked. The `document_detail` route (lines 190-208) has the same issue, including an early return at line 199 that correctly closes, but any unexpected exception still leaks. In a long-running server, repeated leaks exhaust the SQLite lock and file descriptor limits.

**Fix — option A (context manager pattern from `config/db.py`):**
```python
from contextlib import closing
with closing(sqlite3.connect(DB_PATH)) as conn:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(...)
    conn.commit()
```
**Fix — option B (try/finally):**
```python
conn = sqlite3.connect(DB_PATH)
try:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(...)
    conn.commit()
finally:
    conn.close()
```

---

### WR-02: Connection leak in `routes_admin.py` — same unprotected pattern

**File:** `kb_server/ui/routes_admin.py:103-109`, `135-139`
**Code:**
```python
conn = sqlite3.connect(str(db_path))
conn.execute(...)
conn.commit()
conn.close()  # Only reached if no exception
```
**Risk:** Same as WR-01. Three separate endpoints (`delete_document`, `delete_failed_documents`) create connections without safe cleanup. These are callable by any authenticated user and could be triggered repeatedly to accelerate leaks.

**Fix:** Same as WR-01 — wrap in `try/finally` or `closing()` context manager.

---

### WR-03: Connection leak in `query_analyzer.py` — four methods all leak

**File:** `kb_server/analytics/query_analyzer.py:33-46`, `60-82`, `96-110`, `119-137`
**Risk:** All four methods (`load_queries`, `get_most_common_queries`, `get_low_score_queries`, `get_zero_result_queries`) open a connection with `sqlite3.connect()` and close manually. None use context managers or try/finally. Any query failure (e.g., `OperationalError` on a missing table) leaks the connection.

**Fix:** Wrap each in `with sqlite3.connect(self.db_path) as conn:` — the context manager auto-commits or rollbacks and closes.

---

### WR-04: Foreign keys are never enabled — `ON DELETE CASCADE` silently ignored

**File:** All SQLite connections, particularly `ingest/core/metadata.py:56`
**Code (missing):**
```python
self.conn.execute("PRAGMA foreign_keys = ON")  # NEVER CALLED
```
**Risk:** SQLite disables foreign key enforcement by default. The `job_progress` table declares `FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE` (line 169-170), but without `PRAGMA foreign_keys=ON` this constraint is entirely ignored. Deleting a job will orphan all its `job_progress` rows. The `reclassify_history` FK on `session_timestamp` (line 214) is also silently ignored.

**Fix:** Add `PRAGMA foreign_keys = ON` after every `PRAGMA journal_mode=WAL` call in every `connect()` method:
```python
self._conn.execute("PRAGMA journal_mode=WAL")
self._conn.execute("PRAGMA synchronous=NORMAL")
self._conn.execute("PRAGMA foreign_keys = ON")
```
Also add it to `_conn()` in `auth_registry.py` and the inline connections in `routes.py`, `routes_admin.py`, `query_analyzer.py`.

---

### WR-05: Missing indexes on `api_keys.prefix` and `api_keys.revoked` — full table scan on auth

**File:** `kb_server/auth_registry.py:132-136`
**Code:**
```sql
CREATE TABLE IF NOT EXISTS api_keys (
    ...
    prefix      TEXT NOT NULL,
    ...
    revoked     INTEGER NOT NULL DEFAULT 0,
    ...
);
```
**Risk:** `revoke_key()` (line 132) queries `WHERE prefix = ? AND revoked = 0`, and `verify_key()` (line 114) filters on `key_hash` (which has a UNIQUE index, so that's fine). But `revoke_key()` does a full table scan on a prefix lookup. The `list_keys()` (line 153) also does an unsorted full scan (though that's a minor concern for an admin listing). Without an index on `prefix`, revocation latency grows linearly with the number of keys.

**Fix:**
```python
conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_revoked ON api_keys(revoked)")
```

---

### WR-06: Missing indexes on `query_log.timestamp` — cleanup and stats degrade over time

**File:** `kb_server/telemetry/query_logger.py:27-43`
**Code:**
```sql
CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    ...
);
```
**Risk:** `cleanup_old_queries()` (line 117) runs `DELETE FROM query_log WHERE timestamp < ?` — a full table scan. `get_query_stats()` (line 133) aggregates the entire table. The `QueryAnalyzer` in `query_analyzer.py` also does multiple full table scans (`GROUP BY query_text`, `WHERE max_score < ?`). Without indexes, as the table grows, cleanup and analytics queries become progressively slower, eventually locking the database for seconds.

**Fix:**
```python
conn.execute("CREATE INDEX IF NOT EXISTS idx_ql_timestamp ON query_log(timestamp)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_ql_max_score ON query_log(max_score)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_ql_query_text ON query_log(query_text)")
```

---

### WR-07: `Migration DDL lacks IF NOT EXISTS — not idempotent, crashes on re-run`

**File:** `ingest/core/metadata.py:125-219`
**Code:**
```sql
CREATE TABLE schema_version (...);
CREATE TABLE jobs (...);
CREATE TABLE job_progress (...);
CREATE TABLE files (...);
CREATE TABLE reclassify_backups (...);
CREATE TABLE reclassify_history (...);
```
**Risk:** `_create_schema_v2()` uses bare `CREATE TABLE` without `IF NOT EXISTS`. If `_migrate()` ever calls this path when tables already exist (e.g., after a partial migration failure or manual DB reset), it raises `sqlite3.OperationalError: table already exists`. While the migration logic guards against this (fresh DB has version=0, migration paths are sequential), a corrupted version number or a mid-migration crash could trigger a re-run that fails destructively.

**Fix:** Use `CREATE TABLE IF NOT EXISTS` for all DDL statements in `_create_schema_v2()` (consistent with `IngestRegistry._migrate()` at line 793 which already uses `IF NOT EXISTS`).

---

### WR-08: Unsafe SQL string formatting in ATTACH DATABASE path

**File:** `ingest/core/metadata.py:235`
**Code:**
```python
self.conn.execute(f"ATTACH DATABASE '{v1_path}' AS old")
```
**Risk:** The database path is interpolated directly into the SQL string via an f-string. If a path contains a single quote (e.g., `/path/team's docs/registry.db`), the SQL statement becomes malformed, causing an error or — in a pathologically crafted scenario — SQL injection. While the path is constructed from `self.db_path.parent / "registry.db"` (a controlled origin), this is a fragile pattern that violates the codebase's otherwise consistent use of parameterized queries.

**Fix:**
```python
self.conn.execute("ATTACH DATABASE ? AS old", (str(v1_path),))
```
Note: SQLite supports parameterized ATTACH DATABASE from Python's sqlite3 driver.

---

## Info

### IN-01: `SELECT *` in production queries — returning more columns than needed

**Files:**
- `ingest/core/metadata.py:385,394,646,682` (`SELECT * FROM quota_config`, `quota_usage`, `connector_state`)
- `ingest/core/metadata.py:1092,1098` (`SELECT * FROM files` in `list_all`)
- `kb_server/analytics/query_analyzer.py:37,101` (`SELECT * FROM query_log`)
- `ingest/cli/export.py:89` (`SELECT * FROM files`)

**Risk:** Minor — `SELECT *` returns all columns even when callers only use a subset. This creates a hidden coupling: adding a column to the table changes the shape of the returned dicts, which may break consumers. For `list_all` and `query_analyzer.load_queries`, this also unnecessarily increases memory pressure.

**Suggestion:** Enumerate required columns explicitly, e.g.:
```python
SELECT path, sha256, status, chunks, indexed_at FROM files
```

---

### IN-02: `get_most_common_queries` and `get_zero_result_queries` run full table aggregations with no LIMIT guard on the inner scan

**File:** `kb_server/analytics/query_analyzer.py:63-70`, `122-128`

**Risk:** `GROUP BY query_text ORDER BY frequency DESC` on the entire `query_log` table will scan every row. If the table has millions of rows, these queries become expensive. The outer `LIMIT ?` only caps the result set, not the scan.

**Suggestion:** Consider adding a time-range filter (e.g., `WHERE timestamp > ?`) to scope analytics to the recent period, or add an index on `query_text` to make GROUP BY more efficient.

---

### IN-03: `config/db.py:ensure_config_table()` must be called separately — not integrated into `get_connection()`

**File:** `kb_server/config/db.py:20-38`, `41-61`

**Risk:** The `get_connection()` context manager does not call `ensure_config_table()`. Callers must remember to call it manually. If a new consumer uses `get_connection()` without calling `ensure_config_table()`, they may encounter "no such table: config" errors at runtime.

**Suggestion:** Either integrate `ensure_config_table()` into `get_connection()` or document it in the function's docstring as a required call.

---

### IN-04: `query_log.timestamp` stored as ISO text string instead of REAL epoch

**File:** `kb_server/telemetry/query_logger.py:31`

**Code:**
```sql
timestamp TEXT NOT NULL
```

**Risk:** Storing timestamps as ISO text is 4-8× larger than REAL (Unix epoch) and requires string comparison for range queries. While ISO 8601 lexicographic ordering happens to match chronological order, this is fragile — a format change (e.g., adding timezone offset) would break `ORDER BY` and `WHERE timestamp < ?` comparisons.

**Suggestion:** Change to `timestamp REAL NOT NULL` and store `time.time()` instead of `datetime.utcnow().isoformat()`.

---

### IN-05: Environment variable paths evaluated at import time in routes.py

**File:** `kb_server/ui/routes.py:12`

**Code:**
```python
DB_PATH = Path(os.getenv("KB_METADATA_DB", "data/kb_metadata.db"))
```

**Risk:** This is evaluated once at module import time. If the environment variable changes after the module is loaded (e.g., during testing or process reconfiguration), the DB path won't update. This also prevents the path from being overridden in unit tests without mocking.

**Suggestion:** Change to a lazy property or function:
```python
def get_db_path() -> Path:
    return Path(os.getenv("KB_METADATA_DB", "data/kb_metadata.db"))
```

---

### IN-06: Singleton pattern in `auth_registry.get_registry()` not thread-safe for creation

**File:** `kb_server/auth_registry.py:171-175`

**Code:**
```python
def get_registry() -> AuthRegistry:
    global _registry
    if _registry is None:
        _registry = AuthRegistry()
    return _registry
```

**Risk:** Two threads can race past the `is None` check, each creating an `AuthRegistry` instance. `_registry` will point to whichever one wins, and the other instance (with its own database connection/schema) will be orphaned. `AuthRegistry.__init__` calls `_init_db()` which creates tables, so no data loss occurs, but memory and file descriptors are wasted.

**Suggestion:** Add a threading lock or use a module-level `__getattr__` pattern:
```python
_registry_lock = threading.Lock()
_registry: Optional[AuthRegistry] = None

def get_registry() -> AuthRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = AuthRegistry()
    return _registry
```

---

## Database Schema Summary

| Database File | Tables | Managed By | WAL Mode | check_same_thread | Foreign Keys Enabled |
|---|---|---|---|---|---|
| `data/kb_metadata.db` | schema_version, jobs, job_progress, files, reclassify_backups, reclassify_history, connector_state, quota_config, quota_usage | `MetadataStore` (ingest/core/metadata.py) + `config/db.py` | ✅ Yes | ✅ False | ❌ No |
| `data/registry.db` (legacy) | files | `IngestRegistry` (ingest/core/metadata.py) | ❌ No | ❌ Default (True) | ❌ No |
| `data/query_log.db` | query_log | `QueryLogger` (telemetry/query_logger.py) | ❌ (Default, each connection fresh) | ❌ Default | N/A |
| `data/auth.db` | api_keys | `AuthRegistry` (auth_registry.py) | ❌ (Connection per-op) | ❌ Default | N/A |
| `data/kb_metadata.db` (ad-hoc) | config, config_version | `config/db.py` | ✅ Yes | ✅ False | ❌ No |

## Migration Analysis

| Phase | From/To | Idempotent? | Reversible? | Tested? |
|---|---|---|---|---|
| `_migrate_v1_to_v2` | v1 → v2 | ❌ (bare CREATE TABLE) | ❌ | Partial |
| `_migrate_v2_to_v3` | v2 → v3 | ✅ (checks table exists) | ❌ | No |
| `_migrate_v3_to_v4` | v3 → v4 | ✅ (checks table exists) | ❌ | No |

**Key finding:** The migration system correctly sequences upgrades using `_get_schema_version()`, but no migration can be rolled back. The v1→v2 migration is the most fragile because it calls `_create_schema_v2()` (bare DDL) and uses `ATTACH DATABASE` with string interpolation.

---

_Reviewed: 2026-06-15T12:00:00Z_
_Reviewer: gsd-code-reviewer (database-administrator-review)_
_Depth: deep_
