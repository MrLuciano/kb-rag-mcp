# v0.1.5 Requirements — Streamable HTTP & Management Platform

## Phase 28: MCP Streamable HTTP Transport
- [ ] R28-01: Add `MCP_TRANSPORT = streamable-http` branch in `server.py:main()`
- [ ] R28-02: Wire `StreamableHTTPSessionManager` around existing `mcp.server.Server` instance
- [ ] R28-03: Single `/mcp` endpoint handling GET/POST/DELETE/OPTIONS
- [ ] R28-04: CORS middleware for browser access (allow all origins, restrict in production)
- [ ] R28-05: Auth header validation middleware (from existing `auth.py`)
- [ ] R28-06: Rate limiting integration (existing module)
- [ ] R28-07: Observable: set `_current_subject`, `_current_transport`, metrics records
- [ ] R28-08: Env vars: `MCP_HOST`, `MCP_PORT`, `MCP_ENDPOINT`, `MCP_JSON_RESPONSE`, `MCP_STATELESS`, `MCP_SESSION_TIMEOUT`
- [ ] R28-09: Docs: update REFERENCE.md, INSTRUCTIONS.md with Streamable HTTP config
- [ ] R28-10: Tests: `test_server_streamable_http.py` covering init, tool call, auth rejection

## Phase 28b: Auth & User Management API (REST)
- [ ] R28b-01: SQLAlchemy `User` model: id (UUID), username (unique), role (admin/user), is_active, created_at, updated_at
- [ ] R28b-02: SQLAlchemy `ApiKey` model: id, user_id (FK), key_hash (SHA-256), prefix, description, is_revoked, last_used_at, created_at
- [ ] R28b-03: SQLAlchemy `AuditLog` model: id, timestamp, actor_id (UUID), action, resource_type, resource_id, details
- [ ] R28b-04: FastAPI `get_current_user` dependency via `X-API-Key` header
- [ ] R28b-05: FastAPI `require_admin` / `require_auth` dependency guards
- [ ] R28b-06: `POST /api/v1/auth/session` — exchange API key for JWT session cookie
- [ ] R28b-07: `POST /api/v1/users` — admin creates user
- [ ] R28b-08: `GET /api/v1/users` — admin lists users (paginated, no PII)
- [ ] R28b-09: `GET /api/v1/users/me` — current user profile (Art 15 access)
- [ ] R28b-10: `DELETE /api/v1/users/{id}` — admin deletes user (tombstone/erasure)
- [ ] R28b-11: `POST /api/v1/users/{id}/erasure-request` — user or admin requests erasure (GDPR Art 17)
- [ ] R28b-12: `POST /api/v1/admin/erasure-requests/{id}/approve` — DPO/admin approves erasure
- [ ] R28b-13: `POST /api/v1/users/{id}/export` — data portability export (Art 20)
- [ ] R28b-14: `POST /api/v1/api-keys` — create new API key (shown once)
- [ ] R28b-15: `GET /api/v1/api-keys` — list own keys (prefix + meta, never raw key)
- [ ] R28b-16: `DELETE /api/v1/api-keys/{id}` — revoke key
- [ ] R28b-17: Audit logging on all user/data access events
- [ ] R28b-18: 90-day audit log auto-prune
- [ ] R28b-19: Data inventory document (`docs/DATA_INVENTORY.md`) for breach notification readiness

## Phase 28c: Admin SPA Panel (Web UI)
- [ ] R28c-01: Add Alpine.js CDN to `base.html`
- [ ] R28c-02: SPA shell template at `/admin/` with sidebar + tab container
- [ ] R28c-03: Tab: Documents — HTMX loads document browse/search partials
- [ ] R28c-04: Tab: Monitoring — Grafana dashboard iframe embed
- [ ] R28c-05: Tab: Admin — user management (create/list/delete users, manage API keys)
- [ ] R28c-06: Tab: Profile — personal API keys, usage stats, data export, erasure request
- [ ] R28c-07: Login modal — enter API key → stored in localStorage → Bearer header on all requests
- [ ] R28c-08: Role-based tab visibility (admin tab only for admin role)
- [ ] R28c-09: 401 interception → show re-login modal
- [ ] R28c-10: Logout → clear localStorage, reset to login modal

## Phase 38: Grafana Dashboard Embedding
- [ ] R38-01: FastAPI helper function `build_grafana_embed_url()` for generating iframe URLs
- [ ] R38-02: FastAPI helper function `grafana_embed_html()` for complete iframe HTML snippet
- [ ] R38-03: CSP middleware adding `frame-src` for Grafana origin
- [ ] R38-04: Monitoring tab in SPA renders iframe with Grafana dashboard
- [ ] R38-05: Grafana configuration docs in OPERATIONS.md (`allow_embedding = true`, anonymous Viewer, CSP)
- [ ] R38-06: Time range selector UI above iframe (last 1h, 6h, 24h, 7d)

## Phase 39: Observability Backlog
- [ ] R39-01: OBS-01: Health/Readiness liveness + readiness endpoints
- [ ] R39-02: OBS-02: Request Identity Middleware (request_id per operation)
- [ ] R39-03: METRICS-01: Per-operation percentile metrics (p50, p95, p99 latency)

## Phase 40: Configuration Backlog
- [ ] R40-01: CONF-01: Hot-reload configuration (watch `.env` for changes, live update)
- [ ] R40-02: CONF-02: Configuration API endpoint (`GET /api/v1/config`, `PUT /api/v1/config`)

## Phase 41: MCP Provider Alias
- [ ] R41-01: PROV-01: Provider aliases via env/config (`MCP_TOOL_ALIAS_*`)

## Integration & Non-Functional
- [ ] R-INT-01: Backward compatible — existing stdio and SSE transports unchanged
- [ ] R-INT-02: Auth API keys remain compatible with existing `ingest.cli.main auth` CLI
- [ ] R-INT-03: All existing tests continue to pass (1165 passed baseline)
- [ ] R-INT-04: No new npm/Node.js dependencies — zero-build frontend
- [ ] R-INT-05: GDPR compliance documentation (`docs/PRIVACY.md`)
