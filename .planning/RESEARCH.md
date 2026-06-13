# v0.1.5 Research Findings

## Grafana Dashboard Embedding

**How:** FastAPI helper generates iframe URLs for Grafana dashboards/panels. Grafana must set `allow_embedding = true` in `grafana.ini` (or `GF_SECURITY_ALLOW_EMBEDDING=true` in Docker). Embed with `&kiosk=tv` to hide nav, `&theme=light` for light theme.

**Auth:** For internal setup, use anonymous Viewer role in Grafana. No token needed. If auth required, Grafana JWT auth or reverse-proxy header.

**CSP:** FastAPI sets `Content-Security-Policy: frame-src 'self' https://grafana.internal:3000;`

**Config:** `grafana.ini`: `[security] allow_embedding = true`, `[auth.anonymous] enabled = true, org_role = Viewer`, `[cookies] samesite_mode = lax`

## Auth & User Management

**Pattern:** FastAPI `APIKeyHeader` dependency extraction → SHA-256 hash lookup → `Depends()` chain: `get_current_user` → `get_active_user` → `require_admin`/`require_auth`.

**Auth modes:** API key header (`X-API-Key`) for programmatic access. JWT session cookie for browser UI (exchanged via `POST /api/v1/auth/session`).

**User model:** id (UUID), username (unique), role (admin/user), is_active, created_at, updated_at. No password, no email required. API keys in separate table with FK cascade.

## SPA Architecture

**Framework:** Keep existing Jinja2+HTMX+Bootstrap 5. Add Alpine.js (CDN, 15KB, no build step) for client-side state: active tab, auth token, role-based visibility.

**Route:** `/admin/` returns SPA shell template with sidebar + tab container. Tab content loads via HTMX partials from `/admin/tabs/{name}`.

**Auth flow:** Login modal → store API key in localStorage → `hx-headers` on every HTMX request → middleware validates → on 401 show re-login modal.

**No build tooling:** Alpine.js and HTMX loaded from CDN. JS files in `kb_server/ui/static/js/admin/` if needed.

## MCP Streamable HTTP

**Library:** `mcp==1.27.1` provides `StreamableHTTPSessionManager(app, json_response, stateless, security_settings, session_idle_timeout)` and `TransportSecuritySettings`. Wraps existing `mcp.server.Server` instance.

**Route:** Single `/mcp` endpoint handles GET (SSE stream), POST (JSON-RPC), DELETE (session terminate), OPTIONS (CORS preflight). After `session_mgr.run()` lifespan + uvicorn.

**Integration:** New `elif TRANSPORT == "streamable-http"` branch in `server.py:main()`. CORS middleware allows browser access. Rate limiting + auth middleware applied before `session_mgr.handle_request()`.

**Variables:** `MCP_HOST`, `MCP_PORT`, `MCP_ENDPOINT`, `MCP_JSON_RESPONSE`, `MCP_STATELESS`, `MCP_SESSION_TIMEOUT`.

## GDPR Compliance

**Data minimization:** Store only: username (can be pseudonym), role, SHA-256 hashed API keys, created_at/last_used_at timestamps. No email, no full name, no IP at user level.

**Right to erasure:** State machine: `active → erasure_requested → erasure_approved → erasure_completed`. Tombstone pattern (anonymize username, clear hash, hard-delete API keys, keep UUID for referential integrity). Designated admin role for erasure approval.

**Right of access (Art 15):** `GET /api/v1/users/me` returns all stored data.

**Right to portability (Art 20):** `GET /api/v1/users/{id}/export` returns JSON export.

**Audit logging:** All user data access/modification logged with `actor_id` (UUID, not PII). 90-day retention with auto-prune.

**Data inventory:** Maintained `data_inventory.md` for breach notification readiness.
