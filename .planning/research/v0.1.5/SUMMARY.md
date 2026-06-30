# Project Research Summary

**Project:** kb-rag-mcp v0.1.5 — Admin Platform
**Domain:** Self-hosted RAG MCP server with browser-based admin panel
**Researched:** 2026-06-15
**Confidence:** HIGH

## Executive Summary

kb-rag-mcp is evolving from a CLI-first RAG MCP server into a full admin platform with browser-based management, user authentication, configuration hot-reload, observability, and Grafana dashboard embedding. Research confirms this is a **foundation-first build**: the admin SPA is gated on auth, auth is gated on config (for JWT secrets), and config/streamable-http have no dependencies and can be built first. The recommended approach adds **zero new containers** to the deployment topology — everything lives inside the existing FastAPI+Jinja2 `web-ui` service.

The core differentiator vs. competitors (Open WebUI, Dify, AnythingLLM) is **MCP-first architecture**. The admin panel supports the MCP server, not replaces it. Key competitive advantages include GDPR erasure workflows with full audit trail, config hot-reload without restart, Grafana dashboard embedding, and provider alias resolution — all built on the existing Python 3.11+ stack with only **2 new pip dependencies** (`sqlalchemy` declared explicitly, `aiosqlite` for async DB) and a **zero-build-step frontend** (Alpine.js + HTMX + Bootstrap 5 via CDN).

**Key risks** center on security boundary enforcement: auth bypass on the Streamable HTTP `/mcp` endpoint if middleware is method-naive (GET stream requires auth!), CSP conflicts between Alpine.js and Grafana iframe embedding, SQLite WAL unbounded growth under new concurrent write load, and localStorage-based API key storage enabling XSS exfiltration. All are preventable with known patterns (ASGI auth middleware, Alpine.js CSP build, WAL pragmas on all connections, HttpOnly session cookies). The most expensive-to-fix pitfall is GDPR erasure leaving PII in audit log free-text fields — requires a data inventory before any erasure code is written.

## Key Findings

### Recommended Stack

The v0.1.5 admin platform adds **minimal new technology** to the validated Python 3.11+ / FastAPI / Qdrant / MCP stack. Only 2 new pip dependencies needed; frontend is CDN-only with zero build step.

**Core additions:**
- **`sqlalchemy>=2.0`**: Declare existing transitive dep explicitly for Phase 28b auth models (User, ApiKey, AuditLog, ErasureRequest) with async ORM support
- **`aiosqlite>=0.22`**: Async SQLite driver for SQLAlchemy async sessions in FastAPI — pure Python, no C deps, required for async ORM from asyncio endpoints
- **`mcp>=1.27.0,<2`**: Add `<2` upper bound to prevent accidental upgrade to v2.0 (alpha, target stable 2026-07-27). Streamable HTTP transport is fully supported in v1.27.1.
- **Alpine.js 3.15.12** (CDN): Zero-build-step reactivity for SPA state (tab switching, modals, auth state). 45KB minified.
- **HTMX 2.0.10** (CDN): Server-rendered tab partials via `hx-get`/`hx-trigger`. 50KB minified. Upgrade from existing 1.9.10 is safe (backward compat for used attributes).
- **Bootstrap 5.3.8** (CDN): Sidebar layout, tables, modals, form controls. Patch-level upgrade from 5.3.0.

**Zero new deps needed for:** MCP Streamable HTTP (built into `mcp>=1.19.0`), JWT sessions (`pyjwt[crypto]` already installed), Auth API (FastAPI Depends guards already available), Config REST API (FastAPI + SQLite), Provider Aliases (config-based resolution), Percentile metrics (sorted-list approach), CSP middleware (Starlette middleware), CSV/JSON export (Python stdlib).

See [STACK.md](STACK.md) for full details.

### Expected Features

