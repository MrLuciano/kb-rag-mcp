# Requirements: kb-rag-mcp

**Defined:** 2026-06-15
**Core Value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## v1 Requirements

Requirements for v0.1.5 milestone. Each maps to roadmap phases.

### Streamable HTTP Transport (Phase 28)

- [ ] **SH-01**: Server starts Streamable HTTP transport when `MCP_TRANSPORT=streamable-http` is set
- [ ] **SH-02**: `/mcp` endpoint accepts GET (SSE stream), POST (JSON-RPC), DELETE (session terminate), OPTIONS (CORS preflight)
- [ ] **SH-03**: Auth middleware applies to ALL HTTP methods on `/mcp` (including GET stream)
- [ ] **SH-04**: Session lifecycle managed: idle timeout (300s default), session count limit, background cleanup
- [ ] **SH-05**: Prometheus metrics track allowed/rejected requests per transport

### Auth & User Management API (Phase 28b)

- [ ] **AUTH-01**: SQLAlchemy models for User (UUID PK, username, role, is_active, timestamps)
- [ ] **AUTH-02**: SQLAlchemy models for ApiKey (UUID PK, user_id FK, SHA-256 hash, prefix, description, is_revoked, last_used_at)
- [ ] **AUTH-03**: SQLAlchemy models for AuditLog (UUID PK, actor_id, action, resource_type, resource_id, details, timestamp)
- [ ] **AUTH-04**: SQLAlchemy models for ErasureRequest (UUID PK, user_id FK, status state machine, approval chain, timestamps)
- [ ] **AUTH-05**: POST `/api/v1/auth/session` — exchange API key for JWT session cookie (HttpOnly, SameSite=Lax, 8h)
- [ ] **AUTH-06**: POST/GET `/api/v1/users` — admin creates users, lists users (paginated, no PII)
- [ ] **AUTH-07**: GET `/api/v1/users/me` — current user profile (GDPR Article 15)
- [ ] **AUTH-08**: DELETE `/api/v1/users/{id}` — admin deletes user (tombstone: anonymize username, clear hash, keep UUID)
- [ ] **AUTH-09**: FastAPI `Depends()` chain: `get_current_user` → `get_active_user` → `require_admin`/`require_auth`
- [ ] **AUTH-10**: POST/GET/DELETE `/api/v1/api-keys` — create (shown once), list (prefix + meta), revoke
- [ ] **AUTH-11**: GDPR erasure flow: `active → erasure_requested → erasure_approved → erasure_completed`
- [ ] **AUTH-12**: GDPR data export endpoint (Article 20) — returns user data as JSON
- [ ] **AUTH-13**: Audit log auto-prune after 90 days
- [ ] **AUTH-14**: Pre-requisite: migrate ALL existing SQLite connections to WAL mode with `db_utils.py` helper before any concurrent writes
- [ ] **AUTH-15**: GDPR data inventory documenting all PII fields and retention periods

### Config API (Phase 40)

- [ ] **CONF-01**: `config` table in `kb_metadata.db` with key (TEXT PK), value, type, group, description, updated_at, updated_by
- [ ] **CONF-02**: GET `/api/v1/config` — all config grouped by category
- [ ] **CONF-03**: GET `/api/v1/config/{key}` — single value
- [ ] **CONF-04**: PUT `/api/v1/config/{key}` — update value with type validation, triggers hot-reload
- [ ] **CONF-05**: POST `/api/v1/config/reset` — reset all to env defaults
- [ ] **CONF-06**: Layered config loader: SQLite → `.env` file → env var defaults (`os.getenv`)
- [ ] **CONF-07**: Hot-reload event bus with version-based change detection; `reload_if_changed()` hooks are synchronous to avoid races
- [ ] **CONF-08**: Fallback: if SQLite unavailable, falls back to `.env`; if `.env` missing, falls back to hardcoded defaults

### Admin SPA Panel (Phase 28c)

- [ ] **SPA-01**: Admin route at `/admin/` served by Jinja2 template with Alpine.js+HTMX+Bootstrap 5
- [ ] **SPA-02**: Login modal reads API key, exchanges for JWT session cookie via `/api/v1/auth/session`
- [ ] **SPA-03**: API key persisted in `localStorage`; HTMX headers include `Authorization: Bearer` via `hx-headers`
- [ ] **SPA-04**: Sidebar with tabs: Documents, Monitoring, Ingestion, Admin (admin-only), Profile — role-gated
- [ ] **SPA-05**: Tab content loaded via HTMX `hx-get="/admin/tabs/{name}"`
- [ ] **SPA-06**: Monitor lights bar (7 lights: Qdrant, Embedding, LLM, Cache, Database, Filesystem, Grafana) with auto-refresh 30s
- [ ] **SPA-07**: Profile tab: API key management (create/list/revoke), "Export My Data", "Request Erasure"
- [ ] **SPA-08**: Admin Config tab: editable config table grouped by category, inline edit, search, reset all
- [ ] **SPA-09**: Document browse cleanup: checkbox selection, delete/re-ingest per doc, confirmation modals
- [ ] **SPA-10**: CSP middleware: Alpine.js CSP build (not default), nonce-based script-src, `frame-src` for Grafana
- [ ] **SPA-11**: SRI integrity hashes on all CDN scripts
- [ ] **SPA-12**: Logout clears JWT cookie, resets Alpine auth state

