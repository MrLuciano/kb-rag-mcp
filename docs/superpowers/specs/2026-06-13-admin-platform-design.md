# v0.1.5 Admin Platform Design

**Date:** 2026-06-13
**Status:** Draft
**Applies to:** Milestone v0.1.5 (Streamable HTTP & Management Platform)

## Overview

Three-layer architecture adding a management platform to the existing kb-rag-mcp system:

- **Layer 0 (Foundation):** Streamable HTTP transport, Auth & User REST API, Config API, Observability, Provider Aliases
- **Layer 1 (Admin Shell):** SPA panel with login, sidebar tabs, role gating
- **Layer 2 (Tab Content):** Admin config page, monitor lights, ingestion tab, RAGAS tab, browser cleanup, Grafana embed, profile page

## Layer 0 — Backend Foundation

### Config API (Phase 40)

**Storage:** New `config` table in `kb_metadata.db`:
```
key (TEXT PK), value (TEXT), type (str/int/bool/float/list),
group (TEXT), description (TEXT), updated_at, updated_by
```

**Endpoints:**
- `GET /api/v1/config` — all config grouped by category
- `GET /api/v1/config/{key}` — single value
- `PUT /api/v1/config/{key}` — update value, triggers hot-reload
- `POST /api/v1/config/reset` — reset all to env defaults

**Hot-reload chain:** SQLite config → `.env` file → env var defaults. Each component exposes a `reload_if_changed()` hook. On `PUT`, the config layer broadcasts change event; watching components re-read. Existing env var usage unchanged — the config layer wraps `os.getenv` with SQLite override.

**Fallback behavior:** If SQLite is unavailable, falls back to `.env` file. If `.env` is missing, falls back to env var defaults hardcoded in each module. No single point of failure.

### Streamable HTTP (Phase 28, reopened)

**Transport:** `StreamableHTTPSessionManager(app=app)` wrapping existing `mcp.server.Server("kb-rag")`.

**Route:** Single `/mcp` endpoint handling GET (SSE stream), POST (JSON-RPC), DELETE (session terminate), OPTIONS (CORS preflight).

**Stack:**
1. Starlette app with CORS middleware (allow `Authorization`, `Mcp-Session-Id`, `Content-Type` headers)
2. Auth middleware: `verify_request()` from existing `auth.py`
3. Rate limiting: existing token bucket
4. Session management: `StreamableHTTPSessionManager`
5. Metrics: existing `_current_subject`, `_current_transport`, Prometheus counters

**Env vars:** `MCP_HOST` (127.0.0.1), `MCP_PORT` (8765), `MCP_ENDPOINT` (/mcp), `MCP_JSON_RESPONSE` (false), `MCP_STATELESS` (false), `MCP_SESSION_TIMEOUT` (300).

**Existing transports unchanged:** stdio and SSE remain; this adds a third transport option.

### Auth & User Management API (Phase 28b)

**Models (SQLAlchemy):**
- `User`: id (UUID PK), username (unique), role (admin/user), is_active, created_at, updated_at
- `ApiKey`: id (UUID PK), user_id (FK), key_hash (SHA-256), prefix (8 chars), description, is_revoked, last_used_at, created_at
- `AuditLog`: id (UUID PK), timestamp, actor_id (UUID), action, resource_type, resource_id, details
- `ErasureRequest`: id (UUID PK), user_id (FK), status (requested/approved/rejected/completed), requested_by, approved_by, reason, timestamps

