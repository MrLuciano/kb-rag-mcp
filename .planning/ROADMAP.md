# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v0.1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](milestones/v0.1.0-ROADMAP.md)
- ✅ **v0.1.1 Quality & Operational Excellence** — Phases 5–8 (shipped 2026-05-23) — [archive](milestones/v0.1.1-ROADMAP.md)
- ✅ **v0.1.2 Tech Debt & Classification** — Phases 9–11.1 (shipped 2026-05-27) — [archive](milestones/v0.1.2-ROADMAP.md)
- ✅ **v0.1.3 Post-Ship Polish & Infrastructure** — Phases 12–22 (shipped 2026-05-27) — [archive](milestones/v0.1.3-ROADMAP.md)
- ✅ **v0.1.4 Platform, Analytics & Enterprise** — Phases 23–37 (shipped 2026-06-11) — [archive](milestones/v0.1.4-ROADMAP.md)
- 🔄 **v0.1.5 Streamable HTTP & Management Platform** — Phases 28 (reopened), 28b, 28c, 38, 39, 40, 41 (active)

## Phases

<details>
<summary>✅ v0.1.0 Release-Readiness (Phases 1–4) — SHIPPED 2026-05-19</summary>

- [x] Phase 1: Codebase Consolidation (4/4 plans) — completed 2026-05-16
- [x] Phase 2: Data Integrity & Security (3/3 plans) — completed 2026-05-17
- [x] Phase 3: Test Coverage & CI (3/3 plans) — completed 2026-05-19
- [x] Phase 4: Deployment & Release (inline) — completed 2026-05-19

**Delivered:** Deleted legacy `server/` module, implemented real BM25 hybrid search, unified env loading,
file-watcher deletion, secrets remediation, 88% branch coverage (491 tests), GitHub Actions CI,
multi-stage Dockerfile, quickstart.sh, and new README getting-started guide.

</details>

<details>
<summary>✅ v0.1.1 Quality & Operational Excellence (Phases 5-8) — SHIPPED 2026-05-23</summary>

- [x] Phase 5: SSE Stability & Python 3.13 Compatibility (2/2 plans) — completed 2026-05-21
- [x] Phase 6: Test Coverage & Isolation (3/3 plans) — completed 2026-05-22
- [x] Phase 7: Logging, Quality Gate & Coverage Enforcement (2/2 plans) — completed 2026-05-23
- [x] Phase 8: Ingest Improvements & Documentation (3/3 plans) — completed 2026-05-23

**Delivered:** SSE stability with Python 3.13 support, full test isolation (518 unit tests pass without Qdrant/LM Studio/Redis), 90% branch coverage enforcement on PR-to-master, OTCS auto-tagging for 10 OpenText products, `kb-ingest status` CLI command, English-only codebase with 105 docstring gaps fixed (32 missing + 73 Portuguese → 0), comprehensive documentation refresh.

</details>

<details>
<summary>✅ v0.1.2 Tech Debt & Classification (Phases 9–11.1) — SHIPPED 2026-05-27</summary>

- [x] Phase 9: Startup Reliability (3/3 plans) — completed 2026-05-25
- [x] Phase 10: CI & Test Infrastructure (3/3 plans) — completed 2026-05-25
- [x] Phase 11: Auto-Classification (2/2 plans) — completed 2026-05-25
- [x] Phase 11.1: Vendor/Subsystem Integration Completion (1/1 plan) — completed 2026-05-27

**Delivered:** Lazy cross-encoder loading (~500MB saved, ~10s faster startup), pre-flight health checks with non-fatal warnings, `kb-ingest check health` CLI, 4 embedding backends documented (OPERATIONS.md), Helm lint CI gate, MagicMock pollution resolved (3 test files), logging coverage CI gate (40% threshold), auto-classification (Vendor/Product/Subsystem/Version), metadata gap-filling from PDF/DOCX, vendor/subsystem fields visible in search results and filterable via MCP tools.

</details>

<details>
<summary>✅ v0.1.3 Post-Ship Polish & Infrastructure (Phases 12–22) — SHIPPED 2026-05-27</summary>

- [x] Phase 12: English Comments & Docstrings (3/3 plans) — completed 2026-05-25
- [x] Phase 13: Docs Sync & Readme Languages (4/4 plans) — completed 2026-05-26
- [x] Phase 14: Health Dashboard (6/6 plans) — completed 2026-05-26
- [x] Phase 15: PowerShell Ports Script (2/2 plans) — completed 2026-05-26
- [x] Phase 16: Reclassification (3/3 plans) — completed 2026-05-27
- [x] Phase 17: Capability Negotiation (3/3 plans) — completed 2026-05-27
- [x] Phase 18: Grafana Datasource Fix (1/1 plan) — completed 2026-05-27
- [x] Phase 19: VERIFICATION.md Backfill (1/1 plan) — completed 2026-05-27
- [x] Phase 20: Test Environment Fixes (1/1 plan) — completed 2026-05-27
- [x] Phase 21: Codebase Hygiene Sweep (1/1 plan) — completed 2026-05-27
- [x] Phase 22: Integration Checker CI Gate (1/1 plan) — completed 2026-05-27

