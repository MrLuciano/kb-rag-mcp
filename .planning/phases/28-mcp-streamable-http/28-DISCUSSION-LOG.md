# Phase 28: MCP Streamable HTTP Transport - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 28-mcp-streamable-http
**Areas discussed:** Session Limit Policy

---

## Session Limit Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Reject new (503/429) | Return HTTP 503/429 — clean rejection, client can retry | |
| Evict oldest idle | Silently drop longest-idle session to make room | ✓ |

**User's choice:** Evict oldest idle
**Notes:** User wanted transparent eviction rather than blocking new connections.

| Option | Description | Selected |
|--------|-------------|----------|
| 50 sessions | Conservative — single-user or small team | ✓ (configurable) |
| 200 sessions | Balanced — browser tabs + AI clients | |
| 1000 sessions | Generous — unlikely to hit | |

**User's choice:** 50 by default, configurable via env var
**Notes:** User typed freeform response. Decision: MCP_MAX_SESSIONS env var, default 50.

| Option | Description | Selected |
|--------|-------------|----------|
| JSON-RPC error -32000 | Standard MCP error for "Session not found" | ✓ |
| HTTP 404 with error body | Non-standard, simpler for HTTP-only clients | |

**User's choice:** JSON-RPC error -32000
**Notes:** Clean protocol semantics.

| Option | Description | Selected |
|--------|-------------|----------|
| Periodic sweep (every 60s) | Asyncio task, predictable load | ✓ |
| Lazy cleanup on each request | No background task, simpler | |
| Hybrid: periodic + lazy | Both, most robust, most code | |

**User's choice:** Periodic sweep every 60s
**Notes:** Simple and predictable.

---

## the agent's Discretion

- Error response format (JSON-RPC vs plain JSON for non-JSON-RPC errors)
- CORS policy specifics (wildcard vs configurable origins)
- Prometheus metrics granularity beyond rate-limit counters

## Deferred Ideas

None — discussion stayed within phase scope.
