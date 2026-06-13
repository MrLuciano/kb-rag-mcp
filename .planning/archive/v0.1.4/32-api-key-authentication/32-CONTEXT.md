# Phase 32: API Key Authentication

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** Medium
**Code:** AUTH-01
**Competitive Reference:** [kalicyh/mcp-rag](https://github.com/kalicyh/mcp-rag) — API key authentication
**Promoted from:** `.planning/ROADMAP.md` Backlog (Medium Priority)

## Objective

Add global and collection-scoped API keys with `enabled`/`allow_anonymous` flags. Needed for production self-hosted deployment where unauthenticated access is a security concern.

## Expected Deliverables

- API key generation and storage (hashed in SQLite, per-KB and global keys)
- Middleware to validate API keys on all MCP/HTTP endpoints
- `enabled` flag to disable auth entirely (backward compatible default)
- `allow_anonymous` flag per KB (for internal deployments where auth is optional)
- CLI commands to generate, list, revoke keys
- MCP tool: `create_api_key`, `list_api_keys`, `revoke_api_key`
- Key rotation support without downtime

## Key Design Decisions

- **Key format:** 32-byte random hex, SHA256-hashed in DB (never stored plaintext)
- **Validation:** Middleware on all HTTP endpoints (SSE, Streamable HTTP, health)
- **Scope:** Global keys vs per-KB keys (per-KB allows key delegation to tenants)
- **Default behavior:** `AUTH_ENABLED=false` (backward compatible, no auth on stdio transport)
- **Transport-specific:** Auth only enforced on HTTP transports (stdio relies on OS-level access)

## Implementation Scope

1. Add `api_keys` table to registry SQLite (`kb_registry.db`)
2. Add `auth_enabled` and `allow_anonymous` fields to `knowledge_bases` table
3. Middleware in `server.py` that validates `Authorization: Bearer <key>` header
4. Auth disabled for stdio transport (already OS-level secured by design)
5. CLI: `kb-ingest api-key create`, `kb-ingest api-key list`, `kb-ingest api-key revoke`

## Open Questions

1. Should API keys support expiry dates or be permanent?
2. Do we need rate limiting per key (separate from RATE-01)?
3. How to handle key revocation in-flight requests?

## See Also

- `kalicyh/mcp-rag` auth implementation (GitHub: kalicyh/mcp-rag)
- `kb_server/kb_registry.py` — existing registry
- `kb_server/server.py` — HTTP transport layer