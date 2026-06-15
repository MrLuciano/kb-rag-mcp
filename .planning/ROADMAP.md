# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v0.1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](milestones/v0.1.0-ROADMAP.md)
- ✅ **v0.1.1 Quality & Operational Excellence** — Phases 5–8 (shipped 2026-05-23) — [archive](milestones/v0.1.1-ROADMAP.md)
- ✅ **v0.1.2 Tech Debt & Classification** — Phases 9–11.1 (shipped 2026-05-27) — [archive](milestones/v0.1.2-ROADMAP.md)
- ✅ **v0.1.3 Post-Ship Polish & Infrastructure** — Phases 12–22 (shipped 2026-05-27) — [archive](milestones/v0.1.3-ROADMAP.md)
- ✅ **v0.1.4 Platform, Analytics & Enterprise** — Phases 23–37 (shipped 2026-06-11)
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

<details open>
<summary>✅ v0.1.4 Phase Overview — SHIPPED 2026-06-11</summary>

**All 15 phases (23-37) complete:**

- [x] Phase 23: Documentation Overhaul — 3 plans (doc reorganization, README restructuring, CHANGELOG/REFERENCE update) — completed 2026-05-27
- [x] Phase 24: RAGAS Evaluation Pipeline — 4 plans (custom metrics, dataset loading, CLI + exporter, LLM wrappers) — completed 2026-06-11
- [x] Phase 25: Optimization Experiments — 4 plans (chunking experiments, scoring experiments, metric computation, CLI runner) — completed 2026-06-11
- [x] Phase 26: KB Content Discoverability — Dynamic content-summary tool descriptions + `kb://overview` MCP Resource — completed 2026-06-03
- [x] Phase 27: Knowledge Base Registry — SQLite-backed KB registry with public/agent_private scopes, stable `kb_<id>` collection names — completed 2026-06-03
- [x] Phase 28: MCP Streamable HTTP Transport — `/mcp` HTTP endpoint alongside stdio/SSE — completed 2026-06-03
- [x] Phase 29: Enterprise Data Source Connectors — 4 plans (connector foundation, Confluence, JIRA, Git) — completed 2026-06-10
- [x] Phase 30: Cross-Document Knowledge Graph — 2 plans (graph metadata derivation, MCP tools) — completed 2026-06-10
- [x] Phase 31: MCP Prompt Templates — 1 plan (extract_answer + summarize_documents prompts) — completed 2026-06-10
- [x] Phase 32: API Key Authentication — 1 plan (SQLite key registry, SSE middleware, CLI) — completed 2026-06-10
- [x] Phase 33: Request Rate Limiting — 1 plan (token bucket per subject, HTTP 429, prometheus metrics) — completed 2026-06-10
- [x] Phase 34: Upload and Index Quotas — 1 plan (quota config/usage tables, CLI, ingest enforcement) — completed 2026-06-10
- [x] Phase 35: Multi-KB Aggregated Search — 1 plan (multi-KB search with resolve_multi, multi_search, merge + dedup) — completed 2026-06-10
- [x] Phase 36: Provider Budget & Circuit Breaker — 1 plan (resilience layer, circuit breaker, budget tracking, fallback chain, 7 prometheus metrics) — completed 2026-06-11
- [x] Phase 37: Request-level Retrieval Cache — 1 plan (LRU retrieval cache, deterministic cache keys, TTL expiry, invalidation hooks) — completed 2026-06-11

**Delivered:** Documentation restructuring + KB content discoverability + KB Registry with SQLite scoping (3 MCP CRUD tools, ingest `--kb-id` flag, legacy migration) + MCP Streamable HTTP transport (stdio + SSE + Streamable HTTP, 3 transports) + Optimization Experiments framework (chunking strategies, scoring variants, IR metrics, `kb-rag optimize` CLI) + RAGAS Evaluation Pipeline (4 custom metrics, dataset loading, CLI, 4 LLM backends) + Multi-KB Aggregated Search + Enterprise Connectors (Confluence, JIRA, Git) + Cross-Document Knowledge Graph + MCP Prompt Templates + API Key Authentication + Request Rate Limiting + Upload/Index Quotas + Provider Budget & Circuit Breaker + Request-level Retrieval Cache.

**All 15 phases (23-37) of v0.1.4 are complete.** Phase 24 (RAGAS Evaluation) was executed and verified — 4 plans, 57 tests. All features are implemented and tested.

</details>

## v0.1.5 Streamable HTTP & Management Platform

<details open>
<summary>🔄 v0.1.5 Phase Overview — PLANNING</summary>

**Target features:**

- [x] Phase 28 (reopened): MCP Streamable HTTP Transport — single `/mcp` endpoint, `StreamableHTTPSessionManager`, CORS, auth middleware, session lifecycle, Prometheus metrics (completed 2026-06-15)
  - Plans: [28-01-PLAN.md](phases/28-mcp-streamable-http/28-01-PLAN.md) — 5 tasks (transport, auth, rate limit, docs)
  - [28-02-PLAN.md](phases/28-mcp-streamable-http/28-02-PLAN.md) — 2 tasks (session limit, metrics, sweep)
