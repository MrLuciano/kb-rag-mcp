# Plan 28-01 SUMMARY: MCP Streamable HTTP Transport

## Objective

Add a third MCP transport (streamable HTTP) alongside existing stdio and SSE, enabling browser-based MCP clients to connect via HTTP POST/GET.

## Verification Results

| Check | Result |
|-------|--------|
| `test_streamable_http_transport_env` | ✅ PASS |
| `test_streamable_http_auth_rejection` | ✅ PASS |
| `test_streamable_http_rate_limiting` | ✅ PASS |
| `record_rate_limit_allowed/rejected importable` | ✅ OK |
| `docs/REFERENCE.md` has streamable-http | ✅ 1 match |
| `docs/INSTRUCTIONS.md` has streamable-http | ✅ 1 match |

## Tasks Executed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | Streamable-http transport branch in server.py | ✅ | cf0e00a |
| 2 | Auth middleware for streamable-http endpoint | ✅ | 34fa618 |
| 3 | Subject resolution and rate limiting | ✅ | 5a3b426 |
| 4 | Prometheus metrics verification | ✅ | (wired in Task 3) |
| 5 | Documentation (REFERENCE.md, INSTRUCTIONS.md) | ✅ | a7c5e18 |

## Key Files Modified

- `kb_server/server.py` — Added `elif TRANSPORT == "streamable-http":` block with `handle_mcp` handler, CORS middleware, auth, subject resolution, rate limiting, and Prometheus metrics
- `tests/test_server_streamable_http.py` — 3 new tests for transport, auth rejection, and rate limiting
- `docs/REFERENCE.md` — Added Streamable HTTP config table and client usage
- `docs/INSTRUCTIONS.md` — Updated server run command

## Implementation Notes

- Uses `StreamableHTTPSessionManager` from `mcp.server.streamable_http_manager`
- Subject derived from Bearer token prefix (`key:XXXX`) or `X-Forwarded-For`/client IP
- Auth check uses existing `kb_server.auth` module (`is_auth_enabled`, `verify_request`)
- Rate limiting uses existing server-level `rate_limiter` with `record_rate_limit_allowed/rejected` counters
- Configuration via env vars: `MCP_HOST`, `MCP_PORT`, `MCP_ENDPOINT`, `MCP_JSON_RESPONSE`, `MCP_STATELESS`, `MCP_SESSION_TIMEOUT`
