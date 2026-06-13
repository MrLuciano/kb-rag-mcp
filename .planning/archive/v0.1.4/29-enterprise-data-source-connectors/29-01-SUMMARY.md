# Phase 29-01 SUMMARY: Connector Foundation

**Date:** 2026-06-10
**Type:** execute
**Status:** Complete

## Changes Made

### `ingest/core/metadata.py` — Connector-aware schema
- Bumped `SCHEMA_VERSION` from 2 to 3
- Added `_migrate_v2_to_v3()`: creates `connector_state` table with indices for connector type, status, and ingested_at
- Updated `_migrate()` to chain v2→v3 migration through all paths (fresh, v1, v2)
- Added 6 connector state helper methods: `upsert_connector_state`, `get_connector_state`, `list_connector_state`, `delete_connector_state`, `get_connector_sync_checkpoint`

### `ingest/connectors/` — New package (4 modules)
- **`models.py`**: `RemoteDocument`, `ConnectorConfig`, `SyncResult` — typed dataclasses for remote documents, config, and sync lifecycle
- **`base.py`**: `ConnectorBase` ABC — abstract `fetch_documents(since)`, `fetch_document(id)`, `connect()`, `close()` — source-agnostic design that future Confluence/JIRA/Git implementations will subclass
- **`factory.py`**: Module-level `register()`, `create_connector()`, `list_supported_types()` — runtime lookup without import coupling
- **`staging.py`**: `stage_document()`, `stage_documents()`, `get_staging_root()`, `cleanup_stale_staging()`, `resolve_staged_metadata()`, `_safe_path_component()` — bridges remote content into local files with embedded metadata headers

### `ingest/cli/connectors.py` — New CLI module
- `connectors list` — lists registered connector types from the factory
- `connectors stage` — validates connector type, configures staging, supports `--clean` and `--staging-dir` options

### `ingest/cli/main.py` — CLI registration
- Imported and registered `connectors_group` as a top-level CLI command

### `ingest/ingest.py` — Connector-aware ingest path
- Added `staged_paths` and `connector_source` parameters to `run_ingest()`
- When processing staged files, uses `resolve_staged_metadata()` to extract connector identity and records sync state via `MetadataStore.upsert_connector_state()`

### Test files (3 new, 1 extended)
- `tests/test_connectors_base.py` — 12 tests covering models (RemoteDocument, SyncResult, ConnectorConfig) and factory (register/create/list)
- `tests/test_connectors_staging.py` — 12 tests covering path sanitization, staging root, single/batch staging, stale cleanup, metadata resolution
- `tests/test_ingest_registry.py` — 6 new connector state round-trip tests (upsert, update, not-found, list filtering, delete, checkpoint, schema migration)
- `tests/test_cli.py` — 4 new connector CLI tests (list, unknown type error, known type stage)

## Verification Results

| Test Suite | Status |
|---|---|
| `test_ingest_registry.py` | 10 passed |
| `test_connectors_base.py` | 12 passed |
| `test_connectors_staging.py` | 12 passed |
| `test_cli.py` | 23 passed |
| `test_job_system.py` | 25 passed |
| `test_worker_system.py` | 32 passed |
| Full test suite | 834 passed, 2 pre-existing failures |

## Artifacts Produced

| Artifact | Lines | Contains |
|---|---|---|
| `ingest/connectors/base.py` | 59 | `ConnectorBase` ABC |
| `ingest/core/metadata.py` (v2→v3) | ~100 new | `connector_state` table + helpers |
| `ingest/connectors/staging.py` | 143 | `stage_document` + helpers |

## Next Steps

- **Phase 29-02**: Confluence connector (Cloud + 7.9.3 Server/DC)
- **Phase 29-03**: JIRA connector (Cloud + Data Center)
- **Phase 29-04**: Git repository connector
