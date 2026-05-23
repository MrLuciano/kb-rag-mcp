---
phase: 08-ingest-improvements-documentation
plan: 02
subsystem: CLI, Ingest Registry
tags: [status, cli, ingest, registry, rich]
requires: [08-01]
provides: [INGEST-02]
affects: [ingest/core/metadata.py, ingest/cli/main.py]
tech-stack:
  added: [rich.table, rich.panel, click.group]
  patterns: [Click subcommand group, Rich table with Panel, per-source SQL aggregation]
key-files:
  created:
    - ingest/cli/status.py — Click command group with `status` subcommand; Rich table output
    - tests/test_status_cli.py — 4 test cases for empty DB, data accuracy, CLI help, source filtering
  modified:
    - ingest/core/metadata.py — Added `per_source_summary()` method to `IngestRegistry`
    - ingest/cli/main.py — Imported and registered `status_group`
decisions: []
metrics:
  duration: "~30 min"
  completed_date: "2026-05-23"
---

# Phase 8 Plan 2: Ingest Status CLI Summary

**One-liner:** Add `kb-ingest status` CLI command with per-source directory breakdown via `IngestRegistry.per_source_summary()` and Rich table output.

Fulfills requirement **INGEST-02**: operators can query ingest status at a glance without inspecting SQLite directly.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add `per_source_summary()` to IngestRegistry | `bf42179` | `ingest/core/metadata.py` |
| 2 | Create `ingest/cli/status.py` with Rich table | `9f03bd4` | `ingest/cli/status.py` |
| 3 | Register status command and add tests | `53b624a` | `ingest/cli/main.py`, `tests/test_status_cli.py` |

## Implementation Details

### Task 1 — per_source_summary()

- Added `IngestRegistry.per_source_summary() → list[dict]` to `ingest/core/metadata.py`
- SQL query groups the `files` table by source directory (first path component before `/`), files at root grouped under `"(root)"`
- Returns list of dicts with keys: `source`, `files`, `ok`, `errors`, `chunks`, `last_indexed`
- Parameterized SQL with no string interpolation (per threat model T-08-03)
- Logs result count at DEBUG level

### Task 2 — status.py

- New Click command group `status_group(name="status")` in `ingest/cli/status.py`
- `status` subcommand with `--source` option (case-insensitive partial match filtering)
- Rich `Table` with columns: Source, Files, Chunks, Errors, Last Ingest
  - Unix timestamps formatted as `"%Y-%m-%d %H:%M"` or `"—"` if `None`
- TOTAL row with aggregate sums (dim style)
- Wrapped in green-bordered `Panel` ("Ingest Status")
- Graceful handling: empty DB shows "No ingest data found."

### Task 3 — Registration + Tests

- Registered `status_group` in `ingest/cli/main.py` (import + `cli.add_command`)
- Four tests in `tests/test_status_cli.py`:
  1. `test_per_source_summary_empty` — empty DB returns `[]`
  2. `test_per_source_summary_with_data` — 2 files ok + 1 error verifies counts
  3. `test_status_cli_invocation` — `--help` shows "Show ingest status"
  4. `test_status_with_source_filter` — filtering by source returns only matching rows

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

```
tests/test_status_cli.py::TestStatusCommand::test_per_source_summary_empty  PASSED
tests/test_status_cli.py::TestStatusCommand::test_per_source_summary_with_data  PASSED
tests/test_status_cli.py::TestStatusCommand::test_status_cli_invocation  PASSED
tests/test_status_cli.py::TestStatusCommand::test_status_with_source_filter  PASSED
```

Full regression suite: 534 passed, 5 skipped (pre-existing skip in 3 test files). No regressions.

## Pre-existing Test Failures (not caused by this plan)

- `tests/test_sse_handler.py::test_handle_sse_returns_response` — `AttributeError: 'SseServerTransport' object has no attribute 'handle_post_message'` (starlette API change, unrelated)

## Self-Check

✅ `IngestRegistry.per_source_summary()` returns per-source breakdown with correct file, error, and chunk counts.
✅ `kb-ingest status` displays Rich table with Source, Files, Chunks, Errors, Last Ingest columns.
✅ `kb-ingest status --source <name>` filters by source.
✅ Empty databases produce "No ingest data found." without crash.
✅ 4 test cases in `tests/test_status_cli.py` all pass.
✅ Full test suite (excluding pre-existing SSE failure): 534 passed.
