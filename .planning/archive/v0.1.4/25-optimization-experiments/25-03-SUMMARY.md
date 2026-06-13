---
phase: 25-optimization-experiments
plan: 03
subsystem: optimization
tags: [scoring, reranking, hybrid-search, dense-only, cross-encoder, ir-metrics]

requires:
  - phase: 25-optimization-experiments
    provides: ExperimentConfig, MetricComputer, GoldenDataset patterns

provides:
  - ScoringVariant abstract base class with three concrete implementations
  - DenseOnlyVariant with configurable distance metric (COSINE, DOT, EUCLID, MANHATTAN)
  - HybridVariant with dense_weight, sparse_weight, rrf_k overrides
  - RerankedVariant with cross-encoder reranking and warmup
  - ScoringEngine.run_experiment() for query-time evaluation against indexed collections
  - create_variant() factory for dense_only, hybrid, reranked
  - DISTANCE_METRICS lazy mapping to qdrant_client.models.Distance
  - 15 passing unit tests for all variants and engine

affects:
  - 25-optimization-experiments
  - 25-04

tech-stack:
  added: []
  patterns:
    - "Strategy pattern: ScoringVariant ABC with swappable search implementations"
    - "Lazy qdrant enum loading to avoid module-level heavy imports"
    - "Mock-isolated tests: no external services (Qdrant, LM Studio, sentence-transformers)"

key-files:
  created:
    - tests/test_scoring_experiments.py
  modified:
    - kb_server/optimization/scoring_experiments.py

key-decisions:
  - "HybridVariant temporarily overrides global HybridSearcher weights in search() and restores them in finally block"
  - "RerankedVariant uses get_reranker() global instance and calls _load_model() for warmup to avoid non-deterministic first-run scores"
  - "DISTANCE_METRICS uses lazy _init_distance_metrics() with dict.update() to support both direct import and module reference access"
  - "ScoringEngine does NOT re-ingest; it assumes caller manages collection lifecycle"

patterns-established:
  - "ScoringVariant strategy pattern for swappable search implementations"
  - "Lazy enum loading for heavy dependencies (qdrant_client.models.Distance)"
  - "Graceful degradation in RerankedVariant: returns base results if reranking fails"

requirements-completed:
  - OPT-02

duration: 1min
completed: 2026-06-11
---

# Phase 25 Plan 03: Scoring Experiments Summary

**Scoring and reranking experiment variants with configurable distance metrics, hybrid weights, and cross-encoder reranking A/B comparison.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-06-11T14:50:30Z
- **Completed:** 2026-06-11T14:51:38Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- ScoringVariant abstract base class with DenseOnlyVariant, HybridVariant, RerankedVariant
- ScoringEngine.run_experiment() evaluates retrieval quality against existing indexed collections
- create_variant() factory supports "dense_only", "hybrid", "reranked" with base chaining
- DISTANCE_METRICS lazy mapping to qdrant_client.models.Distance (COSINE, DOT, EUCLID, MANHATTAN)
- 15 passing unit tests covering all variants, factory, engine, and distance metrics
- All tests run without external services (mock-isolated)

## Task Commits

1. **Task 1: Implement scoring variants and ScoringEngine** — `0ae08d0` (feat)
2. **Task 2: Add unit tests for scoring variants** — `3fce64e` (test)

## Files Created/Modified

- `kb_server/optimization/scoring_experiments.py` — ScoringVariant, DenseOnlyVariant, HybridVariant, RerankedVariant, ScoringEngine, create_variant, DISTANCE_METRICS
- `tests/test_scoring_experiments.py` — 15 unit tests for all variants and engine

## Decisions Made

- HybridVariant temporarily overrides global HybridSearcher weights during search() and restores them in a finally block, avoiding global state pollution
- RerankedVariant uses get_reranker() global instance and calls _load_model() for warmup to ensure deterministic scores (per RESEARCH.md Pitfall 3)
- DISTANCE_METRICS uses lazy _init_distance_metrics() with dict.update() instead of reassignment, so both `from module import` and `module.DICT` access patterns work
- ScoringEngine does NOT re-ingest or create collections; it assumes caller manages collection lifecycle

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All verification checks passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Scoring experiments complete and ready for Plan 25-04 (CLI integration and experiment orchestration)
- ScoringEngine.run_experiment() can be called directly by experiment runners
- All 15 tests pass, flake8 clean

## Self-Check: PASSED

- All key files exist on disk
- Both task commits (0ae08d0, 3fce64e) exist in git history
- 15/15 tests pass
- flake8 reports zero errors on all new files
- scoring_experiments module imports without errors

---
*Phase: 25-optimization-experiments*
*Completed: 2026-06-11*
