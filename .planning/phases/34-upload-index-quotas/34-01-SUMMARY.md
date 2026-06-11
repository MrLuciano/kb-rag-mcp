# Phase 34 SUMMARY: Upload and Index Quotas

**Date:** 2026-06-10
**Type:** execute
**Status:** Complete

## Changes Made

### `ingest/core/metadata.py` — Schema v4 + quota helpers (+238 lines)
- **SCHEMA_VERSION** bumped 3→4
- **`_migrate_v3_to_v4()`**: Creates `quota_config` (single-row limits) and `quota_usage` (single-row counters) tables with safe idempotent migration
- **`set_quotas()`**: Configure any/all of the 6 quota fields; `None` = unlimited
- **`get_quotas()`**: Read current limit configuration
- **`get_quota_usage()`**: Read current usage counters
- **`check_quota()`**: Validate files_count, bytes_total, file_bytes against limits + current usage; returns `(ok, message)` tuple
- **`update_quota_usage()`**: Increment counters after successful ingest
- **`reset_quota_usage()`**: Zero all counters (returns previous state)

### Quota Fields
| Field | Default | Enforced At |
|---|---|---|
| `max_files_per_upload` | unlimited | Per ingest call |
| `max_bytes_per_upload` | unlimited | Per ingest call |
| `max_bytes_per_file` | unlimited | Per file |
| `max_documents_per_index` | unlimited | Cumulative |
| `max_chunks_per_index` | unlimited | Cumulative |
| `max_chars_per_index` | unlimited | Cumulative |

### `ingest/ingest.py` — Quota enforcement (+14 lines)
- `run_ingest()` checks quotas before entering the file processing loop
- Rejects with `RuntimeError` before any expensive chunking/embedding/upsert
- Covers both direct directory ingest and staged connector ingest

### `ingest/cli/quota.py` — CLI commands (new, 151 lines)
- `kb-rag quota show` — limits + usage in human-readable tables
- `kb-rag quota set [--max-* N]` — set any quota field (omit = unchanged)
- `kb-rag quota reset` — zero usage counters (with `y/N` confirmation)

## Verification

| Suite | Result |
|---|---|
| `test_quotas.py` | 21/21 passed |
| `test_ingest_registry.py` | 10/10 passed (existing migration tests) |
| Full suite | 999 passed, 2 pre-existing failures |