**Must have (P1 — admin platform is incomplete without these):**
- **Streamable HTTP Transport** — enables browser-based MCP clients; plan already exists
- **Auth & User Management API** — gates admin SPA; includes User/ApiKey/AuditLog/ErasureRequest models + CRUD
- **Admin SPA shell with login** — tabbed layout (Documents, Monitoring, Ingestion, Admin, Profile), role gating
- **Config API + Admin Config tab** — core differentiator; edit settings from browser with hot-reload
- **Monitor lights bar** — 7-light health indicator; low effort, high ops confidence signal
- **Profile tab** — API key management (create/list/revoke), GDPR erasure request, user data export
- **Grafana embed in Monitoring tab** — single-pane-of-glass with existing 6-tab dashboard
- **Document browse cleanup** — checkbox selection + delete/re-ingest actions on existing browse UI

**Should have (P2 — P3):**
- Advanced filters (date range, file type, vendor, product)
- Document export (CSV/JSON with filter integration)
- RAGAS evaluation tab (run golden-set eval from browser)
- Ingestion tab (manual job create + monitoring)
- Provider alias config (multi-backend name resolution)
- Percentile metrics (p50/p95/p99 per operation)
- Request ID middleware (correlate MCP calls with logs)

**Defer (v0.2+):** Ingestion scheduler tab, SSO/OAuth, password-based auth, built-in chat UI (anti-feature).

See [FEATURES.md](FEATURES.md) for full analysis including competitor comparison across Open WebUI, Dify, RAGFlow, and AnythingLLM.

### Architecture Approach

The admin platform adds **three new packages** to the existing codebase, all living inside the existing `web-ui` container — no new services or containers:

1. **`kb_server/auth/`** — SQLAlchemy models (User, ApiKey, AuditLog, ErasureRequest), Pydantic schemas, FastAPI Depends guards, CRUD service, REST router. Separate from existing `auth.py` + `auth_registry.py` (which handle MCP transport key-only auth).
2. **`kb_server/config/`** — Config REST API, layered config loader (SQLite → `.env` → defaults), hot-reload event bus with version-based change detection. Config table added to existing `kb_metadata.db`.
3. **`kb_server/observability/`** — Request ID middleware (Starlette `BaseHTTPMiddleware` + contextvars), per-operation percentile metrics (bounded-memory ring buffer or HDR histogram), Prometheus gauge export.

**Key patterns:**
- **Config Chain (Layered Override):** SQLite → `.env` → defaults. Hot-reload via event bus with version counter. Components call `reload_if_changed()` — must be synchronous to avoid race conditions.
- **FastAPI Depends Authorization Chain:** API key (Bearer header) or JWT (session cookie) → user lookup → role check. Middleware applied to ALL HTTP methods on `/mcp` (GET stream requires auth too!).
- **Admin SPA:** Server-rendered Jinja2 partials, loaded via HTMX into Alpine.js-managed tabs. No build step. No client-side routing.
- **GDPR Erasure:** State machine with tombstone pattern + free-text scrubbing + erasure ledger for crash recovery.

**What stays unchanged:** MCP transport selection, MCP auth (`auth.py` + `auth_registry.py`), ingest pipeline, UI routes, health server, metrics endpoint, all 1165+ existing tests.

See [ARCHITECTURE.md](ARCHITECTURE.md) for full data flow diagrams, component responsibilities, and anti-patterns.

### Critical Pitfalls