**Delivered:** English-only codebase (0 Portuguese comments; CI gate), multilingual README (EN/PT-BR/ES), Grafana + Prometheus monitoring stack (6 tabs, 28 panels, 4 services), PowerShell Windows firewall config, document reclassification engine with rollback, capability negotiation with FilterTermsCache, Grafana datasource fix (stable UID), 13 VERIFICATION.md backfill files + gap detection, LOG_PATH PermissionError fix, codebase hygiene sweep (13 unused imports, 3 TODOs, 2 dead code instances), integration checker CI gate (3 checks, needs: test).

</details>

## v0.1.4 Platform, Analytics & Enterprise

<details>
<summary>✅ v0.1.4 Phase Overview — SHIPPED 2026-06-11 — [archive](milestones/v0.1.4-ROADMAP.md)</summary>

**All 15 phases (23-37) complete:**

- [x] Phase 23: Documentation Overhaul — 3 plans — completed 2026-05-27
- [x] Phase 24: RAGAS Evaluation Pipeline — 4 plans — completed 2026-06-11
- [x] Phase 25: Optimization Experiments — 4 plans — completed 2026-06-11
- [x] Phase 26: KB Content Discoverability — 1 plan — completed 2026-06-03
- [x] Phase 27: Knowledge Base Registry — 1 plan — completed 2026-06-03
- [x] Phase 28: MCP Streamable HTTP Transport — 2 plans — completed 2026-06-03
- [x] Phase 29: Enterprise Data Source Connectors — 4 plans — completed 2026-06-10
- [x] Phase 30: Cross-Document Knowledge Graph — 2 plans — completed 2026-06-10
- [x] Phase 31: MCP Prompt Templates — 1 plan — completed 2026-06-10
- [x] Phase 32: API Key Authentication — 1 plan — completed 2026-06-10
- [x] Phase 33: Request Rate Limiting — 1 plan — completed 2026-06-10
- [x] Phase 34: Upload and Index Quotas — 1 plan — completed 2026-06-10
- [x] Phase 35: Multi-KB Aggregated Search — 1 plan — completed 2026-06-10
- [x] Phase 36: Provider Budget & Circuit Breaker — 1 plan — completed 2026-06-11
- [x] Phase 37: Request-level Retrieval Cache — 1 plan — completed 2026-06-11

**Delivered:** Documentation restructuring + KB content discoverability + KB Registry + MCP Streamable HTTP transport + Optimization Experiments + RAGAS Evaluation Pipeline + Multi-KB Aggregated Search + Enterprise Connectors + Cross-Document Knowledge Graph + MCP Prompt Templates + API Key Authentication + Rate Limiting + Quotas + Circuit Breakers + Retrieval Cache.

</details>

## v0.1.5 Streamable HTTP & Management Platform

<details open>
<summary>🔄 v0.1.5 Phase Overview — 16/17 PHASES COMPLETE</summary>

**Completed:** Phase 28, 28b, 28c, 28c-fixes, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 50

**Completed:** All 17 phases complete

- [x] Phase 28 (reopened): MCP Streamable HTTP Transport — single `/mcp` endpoint, `StreamableHTTPSessionManager`, CORS, auth middleware, session lifecycle, Prometheus metrics (completed 2026-06-15)
  - Plans: [28-01-PLAN.md](phases/28-mcp-streamable-http/28-01-PLAN.md) — 5 tasks (transport, auth, rate limit, docs)
  - [28-02-PLAN.md](phases/28-mcp-streamable-http/28-02-PLAN.md) — 2 tasks (session limit, metrics, sweep)
- [x] Phase 28b: Auth & User Management API — SQLAlchemy User/ApiKey/AuditLog models, CRUD REST endpoints, role-based access, GDPR erasure workflow (completed 2026-06-16)
  - Plans: [28b-01-PLAN.md](phases/28b-auth-api/28b-01-PLAN.md) — 7 tasks
- [x] Phase 28c: Admin SPA Panel — Alpine.js + HTMX tabbed UI at `/admin/`, login modal, admin/user role gating, tab content (config, monitoring, ingestion, RAGAS, browser cleanup, profile), advanced filters (date range, file type, vendor, product), document export (CSV/JSON) (completed 2026-06-16 via Phase 28c-fixes)
  - Plans: [28c-fixes-01-PLAN.md](phases/28c-fixes/28c-fixes-01-PLAN.md) — 3 tasks (auth, documents, CSP/SRI), [28c-fixes-02-PLAN.md](phases/28c-fixes/28c-fixes-02-PLAN.md) — 4 tasks (monitor, config, partials, route ordering), [28c-fixes-03-PLAN.md](phases/28c-fixes/28c-fixes-03-PLAN.md) — 4 tasks (auth router, Alpine.js CDN, gating, admin seeding), [28c-fixes-04-PLAN.md](phases/28c-fixes/28c-fixes-04-PLAN.md) — 2 tasks (session management, credentials)
