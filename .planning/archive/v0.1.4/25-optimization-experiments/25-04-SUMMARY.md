---
phase: 25-optimization-experiments
plan: 04
subsystem: optimization
tags: [experiment-runner, cli, parameter-sweep, compare, chunking, scoring]

requires:
  - phase: 25-optimization-experiments
    provides: ChunkingEngine, ScoringEngine, MetricComputer, ExperimentResultStore

provides:
  - ExperimentRunner class for orchestrating chunking and scoring experiments
  - `kb-rag optimize` CLI with chunk, scoring, compare, list subcommands
  - Parameter sweep over all combinations via itertools.product
  - Auto-save baseline on first parameter sweep run
  - Formatted console comparison tables via ResultsExporter
  - 15 passing integration tests for runner and CLI

affects:
  - 25-optimization-experiments

tech-stack:
  added: []
  patterns:
    - "ExperimentRunner orchestrates ChunkingEngine and ScoringEngine"
    - "Standalone convenience functions for programmatic usage"
    - "Click CLI group with subcommands following evaluate.py pattern"
    - "Auto-save baseline on first parameter sweep run"

key-files:
  created:
    - kb_server/optimization/experiment_runner.py
    - ingest/cli/optimize.py
  modified:
    - ingest/cli/main.py
    - tests/test_optimization.py

key-decisions:
  - "ExperimentRunner accepts VectorStore and GoldenDataset as constructor args (does not create them)"
  - "Standalone convenience functions create runner and run one experiment for simpler programmatic usage"
  - "CLI commands create VectorStore and connect to Qdrant with graceful warning on failure"
  - "Parameter sweep auto-saves baseline only if no baseline exists yet"
  - "Compare command delegates to ExperimentResultStore.compare and adds ResultsExporter.to_console formatted table"

patterns-established:
  - "Async experiment runner pattern: runner.run_* -> engine.run_experiment -> store.save"
  - "Click CLI pattern matching evaluate.py: load dataset, validate, run, display, export"
  - "Mock-isolated CLI tests using click.testing.CliRunner with tmp_path fixture for real files"

requirements-completed:
  - OPT-01
  - OPT-02
  - OPT-03

duration: 4min
completed: 2026-06-11
---

# Phase 25 Plan 04: Experiment Orchestrator and Optimize CLI Summary

**Experiment orchestration layer and `kb-rag optimize` CLI tying chunking experiments, scoring experiments, and result comparison into a single user-facing workflow with 15 integration tests.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-11T15:14:44Z
- **Completed:** 2026-06-11T15:19:24Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- ExperimentRunner class with run_chunking_experiment, run_scoring_experiment, run_parameter_sweep, compare_runs, list_runs
- Standalone convenience functions run_chunking_experiment and run_scoring_experiment
- `kb-rag optimize` CLI group with chunk, scoring, compare, list subcommands
- Parameter sweep generates all combinations via itertools.product and auto-saves baseline
- Compare command produces formatted console tables via ResultsExporter.to_console
- 15 passing integration tests covering runner, parameter sweep, CLI, and standalone functions
- All tests mock external services (no Qdrant or LM Studio needed)

## Task Commits

1. **Task 1: Create experiment_runner.py and optimize CLI** — `7341950` (feat)
2. **Task 2: Update test_optimization.py with integration tests** — `9babf41` (test)

## Files Created/Modified

- `kb_server/optimization/experiment_runner.py` — ExperimentRunner class and standalone convenience functions
- `ingest/cli/optimize.py` — `kb-rag optimize` CLI with chunk, scoring, compare, list subcommands
- `ingest/cli/main.py` — Registered `cli.add_command(optimize, name="optimize")`
- `tests/test_optimization.py` — 15 integration tests (replaced old NotImplementedError stub tests)

## Decisions Made

- ExperimentRunner accepts VectorStore and GoldenDataset as constructor args rather than creating them internally, keeping the runner decoupled from connection logic
- Standalone convenience functions create a runner and run one experiment for simpler programmatic API
- CLI commands create VectorStore and attempt to connect, but warn gracefully on failure so the command can still run in test environments
- Parameter sweep auto-saves baseline only if no baseline exists yet, avoiding overwriting an existing baseline
- Compare command delegates to ExperimentResultStore.compare and adds a formatted console table string via ResultsExporter.to_console

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-existing test failures in `tests/test_cli_reclassify.py` (2 failures) — unrelated to this plan; confirmed pre-existing from prior phases
- No new issues introduced

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 4 plans in Phase 25 complete (25-01, 25-02, 25-03, 25-04)
- Phase 25 ready for completion and verification
- `kb-rag optimize` CLI is fully functional with all subcommands

## Self-Check: PASSED

- All 4 key files exist on disk
- Both task commits (7341950, 9babf41) exist in git history
- 15/15 tests in test_optimization.py pass
- 56/56 optimization tests pass together
- flake8 reports zero errors on all new/modified files
- All imports succeed without errors
- CLI help displays correctly for all subcommands

---
*Phase: 25-optimization-experiments*
*Completed: 2026-06-11*
