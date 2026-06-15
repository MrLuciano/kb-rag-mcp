# Phase 28c: Admin SPA Panel - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Full browser-based admin panel with login, tabbed interface, role gating, document management, advanced filters, and document export. Built with Alpine.js + HTMX + Bootstrap 5 — no build step, CDN-loaded scripts.

Requirements: SPA-01 through SPA-12, FILT-01 through FILT-05, EXPT-01 through EXPT-04

</domain>

<decisions>
## Implementation Decisions

### Auth Flow
- **D-01:** Add `POST /api/v1/auth/session` endpoint to Phase 28b auth router — exchanges API key for HttpOnly JWT session cookie (8h expiry, SameSite=Lax). This is the primary auth mechanism for the admin SPA.
- **D-02:** API key also stored in `localStorage` for HTMX `Authorization: Bearer` header via `hx-headers`, enabling direct API calls alongside session-based auth.
- **D-03:** 401 interceptor via HTMX event handler catches auth failures, shows login modal for re-entry. No page redirect — modal overlay preserves current view.

### Tab Loading & Refresh
- **D-04:** HTMX partials per tab — each tab loaded via `hx-get="/admin/tabs/{name}"`. Monitoring and Ingestion tabs auto-refresh on configurable intervals. Documents, Admin, Profile load on demand.
- **D-05:** Tab content is server-rendered Jinja2 partials, returned as HTML fragments. No JSON API rendering on the client side.

### Monitor Lights Bar
- **D-06:** 7 status lights (Qdrant, Embedding, LLM, Cache, Database, Filesystem, Grafana) auto-refreshed via `hx-trigger="every 30s"` from the `/health/detailed` endpoint.
- **D-07:** Visual: colored dots (green=healthy, yellow=degraded/warning, red=unhealthy, gray=not configured) with component name label. Powered by Alpine.js `x-data` bound to health check response.

### Document Browse
- **D-08:** Table layout with sortable columns (name, file type, vendor, product, date, status). Filter bar above: date range (from/to), file type multi-select, vendor dropdown, product dropdown.
- **D-09:** Server-side pagination, 25 results per page. Pagination controls (prev/next, page numbers). Filter state reflected in URL query params for shareable/bookmarkable URLs.

### CSP & Security
- **D-10:** Strict CSP with Alpine.js CSP build (not default), nonce-based `script-src` for inline scripts, `frame-src` for Grafana iframe embed.
- **D-11:** SRI integrity hashes on all CDN-loaded scripts (Alpine.js, HTMX, Bootstrap 5 CSS/JS). CDN URLs pinned to specific versions with integrity attribute.

### Document Export
- **D-12:** Synchronous CSV/JSON download — export endpoint returns the file directly. HTMX-triggered download via anchor click or form submission. Background jobs reserved for future scaling.

### the agent's Discretion
- Bootstrap 5 theme customization details (CDN theme vs custom CSS variables).
- Mobile responsiveness approach — whether admin panel is desktop-only with basic mobile fallback.
- Nonce generation and middleware implementation details.
- Exact HTMX event names and Alpine.js component structure.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Auth & Config (Dependencies)
- `.planning/phases/28b-auth-api/28b-CONTEXT.md` — Auth endpoints, deps, API key/JWT session design
- `.planning/phases/40-config-backlog/40-CONTEXT.md` — Config API endpoints, inline editing source
- `kb_server/auth/router.py` — Existing auth router (add session endpoint here)
- `kb_server/auth/deps.py` — Dependency guards for session-based auth

### Health & Monitoring
- `.planning/phases/39-observability/39-CONTEXT.md` — Health checks, Grafana connectivity
- `kb_server/health.py` — `check_all_components()` returns the 7 component statuses
- `kb_server/health_server.py` — `/health/detailed` endpoint providing status data

### Requirements & Roadmap
- `.planning/ROADMAP.md` §Phase 28c — Phase goal, success criteria, requirement mapping
- `.planning/REQUIREMENTS.md` §Admin SPA Panel — SPA-01 through SPA-12 definitions
- `.planning/REQUIREMENTS.md` §Advanced Filters — FILT-01 through FILT-05 definitions
- `.planning/REQUIREMENTS.md` §Document Export — EXPT-01 through EXPT-04 definitions

### Frontend Architecture
- `kb_server/ui/app.py` — Existing FastAPI UI app (mount admin router here)
- `kb_server/ui/routes_admin.py` — Admin route definitions (create if doesn't exist)
- `kb_server/ui/templates/base.html` — Base Jinja2 template (Alpine.js CDN link, CSP nonce)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kb_server/auth/` — Auth package with API key verification, dependency guards, user management. Needs `POST /api/v1/auth/session` endpoint added for JWT session support.
- `kb_server/health.py:331` — `check_all_components()` returns status dict with 6 components. The monitor lights bar's data source.
- `kb_server/health_server.py:68` — `/health/detailed` endpoint returning component health as JSON. Monitor lights poll this endpoint.

### Established Patterns
- **No build step**: Project has zero Node.js toolchain. All frontend assets are CDN-loaded (Alpine.js, HTMX, Bootstrap 5 CSS).
- **Jinja2 server-side rendering**: All HTML rendered server-side. HTMX for dynamic partial loading. No client-side rendering framework.
- **Existing ui package**: `kb_server/ui/` with `app.py`, templates, and routes. Admin SPA extends this package.

### Integration Points
- `kb_server/ui/app.py` — Mount admin router and add CSP middleware here
- `kb_server/auth/router.py` — Add `POST /api/v1/auth/session` endpoint
- `kb_server/health_server.py` — `/health/detailed` is the data source for monitor lights
- `kb_server/config/router.py` — Config API at `/api/v1/config` is the data source for Admin Config tab inline editor

</code_context>

<specifics>
## Specific Ideas

- Login modal should be a centered Bootstrap card with API key input field and "Log in" button
- Sidebar with icon+label for each tab, active tab highlighted
- Logout button in sidebar footer or profile tab
- Document browse: checkbox column for multi-select, action bar appears when items selected (delete, re-ingest, export)

</specifics>

<deferred>
## Deferred Ideas

- Advanced filters (28c-03) and document export (28c-04) are planned as separate future plans within this phase
- SSE-based real-time monitor lights was considered but HTMX polling was chosen for simplicity
- Background jobs for large exports deferred — synchronous download sufficient for current scale

</deferred>

---

*Phase: 28c-admin-spa-panel*
*Context gathered: 2026-06-15 via discuss-phase*
