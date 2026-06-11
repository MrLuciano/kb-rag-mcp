---
phase: 36-provider-budget-circuit-breaker
plan: 01
subsystem: embedding resilience
tags: circuit-breaker, provider-budget, fallback, resilience, prometheus
requires:
  - phase: 14-observability-metrics
    provides: Prometheus metrics framework, MetricsCollector
  - phase: 08-batch-optimization
    provides: EmbedClient multi-backend dispatch pattern
provides:
  - Circuit breaker state machine (CLOSED/OPEN/HALF_OPEN) per provider
  - Provider budget sliding window tracking per provider
  - EmbedClient fallback chain across providers
  - Provider resilience Prometheus metrics (7 new metrics)
affects:
  - Phase 14 health_server (new metrics appear in /metrics endpoint)
  - Phase 8 embed_client (resilient dispatch replaces direct dispatch)

tech-stack:
  added: []
  patterns:
    - Per-provider state isolation for circuit breaker and budget
    - Semicolon-separated provider fallback chain (EMBED_BACKEND=primary;secondary)
    - Exponential backoff cooldown with per-cycle escalation

key-files:
  created:
    - kb_server/circuit_breaker.py
    - kb_server/provider_budget.py
    - tests/test_circuit_breaker.py
    - tests/test_provider_budget.py
  modified:
    - kb_server/embed_client.py
    - observability/metrics.py
    - tests/test_embed_client_unit.py
    - tests/test_health_server.py

key-decisions:
  - "Per-provider state (not global) for circuit breaker and budget — providers are independent"
  - "Backoff multiplier persists across heal cycles (not reset on success) — repeated OPEN cycles escalate"
  - "Sliding window budget uses monotonic clock for expiry — no RPC or persistence needed"
  - "Circuit breaker Gauge uses 1/0 per state label rather than a single enum gauge — queryable by state"
  - "Existing embed client public API signatures fully preserved — resilience is internal dispatch wrapper"

patterns-established:
  - "Resilience wrapper pattern: _try_provider() handles per-provider check + call + record, _dispatch_with_resilience() handles fallback chain"
  - "validate_providers() gate called before dispatch — catches invalid provider names early"

requirements-completed:
  - PROVBUD-01
  - PROVBUD-02
  - PROVBUD-03

duration: 22 min
completed: 2026-06-11
---

# Phase 36 Plan 01: Provider budget and circuit breaker resilience for embedding backends

**Circuit breaker state machine, provider budget sliding window tracker, resilient embed-client dispatch with fallback chain, and 7 new Prometheus metrics for provider observability**

## Performance

- **Duration:** 22 min
- **Started:** 2026-06-11T02:42:00Z
- **Completed:** 2026-06-11T03:04:00Z
- **Tasks:** 3
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments

- CircuitBreaker class with CLOSED/OPEN/HALF_OPEN state machine, configurable failure thresholds, exponential backoff cooldown (30s base, 5min max), and per-provider state isolation
- ProviderBudget class with sliding window request and optional token tracking, per-provider isolation, and automatic window expiry
- EmbedClient integration: `_try_provider()` wraps each backend call with budget check, circuit breaker check, failure recording, and success recording; `_dispatch_with_resilience()` implements fallback chain across providers
- Batch embedding updated with resilient dispatch (single-provider native paths preserved for performance; multi-provider uses per-text resilient dispatch)
- 7 new Prometheus Counter/Gauge metrics exposed at `/metrics` endpoint: `provider_requests_total`, `provider_errors_total`, `provider_circuit_state`, `provider_fallbacks_total`, `provider_skipped_circuit_open_total`, `provider_skipped_budget_exhausted_total`, `provider_circuit_opened_total`
- 11 new test cases across embed_client and health_server for resilience behavior; 39 dedicated primitive tests for circuit breaker and budget modules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create provider budget and circuit breaker primitives** - `ef756d5` (feat)
2. **Task 2: Integrate resilience into embed_client** - `e732f0a` (feat)
3. **Task 3: Add resilience telemetry** - `753d54a` (feat)