1. **Auth bypass on MCP stream endpoint** — GET on `/mcp` (SSE stream) is the server→client return channel and MUST be authenticated. Implement auth as ASGI middleware that applies to ALL HTTP methods (GET/POST/DELETE/OPTIONS), not function-call-based per route.
2. **CSP conflict between Alpine.js and Grafana iframe** — Alpine.js default CDN build requires `'unsafe-eval'`; Grafana iframe requires `frame-src`. Use Alpine.js CSP build (`@alpinejs/csp`) instead. Implement explicit CSP middleware with nonce-based script loading.
3. **SQLite WAL unbounded growth under concurrent write load** — New auth/config/audit writes + existing non-WAL connections (query_logger.py, routes.py) will produce `SQLITE_BUSY`. Fix: `db_utils.py` helper that enables WAL on EVERY connection, set `journal_size_limit`, lower `wal_autocheckpoint`. This is a Phase 28b prerequisite.
4. **localStorage API key storage enables XSS exfiltration** — Admin SPA must use HttpOnly JWT cookies, not localStorage. Any stored XSS in config values would leak the key. Sanitize all config values (Jinja2 auto-escaping, no `| safe`). Add SRI integrity hashes to all CDN scripts.
5. **Streamable HTTP session orphan at disconnect** — Clients that disconnect without `DELETE /mcp` leak sessions. Implement mandatory idle timeout (300s default), session count limit, background cleanup task. Test with forced disconnect.
6. **GDPR erasure leaves PII in audit log free-text fields** — `AuditLog.details` JSON may contain unintentional PII. Requires `docs/DATA_INVENTORY.md` before erasure code, free-text scrubbing step in erasure workflow, and erasure ledger for crash recovery.
7. **Hot-reload race condition in config layer** — Broadcast-and-hook pattern is non-atomic. Use config version counter; make `reload_if_changed()` synchronous (no await in critical section); design config keys to be independently toggleable.

See [PITFALLS.md](PITFALLS.md) for full 10-pitfall analysis, recovery strategies, and per-pitfall test requirements.

## Implications for Roadmap

Based on the architecture dependency graph, suggested phase execution order:

### Phase 1: Foundation — Streamable HTTP + Config Backlog (Parallelizable)
**Rationale:** Both have zero dependencies. Phase 28 (Streamable HTTP) plan already exists. Phase 40 (Config API + loader + hot-reload) is needed by Auth (JWT secret storage) and Admin SPA (config tab). Running them in parallel saves time.
**Delivers:** Browser-compatible MCP transport (GET/POST/DELETE /mcp), config REST API, layered config loader, hot-reload event bus.
**Addresses features:** Streamable HTTP Transport (Phase 28), Config API (Phase 40 — P1 must-have)
**Avoids pitfalls:** Session orphan (idle timeout + session limit), hot-reload race condition (version counter + sync hooks)
**Research flag:** LOW — Streamable HTTP patterns are well-defined in MCP SDK; config layers are standard FastAPI+SQLite. Plan 28-01 already complete. But session lifecycle details (timeout values, test patterns) warrant a quick `/gsd-plan-phase --research-phase` for Phase 28.

### Phase 2: Backend Services — Auth API + Provider Aliases + Observability (Concurrent)
**Rationale:** Phase 28b (Auth & User API) gates the entire admin SPA — without it, no login, no user management, no admin role. Phase 41 (Provider Aliases) depends on Config table (built in Phase 1) but is self-contained. Phase 39's OBS-02 (Request ID) and METRICS-01 (Percentiles) have no deps. All three can run concurrently.
**Delivers:** User/ApiKey/AuditLog/ErasureRequest models + CRUD + GDPR erasure endpoints, JWT session auth, FastAPI Depends guards, API key management UI, provider alias resolution in EmbedClient, request ID middleware, percentile metrics.
**Addresses features:** Auth & User API (P1), Provider Aliases (P3), Request ID middleware (P3), Percentile metrics (P3)
**Avoids pitfalls:** JWT no-rotation hijack (opaque sessions or refresh rotation), GDPR audit-log PII (DATA_INVENTORY.md + free-text scrubbing), Non-WAL SQLite contention (db_utils.py pre-requisite task)
**Pre-requisite:** Dedicated task to migrate ALL existing SQLite connections to WAL mode via `db_utils.py` helper. Without this, Phase 28b + Phase 40 writes will cause `SQLITE_BUSY` regressions.
**Research flag:** MEDIUM — Auth is the most complex domain in v0.1.5. GDPR erasure workflow, refresh token rotation, and opaque session patterns need deeper research during Phase 28b planning. `/gsd-plan-phase --research-phase` recommended for Phase 28b.