- [x] Phase 28c-fixes: Admin SPA Gap Closure — Fix UAT failures from Phase 28c (auth flow, document browse, CSP/SRI, monitor lights, config editor, partials, route ordering, auth router mount, session management, credentials UI) (completed 2026-06-16)
  - Plans: [28c-fixes-01-PLAN.md](phases/28c-fixes/28c-fixes-01-PLAN.md) — 3 tasks, [28c-fixes-02-PLAN.md](phases/28c-fixes/28c-fixes-02-PLAN.md) — 4 tasks, [28c-fixes-03-PLAN.md](phases/28c-fixes/28c-fixes-03-PLAN.md) — 4 tasks, [28c-fixes-04-PLAN.md](phases/28c-fixes/28c-fixes-04-PLAN.md) — 2 tasks
- [x] Phase 38: Grafana Dashboard Embedding — iframe embed helper, time range selector, Jinja2 globals (completed 2026-06-16)
  - Plans: [38-01-PLAN.md](phases/38-grafana-embed/38-01-PLAN.md) — 1 task
- [x] Phase 39: Observability Backlog — OBS-01 (Grafana health check), OBS-02 (request ID middleware), METRICS-01 (percentile metrics) (completed 2026-06-16)
  - Plans: [39-01-PLAN.md](phases/39-observability/39-01-PLAN.md) — 4 tasks
- [x] Phase 40: Configuration Backlog — CONF-01 (config table + ConfigLoader), CONF-02 (config REST API), CONF-03-08 (hot-reload, seeding, os.getenv replacement) (completed 2026-06-16)
  - Plans: [40-01-PLAN.md](phases/40-config-backlog/40-01-PLAN.md) — 2 tasks, [40-02-PLAN.md](phases/40-config-backlog/40-02-PLAN.md) — 3 tasks
- [x] Phase 41: Provider Alias — PROV-01 (provider alias resolution + hot-reload) (completed 2026-06-16)
  - Plans: [41-01-PLAN.md](phases/41-provider-alias/41-01-PLAN.md) — 2 tasks (ConfigLoader alias methods + EmbedClient integration)
- [x] Phase 42: Query Logging Analytics Dashboard — Visualize query logs in the SPA (popular queries, no-results queries, latency distribution) (completed 2026-06-16)
  - Plans: [42-01-PLAN.md](phases/42-query-analytics-dashboard/42-01-PLAN.md) — 2 tasks (get_latency_stats + analytics route + template + tests)
- [x] Phase 43: Chunk Preview in Document Detail — Inline chunk viewer with highlight for matched terms (completed 2026-06-17)
  - Plans: [43-01-PLAN.md](phases/43-chunk-preview-document-detail/43-01-PLAN.md)
- [x] Phase 44: Auth Security Hardening — Mount auth router on server, erasure separation, ownership checks, secure cookie, verify_key batching, rate-limit hashing (completed 2026-06-17)
  - Plans: [44-01-PLAN.md](phases/44-auth-security-hardening/44-01-PLAN.md)
- [x] Phase 45: Database Reliability — SQLite connection leaks, FK enforcement, missing indexes, migration DDL safe re-runs (completed 2026-06-17)
  - Plans: [45-01-PLAN.md](phases/45-database-reliability/45-01-PLAN.md)
- [x] Phase 46: Code Quality & Coverage — utcnow deprecation fix, flake8 cleanup, coverage gap, test tagging, unused imports (completed 2026-06-17)
  - Plans: [46-01-PLAN.md](phases/46-code-quality-coverage/46-01-PLAN.md) — 3 tasks (utcnow replacement, F401 cleanup, integration tags)
- [x] Phase 47: LM Studio Dependency Handling — Graceful fallback when LM Studio is unreachable; startup health-check (completed 2026-06-17)
  - Plans: [47-01-PLAN.md](phases/47-lm-studio-dependency/47-01-PLAN.md) — 2 tasks (graceful error fallback + kb-ingest check embedding)
- [-] Phase 48: Cross-Encoder Lazy Loading — ✅ Already implemented and tested (shipped in v0.1.3 Phase 20)
  - Plans: Already done
- [-] Phase 49: Qdrant Mock Cleanup — ✅ Already resolved (Phase 10 imported real qdrant before stubs; conftest.py uses proper patch)
  - Plans: Already done
- [x] Phase 50: SSE Test Process Consolidation — Refactor test_smoke.py for per-function @patch to consolidate SSE test process (completed 2026-06-17)
  - Plans: [50-01-PLAN.md](phases/50-sse-test-consolidation/50-01-PLAN.md)

</details>

## Phase Details

