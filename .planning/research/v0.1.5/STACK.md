# Stack Research — v0.1.5 Admin Platform Additions

**Domain:** RAG MCP Server Admin Platform (Streamable HTTP, Auth API, Admin SPA, Observability, Config, Provider Aliases)
**Researched:** 2026-06-15
**Confidence:** HIGH

## Context

This document covers **new dependencies and technology choices** for the v0.1.5 admin platform features. The existing stack (Python 3.11+, FastAPI 0.136.1, Starlette 1.0.0, Qdrant, MCP 1.27.1, Jinja2, Prometheus, SQLite) is validated and unchanged. This only documents what we need to **add**.

## Recommended Stack — New Additions

### New Python Dependencies

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `sqlalchemy` | >=2.0,<3 | ORM for User/ApiKey/AuditLog/ErasureRequest models | SQLAlchemy==2.0.49 is already installed as a transitive dependency (via langchain-classic). Need to declare it explicitly for Phase 28b auth models. 2.x provides async ORM support via aiosqlite. |
| `aiosqlite` | >=0.22.1 | Async SQLite driver for SQLAlchemy async sessions | Required for async ORM operations from FastAPI endpoints. Pure Python, no C deps. aiosqlite 0.22.1 is the latest stable (supports py3.10+). |

### No New Python Dependencies

The following features require **zero new pip packages**:

| Feature | Why No New Deps |
|---------|-----------------|
| MCP Streamable HTTP | `mcp==1.27.1` already includes `mcp.server.streamable_http_manager.StreamableHTTPSessionManager` and `streamable_http_app`. Transport added at v1.19.0+. |
| JWT Session Tokens | `pyjwt[crypto]==2.12.1` and `cryptography==48.0.0` already installed. Import `jwt` from `pyjwt`. |
| Auth API (FastAPI Depends guards) | FastAPI already installed. Pydantic schemas for request/response validation use existing `pydantic==2.13.4`. |
| Request ID Middleware | Starlette middleware pattern already in use (`kb_server/server.py` uses CORSMiddleware). No extra package needed. |
| Percentile Latency Metrics | Manual sorted-list approach (NOT `hdrhistogram` package). Only p50/p95/p99 needed for 4 operations. Sorted list of latencies per scrape interval, compute percentiles at `/metrics` scrape time, reset. Keeps dep footprint low. |
| Config REST API | FastAPI + existing SQLite/SQLAlchemy. Hot-reload: Python `asyncio.Event` pattern. |
| Provider Aliases | Config-based resolution. No new deps. |
| CSV/JSON Export | Python stdlib `csv` and `json` modules. |
| CSP Middleware (Grafana iframe) | Starlette already has `Middleware` support; add `frame-src` directive via existing middleware stack. |

### Frontend — CDN Only (No Build Step)

| Library | Version | CDN URL | Why |
|---------|---------|---------|-----|
| Alpine.js | 3.15.12 | `https://cdn.jsdelivr.net/npm/alpinejs@3.15.12/dist/cdn.min.js` | Latest stable as of Apr 2026. 45KB minified. No build step. Use with `defer` attribute. Manage SPA state (active tab, auth status, modal visibility). |
| HTMX | 2.0.10 | `https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js` | Current stable line. 50KB minified. The existing project uses 1.9.10 — upgrading to 2.x for new admin pages is safe (backward compat for basic attributes used; drops IE11 which is irrelevant for admin tools). For zero risk, keep both: 1.x in base.html for existing browse/search pages, 2.x in admin shell. |
| Bootstrap 5 | 5.3.8 | CSS: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css` | Latest stable. Sidebar layout, tables, modals, badges, form controls. Currently the project uses 5.3.0 — upgrading to 5.3.8 is a patch-level bump (no breaking changes between 5.3.x). |

**Why CDN instead of npm/build step:** The entire kb-rag-mcp project has zero frontend build infrastructure. Adding npm/Webpack/Vite would create maintenance overhead, CI complexity, and dependency conflicts. The admin SPA is simple enough (6-7 tab partials, a modal, sidebar nav) that CDN-loaded Alpine.js + HTMX + Bootstrap 5 handles everything with zero build tooling.

### MCP Version Constraint

| Current | Action | Rationale |
|---------|--------|-----------|
| `mcp>=1.0.0` in requirements.in → pinned `1.27.1` in requirements.txt | **Add `<2` upper bound:** `mcp>=1.27.0,<2` | MCP Python SDK v2.0 is in alpha (targeting stable 2026-07-27). The repo recommends adding `<2` upper bound for all v1.x consumers to prevent accidental upgrade. Streamable HTTP transport is fully supported in v1.27.1. |

## New Dependencies to Add to `requirements.in`

```text
# ── Phase 28b: Auth Models (SQLAlchemy ORM) ──────────────────────
sqlalchemy>=2.0.0                    # Already transitive dep; declare explicitly
aiosqlite>=0.22.0                    # Async SQLite for async ORM sessions

