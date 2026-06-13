# Phase 33: Request Rate Limiting

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** Medium
**Code:** RATE-01
**Competitive Reference:** [kalicyh/mcp-rag](https://github.com/kalicyh/mcp-rag) — request rate limiting
**Promoted from:** `.planning/ROADMAP.md` Backlog (Medium Priority)

## Objective

Implement token bucket rate limiting per subject (API key, IP address). Protects against accidental or intentional abuse — limits how many requests can hit the server in a given time window.

## Expected Deliverables

- Token bucket algorithm implementation
- Rate limit per API key (from AUTH-01) and per IP address
- Configurable limits: `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`
- HTTP 429 response when limit exceeded with `Retry-After` header
- Prometheus metrics: `rate_limit_exceeded_total`, `rate_limit_remaining`
- Optional: per-endpoint rate limits (ingest vs search vs admin)

## Key Design Decisions

- **Algorithm:** Token bucket (allows burst) vs sliding window (smoother). Token bucket is simpler.
- **Storage:** In-memory dict (ephemeral, resets on restart) — adequate for single-instance
- **Scope:** Applies to HTTP transports only (stdio doesn't expose network endpoints)
- **Response:** Return HTTP 429 with JSON error body and `Retry-After` seconds header
- **Config:** Env vars `RATE_LIMIT_REQUESTS` (default 100), `RATE_LIMIT_WINDOW` (default 60 seconds)

## Implementation Scope

1. Token bucket class in `kb_server/rate_limiter.py`
2. Middleware in `server.py` that checks rate limit before processing HTTP requests
3. Middleware runs after auth (if AUTH-01 is implemented) so key is available for per-key limits
4. Prometheus counter and gauge for monitoring
5. Optional per-IP limits when no API key present

## Open Questions

1. Should rate limits be configurable per KB (tenant-level)?
2. Do we need Redis-backed distributed rate limiting for multi-instance deployments?
3. Should ingest vs search have different limits?

## See Also

- `kalicyh/mcp-rag` rate limiting (GitHub: kalicyh/mcp-rag)
- `kb_server/server.py` — HTTP middleware pattern
- `observability/metrics.py` — existing Prometheus metrics