### Phase 28: MCP Streamable HTTP Transport (Reopened)
**Goal**: Browser-compatible MCP transport via a single `/mcp` HTTP endpoint supporting GET (SSE stream), POST (JSON-RPC), DELETE (session terminate), and OPTIONS (CORS preflight)
**Depends on**: Nothing (parallel with Phase 40)
**Requirements**: SH-01, SH-02, SH-03, SH-04, SH-05
**Success Criteria** (what must be TRUE):
  1. Server starts Streamable HTTP transport when `MCP_TRANSPORT=streamable-http` is set
  2. Browser-based MCP clients can connect via GET (SSE stream), POST (JSON-RPC), and DELETE (session terminate) on `/mcp`
  3. Auth middleware applies to ALL HTTP methods on `/mcp` including the GET SSE stream
  4. Sessions are automatically cleaned up after idle timeout (300s default) with configurable session count limit
  5. Prometheus metrics track allowed/rejected requests per transport type
**Plans**: [28-01-PLAN.md](phases/28-mcp-streamable-http/28-01-PLAN.md) — 5 tasks (transport, auth, rate limit, docs), [28-02-PLAN.md](phases/28-mcp-streamable-http/28-02-PLAN.md) — 2 tasks (session limit, metrics, sweep)

### Phase 28b: Auth & User Management API
**Goal**: User authentication, role-based access control, API key management, and GDPR-compliant data management
**Depends on**: Phase 40 (JWT secret from config), Phase 28 (for WAL migration prereq)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10, AUTH-11, AUTH-12, AUTH-13, AUTH-14, AUTH-15
**Success Criteria** (what must be TRUE):
  1. Admin can create users and list them (paginated, no PII exposed)
  2. User can exchange API key for JWT session cookie via `POST /api/v1/auth/session` (HttpOnly, SameSite=Lax, 8h)
  3. User can view own profile (GDPR Article 15), manage API keys (create/list/revoke), and request GDPR erasure
  4. Admin can delete users (tombstone: anonymize username, clear hash, keep UUID) and manage GDPR erasure state machine
  5. All SQLite connections use WAL mode via `db_utils.py` helper; audit log auto-prunes after 90 days
**Plans**: [28b-01-PLAN.md](phases/28b-auth-api/28b-01-PLAN.md) — 7 tasks, [28b-02-PLAN.md](phases/28b-auth-api/28b-02-PLAN.md) — 2 tasks (gap closure: fix Users tab Alpine CSP + auth null)

### Phase 28c: Admin SPA Panel
**Goal**: Full browser-based admin panel with login, tabbed interface, role gating, document management, advanced filters, and document export
**Depends on**: Phase 28b (auth endpoints), Phase 40 (config REST API), Phase 38 (Grafana embed for monitoring tab), Phase 39 (health checks for monitor lights)
**Requirements**: SPA-01, SPA-02, SPA-03, SPA-04, SPA-05, SPA-06, SPA-07, SPA-08, SPA-09, SPA-10, SPA-11, SPA-12, FILT-01, FILT-02, FILT-03, FILT-04, FILT-05, EXPT-01, EXPT-02, EXPT-03, EXPT-04
**Success Criteria** (what must be TRUE):
   1. User can log in at `/admin/` with API key via login modal and receive JWT session cookie; logout clears cookie and resets auth state
   2. Tabbed interface shows Documents, Monitoring, Ingestion, Admin, and Profile tabs, role-gated (Admin tab admin-only)
   3. Admin can edit config values inline with inline editing, search, and reset-all; monitor lights bar auto-refreshes every 30s
   4. User can browse documents with advanced filters (date range, file type, vendor, product) with filter state reflected in URL query params
   5. User can export filtered document results as CSV or JSON; large exports run as background jobs with progress indicator
   6. CSP middleware uses Alpine.js CSP build with nonce-based script-src and `frame-src` for Grafana; all CDN scripts have SRI integrity hashes
**Plans**: [28c-01-PLAN.md](phases/28c-admin-spa-panel/28c-01-PLAN.md) — 3 tasks (shell + auth + CSP), [28c-02-PLAN.md](phases/28c-admin-spa-panel/28c-02-PLAN.md) — 3 tasks (monitor lights, config, profile + browse cleanup), [28c-03-PLAN.md](phases/28c-admin-spa-panel/28c-03-PLAN.md) — 3 tasks (filter-values API, get_documents enhancement, filter UI), [28c-04-PLAN.md](phases/28c-admin-spa-panel/28c-04-PLAN.md) — 2 tasks (export endpoint, export button wiring)
**UI hint**: yes

