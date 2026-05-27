---
phase: 16-reclassification-ingested-docs
plan: 02
subsystem: cli
tags: [reclassification, click-cli, rich-ui, rollback]

requires:
  - phase: 16
    provides: reclassify_engine functions from Wave 1

provides:
  - kb-ingest reclassify command group with 4 subcommands
  - Aggregated preview by field with Rich tables
  - Interactive confirmation with --yes bypass
  - Rich progress bars with --no-progress bypass
  - Filter expression parser for metadata queries
  - Session-based and selective rollback support

affects: [17-documentation, cli-interfaces]

tech-stack:
  added: []
  patterns: [click-subcommands, rich-tables, rich-progress, async-cli-handlers]

key-files:
  created: [ingest/cli/reclassify.py, tests/test_cli_reclassify.py]
  modified: [ingest/cli/main.py]

key-decisions:
  - "Click-based CLI (not Typer) to match existing ingest/cli/main.py patterns"
  - "Async implementation functions (_reclassify_impl, etc.) for VectorStore/Qdrant calls"
  - "Aggregated preview for reclassify (by field) vs per-document table for verify"
  - "Filter parser supports quoted and unquoted values: field=\"value\" or field=value"
  - "Rollback validates argument mutual exclusivity (--session XOR pattern+--before)"
  - "_apply_rollback uses default collection from env (no --collection flag for rollback yet)"

patterns-established:
  - "CLI async handlers: sync Click command → asyncio.run(async_impl())"
  - "Rich console output: tables for data, colored messages for status"
  - "Confirmation prompt pattern: console.input() with [y/N] default"
  - "Progress bar disabled via --no-progress for scripting"

requirements-completed: [RECLASSIFY-04, RECLASSIFY-05, RECLASSIFY-06]

duration: 2h 30min
completed: 2026-05-27
---

# Phase 16 Plan 02: CLI Commands - Reclassify, Verify, Rollback, Sessions Summary

**Complete: 4 CLI subcommands implemented with 18 passing tests**

## Performance

- **Duration:** 2h 30min
- **Started:** 2026-05-27T03:15:00Z
- **Completed:** 2026-05-27T05:45:00Z
- **Tasks:** 6 of 6 completed (100%)
- **Files modified:** 1 (ingest/cli/main.py)
- **Files created:** 2 (ingest/cli/reclassify.py, tests/test_cli_reclassify.py)
- **Tests:** 18 passing (all new CLI tests)

## Accomplishments

- **Step 1 Complete**: CLI module structure
  - Created ingest/cli/reclassify.py with 4 subcommands (run, verify, sessions, rollback)
  - Registered reclassify_group in main CLI with Click
  - All flags implemented: --collection, --filter, --yes, --allow-missing, --include-custom, --no-progress
  - 6 tests for command registration and flag presence

- **Step 2 Complete**: Reclassify run command
  - 7-step workflow: detect → preview → confirm → backup → update → log → cleanup
  - Aggregated preview with Rich table showing field-level changes
  - Interactive confirmation prompt (--yes to skip)
  - Filter expression parser with quoted/unquoted value support
  - Rich progress bar during updates (--no-progress to disable)
  - CollectionRouter integration for collection resolution
  - 5 tests for filter parsing and preview rendering

- **Step 3 Complete**: Verify command
  - Per-document mismatch table showing current vs expected metadata
  - Uses detect_changed_classifications with allow_missing=False
  - Displays hint to run reclassify command
  - 2 tests for verify output (no mismatches, with mismatches)

- **Step 4 Complete**: Sessions command
  - Lists all backup sessions from reclassify_backups table
  - Shows session timestamp, document count, field count
  - Human-readable date formatting
  - Displays tip for rollback command
  - 2 tests for sessions list (empty, with sessions)

- **Step 5 Complete**: Rollback command
  - Session-based rollback: --session flag restores entire session
  - Selective rollback: pattern + --before flag restores specific documents
  - Argument validation with mutual exclusivity checks
  - Confirmation prompt with preview (--yes to skip)
  - _apply_rollback helper updates Qdrant metadata
  - Logs rollback to reclassify_history audit table
  - 3 tests for rollback (validation, not found, restore)

- **Step 6 Complete**: Integration testing
  - All 18 CLI tests passing
  - All 15 Wave 1 tests passing (33 total reclassification tests)
  - No regressions in test suite
  - Commands work together in realistic workflows

## Task Commits

1. **Step 1**: CLI module structure - `d7e4a2a` (feat)
2. **Step 2**: Reclassify run command - `0298e8a` (feat)
3. **Step 3**: Verify command - `b78877a` (feat)
4. **Step 4**: Sessions command - `6174947` (feat)
5. **Step 5**: Rollback command - `6fb69d5` (feat)
6. **Step 6**: Integration testing - (no new commit, all tests passing)

## Files Created/Modified

- `ingest/cli/reclassify.py` - NEW: 4 subcommands (run, verify, sessions, rollback) with async implementations, Rich UI components
- `ingest/cli/main.py` - Modified: registered reclassify_group
- `tests/test_cli_reclassify.py` - NEW: 18 unit tests for CLI commands

## Decisions Made

- **Click vs Typer**: Used Click to match existing ingest/cli/main.py patterns (main.py is Click-based, not Typer)
- **Async handlers**: Sync Click commands call `asyncio.run(async_impl())` for VectorStore/Qdrant operations
- **Aggregated vs detailed**: Reclassify shows aggregated summary by field (compact), verify shows per-document table (detailed)
- **Filter parser**: Simple regex-based parser supports `field="value"` and `field=value` syntax
- **Rollback validation**: Enforced mutual exclusivity: `--session` cannot be combined with `pattern` or `--before`
- **Default collection**: _apply_rollback uses default collection from env (no --collection flag for rollback yet)

## Deviations from Plan

None - All 6 steps executed as specified in PLAN.md.

## Issues Encountered

- **CollectionRouter mocking**: Initial tests failed because CollectionRouter is imported inside function. Fixed by patching `kb_server.collections.router.CollectionRouter` instead of `ingest.cli.reclassify.CollectionRouter`.

## Blockers

None - Plan 16-02 complete and ready for documentation (Plan 16-03).

## Next Phase Readiness

**READY**: Plan 16-02 is 100% complete (6 of 6 steps). All requirements met:
- ✅ kb-ingest reclassify run command with preview and confirmation
- ✅ kb-ingest reclassify verify command showing mismatches
- ✅ kb-ingest reclassify sessions listing backup sessions
- ✅ kb-ingest reclassify rollback with session-based and selective modes
- ✅ All flags implemented and tested
- ✅ Rich preview with aggregated summary by field
- ✅ Rich progress bar during updates
- ✅ 18 tests passing

Plan 16-03 (Documentation) can now proceed to document the CLI commands in README.md and OPERATIONS.md.

---
*Phase: 16-reclassification-ingested-docs*
*Completed: 2026-05-27*
*STATUS: ✅ COMPLETE - 6 of 6 steps complete, 18 tests passing*
