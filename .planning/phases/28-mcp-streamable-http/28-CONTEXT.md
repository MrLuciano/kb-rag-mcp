# Phase 28: MCP Streamable HTTP Transport - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Browser-compatible MCP transport via a single `/mcp` HTTP endpoint supporting GET (SSE stream), POST (JSON-RPC), DELETE (session terminate), and OPTIONS (CORS preflight). Phase 28 is reopened for remaining session lifecycle management, metrics improvements, and edge-case hardening beyond what Plan 28-01 implemented.

Requirements: SH-01, SH-02, SH-03, SH-04, SH-05

Success criteria from ROADMAP.md:
1. Server starts Streamable HTTP transport when `MCP_TRANSPORT=streamable-http` is set
2. Browser-based MCP clients can connect via GET (SSE stream), POST (JSON-RPC), and DELETE (session terminate) on `/mcp`
3. Auth middleware applies to ALL HTTP methods on `/mcp` including the GET SSE stream
4. Sessions are automatically cleaned up after idle timeout (300s default) with configurable session count limit
5. Prometheus metrics track allowed/rejected requests per transport type

</domain>

<decisions>
## Implementation Decisions

### Session Limit Policy
- **D-01:** When session limit reached, evict the oldest idle session to make room for new connections (rather than rejecting new connections)
- **D-02:** Default max concurrent sessions: 50. Must be configurable via env var (follows `MCP_*` naming pattern, e.g., `MCP_MAX_SESSIONS`)
- **D-03:** Evicted clients receive JSON-RPC error code `-32000` ("Session not found") on their next request
- **D-04:** Background session cleanup via periodic sweep every 60 seconds (asyncio task)

### the agent's Discretion
- Error response format for non-JSON-RPC errors (auth failures, rate limits) — agent chooses between `{"error":"..."}` plain JSON or JSON-RPC format
- CORS policy specifics — agent chooses whether to keep wildcard or add configurable origins
- Prometheus metrics granularity beyond rate-limit counters — agent chooses which counters/gauges/histograms to add

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Files
- `kb_server/server.py` — Existing MCP server with stdio/SSE/streamable-http transport branches. The streamable-http branch is where new code integrates.
- `kb_server/auth.py` — Auth module with `verify_request()`, `is_auth_enabled()`, and subject resolution used by the transport layer.
- `observability/metrics.py` — Prometheus metrics functions including `record_rate_limit_allowed`, `record_rate_limit_rejected`.
- `docs/REFERENCE.md` — Configuration reference; streamable-http env var table exists from Plan 28-01.

### Planning Artifacts
- `.planning/phases/28-mcp-streamable-http/28-01-PLAN.md` — Existing Plan 28-01 with 5 tasks already executed (transport branch, auth middleware, subject resolution, rate limiting, docs). New plans should not duplicate completed work.
- `.planning/ROADMAP.md` §Phase 28 — Phase goal, success criteria, and requirement mapping.
- `.planning/REQUIREMENTS.md` §Streamable HTTP Transport — SH-01 through SH-05 requirement definitions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mcp.server.streamable_http_manager.StreamableHTTPSessionManager` — Core session management from mcp library. Handles session creation, request routing, and idle timeout (300s default via `session_idle_timeout` parameter). Does NOT handle session count limits — that needs custom wrapper logic.
- `kb_server.auth.verify_request()` / `is_auth_enabled()` — Existing auth middleware. Plan 28-01 already integrates these in the `/mcp` handler.
- `observability.metrics.record_rate_limit_allowed()` / `record_rate_limit_rejected()` — Prometheus counters already called with `"streamable-http"` label from Plan 28-01.

### Established Patterns
- **Env var config pattern**: All transport configuration uses `MCP_*` env vars loaded in the transport branch with `os.getenv("MCP_*", default)`.
- **Auth middleware pattern**: `is_auth_enabled()` check at top of handler, then `verify_request()` returning `(ok, err)` tuple. 401 on failure.
- **Rate limiting pattern**: Subject derived from auth key prefix or client IP, then `rate_limiter.check(subject)`. 429 on limit exceeded.
- **Starlette/uvicorn app pattern**: The transport branch creates a `Starlette()` app with routes/middleware and wraps it in `uvicorn.Server(config).serve()`.

### Integration Points
- `kb_server/server.py` `main()` — The `elif TRANSPORT == "streamable-http":` branch is where all new functionality connects. Currently has Starlette app creation, CORS middleware, route registration, and session manager instantiation.
- Session manager `handle_request` — All HTTP methods (GET, POST, DELETE, OPTIONS) route through this single method. Auth, rate limiting, and subject resolution are handled in the wrapper `handle_mcp()` function before delegation.
- Prometheus metrics — Rate-limit counters already call into `observability/metrics.py`. New metrics (session counts, request volume) would follow the same pattern.

</code_context>

<specifics>
## Specific Ideas

- Session limit env var should follow existing `MCP_*` naming (e.g., `MCP_MAX_SESSIONS`) alongside existing vars like `MCP_SESSION_TIMEOUT`, `MCP_STATELESS`, `MCP_JSON_RESPONSE`.
- The session limit enforcement wraps around `StreamableHTTPSessionManager` — the mcp library's session manager doesn't natively support max session limits, so this needs a wrapper or interceptor.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 28-mcp-streamable-http*
*Context gathered: 2026-06-15*