### Phase 28c-fixes: Admin SPA Gap Closure
**Goal**: Fix all UAT-verified gaps from Phase 28c so the Admin SPA matches the approved 28c-UI-SPEC.md design contract
**Depends on**: Phase 28c (core shell and tabs already built), Phase 28b (auth session endpoint), Phase 40 (config REST API)
**Requirements**: SPA-01, SPA-02, SPA-03, SPA-04, SPA-05, SPA-06, SPA-07, SPA-08, SPA-09, SPA-12
**Success Criteria** (what must be TRUE):
    1. Auth flow exchanges API key for JWT session cookie via POST /api/v1/auth/session; login modal uses Alpine.js x-show
    2. Document browse table has checkbox column, bulk toolbar, and per-document Actions dropdown with hx-confirm
    3. All inline scripts have CSP nonces; all CDN resources have SRI integrity hashes
    4. Monitor lights show 7 components with latency, click-to-expand details, ARIA labels, and warning state
    5. Config editor has Reset All button, Group badges, HTMX PUT save, and aria-live error announcements
    6. Missing ingestion and RAGAS partials exist and are loaded by parent tabs
    7. Sidebar width is 280px with icon-only (md) and hamburger (sm) responsive behavior
    8. All copywriting matches 28c-UI-SPEC.md (labels, empty states, placeholders, tab names)
    9. Alpine.js loads from valid CDN URL (no 404); error messages distinguish 401 vs 404 vs 500
   10. Auth router mounted on UI app; all admin tab endpoints server-side gated with Depends(get_current_user)
   11. Default admin account auto-seeded on first startup with API key logged to stdout
   12. Session timeout is configurable via env var (default 30 min); session tracking in UserSession table
   13. Admin can view active sessions and revoke them; Admin tab has API key management (generate/revoke)
**Plans**: [28c-fixes-01-PLAN.md](phases/28c-fixes/28c-fixes-01-PLAN.md) — 3 tasks (auth flow, document browse, CSP/SRI), [28c-fixes-02-PLAN.md](phases/28c-fixes/28c-fixes-02-PLAN.md) — 3 tasks (monitor lights, config editor, partials + copy/spacing), [28c-fixes-03-PLAN.md](phases/28c-fixes/28c-fixes-03-PLAN.md) — 3 tasks (Alpine.js CDN fix, auth router mount + admin seed, server-side auth gating), [28c-fixes-04-PLAN.md](phases/28c-fixes/28c-fixes-04-PLAN.md) — 2 tasks (session timeout + tracking, session management + credentials UI), [28c-fixes-05-PLAN.md](phases/28c-fixes/28c-fixes-05-PLAN.md) — 1 task (register adminApp via Alpine.data for CSP compatibility)

### Phase 38: Grafana Dashboard Embedding
**Goal**: Embed the existing Grafana monitoring dashboard inside the admin SPA Monitoring tab with configurable time ranges
**Depends on**: Phase 28c (admin shell with Monitoring tab template)
**Requirements**: GRAF-01, GRAF-02, GRAF-03, GRAF-04
**Success Criteria** (what must be TRUE):
  1. Grafana dashboard renders inside the Monitoring tab via iframe
  2. Time range selector (1h/6h/24h/7d) updates iframe `from`/`to` URL parameters
  3. CSP `frame-src` directive is configurable via `GRAFANA_URL` config entry
  4. Grafana is configured with `allow_embedding=true` and anonymous Viewer role
**Plans**: [38-01-PLAN.md](phases/38-grafana-embed/38-01-PLAN.md) — 1 task

### Phase 39: Observability Backlog
**Goal**: Request tracing, percentile latency metrics, and health endpoint with Grafana connectivity check for operational insight
**Depends on**: Nothing (parallel with Phase 28b, Phase 41)
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04
**Success Criteria** (what must be TRUE):
  1. Every HTTP request gets a unique `X-Request-Id` (UUID) header that propagates via context var and appears as response header
  2. P50/P95/P99 latency metrics are exposed for `search_kb`, `list_documents`, `get_chunk`, `kb_stats` operations
  3. Health API endpoint `GET /api/v1/health` includes Grafana connectivity check
  4. Percentile metrics use bounded-memory storage (sorted-list or ring buffer) and reset every scrape interval
**Plans**: [39-01-PLAN.md](phases/39-observability/39-01-PLAN.md) — 4 tasks

### Phase 40: Configuration Backlog
**Goal**: Database-backed configuration with layered loading, REST API, and hot-reload event bus
**Depends on**: Nothing (parallel with Phase 28)
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, CONF-06, CONF-07, CONF-08
**Success Criteria** (what must be TRUE):
  1. Config values stored in SQLite `config` table with key (TEXT PK), value, type, group, description, updated_at, updated_by
  2. Admin can view all config grouped by category, get single value, update value with type validation, and reset all to env defaults via REST API
  3. Config loader resolves values via chain: SQLite → `.env` file → `os.getenv` defaults
  4. Hot-reload event bus with version-based change detection notifies components via synchronous `reload_if_changed()` hooks
  5. System falls back gracefully if SQLite unavailable (→ `.env` → hardcoded defaults)
**Plans**: [40-01-PLAN.md](phases/40-config-backlog/40-01-PLAN.md) — 2 tasks (table, loader, router), [40-02-PLAN.md](phases/40-config-backlog/40-02-PLAN.md) — 3 tasks (mount, hot-reload, os.getenv replacement)