### Phase 3: Admin SPA Shell
**Rationale:** Depends on Auth endpoints (Phase 28b) existing. The SPA shell provides the tabbed layout, login modal, and role-gated navigation. Tab partials load via HTMX from existing or new endpoints.
**Delivers:** Admin SPA with sidebar (Documents, Monitoring, Ingestion, Admin, Profile tabs), login/logout flow, role-gated tab visibility, CSP middleware with Alpine.js CSP build, nonce-based script loading.
**Addresses features:** Admin SPA shell (P1), Profile tab (P1), Monitor lights bar (P1), Document browse cleanup (P1)
**Avoids pitfalls:** CSP Grafana+Alpine conflict (CSP middleware + Alpine CSP build), localStorage XSS (HttpOnly cookie), CDN integrity (SRI hashes)
**Research flag:** MEDIUM — CSP configuration details (nonce generation in Starlette middleware, Alpine CSP build migration specifics) need research during Phase 28c planning. HTMX + CSP nonce integration is subtle.

### Phase 4: Grafana Embed + Health API Endpoint
**Rationale:** Depends on Phase 28c admin shell existing (monitoring tab template). Grafana embed is a standalone integration — iframe embed + time range selector + CSP `frame-src` config.
**Delivers:** Grafana dashboard embedded in Monitoring tab, time range selector, health API endpoint (`GET /api/v1/health`), CSP `frame-src` directive configured.
**Addresses features:** Grafana Dashboard Embed (P1 — monitoring tab)
**Avoids pitfalls:** Grafana embed CSP (verify `frame-src` matches GRAFANA_URL, test with `curl -I`)
**Research flag:** LOW — Standard iframe embed pattern. Grafana configuration (`allow_embedding`, `frame-ancestors`) is well-documented.

### Phase 5: SPA Enhancements — Advanced Filters + Export + Ingestion Tab
**Rationale:** All depend on admin shell existing. Each is independent and can be ordered by priority. Advanced filters and document export enhance the existing browse experience. Ingestion tab provides job management from browser.
**Delivers:** Date range/file type/vendor/product filters on document browse, CSV/JSON export with filter integration, ingestion job create + monitor + schedule UI.
**Addresses features:** Advanced Filters (P2), Document Export (P2), Ingestion Tab (P2)
**Research flag:** LOW — Standard CRUD patterns, all existing backend services already exist.

### Phase Ordering Rationale

- **Foundation-first** (Phase 1) is driven by dependency analysis: Config has zero deps and is needed by everything else. Streamable HTTP is the enabler for browser-based MCP clients.
- **Auth gates the SPA** (Phase 2 before Phase 3) — the admin SPA cannot function without login, role gating, and API key management. Building auth first also validates the Config + SQLAlchemy patterns.
- **Security-sensitive prereqs first** — the SQLite WAL migration task must happen BEFORE any Phase 2 concurrent writes begin. CSP middleware must be configured BEFORE any SPA templates are written.
- **Observability is parallel-suitable** (Phase 2) — Request ID and Percentiles have no deps and can be built concurrently with Auth.
- **Grafana and SPA enhancements** are natural follow-ups once the admin shell exists.

### Research Flags

Phases needing deeper research during planning:
- **Phase 28 (Streamable HTTP):** Session lifecycle management (timeout values, session resumption patterns, SSE stream auth). LOW complexity but has security implications. Quick research recommended.
- **Phase 28b (Auth & User API):** HIGH complexity. GDPR erasure state machine design, refresh token rotation with reuse detection, opaque session vs JWT trade-off for browser SPA, data inventory scope. `/gsd-plan-phase --research-phase` recommended.
- **Phase 28c (Admin SPA):** CSP nonce generation in Starlette middleware patterns, Alpine.js CSP build migration steps, HTMX + CSP nonce integration. MEDIUM complexity. Research during planning recommended.
- **Phase 40 (Config):** Hot-reload event bus implementation patterns in asyncio. Can be verified by quick research but patterns are well-understood.