# ── MCP version lock for v2 compatibility ────────────────────────
# Add <2 upper bound to existing mcp line:
# mcp>=1.27.0,<2
```

That's it — only **2 new pip dependencies** for the entire v0.1.5 milestone.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Percentile tracking | Manual sorted-list | `hdrhistogram` (PyPI, v0.10.7) | Manual approach avoids a C-dependent library for what amounts to 4 operations × p50/p95/p99. HDR histogram is overkill when reset-on-scrape means we never accumulate more than ~10K samples. Manual sorted-list with `sortedcontainers` would also be overkill — a plain `list.sort()` every 15s at Prometheus scrape is trivially fast. |
| JWT library | `pyjwt[crypto]` (already installed) | `python-jose` | `python-jose` is unmaintained (last release 2021). `pyjwt` is actively maintained, already pinned, and `[crypto]` extras give us RSA/EC support if needed later. |
| Password hashing | Not needed | `passlib` + `bcrypt` | The auth model uses API keys (SHA-256 hashed for storage, 43-char random tokens for transmission), not passwords. No login form with password field. JWT is a session cookie exchanged for an API key, not a login credential. |
| Admin SPA frontend framework | Alpine.js + HTMX | React/Vue/Svelte with build step | The project has zero JS tooling. Adding Vite/Webpack would require CI pipeline changes, npm audit maintenance, and unnecessary complexity for a 6-tab admin panel. Alpine.js handles reactivity (tab switching, modals, auth state) without a build step. |
| HTMX version | 2.0.10 (new admin pages) | Keep 1.9.10 everywhere | HTMX 2.x is the current stable. The new admin shell uses HTMX for tab content loading via `hx-get`/`hx-trigger` — these are identical in 1.x and 2.x. 2.x drops IE support (irrelevant). Safest path: update base.html to 2.0.10 and test existing browse/search for regressions. |
| Async DB driver | `aiosqlite` | `aiofiles` + raw sqlite3 | Existing auth_registry uses sync `sqlite3` with `threading.Lock`. For new FastAPI endpoints, async DB access is architecturally consistent with the asyncio codebase. `aiosqlite` wraps SQLite's C API with zero-copy async. SQLAlchemy async + aiosqlite allows proper `async for` / `await` patterns in FastAPI Depends. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `passlib` / `bcrypt` | No password-based auth in this system. API keys are random tokens (SHA-256 hashed for storage). Adding bcrypt would bloat deps for zero benefit. | SHA-256 via `hashlib` (already used in `auth_registry.py`) |
| `hdrhistogram` (PyPI package) | C-native HDR histogram library is overengineered for reset-on-scrape percentile tracking. Pure-Python fallback is unmaintained (last release 2023). | Manual sorted-list with periodic reset |
| `python-jose` | Unmaintained since 2021. `pyjwt` is the de facto standard for JWT in Python. | `pyjwt[crypto]` (already installed) |
| React / Vue / Svelte | Requires npm, build step, CI pipeline changes, bundle analysis. Admin SPA is too simple to justify. | Alpine.js + HTMX + Bootstrap 5 (CDN) |
| `alembic` for DB migrations | The auth tables are simple (4 models, all in the same SQLite DB). Schema changes are unlikely. If needed later, a single migration script can be hand-written. Don't introduce alembic's complexity for 4 tables that may never migrate. | Raw SQL schema creation on first import (same pattern as `auth_registry.py`'s `_init_db()`) |
| Redis session store | JWT cookies are self-contained (no server-side session store needed). API key verification is a fast SQLite lookup. | JWT + SQLite direct lookup |

## Integration Points with Existing Stack

| New Component | Integrates With | How |
|---------------|-----------------|-----|
| Auth API (Phase 28b) | Existing `auth_registry.py` | Auth API manages the same API keys that MCP transport auth uses. Auth API writes to the same `data/auth.db` via SQLAlchemy ORM. Backward compat: the existing sync `auth_registry.py` continues to work. |
| Auth API (Phase 28b) | Existing FastAPI health server (port 8001) | Auth API endpoints mount on the same FastAPI app (`kb_server/ui/app.py`) at `/api/v1/auth/`, `/api/v1/users/`, `/api/v1/api-keys/`. |
| Admin SPA (Phase 28c) | Existing Jinja2 templates | New `kb_server/ui/templates/admin/` directory; `shell.html` extends `base.html`; tab partials loaded via HTMX. |
| Admin SPA (Phase 28c) | Existing browse/search routes | Admin sidebar includes "Documents" tab linking to existing browse UI, updated with checkbox selection. |
| Config API (Phase 40) | `.env` file loading | Hot-reload chain: SQLite config → `.env` → env var defaults. `bootstrap_env()` modified to check SQLite overrides after loading `.env`. |
| Config API (Phase 40) | `kb_metadata.db` | Config table added to existing `kb_metadata.db` database (same file used for query logs). |
| Streamable HTTP (Phase 28) | Existing `mcp.server.Server` | `StreamableHTTPSessionManager(app=app)` wrapping existing `mcp.server.Server("kb-rag")` instance. Mounted as a third transport alongside stdio and SSE. |
| Request ID Middleware (Phase 39) | Existing logging | `logging.basicConfig` format updated to include `request_id` field. Context var `_current_request_id` set per-request, read by all log statements. |
| Percentile Metrics (Phase 39) | Existing Prometheus `/metrics` | Histogram values exported as Prometheus Gauge metrics (`search_kb_p50_ms`, `search_kb_p95_ms`, `search_kb_p99_ms`) with operation label. |
| Grafana Embed (Phase 38) | Existing health server | CSP middleware `frame-src` directive added to the Starlette/FastAPI app serving the admin UI. Time range selector passes `from`/`to` URL params to iframe. |
| Provider Aliases (Phase 41) | Existing `EmbedClient` | Resolution chain: `EMBED_BACKEND` env var → config lookup for `provider_alias.<value>` → resolved backend name. If no alias, use value as-is. |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `sqlalchemy>=2.0` | Python 3.11+ | SQLAlchemy 2.0+ supports native async via `AsyncEngine` and `async_sessionmaker`. No `greenlet` issues on py3.11+. |
| `aiosqlite>=0.22` | Python 3.10+ | 0.22.x is the current stable line. Pure Python, no binary deps. |
| `pyjwt[crypto]==2.12.1` | Python 3.8+ | Already pinned. Works with `cryptography==48.0.0`. |
| `alpinejs@3.15.12` | All modern browsers | Works with `defer` attribute in `<head>`. CDN file is 45KB minified. |
| `htmx.org@2.0.10` | All modern browsers | 50KB minified. v2.x drops IE11. All attributes used in admin SPA (`hx-get`, `hx-post`, `hx-trigger`, `hx-target`, `hx-swap`, `hx-headers`) are identical in v1 and v2. |
| `bootstrap@5.3.8` | All modern browsers | Patch-level upgrade from 5.3.0. No breaking changes. Requires Bootstrap JS bundle for sidebar toggle and modals. |

## Sources

- **MCP Python SDK README** (GitHub, v1.x branch) — Confirmed Streamable HTTP transport support at v1.19.0+. `<2` upper bound recommendation.
- **jsDelivr CDN** — Alpine.js 3.15.12 available, HTMX 2.0.10 available, Bootstrap 5.3.8 available.
- **HTMX official site** (htmx.org) — v2.0.10 is current stable; v4.0 in beta, target stable mid-2026.
- **Alpine.js official site** (alpinejs.dev) — v3.15.12 is current; CDN installation instructions.
- **Bootstrap docs** (getbootstrap.com) — v5.3.8 is latest; CDN installation with integrity hashes.
- **pyjwt PyPI** — v2.12.1 latest stable; `[crypto]` extras for RSA/EC support.
- **aiosqlite PyPI** — v0.22.1 latest; async SQLite wrapper.
- **hdrhistogram PyPI** — v0.10.7 latest (August 2023); pure Python HDR histogram implementation.
- **Existing codebase** (`requirements.txt`, `kb_server/server.py`, `kb_server/auth.py`, `kb_server/ui/app.py`, `kb_server/ui/templates/base.html`) — Validated current state.
- **Admin Platform Design spec** (`docs/superpowers/specs/2026-06-13-admin-platform-design.md`) — Architecture decisions.

---

*Stack research for: kb-rag-mcp v0.1.5 Admin Platform additions*
*Researched: 2026-06-15*
