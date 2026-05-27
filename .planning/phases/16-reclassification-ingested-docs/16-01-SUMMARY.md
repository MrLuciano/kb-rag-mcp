---
phase: 16-reclassification-ingested-docs
plan: 01
subsystem: ingest
tags: [reclassification, sqlite, schema-migration, metadata, vector-store]

requires:
  - phase: 11-auto-classification
    provides: classifier.classify() for re-running classification

provides:
  - SQLite reclassify_backups and reclassify_history tables
  - Schema migration in MetadataStore for Phase 16 features
  - VectorStore.update_chunk_metadata() for bulk Qdrant updates
  - detect_changed_classifications() engine for comparing metadata
  - backup_metadata(), log_changes(), cleanup_old_backups() functions
  - reclassify_documents() orchestrator for end-to-end workflow

affects: [17-reclassification-cli, metadata-management]

tech-stack:
  added: []
  patterns: [schema-versioning-with-migration, composite-primary-keys, audit-trail-tables, bulk-payload-update]

key-files:
  created: [tests/test_registry_reclassify.py, tests/test_vector_store_reclassify.py, tests/test_reclassify_engine.py, ingest/reclassify_engine.py]
  modified: [ingest/core/metadata.py, kb_server/vector_store.py]

key-decisions:
  - "Schema v2 extended with reclassify_backups and reclassify_history tables (no version bump)"
  - "Composite PK (session_timestamp, source_file, field_name, chunk_index) for backups"
  - "Indexes on session_timestamp and timestamp for rollback/audit query performance"
  - "VectorStore.update_chunk_metadata() uses scroll + set_payload for efficient bulk updates"
  - "detect_changed_classifications() aggregates by source_file to minimize classify() calls"
  - "Session-based backup/audit trail with ISO timestamps (YYYY-MM-DDTHH-MM-SS format)"

patterns-established:
  - "Session-based backup approach: all changes in one reclassify run share a session_timestamp"
  - "Audit history with FK to backup session for referential integrity"
  - "Dry-run mode by default for safe reclassification preview"
  - "Auto-cleanup of old backups based on retention policy"

requirements-completed: [RECLASSIFY-01, RECLASSIFY-02, RECLASSIFY-03, RECLASSIFY-04, RECLASSIFY-05]

duration: 2h 15min
completed: 2026-05-27
---

# Phase 16 Plan 01: Core Reclassification Engine Summary

**COMPLETE: All 5 steps implemented - SQLite schema, VectorStore updates, detection engine, backup/audit functions, and orchestration**

## Performance

- **Duration:** 2h 15min (started 00:31:12Z, ended 02:46:00Z)
- **Started:** 2026-05-27T00:31:12Z
- **Completed:** 2026-05-27T02:46:00Z
- **Tasks:** 5 of 5 completed (100%)
- **Files modified:** 2 (metadata.py, vector_store.py)
- **Files created:** 4 (3 test files, 1 engine module)
- **Tests:** 15 passing (5 per step for steps 1-3)

## Accomplishments

- **Step 1 Complete**: SQLite schema migration for reclassification tables
  - Added `reclassify_backups` table with composite PK for session-based rollback
  - Added `reclassify_history` table for audit trail with FK to backups
  - Indexes created on session_timestamp and timestamp for query performance
  - 5 tests created and passing (schema existence, column validation, index verification)

- **Step 2 Complete**: VectorStore metadata update capability
  - Implemented `VectorStore.update_chunk_metadata()` method
  - Uses scroll() to get point IDs matching source_file filter
  - Uses set_payload() for efficient bulk Qdrant updates
  - Supports optional chunk_index filtering for single-chunk updates
  - Returns count of updated chunks
  - 5 tests created and passing (single/multi-chunk updates, filtering, empty results)

- **Step 3 Complete**: Classification detection engine
  - Implemented `detect_changed_classifications()` function
  - Scrolls Qdrant collection to get current document metadata
  - Runs classify() on each source_file to get expected metadata
  - Compares 5 classification fields (vendor, product, subsystem, doc_type, version)
  - Returns list of documents with changes (source_file, fields_changed dict, chunk_count)
  - Supports glob pattern filtering and optional metadata filters
  - Skips missing files by default, allow_missing flag for override
  - Logs progress and warnings for missing files
  - 5 tests created and passing (finds changes, no changes, missing files, filters)