### Phase 41: Provider Alias
**Goal**: Configurable provider name aliases for multi-backend embedding resolution with hot-reload
**Depends on**: Phase 40 (config table entries for provider alias storage)
**Requirements**: PROV-01, PROV-02
**Success Criteria** (what must be TRUE):
  1. Admin can define provider aliases via config entries with group `provider_alias` and key pattern `provider_alias.<canonical_name>`
  2. `EmbedClient` reads aliases from config layer on resolution; falls back to value-as-is if no alias found
  3. Alias changes trigger hot-reload via the config event bus without server restart
**Plans**: [41-01-PLAN.md](phases/41-provider-alias/41-01-PLAN.md) — 2 tasks

### Phase 42: Query Logging Analytics Dashboard
**Goal**: Visualize query logs in the Admin SPA — show popular queries, no-results queries, and latency distribution
**Depends on**: Phase 28c (Admin SPA shell), Phase 39 (query logging infrastructure)
**Requirements**: SPA-02
**Success Criteria** (what must be TRUE):
  1. Admin SPA has a Query Analytics tab showing query log data
  2. Tab shows top-N most popular queries with count
  3. Tab shows queries that returned zero results (for content gap analysis)
  4. Latency distribution chart (p50/p95/p99) rendered in the SPA
  5. Data refreshes on tab visit or manual refresh
**Plans**: [42-01-PLAN.md](phases/42-query-analytics-dashboard/42-01-PLAN.md) — 1 plan, 2 tasks

### Phase 43: Chunk Preview in Document Detail
**Goal**: Inline chunk viewer in the document detail page that shows all chunks with matched term highlighting
**Depends on**: Phase 28c (Admin SPA detail view integration)
**Requirements**: SPA-03
**Success Criteria** (what must be TRUE):
   1. Document detail page shows an expandable chunk list
   2. Each chunk displays text content with chunk index label
   3. Search terms are highlighted within chunk text via server-side `<mark>` wrapping
   4. Chunks are paginated with HTMX progressive reveal
   5. Works with existing `/ui/document/{id}` route
**Plans**: [43-01-PLAN.md](phases/43-chunk-preview-document-detail/43-01-PLAN.md) — 3 tasks (backend route extension + accordion template + tests)

### Phase 44: Auth Security Hardening
**Goal**: Fix auth infrastructure gaps — mount auth router, add erasure separation of duties, enforce ownership checks, secure session cookies, batch verify_key writes, hash rate-limit subjects
**Depends on**: Phase 28b (Auth API — the endpoints being hardened)
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06
**Success Criteria** (what must be TRUE):
   1. Auth router mounted and all auth endpoints reachable at runtime
   2. Erasure approve and execute are separate endpoints callable by different roles
   3. export_user_data and list_api_keys verify caller owns the target user_id
   4. Session cookie sets secure=True when HTTPS is detected or env var is set
   5. verify_key does not write to DB on every call (batched or cached)
   6. API key prefix is not exposed in rate-limit subject tracking
**Plans**: 1 plan

Plans:
- [ ] 44-01-PLAN.md — 6 tasks: mount auth router, erasure separation, ownership checks, secure cookie, verify_key batching, rate-limit hashing

### Phase 45: Database Reliability
**Goal**: Fix SQLite connection management — use context managers everywhere, enforce foreign keys, add missing indexes, make migration DDL idempotent
**Depends on**: Nothing (infrastructure-level fixes)
**Requirements**: DB-01, DB-02, DB-03, DB-04
**Success Criteria** (what must be TRUE):
   1. All sqlite3.connect() calls in UI routes use context managers
   2. PRAGMA foreign_keys=ON is set on every SQLite connection
   3. Indexes exist on api_keys.prefix and query_log.timestamp
   4. All CREATE TABLE statements use IF NOT EXISTS
**Plans**: 1 plan

Plans:
- [ ] 45-01-PLAN.md — 4 tasks: connection context managers, FK PRAGMA, missing indexes, migration idempotency

### Phase 46: Code Quality & Coverage
**Goal**: Fix code quality baseline — migrate datetime.utcnow(), reduce flake8 violations to 0, close coverage gap, tag pre-existing test failures, remove unused imports
**Depends on**: Nothing
**Requirements**: Q-01, Q-02, Q-03, Q-04, Q-05
**Success Criteria** (what must be TRUE):
  1. Zero uses of deprecated datetime.utcnow() in source code
  2. flake8 exits with 0 on kb_server/ and ingest/
  3. Branch coverage meets or exceeds CI fail_under threshold
  4. Pre-existing test failures tagged with @pytest.mark.integration
  5. Zero unused imports in production code
**Plans**: 1 plan — [46-01-PLAN.md](phases/46-code-quality-coverage/46-01-PLAN.md) (3 tasks: utcnow replacement, F401 cleanup, integration tags)

### Phase 47: LM Studio Dependency Handling
**Goal**: Add graceful fallback when LM Studio / embedding backend is unreachable; add startup health-check and `kb-ingest check` command
**Depends on**: Nothing
**Requirements**: T-02
**Success Criteria** (what must be TRUE):
  1. Embedding health check warns at startup if backend unreachable (non-fatal)
  2. `kb-ingest check` validates LM Studio/Ollama connectivity
  3. Embedding pipeline reports clear error when backend is down (not a crash)