Phases with standard patterns (skip research-phase):
- **Phase 38 (Grafana Embed):** Standard iframe embed. Well-documented. Skip research.
- **Phase 39 (OBS-02, METRICS-01):** Starlette middleware and Prometheus gauge patterns are established in codebase. Skip research.
- **Phase 41 (Provider Aliases):** Config table lookup + EmbedClient modification. Trivially simple. Skip research.
- **SPA-04 / SPA-05 (Export / Filters):** Standard CRUD + CSV/JSON serialization. Skip research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against official sources: MCP SDK README, jsDelivr CDN listings, PyPI releases, HTMX/Alpine/Bootstrap official docs. Existing `requirements.txt` cross-referenced. |
| Features | HIGH | Competitor analysis across 4 major projects (Open WebUI 126k★, Dify 130k★, RAGFlow, AnythingLLM 30k★). Feature matrix verified against current product docs. Anti-features sourced from domain experience with self-hosted tools. |
| Architecture | HIGH | Based on existing codebase inspection (server.py, auth.py, auth_registry.py, ui/app.py, health.py, observability/metrics.py, ingest/job/manager.py). Design spec cross-referenced. Anti-patterns derived from common mistakes in similar projects. |
| Pitfalls | HIGH | Sourced from: MCP Streamable HTTP spec, SQLite WAL documentation, Auth0/OWASP security best practices, GDPR engineering guides, Prometheus best practices, Starlette CSP implementation docs. Each pitfall has verified prevention strategy and test requirement. |

**Overall confidence:** HIGH

### Gaps to Address

- **MCP session timeout default value** — `MCP_SESSION_TIMEOUT=300s` is a reasonable starting point but should be validated against real deployment patterns. Monitor and adjust after launch.
- **Grafana URL validation regex** — The CSP `frame-src` needs to be configurable and validated. The regex pattern needs to be specific enough for deployment configurations (e.g., allowing `https://grafana.{namespace}.svc.cluster.local` in Kubernetes). Define during Phase 38 implementation.
- **CSP nonce generation performance** — Generating a unique nonce per request via `secrets.token_urlsafe()` adds ~0.001ms per request. Validate this doesn't become an issue at 1000+ req/s (unlikely for admin SPA which serves one user).
- **SQLite vs PostgreSQL migration thresholds** — Current design assumes SQLite is sufficient for 0-10 admin users. Monitor auth/config write contention after launch. Define threshold metrics (writes/second, `SQLITE_BUSY` rate) that trigger migration consideration.
- **Embedding model hot-reload caveat** — Config API warns "some changes require restart" but the UX for this is not designed. Define which config keys need restart and how the UI communicates this. Document in Phase 40.

## Sources

### Primary (HIGH confidence)
- MCP Python SDK README (GitHub, v1.x branch) — Streamable HTTP transport support at v1.19.0+, `<2` bound recommendation
- jsDelivr CDN — Alpine.js 3.15.12, HTMX 2.0.10, Bootstrap 5.3.8 availability
- Alpine.js official docs (alpinejs.dev) — CSP build documentation
- SQLite WAL mode documentation — auto-checkpoint behavior, journal_size_limit
- Auth0 Token Storage Best Practices — localStorage vs HttpOnly cookie for SPA
- OWASP JWT Cheat Sheet — refresh token rotation, reuse detection
- Prometheus Histogram best practices — bounded-memory percentile computation
- Grafana embedding docs — `allow_embedding`, `frame-ancestors` configuration
- Existing codebase (`requirements.txt`, `server.py`, `auth.py`, `ui/app.py`, etc.) — validated current state

### Secondary (MEDIUM confidence)
- HTMX Web Security Basics — CSS/HTML injection prevention, CSP interaction
- GDPR Right to Erasure Engineering (Wolf-Tech) — tombstone patterns, audit-log PII scrubbing
- FastAPI + SQLAlchemy async + SQLite WAL — `create_async_engine` connection pragma setup
- Starlette Middleware CSP implementation — nonce-based script-src
- Open WebUI (126k★), Dify (130k★), RAGFlow, AnythingLLM (30k★) — feature comparison

### Tertiary (LOW confidence)
- SQLite Forum: WAL file unbounded growth under continuous writes — community reports, not official docs
- hdrhistogram PyPI (v0.10.7) — pure Python HDR histogram; evaluated but not selected
- PyJWT recommended refresh token patterns — various blog posts, not official PyJWT docs

---

*Research completed: 2026-06-15*
*Ready for roadmap: yes*
