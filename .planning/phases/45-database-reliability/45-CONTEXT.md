# Phase 45: Database Reliability - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix four SQLite database issues: connection leaks (context managers), unenforced foreign keys, missing indexes, and fragile migration DDL.

Requirements: DB-01, DB-02, DB-03, DB-04

</domain>

<decisions>
## Implementation Decisions

### DB-01: Connection Leaks
- **D-01:** Refactor raw `sqlite3.connect()` calls in `kb_server/ui/routes.py`, `kb_server/ui/routes_admin.py`, and `tests/test_query_analyzer.py` to use `with sqlite3.connect() as conn:` context managers. Ensure all manual `conn.close()` calls are replaced.

### DB-02: Foreign Keys
- **D-02:** Add `conn.execute("PRAGMA foreign_keys=ON")` to every `connect()` method in `ingest/core/metadata.py` (`MetadataStore.connect()`, `IngestRegistry.connect()`) and `kb_server/auth_registry.py` (`AuthRegistry._conn()`). Must be set per-connection as SQLite does not persist this setting.

### DB-03: Missing Indexes
- **D-03:** Add `CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix)` to `kb_server/auth_registry.py` schema init.
- **D-04:** Add `CREATE INDEX IF NOT EXISTS idx_query_log_timestamp ON query_log(timestamp)` to `kb_server/telemetry/query_logger.py` schema init.

### DB-04: Migration DDL
- **D-05:** Add `IF NOT EXISTS` to all bare `CREATE TABLE` statements in `ingest/core/metadata.py` migration methods (`_migrate_v2_to_v3`, `_migrate_v3_to_v4`) for the `connector_state`, `quota_config`, and `quota_usage` tables.

### the agent's Discretion
- Testing strategy for verifying context managers work correctly
- Whether to add a test that verifies foreign keys are enforced

</decisions>

<canonical_refs>
## Canonical References

- `kb_server/ui/routes.py:48-80` — `get_documents()` with raw connect
- `kb_server/ui/routes.py:190-208` — `document_detail()` with raw connect
- `kb_server/ui/routes_admin.py:126-129` — delete_document with raw connect
- `kb_server/ui/routes_admin.py:164-168` — delete_failed with raw connect
- `ingest/core/metadata.py:48-58` — MetadataStore.connect()
- `ingest/core/metadata.py:766-774` — IngestRegistry.connect()
- `kb_server/auth_registry.py:36-39` — AuthRegistry._conn()
- `kb_server/telemetry/query_logger.py:25-43` — QueryLogger schema init
</canonical_refs>

<deferred>
None — all 4 items are in scope.

</deferred>

---

*Phase: 45-database-reliability*
*Context gathered: 2026-06-15*