**Plans**: [47-01-PLAN.md](phases/47-lm-studio-dependency/47-01-PLAN.md) — 2 tasks (graceful error fallback + kb-ingest check embedding)

### Phase 48: Cross-Encoder Lazy Loading
**Goal**: Defer 500MB sentence-transformers CrossEncoder model load from import time to first predict() call
**Depends on**: Nothing
**Requirements**: T-03
**Status**: ✅ Already implemented and tested (shipped in v0.1.3 Phase 20). CrossEncoderReranker._load_model() lazily loads on first rerank() call.
**Plans**: Already shipped — no action needed.

### Phase 49: Qdrant Mock Cleanup
**Goal**: Replace sys.modules stubbing with unittest.mock.patch in test fixtures to eliminate MagicMock pollution
**Depends on**: Nothing
**Requirements**: T-04
**Status**: ✅ Already resolved (Phase 10: real qdrant_client imported before stubs; conftest.py uses proper @patch). 50 vector_store unit tests pass with real enum values.
**Plans**: Already shipped — no action needed.

### Phase 50: SSE Test Process Consolidation
**Goal**: Refactor test_smoke.py to use per-function @patch instead of module-level stubs, allowing SSE tests to run in the same process as other tests
**Depends on**: Phase 49 (Qdrant Mock Cleanup — to avoid conflicting stubs)
**Requirements**: T-05
**Success Criteria** (what must be TRUE):
  1. SSE tests no longer require a separate pytest process
  2. test_smoke.py uses per-function @patch decorators
  3. All tests pass when run together: `pytest tests/ -x`
**Plans**: 1 plan

Plans:
- [ ] 50-01-PLAN.md — Refactor test_smoke.py from module-level stubs to per-function fixtures

### Phase 51: Document Tag Management & Re-ingest Control
**Goal**: Bulk classification tag editor via CLI (`kb-rag tags`) and Web UI (`/admin/tags`) for correcting misclassified documents after ingestion
**Depends on**: Phase 28c (Admin SPA shell), Phase 45 (Registry bulk operations)
**Requirements**: TAG-01, TAG-02, TAG-03, TAG-04, TAG-05
**Success Criteria** (what must be TRUE):
  1. `kb-rag tags list` shows tag counts for Product, Type, Version, Status
  2. `kb-rag tags update --dry-run` previews bulk changes without side effects
  3. `kb-rag tags remove` deletes files from registry + Qdrant by payload filter
  4. `kb-rag tags reingest` sets status to pending and deletes Qdrant chunks
  5. Web UI `/admin/tags` shows filterable table with checkboxes and bulk actions toolbar
  6. All destructive operations require confirmation; dry-run available everywhere
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Codebase Consolidation | v0.1.0 | 4/4 | Complete | 2026-05-16 |
| 2. Data Integrity & Security | v0.1.0 | 3/3 | Complete | 2026-05-17 |
| 3. Test Coverage & CI | v0.1.0 | 3/3 | Complete | 2026-05-19 |
| 4. Deployment & Release | v0.1.0 | 3/3 | Complete | 2026-05-19 |
| 5. SSE Stability & Python 3.13 | v0.1.1 | 2/2 | Complete | 2026-05-21 |
| 6. Test Coverage & Isolation | v0.1.1 | 3/3 | Complete | 2026-05-22 |
| 7. Logging, Quality Gate & Coverage | v0.1.1 | 2/2 | Complete | 2026-05-23 |
| 8. Ingest Improvements & Docs | v0.1.1 | 3/3 | Complete | 2026-05-23 |
| 9. Startup Reliability | v0.1.2 | 3/3 | Complete | 2026-05-25 |
| 10. CI & Test Infrastructure | v0.1.2 | 3/3 | Complete | 2026-05-25 |
| 11. Auto-Classification | v0.1.2 | 2/2 | Complete | 2026-05-25 |
| 11.1. Vendor/Subsystem Integration | v0.1.2 | 1/1 | Complete | 2026-05-27 |
| 12. English Comments & Docstrings | v0.1.3 | 3/3 | Complete | 2026-05-25 |
| 13. Docs Sync & Readme Languages | v0.1.3 | 4/4 | Complete | 2026-05-26 |
| 14. Health Dashboard | v0.1.3 | 6/6 | Complete | 2026-05-26 |
| 15. PowerShell Ports Script | v0.1.3 | 2/2 | Complete | 2026-05-26 |
| 16. Reclassification | v0.1.3 | 3/3 | Complete | 2026-05-27 |
| 17. Capability Negotiation | v0.1.3 | 3/3 | Complete | 2026-05-27 |
| 18. Grafana Datasource Fix | v0.1.3 | 1/1 | Complete | 2026-05-27 |
| 19. VERIFICATION.md Backfill | v0.1.3 | 1/1 | Complete | 2026-05-27 |
| 20. Test Environment Fixes | v0.1.3 | 1/1 | Complete | 2026-05-27 |
| 21. Codebase Hygiene Sweep | v0.1.3 | 1/1 | Complete | 2026-05-27 |
| 22. Integration Checker CI Gate | v0.1.3 | 1/1 | Complete | 2026-05-27 |
| 23. Documentation Overhaul | v0.1.4 | 3/3 | Complete | 2026-05-27 |
| 24. RAGAS Evaluation Pipeline | v0.1.4 | 4/4 | Complete | 2026-06-11 |
| 25. Optimization Experiments | v0.1.4 | 4/4 | Complete | 2026-06-11 |
| 26. KB Content Discoverability | v0.1.4 | 1/1 | Complete | 2026-06-03 |
| 27. Knowledge Base Registry | v0.1.4 | 3/3 | Complete | 2026-06-03 |
| 28. MCP Streamable HTTP | v0.1.4 | 2/2 | Complete   | 2026-06-15 |
| 29. Enterprise Data Source Connectors | v0.1.4 | 4/4 | Complete | 2026-06-10 |
| 30. Cross-Document Knowledge Graph | v0.1.4 | 2/2 | Complete | 2026-06-10 |
| 31. MCP Prompt Templates | v0.1.4 | 1/1 | Complete | 2026-06-10 |
| 32. API Key Authentication | v0.1.4 | 1/1 | Complete | 2026-06-10 |
| 33. Request Rate Limiting | v0.1.4 | 1/1 | Complete | 2026-06-10 |
| 34. Upload and Index Quotas | v0.1.4 | 1/1 | Complete | 2026-06-10 |
| 35. Multi-KB Aggregated Search | v0.1.4 | 1/1 | Complete | 2026-06-10 |
| 36. Provider Budget & Circuit Breaker | v0.1.4 | 1/1 | Complete   | 2026-06-11 |
| 37. Request-level Retrieval Cache | v0.1.4 | 1/1 | Complete | 2026-06-11 |

