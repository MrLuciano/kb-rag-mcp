# Phase 33 SUMMARY: Request Rate Limiting

**Date:** 2026-06-10
**Type:** execute
**Status:** Complete

## Changes Made

### `kb_server/rate_limiter.py` — Server-rate limiter (new, 106 lines)
- `ServerRateLimiter` — per-subject (API key prefix, IP, "stdio") token bucket
- Wraps existing `ingest/worker/limiter.RateLimiter` (no duplicate algorithm)
- `check(subject) → (allowed, retry_after)` — non-blocking rejection path
- Auto-creates limiters on first access; periodic idle-subject sweep

### `kb_server/server.py` — Two-layer enforcement (+135 lines)
- **SSE connection level**: Rejects with HTTP 429 + `Retry-After` header (after auth)
- **Tool call level**: Returns structured error `TextContent` for both SSE and stdio
- `contextvars` (`_current_subject`, `_current_transport`) for per-connection tracking
- Config: `RATE_LIMIT_ENABLED` (default false, backward-compatible), `RATE_LIMIT_REQUESTS` (100), `RATE_LIMIT_WINDOW` (60s)
- Background task updates `rate_limit_subjects` gauge every 60s

### `observability/metrics.py` — New metrics (+36 lines)
- `rate_limit_allowed_total{transport}` — Counter
- `rate_limit_rejected_total{transport}` — Counter
- `rate_limit_subjects` — Gauge
- Helper functions: `record_rate_limit_allowed`, `record_rate_limit_rejected`, `update_rate_limit_subjects`

### Subject derivation
- SSE + auth: first 8 chars of bearer token
- SSE + no auth: `X-Forwarded-For` or client IP
- stdio: "stdio"

## Verification

| Suite | Result |
|---|---|
| `test_rate_limiter.py` | 18/18 passed |
| `test_worker_system.py` | 23/23 passed (existing limiter preserved) |
| Full suite | 978 passed, 2 pre-existing failures |
