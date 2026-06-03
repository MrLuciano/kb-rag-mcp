# Phase 36: Provider Budget & Circuit Breaker

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** Medium
**Code:** PROVBUD-01
**Competitive Reference:** [kalicyh/mcp-rag](https://github.com/kalicyh/mcp-rag) — provider budget and circuit breaker
**Promoted from:** `.planning/ROADMAP.md` Backlog (Medium Priority)

## Objective

Implement per-provider request budgets, consecutive failure thresholds, cooldown periods, and automatic fallback to alternative provider on failure. Protects against cascading failures and enables resilient multi-provider configurations.

## Expected Deliverables

- Provider budget tracking (request count, token count per window)
- Circuit breaker states: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing)
- Automatic fallback chain (primary → secondary → tertiary)
- Configurable thresholds: budget limit, failure count, cooldown seconds
- Prometheus metrics: `provider_requests_total`, `provider_errors_total`, `provider_circuit_state`
- Environment variable configuration (no new env vars if possible, reuse existing)

## Circuit Breaker State Machine

```
CLOSED (normal):
  - Request goes through
  - On failure: increment failure counter
  - If failures >= threshold: transition to OPEN

OPEN (failing):
  - Reject requests immediately (fast fail)
  - After cooldown: transition to HALF_OPEN

HALF_OPEN (testing):
  - Allow 1 request through to test
  - If success: transition to CLOSED
  - If failure: transition to OPEN (extend cooldown)
```

## Key Design Decisions

- **Per-provider state:** Circuit breaker and budget state stored per provider (not global)
- **Budget window:** Sliding window (last N minutes) for budget enforcement
- **Fallback chain:** Configurable list of providers in priority order (e.g., `EMBED_BACKEND=lmstudio;ollama;openai-compat`)
- **Cooldown:** Exponential backoff on repeated failures (start at 30s, double each time, max 5 min)
- **Circuit reset:** Budget resets after window expires (sliding window)
- **Integration:** Works with existing `EmbedClient` multi-backend support

## Implementation Scope

1. Circuit breaker class in `kb_server/circuit_breaker.py`
2. Provider budget tracker in `kb_server/provider_budget.py`
3. Integration into `EmbedClient` (wrap each backend call with circuit breaker check)
4. Add to `embed_client.py` — intercept calls, check circuit state, apply fallback
5. Prometheus metrics for circuit state transitions and budget usage
6. Config via env vars: `CIRCUIT_BREAKER_THRESHOLD=5`, `CIRCUIT_BREAKER_COOLDOWN=30`

## Open Questions

1. Should circuit state be persisted (survive server restart)?
2. Do we apply circuit breaker to LLM calls too (not just embeddings)?
3. How to handle budget across multiple concurrent requests (atomic decrement)?

## See Also

- `kalicyh/mcp-rag` provider budget implementation (GitHub: kalicyh/mcp-rag)
- `kb_server/embed_client.py` — existing multi-backend support
- `observability/metrics.py` — existing Prometheus metrics pattern