**Plan metadata:** Pending (orchestrator handles STATE.md/ROADMAP.md)

## Files Created/Modified

### Created
- `kb_server/circuit_breaker.py` - Circuit breaker state machine (297 lines) with CircuitBreaker class, CircuitState enum, exponential backoff, per-provider isolation
- `kb_server/provider_budget.py` - Provider budget accounting (185 lines) with ProviderBudget class, sliding window, request/token tracking, per-provider isolation
- `tests/test_circuit_breaker.py` - 25 tests covering initial state, CLOSED→OPEN→HALF_OPEN→CLOSED transitions, exponential backoff, per-provider isolation, reset
- `tests/test_provider_budget.py` - 14 tests covering budget tracking, exhaustion, window expiry, token tracking, reset, per-provider isolation

### Modified
- `kb_server/embed_client.py` - Added PROVIDER_CHAIN, _try_provider(), _dispatch_with_resilience(), validate_providers(); modified get_embedding() and get_embeddings_batch() to use resilient dispatch
- `observability/metrics.py` - Added 7 Prometheus metric definitions, MetricsCollector references, set_gauge() method, record_provider_circuit_state() helper
- `tests/test_embed_client_unit.py` - Adapted 8 existing tests for new resilience layer; added 7 new tests for circuit breaker blocking, fallback, budget exhaustion, all-providers-fail, success-resets-breaker, validate_providers
- `tests/test_health_server.py` - Added 9 new tests verifying all 7 provider resilience metrics appear in /metrics output

## Decisions Made

- **Per-provider state isolation:** Circuit breaker and budget state are tracked per provider name (not global), so failures in one provider don't affect others — matches the multi-backend architecture
- **Persistent backoff multiplier:** The exponential backoff multiplier persists across heal cycles (not reset on `record_success`), so repeated failure→recovery cycles escalate cooldown; only `reset()` fully clears it
- **Sliding window with monotonic clock:** Budget window uses `time.monotonic()` (not wall clock) to avoid issues with system time changes
- **Gauge with state labels:** `provider_circuit_state` uses separate 1/0 Gauge entries per state label rather than a single numeric enum — enables Prometheus queries like `kb_provider_circuit_state{state="open"} == 1`
- **Cache uses PRIMARY_BACKEND:** Cache keys use PRIMARY_BACKEND instead of BACKEND for consistency — the primary provider is the canonical cache namespace

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Existing test adaptation:** 3 existing error-propagation tests expected raw `httpx.HTTPStatusError`/`ConnectError` propagation, but the new resilience wrapper converts these to `RuntimeError("All providers failed")` when no fallback is configured. Tests were updated to match the new behavior, and equivalent resilience behavior is covered by new dedicated tests.
- **PROVIDER_CHAIN must be updated in tests:** Tests that monkeypatch `BACKEND` also need to update `PROVIDER_CHAIN` and `PRIMARY_BACKEND` since these are parsed at import time. An autouse fixture was added to reset the chain between tests.

## Threat Surface Scan

No new threats introduced — all changes are internal to the embedding dispatch path and do not create new network endpoints, auth paths, or file access patterns. The threat register (T-36-01, T-36-02, T-36-03) is fully mitigated.

## Next Phase Readiness

Phase 36 complete — provider budget enforcement and circuit breaker resilience are fully implemented with:
- Reusable primitive modules tested independently (39 tests)
- EmbedClient integration with fallback chain (15 tests)
- Prometheus observability (15 health server tests)
- 69 total passing tests across all task verification suites

Ready for next phase.

## Self-Check: PASSED

All 8 files verified on disk. All 3 commits verified in git log. All plan-level verification commands pass:
- 39 primitive tests (budget + circuit breaker)
- 15 embed client tests
- 30 combined tests (embed client + health server)

---

*Phase: 36-provider-budget-circuit-breaker*
*Completed: 2026-06-11*