**Endpoints:**
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/session` | API key | Exchange key for JWT cookie (browser use) |
| POST | `/api/v1/users` | Admin | Create user |
| GET | `/api/v1/users` | Admin | List users (paginated, no PII) |
| GET | `/api/v1/users/me` | Auth | Current user profile (Art 15) |
| DELETE | `/api/v1/users/{id}` | Admin | Delete user (tombstone) |
| POST | `/api/v1/users/{id}/erasure-request` | Auth | Request erasure (Art 17) |
| POST | `/api/v1/users/{id}/export` | Auth | Export user data (Art 20) |
| POST | `/api/v1/api-keys` | Auth | Create key (shown once) |
| GET | `/api/v1/api-keys` | Auth | List own keys (prefix + meta only) |
| DELETE | `/api/v1/api-keys/{id}` | Auth | Revoke key |
| POST | `/api/v1/admin/erasure-requests/{id}/approve` | Admin | Approve erasure |

**Role guards:** FastAPI `Depends()` chain: `get_current_user` (API key) → `get_active_user` → `require_admin`/`require_auth`.

**GDPR erasure flow:** `active → erasure_requested → erasure_approved → erasure_completed`. Tombstone pattern: anonymize username, clear hash, hard-delete API keys, keep UUID. Audit log retained with UUID-only reference. 90-day auto-prune on audit logs.

**Key generation:** `secrets.token_urlsafe(32)` (43 chars), prefix = `kb_` + first 6 chars. Stored as SHA-256 hash. Shown once in response.

**Browser session:** `POST /api/v1/auth/session` validates API key, returns JWT cookie (`HttpOnly`, `SameSite=Lax`, `Secure` in production, 8h expiry).

### Observability (Phase 39)

**OBS-01 — Health/Readiness:**
- Upgrade existing `GET /health/detailed` (port 8080) to include Grafana connectivity check
- Expose health summary via admin API: `GET /api/v1/health`
- Kubernetes probes unchanged already point to health server

**OBS-02 — Request Identity:**
- Starlette middleware: auto-generate `X-Request-Id` (UUID) if not present
- Propagate through MCP tool calls via context var (`_current_request_id`)
- Log with request_id in structured log output
- Expose as response header

**METRICS-01 — Percentile Metrics:**
- In-memory HDR histogram (via `py-metrics` or manual sorted-list) per operation: `search_kb`, `list_documents`, `get_chunk`, `kb_stats`
- Track p50/p95/p99 latency per operation
- Expose via existing `/metrics` Prometheus endpoint
- Reset every scrape interval (to avoid unbounded memory)

### Provider Alias (Phase 41)

**Storage:** Config table entries with group `provider_alias`. Key pattern: `provider_alias.<canonical_name>` = alias value.

**Resolution:** Existing `EmbedClient` provider resolution reads aliases from config layer. If `EMBED_BACKEND=aliyun`, config lookup finds `provider_alias.aliyun=dashscope` and resolves to `dashscope` backend.

**Fallback:** If no alias found, uses value as-is (backward compatible).

## Layer 1 — Admin SPA Shell

### Route & Template

- Route: `/admin/` served by FastAPI Jinja2 template
- Template: `kb_server/ui/templates/admin/shell.html` (extends `base.html`)
- CSS: Bootstrap 5 sidebar layout (fixed left, scrollable content)
- JS: Alpine.js (CDN) + HTMX (CDN, already loaded)

### Auth Flow

1. Page load → Alpine reads `localStorage.getItem('kb_api_key')`
2. No key → `x-show="!isAuthenticated"` shows login modal
3. User enters key → `fetch('/api/v1/auth/session', {method:'POST', headers:{'Authorization':'Bearer '+key}})` → on 200 stores key in localStorage, sets `user.role` from response
4. All HTMX requests use `hx-headers='{"Authorization": "Bearer ${apiKey}"}'`
5. Global `htmx:beforeRequest` event handler adds Bearer header
6. On 401 response → `htmx:responseError` handler clears key, shows login modal
7. Logout → `localStorage.removeItem('kb_api_key')`, reset Alpine state

### Sidebar & Tab Layout

```
+--sidebar (240px)----------+--main content (flex-grow)---+
| KB-RAG Admin               |                             |
|                            |                             |
| 📄 Documents   [active]   |  <div x-show="activeTab==   |
| 📊 Monitoring             |    'documents'"> ...        |
| ⚡ Ingestion              |  <div x-show="activeTab==   |
| 🧪 RAGAS                  |    'monitoring'"> ...       |
| ⚙️ Admin     [admin only] |  <div x-show="activeTab==   |
| 👤 Profile                |    'admin'"> ...            |
|                            |                             |
| [— Logout —]              |                             |
+----------------------------+-----------------------------+
```

Tab switching: `x-on:click.prevent="activeTab = tab.id"`, content shown via `x-show="activeTab === 'documents'"`. Each tab loads content via HTMX `hx-get="/admin/tabs/{name}" hx-trigger="load"`.

## Layer 2 — Tab Content Details

### Admin Config Page

- Fetched via `GET /admin/tabs/admin` → returns partial with config table
- Table columns: Group | Key (monospace) | Value (editable input) | Type badge | Actions
- Groups: Embedding, Qdrant, Auth, Rate Limits, Logging, Provider, Ingestion, Server
- Inline edit: click value → input field appears → `PUT /api/v1/config/{key}` on blur/enter
- Search box filters rows by key name
- "Reset All" button → confirmation modal → `POST /api/v1/config/reset`

### Monitor Lights Bar

- Partial loaded via HTMX at top of admin area, auto-refresh `hx-trigger="every 30s"`
- Powered by `GET /health/detailed` endpoint
- 7 lights: Qdrant | Embedding | LLM Provider | Cache | Database | Filesystem | Grafana
- Each light: colored circle (`bg-success`/`bg-warning`/`bg-danger`) + name + latency
- Click → expandable detail: message, latency_ms, last_checked
- Grafana check: test TCP connection to `GRAFANA_URL` (config entry)

### Ingestion Tab

**Manual sub-tab:**
- Product override dropdown (from existing product aliases) + docs path input + file upload (optional)
- "Ingest Now" button → `POST /api/v1/jobs` → redirects to Monitor sub-tab showing live progress
- Progress updates via HTMX polling (`hx-trigger="every 2s"`) on job status

**Schedule sub-tab:**
- Table: Interval | Docs Path | Product Override | Enabled | Last Run | Actions
- "Add Schedule" form: interval dropdown (every hour/6h/daily/weekly), path, product, enabled toggle
- Edit/Delete per row
- Scheduler: background asyncio task reads schedules table, triggers `JobManager.create_job()` at intervals

**Monitor sub-tab:**
- Recent jobs table: Job ID | Status | Files | Chunks | Progress | Started | Errors | Actions
- Progress bar per job
- Click row → detail: per-file status table (file name, status, error message if failed)
- "Cancel" button for RUNNING jobs

### RAGAS Tab

- Golden set editor table: Query | Expected Answer | Expected Docs (optional comma-separated)
- Add row (form at bottom), edit inline, delete row (X button)
- Import: file input → upload JSON/CSV → parse + validate → show preview → confirm save
- Export: button downloads current set as JSON
- "Run Evaluation" button → `POST /api/v1/evaluation/run` → shows progress spinner → results appear below
- Results table: Metric | Score | Timestamp. History of past 10 evaluations below.
- Evaluation uses existing `RAGASEvaluator` pipeline; golden set stored as JSON in data dir.

### Browser Cleanup (modify `/ui/browse`)

- Add checkbox column to document table
- "Select All" checkbox in header
- Action bar (appears when docs selected): "Delete" | "Re-ingest" | "Delete Failed" (filters to error status)
- Per-document dropdown: View | Delete | Re-ingest | View Error (if failed)
- Delete: `DELETE /api/v1/documents/{source_file}` → removes from Qdrant + marks deleted in registry
- Re-ingest: `POST /api/v1/documents/{source_file}/re-ingest` → triggers `process_file()`
- Confirmation modal before destructive actions

### Grafana Embed (Monitoring Tab)

- Iframe: `src="https://grafana.example.com/d-solo/{uid}?orgId=1&kiosk=tv&theme=light"`
- Time range selector above iframe: 1h | 6h | 24h | 7d buttons → updates `from`/`to` params
- CSP middleware adds `frame-src https://grafana.internal:3000` (configurable via `GRAFANA_URL` config entry)
- Grafana config needed: `allow_embedding = true`, anonymous Viewer role