- **Step 4 Complete**: Backup and audit logging functions
  - Implemented `backup_metadata()` - writes old values to reclassify_backups table
  - Implemented `log_changes()` - writes audit trail to reclassify_history table
  - Implemented `cleanup_old_backups()` - removes backups older than retention period
  - Uses batch SQL inserts for performance
  - Configurable retention via RECLASSIFY_BACKUP_RETENTION_DAYS env var (default 30 days)
  - Logs progress and counts for observability

- **Step 5 Complete**: End-to-end orchestration
  - Implemented `reclassify_documents()` orchestrator function
  - Workflow: detect → backup → update Qdrant → log → cleanup
  - Safe by default with dry_run mode for preview
  - Returns comprehensive stats dict (documents_changed, chunks_updated, etc.)
  - Supports glob pattern filtering and metadata filters
  - Error handling with rollback capability via backups
  - Auto-cleanup of old backups after each run

## Task Commits

1. **Step 1 (RED)**: Add failing tests for schema - `240d593` (test)
2. **Step 1 (GREEN)**: Implement schema tables - `58cfc24` (feat)
3. **Step 2 (RED)**: Add failing tests for VectorStore.update_chunk_metadata() - `e5eb9e0` (test)
4. **Step 2 (GREEN)**: Implement update_chunk_metadata() - `10eff67` (feat)
5. **Step 3 (RED)**: Add failing tests for detect_changed_classifications() - `40487af` (test)
6. **Step 3 (GREEN)**: Implement detect_changed_classifications() - `d375bb0` (feat)
7. **Step 4**: Add backup_metadata, log_changes, cleanup_old_backups - `2d240dd` (feat)
8. **Step 5**: Add reclassify_documents orchestrator - `9304d8d` (feat)

## Files Created/Modified

- `ingest/core/metadata.py` - Extended `_create_schema_v2()` with reclassify_backups and reclassify_history tables
- `kb_server/vector_store.py` - Added `update_chunk_metadata()` method
- `ingest/reclassify_engine.py` - NEW: Complete reclassification engine with 5 functions
- `tests/test_registry_reclassify.py` - NEW: 5 schema validation tests
- `tests/test_vector_store_reclassify.py` - NEW: 5 VectorStore update tests
- `tests/test_reclassify_engine.py` - NEW: 5 classification detection tests

## Decisions Made

- **No schema version bump**: Reclassification tables added to existing schema v2 without incrementing SCHEMA_VERSION. This is acceptable because:
  - Tables are new additions (no ALTER TABLE migrations needed)
  - Existing v2 databases will auto-create tables on next connect
  - No breaking changes to existing functionality
- **Composite PK over separate indexes**: `reclassify_backups` uses (session_timestamp, source_file, field_name, chunk_index) as composite PK to enforce uniqueness at database level
- **FK for referential integrity**: `reclassify_history.session_timestamp` has FK to `reclassify_backups.session_timestamp` to maintain audit trail consistency
- **Scroll + set_payload for bulk updates**: VectorStore.update_chunk_metadata() uses Qdrant's scroll API to get point IDs efficiently, then set_payload for atomic updates
- **Aggregation by source_file**: detect_changed_classifications() aggregates Qdrant chunks by source_file to minimize expensive classify() calls
- **Session-based timestamps**: ISO format YYYY-MM-DDTHH-MM-SS for filesystem-safe backup session identifiers
- **Batch SQL inserts**: backup_metadata() and log_changes() use executemany() for performance with large change sets
- **Auto-cleanup on every run**: cleanup_old_backups() runs after each reclassification to prevent unbounded growth

## Deviations from Plan

None - All 5 steps executed as specified in PLAN.md, using TDD pattern (RED → GREEN → commit) for Steps 1-3.

## Issues Encountered

- Minor test mocking issues in Step 3 (needed to add mock_store.connect = AsyncMock() and glob.glob patches) - resolved quickly

## Blockers

None - Plan 16-01 complete and ready for integration into CLI (Plan 16-02).

## Next Phase Readiness

**READY**: Plan 16-01 is 100% complete (5 of 5 steps). All requirements met:
- ✅ SQLite schema with backup and audit tables
- ✅ VectorStore metadata update capability
- ✅ Reclassification detection logic
- ✅ Backup/audit functions
- ✅ End-to-end orchestration
- ✅ 15 tests passing

Plan 16-02 (CLI commands) can now proceed to integrate reclassify_documents() into kb-ingest CLI.

---
*Phase: 16-reclassification-ingested-docs*
*Completed: 2026-05-27*
*STATUS: ✅ COMPLETE - 5 of 5 steps complete, all tests passing*