- [ ] Phase 28b: Auth & User Management API — SQLAlchemy User/ApiKey/AuditLog models, CRUD REST endpoints, role-based access, GDPR erasure workflow
  - Plans: [28b-01-PLAN.md](phases/28b-auth-api/28b-01-PLAN.md) — 7 tasks
- [ ] Phase 28c: Admin SPA Panel — Alpine.js + HTMX tabbed UI at `/admin/`, login modal, admin/user role gating, tab content (config, monitoring, ingestion, RAGAS, browser cleanup, profile), advanced filters (date range, file type, vendor, product), document export (CSV/JSON)
  - Plans: [28c-01-PLAN.md](phases/28c-admin-spa-panel/28c-01-PLAN.md) — 2 tasks (shell), [28c-02-PLAN.md](phases/28c-admin-spa-panel/28c-02-PLAN.md) — 6 tasks (tab content), [28c-03-PLAN.md](phases/28c-admin-spa-panel/28c-03-PLAN.md) — TBD (advanced filters), [28c-04-PLAN.md](phases/28c-admin-spa-panel/28c-04-PLAN.md) — TBD (document export)
- [ ] Phase 38: Grafana Dashboard Embedding — iframe embed helper, time range selector, Jinja2 globals
  - Plans: [38-01-PLAN.md](phases/38-grafana-embed/38-01-PLAN.md) — 1 task
- [ ] Phase 39: Observability Backlog — OBS-01 (Grafana health check), OBS-02 (request ID middleware), METRICS-01 (percentile metrics)
  - Plans: [39-01-PLAN.md](phases/39-observability/39-01-PLAN.md) — 4 tasks
- [ ] Phase 40: Configuration Backlog — CONF-01 (config table + ConfigLoader), CONF-02 (config REST API)
  - Plans: [40-01-PLAN.md](phases/40-config-backlog/40-01-PLAN.md) — 2 tasks
- [-] Phase 41: Provider Alias — PROV-01 (provider alias resolution + hot-reload)
  - Plans: [41-01-PLAN.md](phases/41-provider-alias/41-01-PLAN.md) — 2 tasks (ConfigLoader alias methods + EmbedClient integration)

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
**Plans**: [28b-01-PLAN.md](phases/28b-auth-api/28b-01-PLAN.md) — 7 tasks

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
**Plans**: [28c-01-PLAN.md](phases/28c-admin-spa-panel/28c-01-PLAN.md) — 2 tasks (shell), [28c-02-PLAN.md](phases/28c-admin-spa-panel/28c-02-PLAN.md) — 6 tasks (tab content), 28c-03-PLAN.md — TBD (advanced filters), 28c-04-PLAN.md — TBD (document export)
**UI hint**: yes

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
**Plans**: [40-01-PLAN.md](phases/40-config-backlog/40-01-PLAN.md) — 2 tasks

### Phase 41: Provider Alias
**Goal**: Configurable provider name aliases for multi-backend embedding resolution with hot-reload
**Depends on**: Phase 40 (config table entries for provider alias storage)
**Requirements**: PROV-01, PROV-02
**Success Criteria** (what must be TRUE):
  1. Admin can define provider aliases via config entries with group `provider_alias` and key pattern `provider_alias.<canonical_name>`
  2. `EmbedClient` reads aliases from config layer on resolution; falls back to value-as-is if no alias found
  3. Alias changes trigger hot-reload via the config event bus without server restart
**Plans**: [41-01-PLAN.md](phases/41-provider-alias/41-01-PLAN.md) — 2 tasks

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

| 28. MCP Streamable HTTP (reopened) | v0.1.5 | 2/2 | Planning | — |
| 28b. Auth & User Management API | v0.1.5 | 1/1 | Planned | — |
| 28c. Admin SPA Panel | v0.1.5 | 4/4 | Planned | — |
| 38. Grafana Dashboard Embedding | v0.1.5 | 1/1 | Planned | — |
| 39. Observability Backlog | v0.1.5 | 1/1 | Planned | — |
| 40. Configuration Backlog | v0.1.5 | 1/1 | Planned | — |
| 41. Provider Alias | v0.1.5 | 1/1 | Planned | — |

*Earlier milestones (v0.1.0–v0.1.3): see archived roadmaps in [milestones/](milestones/).*

## Backlog

Items for future milestones (v0.1.6+).

### Low Priority

- **SPA-02: Query Logging Analytics Dashboard** — Visualize query logs in the SPA (popular queries, no-results queries, latency distribution)
- **SPA-03: Chunk Preview in Document Detail** — Inline chunk viewer with highlight for matched terms

### Phase 25: Optimization Experiments

**Goal:** Run systematic chunking and scoring experiments to optimize retrieval quality and provide actionable recommendations for RAG configuration.
**Requirements:** OPT-01, OPT-02, OPT-03
**Depends on:** Phase 24
**Plans:** 4/4 plans executed

Plans:

- [x] 25-01-PLAN.md — Core infrastructure: config, metric_computer, result_store
- [x] 25-02-PLAN.md — Chunking experiments: fixed, recursive, semantic strategies
- [x] 25-03-PLAN.md — Scoring experiments: dense, hybrid, reranked variants
- [x] 25-04-PLAN.md — Experiment runner + CLI: `kb-rag optimize` command