### Profile Tab

- Welcome message: "Logged in as {username} (role)"
- API Keys section: table of own keys (prefix, description, created_at, last_used_at)
- "Generate New Key" button → modal showing key once + download button
- Revoke button per key → confirmation → `DELETE /api/v1/api-keys/{id}`
- "Export My Data" → `GET /api/v1/users/me/export` → downloads JSON
- "Request Data Erasure" → confirmation dialog explaining what happens → `POST /api/v1/users/me/erasure-request`
- Erasure request status displayed if one is pending

## Error Handling

- Config API: invalid type returns 422 with expected type. Missing key returns 404.
- Auth API: invalid key returns 401. Insufficient role returns 403. Duplicate username returns 409.
- Ingestion: per-file errors caught and reported in job detail. Job itself can have FAILED status.
- RAGAS: evaluation failures logged; empty dataset returns 400.
- Monitor lights: failed health check = red light, error message in detail. Component timeout after 5s.
- All API errors follow standard format: `{"error": "message", "code": "ERROR_CODE"}`

## File Changes Summary

| File | Change |
|------|--------|
| `kb_server/server.py` | Add `streamable-http` transport branch |
| `kb_server/auth/models.py` | NEW: SQLAlchemy User/ApiKey/AuditLog/ErasureRequest |
| `kb_server/auth/schemas.py` | NEW: Pydantic request/response models |
| `kb_server/auth/deps.py` | NEW: FastAPI Depends() guards |
| `kb_server/auth/service.py` | NEW: User/Key CRUD service |
| `kb_server/auth/router.py` | NEW: All REST endpoints |
| `kb_server/config/api.py` | NEW: Config API endpoints |
| `kb_server/config/loader.py` | NEW: Config loader with SQLite→env→default chain |
| `kb_server/config/hotreload.py` | NEW: Hot-reload event system |
| `kb_server/ui/routes_admin.py` | NEW: Admin SPA routes + tab partials |
| `kb_server/ui/templates/admin/shell.html` | NEW: SPA shell with sidebar |
| `kb_server/ui/templates/admin/tab_*.html` | NEW: Tab partials (6 files) |
| `kb_server/ui/templates/admin/modal_*.html` | NEW: Login/logout/confirm modals |
| `kb_server/ui/templates/browse.html` | MODIFY: Add cleanup controls |
| `kb_server/ui/templates/base.html` | MODIFY: Add Alpine.js CDN + admin nav link |
| `kb_server/observability/middleware.py` | NEW: Request ID middleware |
| `kb_server/observability/percentiles.py` | NEW: HDR histogram per operation |
| `kb_server/health.py` | MODIFY: Add Grafana check |
| `ingest/job/manager.py` | MODIFY: Add programmatic job create |
| `ingest/scheduler.py` | NEW: Background schedule runner |
| `kb_server/evaluation/dataset.py` | MODIFY: Add CRUD for golden set |
| `tests/test_server_streamable_http.py` | NEW: Streamable HTTP tests |
| `tests/test_auth_api.py` | NEW: Auth API tests |
| `tests/test_config_api.py` | NEW: Config API tests |
| `tests/test_admin_ui.py` | NEW: Admin SPA tests |
| `docs/REFERENCE.md` | MODIFY: Add Streamable HTTP + Auth API docs |
| `docs/OPERATIONS.md` | MODIFY: Add admin panel + config docs |
| `docs/DATA_INVENTORY.md` | NEW: GDPR data inventory |
| `docs/PRIVACY.md` | NEW: GDPR compliance documentation |

## Testing Strategy

- **Unit tests**: Config loader chain, auth Depends guards, API validation, GDPR erasure state machine
- **Integration tests**: Auth API CRUD (mock DB), Config API (mock DB), Streamable HTTP (mock MCP server)
- **UI tests**: HTMX partial rendering, auth flow (mock API), tab switching, role gating
- **Existing tests**: All 1165 existing tests must continue passing (no regressions)
