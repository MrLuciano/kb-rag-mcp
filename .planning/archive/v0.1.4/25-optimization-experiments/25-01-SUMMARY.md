---
phase: 25-optimization-experiments
plan: 01
subsystem: optimization
tags: [experiments, ir-metrics, chunking, scoring, recall, mrr, ndcg]

requires:
  - phase: 24-ragas-evaluation
    provides: GoldenDataset, RAGASEvaluator, ResultsExporter patterns

provides:
  - ExperimentConfig dataclass with OPT_ env var overrides
  - CHUNK_STRATEGIES (fixed, recursive, semantic) with lazy imports
  - SCORING_VARIANTS (dense_only, hybrid_default, hybrid_dense_heavy, sparse_heavy)
  - MetricComputer with recall@k, MRR, NDCG, compute_all
  - ExperimentResultStore with JSON persistence and CSV export
  - 12 passing unit tests for metric computation

affects:
  - 25-optimization-experiments
  - 25-02
  - 25-03
  - 25-04

tech-stack:
  added: []
  patterns:
    - "Pure-Python IR metrics (no LLM-as-judge) for deterministic evaluation"
    - "Lazy-import chunking strategies to avoid startup dependency failures"
    - "ExperimentResultStore JSON persistence with CSV export for comparison"

key-files:
  created:
    - kb_server/optimization/config.py
    - kb_server/optimization/metric_computer.py
    - kb_server/optimization/result_store.py
    - tests/test_metric_computer.py
  modified:
    - pyproject.toml (added PHASE25 pytest marker)

key-decisions:
  - "Use sklearn.metrics.ndcg_score instead of manual NDCG implementation"
  - "Binary relevance (1/0) for NDCG gains to keep metrics deterministic"
  - "Standalone module-level metric functions + MetricComputer class for flexibility"
  - "Lazy-import docling and langchain_text_splitters in chunking strategies"
  - "ExperimentResultStore uses JSON per-run files (not SQLite) for simplicity"

patterns-established:
  - "Pure-Python IR metrics: no external services needed for metric computation"
  - "Experiment parameter validation: validate_experiment_params returns list of errors"
  - "Lazy chunking strategy imports: fall back gracefully if optional deps missing"

requirements-completed:
  - OPT-01
  - OPT-02
  - OPT-03

duration: 2min
completed: 2026-06-11
---

# Phase 25 Plan 01: Optimization Infrastructure Summary

**Core infrastructure for RAG optimization experiments: centralized config, deterministic IR metrics (recall@K, MRR, NDCG), and result persistence with comparison support.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-11T14:45:55Z
- **Completed:** 2026-06-11T14:48:18Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- ExperimentConfig dataclass with all defaults overridable via `OPT_` env vars
- CHUNK_STRATEGIES mapping (fixed, recursive, semantic) with lazy imports and fallback
- SCORING_VARIANTS mapping (dense_only, hybrid_default, hybrid_dense_heavy, sparse_heavy)
- validate_experiment_params function with chunk_size, overlap, and weight validation
- MetricComputer class with recall_at_k, mean_reciprocal_rank, ndcg_at_k, compute_all
- Standalone module-level metric functions for direct testability
- ExperimentResultStore with save, load, list_runs, compare, to_csv, baseline methods
- 12 passing unit tests covering all metric functions and edge cases
- pytest PHASE25 marker registered in pyproject.toml

## Task Commits

1. **Task 1: Create config.py and metric_computer.py** — `b44544f` (feat)
2. **Task 2: Create result_store.py and test_metric_computer.py** — `735692e` (feat)

## Files Created/Modified

- `kb_server/optimization/config.py` — ExperimentConfig, CHUNK_STRATEGIES, SCORING_VARIANTS, validation
- `kb_server/optimization/metric_computer.py` — MetricComputer class and standalone metric functions
- `kb_server/optimization/result_store.py` — ExperimentResultStore with JSON/CSV persistence
- `tests/test_metric_computer.py` — 12 unit tests for recall@K, MRR, NDCG, compute_all
- `pyproject.toml` — Added `PHASE25` pytest marker

## Decisions Made

- Used `sklearn.metrics.ndcg_score` for NDCG (well-tested, handles edge cases) instead of manual implementation
- Binary relevance (1/0) for NDCG gains to keep metrics deterministic and simple
- Provided both standalone functions and MetricComputer class for caller flexibility
- Lazy-import strategy for chunking dependencies (docling, langchain) to avoid import failures at module load time
- JSON per-run files for result storage (human-readable, simple) rather than SQLite

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All verification checks passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Infrastructure complete and ready for Plan 25-02 (chunking experiments)
- MetricComputer.compute_all can be used directly by experiment runners
- ExperimentResultStore can persist and compare experiment runs
- All 12 tests pass, flake8 clean

## Self-Check: PASSED

- All 5 key files exist on disk
- Both task commits (b44544f, 735692e) exist in git history
- 12/12 tests pass
- flake8 reports zero errors on all new files
- All three optimization modules importable without errors

---
*Phase: 25-optimization-experiments*
*Completed: 2026-06-11*