| 28. MCP Streamable HTTP (reopened) | v0.1.5 | 2/2 | Complete | 2026-06-15 |
| 28b. Auth & User Management API | v0.1.5 | 2/2 | Gap closure (fix Users tab) | 2026-06-15 |
| 28c. Admin SPA Panel | v0.1.5 | 4/4 | Complete | 2026-06-15 |
| 38. Grafana Dashboard Embedding | v0.1.5 | 1/1 | Complete | 2026-06-15 |
| 39. Observability Backlog | v0.1.5 | 1/1 | Complete | 2026-06-15 |
| 40. Configuration Backlog | v0.1.5 | 1/1 | Complete | 2026-06-15 |
| 41. Provider Alias | v0.1.5 | 1/1 | Complete | 2026-06-15 |

| 42. Query Logging Analytics Dashboard | v0.1.5 | 1/1 | Complete | 2026-06-15 |
| 43. Chunk Preview in Document Detail | v0.1.5 | 1/1 | Complete | 2026-06-15 |
| 44. Auth Security Hardening | v0.1.5 | 1/1 | Complete | 2026-06-15 |
| 45. Database Reliability | v0.1.5 | 1/1 | Complete | 2026-06-15 |
| 46. Code Quality & Coverage | v0.1.5 | 1/1 | Complete | 2026-06-15 |
| 47. LM Studio Dependency Handling | v0.1.5 | 1/1 | Planned | — |
| 48. Cross-Encoder Lazy Loading | v0.1.5 | 1/1 | Complete | 2026-06-15 (pre-existing) |
| 49. Qdrant Mock Cleanup | v0.1.5 | 1/1 | Complete | 2026-06-15 (pre-existing) |
| 50. SSE Test Process Consolidation | v0.1.5 | 0/0 | Backlog | — |
| 51. Document Tag Management & Re-ingest Control | v0.1.5 | 1/1 | Complete | 2026-06-17 |

*Earlier milestones (v0.1.0–v0.1.3): see archived roadmaps in [milestones/](milestones/).*

## Backlog

### Phase 999.0: Ingestion Schedule Management (BACKLOG)
**Goal**: Create and manage CRON-based ingestion schedules from the Admin UI Schedule tab. Schedules trigger `kb-rag job create` with matching params on cron match. Monitor executions in the Monitor tab.
**Depends on**: Phase 28c (Admin SPA shell with Ingestion tab), Phase 40 (config REST API for config validation)
**Requirements**: SCHED-01, SCHED-02, SCHED-03, SCHED-04, SCHED-05
**Success Criteria** (what must be TRUE):
  1. Admin can view, create, update, and delete ingestion schedules from the Schedule tab
  2. Each schedule stores: name, cron expression, docs path, product, workers, priority, clean, force
  3. Background scheduler runs every 30s, creates Job when cron matches, updates last_run/next_run
  4. Schedules can be enabled/disabled without deletion
  5. Scheduled ingestion jobs appear in the Monitor tab alongside manually created jobs
**Plans**: TBD
**Spec**: [2026-06-24-ingestion-schedule-design.md](phases/999.0-ingestion-schedule/CONTEXT.md)


