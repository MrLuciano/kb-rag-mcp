# Plan 45-01 SUMMARY: Database Reliability

## Objective

Fix four SQLite database issues: connection leaks (context managers), unenforced foreign keys, missing indexes, and fragile migration DDL.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_ui_routes.py -v` | ✅ 20/20 PASS |
| `pytest tests/test_ingest_registry.py -v` | ✅ All pass |
| `pytest tests/test_auth_registry.py -v` | ✅ All pass |
| `pytest tests/test_query_logger.py -v` | ✅ All pass |

## Tasks Executed

| # | Fix | Status |
|---|-----|--------|
| 1 | Refactor 4 raw sqlite3.connect() calls to context managers in routes.py + routes_admin.py | ✅ |
| 2 | Add PRAGMA foreign_keys=ON to MetadataStore, IngestRegistry, and AuthRegistry connections | ✅ |
| 3 | Add indexes on api_keys.prefix and query_log.timestamp | ✅ |
| 4 | Add IF NOT EXISTS to connector_state migration DDL | ✅ |

## Files Modified

- `kb_server/ui/routes.py` — Refactored `get_documents()`, `document_detail()`, and `document_chunks()` to use `with sqlite3.connect() as conn:`
- `kb_server/ui/routes_admin.py` — Refactored `delete_document()` and `delete_failed_documents()` to use `with sqlite3.connect() as conn:`
- `ingest/core/metadata.py` — Added `PRAGMA foreign_keys=ON` to `MetadataStore.connect()` and `IngestRegistry.connect()`; added `IF NOT EXISTS` to `connector_state` migration DDL
- `kb_server/auth_registry.py` — Added `PRAGMA foreign_keys=ON` to `_conn()`; added `CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix)`
- `kb_server/telemetry/query_logger.py` — Added `CREATE INDEX IF NOT EXISTS idx_query_log_timestamp ON query_log(timestamp)`
- `tests/test_ui_routes.py` — Updated mock connections to support context manager protocol (`__enter__`/`__exit__`)