### Observability (Phase 39)

- [ ] **OBS-01**: Request ID middleware: auto-generate `X-Request-Id` (UUID) if not present, propagate via context var, expose as response header
- [ ] **OBS-02**: Per-operation percentile metrics (p50/p95/p99) for `search_kb`, `list_documents`, `get_chunk`, `kb_stats`
- [ ] **OBS-03**: Percentile metrics use bounded-memory sorted-list or ring buffer, reset every scrape interval
- [ ] **OBS-04**: Health API endpoint `GET /api/v1/health` with Grafana connectivity check

### Grafana Dashboard Embedding (Phase 38)

- [ ] **GRAF-01**: Grafana dashboard embedded via iframe in Monitoring tab
- [ ] **GRAF-02**: Time range selector (1h/6h/24h/7d) updates iframe `from`/`to` parameters
- [ ] **GRAF-03**: CSP `frame-src` directive configurable via `GRAFANA_URL` config entry
- [ ] **GRAF-04**: Grafana configured with `allow_embedding=true` and anonymous Viewer role

### Provider Aliases (Phase 41)

- [ ] **PROV-01**: Config table entries with group `provider_alias`, key pattern `provider_alias.<canonical_name>`
- [ ] **PROV-02**: `EmbedClient` reads aliases from config layer on resolution; fallback to value-as-is if no alias found

### Advanced Filters (SPA-05)

- [ ] **FILT-01**: Date range filter on document browse (created_at from/to)
- [ ] **FILT-02**: File type filter (PDF, DOCX, XLSX, PPTX, MD, TXT) with multi-select
- [ ] **FILT-03**: Vendor and product filter dropdowns populated from distinct values
- [ ] **FILT-04**: Filter state reflected in URL query params (shareable/bookmarkable)
- [ ] **FILT-05**: "Clear All Filters" button resets all active filters

### Document Export (SPA-04)

- [ ] **EXPT-01**: Export button in document browse triggers filtered download
- [ ] **EXPT-02**: Export format options: CSV, JSON
- [ ] **EXPT-03**: Respects all active filters (date range, file type, vendor, product)
- [ ] **EXPT-04**: Large export runs as background job with progress indicator

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Ingestion Tab in SPA

- **INGEST-01**: Manual job create with product override + docs path input
- **INGEST-02**: Job schedule management (hour/6h/daily/weekly)
- **INGEST-03**: Job monitor view with per-file progress and status

### RAGAS Tab in SPA

- **RAGAS-01**: Golden set CRUD (inline editor, import CSV/JSON, export)
- **RAGAS-02**: Run evaluation from browser, display results history

## Out of Scope

| Feature | Reason |
|---------|--------|
| Built-in chat UI | Drifts from MCP-server core identity; redirect to MCP client setup |
| Password-based auth | API key + JWT session is simpler and sufficient for internal use |
| SSO/OAuth integration | Heavy integration; teams can use reverse-proxy auth (Cloudflare Access, Authentik) |
| Multi-factor auth | Security is deployer's responsibility; network-level controls recommended |
| Real-time document editing | Shifts from document management to collaborative editor |
| Mobile app | Web-first, MCP clients on mobile are the mobile experience |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SH-01 through SH-05 | Phase 28 (reopened) | In Progress (Plan 28-01 done) |
| AUTH-01 through AUTH-15 | Phase 28b | Pending |
| CONF-01 through CONF-08 | Phase 40 | Pending |
| SPA-01 through SPA-12 | Phase 28c | Pending |
| OBS-01 through OBS-04 | Phase 39 | Pending |
| GRAF-01 through GRAF-04 | Phase 38 | Pending |
| PROV-01 through PROV-02 | Phase 41 | Pending |
| FILT-01 through FILT-05 | SPA-05 | Pending |
| EXPT-01 through EXPT-04 | SPA-04 | Pending |

**Coverage:**
- v1 requirements: 47 total
- Mapped to phases: 47
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-15*
*Last updated: 2026-06-15 after v0.1.5 milestone initialization*
