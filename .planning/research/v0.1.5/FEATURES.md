# Feature Landscape: Admin Platform for Self-Hosted RAG Systems

**Domain:** Admin panel & management platform for self-hosted RAG document systems
**Researched:** 2026-06-15
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any serious admin panel for a self-hosted RAG/document system. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Workspace-level document browser with search** | Every RAG admin panel (Open WebUI, Dify, RAGFlow, AnythingLLM) has one — it's the primary UI surface | MEDIUM | Leverage existing `list_documents` endpoint; add pagination, search, filters in UI |
| **API-key authentication for MCP/API access** | Universal pattern: self-hosted tools authenticate programmatic access via Bearer API keys | LOW | Already exists (`kb_server/auth.py`); spec adds user→key binding, key management UI |
| **Session-based auth for browser admin** | Browser SPA cannot store and send raw API keys securely for every request; JWT cookie is standard (Open WebUI, Dify) | MEDIUM | Passwordless flow: API key → POST session → HttpOnly JWT cookie. Spec does this right. |
| **User management (CRUD, roles)** | Every multi-user system needs it. Open WebUI has admin/user/pending roles. Dify has workspace roles. | MEDIUM | Admin + user roles; tombstone pattern for GDPR. Spec covers this well. |
| **Live system health / status indicators** | Admins need to know if Qdrant, embedding, LLM are up. Open WebUI admin panel has this. | LOW | `GET /health/detailed` exists; add 7-light monitor bar with auto-refresh (30s). Spec is good. |
| **Configurable settings via UI** | Changing env vars → restart is 1990s. Every platform (Open WebUI Admin Settings, Dify Settings) has in-UI config. | MEDIUM | SQLite config table + hot-reload chain. Spec design is solid. |
| **Document export (CSV/JSON)** | Table stakes for any document management system. Every DMS (DocumentPro, xeve, Sanity) supports export with format choice. | LOW | Filtered export of document browse results; use existing filter params |
| **Browse / search documents with filters** | Navigating documents without filtering is unusable at scale. Open WebUI workspace has document browsing. | MEDIUM | Leverage `list_documents`; add date range, file type, vendor, product as query params |
| **Activity / audit logging** | Self-hosted tools need visibility into who did what. Open WebUI has usage analytics. Dify has logs. | MEDIUM | Already in spec: AuditLog model, query logging exists. Tab to view. |
| **Multiple transport support (stdio, SSE, Streamable HTTP)** | MCP client diversity demands it. stdio for local, SSE for existing clients, Streamable HTTP for browser-native. | LOW | Phase 28 plan already done. Streamable HTTP is new MCP standard (Mar 2025). |

### Differentiators (Competitive Advantage)

Features that set kb-rag-mcp apart from the Open WebUI / Dify / AnythingLLM crowd. Align with core value: "AI assistants stop hallucinating about closed-source products."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **MCP-first architecture (not chat-UI-first)** | kb-rag-mcp is an MCP *server* that exposes RAG tools to any MCP client (Claude, Cursor, OpenCode, Copilot). Admin panel *supports* this, not replaces it. All competitors are chat-UI-first. | N/A (architecture) | Core differentiator. Admin panel must *not* become a chat interface. |
| **GDPR erasure workflow with full audit trail** | Enterprise teams handling EU user data need provable erasure. Most RAG tools don't offer this. Dify has basic user mgmt but no Article 17 erasure. | HIGH | ErasureRequest state machine + tombstone pattern + 90-day auto-prune. Spec covers this. |
| **Provider alias system for embedding backends** | Teams using niche embedding providers (DashScope, Aliyun, custom) need configurable name resolution. No competitor offers this. | LOW | Config table `provider_alias.*` entries. Simple but powerful for multi-backend teams. |
| **Config hot-reload without restart** | Changing embedding model / chunk size / rate limits without server restart. Open WebUI needs env var → restart. Dify needs restart for some settings. | MEDIUM | SQLite → `.env` → env var chain with `reload_if_changed()` hooks. Spec design is sound. |
| **Grafana dashboard embedding with time range controls** | Existing 6-tab Grafana dashboard already exists. Embedding it in the admin panel creates a single-pane-of-glass. Open WebUI has NO Grafana integration. Dify has basic analytics only. | LOW | Iframe embed + time range selector + CSP `frame-src`. Grafana already deployed. |
| **HDR percentile metrics (p50/p95/p99)** | Standard in infra tools (Prometheus, Datadog), rare in RAG admin panels. Helps ops teams understand latency distribution per operation. | MEDIUM | In-memory sorted-list per operation, expose via existing `/metrics` endpoint. |
| **Request ID middleware for traceability** | Correlate MCP tool calls with logs. Standard in cloud services, rare in self-hosted RAG. | LOW | Starlette middleware + context var `_current_request_id`. |
| **API key management UI (create, list, revoke)** | Most tools require CLI or config file for API keys. Browser-based key management with one-time-show is better UX. | LOW | Create key (shown once via modal), list prefixes only, revoke. Spec covers this. |
| **Config grouped by category with inline editing** | Better than flat key-value editor. Groups: Embedding, Qdrant, Auth, Rate Limits, etc. | LOW | Config API returns grouped data; UI renders collapsible group sections. |
| **RAGAS evaluation from admin panel** | Run golden-set evaluations from browser, see results history. Dify has basic eval. Open WebUI has model arena (different purpose). | MEDIUM | Golden set CRUD + run eval button + results history table. Leverage existing `RAGASEvaluator`. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem useful but create maintenance burden, security holes, or architectural drift.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Built-in chat UI ("just let me ask questions from the admin panel")** | Users want an immediate gratification "try it" experience without leaving the admin panel | Creates duplicate of every MCP client (Claude Code already does chat). Adds prompt management, conversation history, streaming UI complexity. Drifts from MCP-server core identity. | Provide a "playground" tab that calls `search_kb` directly and shows raw results + tool response, NOT a full chat. Or link to "configure your MCP client" docs. |
| **Password-based auth (username + password login)** | Familiar login UX; users ask for it instinctively | Password infrastructure: hashing, reset flows, rate limiting, breach detection. Complicates the "API key is the ground truth" model. Shifts from machine-to-machine auth to human auth. | Passwordless API key + JWT session flow as specified. API key is the single credential for both programmatic and browser use. |
| **Real-time document editing / collaborative annotation** | "Why can't I edit documents directly in the admin panel?" | Shifts from document management system to full document editor. Requires rich text editor, versioning, conflict resolution, permissions matrix. | Keep documents as source-of-truth files (PDF/DOCX). Admin panel manages metadata, ingestion, and search. Editing happens in native tools. |
| **Multi-factor authentication (MFA)** | Security-conscious teams want it for admin access | Adds TOTP/WebAuthn dependency, enrollment flow, recovery codes. Self-hosted tool — security is deployer's responsibility. They already have network-level controls (VPN, Cloudflare Access). | Document that the system supports reverse-proxy auth (Cloudflare Access, Authentik, Authelia) for admin routes. The API-key → JWT flow is simple and secure enough for internal use. |
| **Team collaboration features (comments, @mentions, sharing)** | "Slack for documents" overlap | Scope creep into collaboration platform territory. Would need real-time DB, notifications, presence. | Keep admin panel focused on management. Collaboration happens in the MCP clients (Claude Code, etc.) where users already work. |
| **OAuth/SAML/SSO integration** | Enterprise SSO is a common requirement | Heavy integration effort for each provider. Requires OIDC flows, IdP metadata parsing, SCIM provisioning. Out of scope for a self-hosted internal tool. Teams already have reverse-proxy auth. | Document "Auth via reverse proxy" pattern (Cloudflare Access, Authentik, Authelia). Admin panel respects `X-Forwarded-User` header when behind proxy. |
| **Drag-and-drop document upload in admin panel** | Feels more intuitive than CLI or file watcher | File upload in browser has size limits (typically 100MB-1GB). Teams with large doc sets (PDFs, PPTXs) need batch ingest via file system. Duplicates CLI ingest. | Admin panel provides "Ingest from path" input + file watcher status. Bulk upload remains CLI/automation concern. Add file upload for small single docs but don't build a full upload manager. |
| **User-facing notification system (email/push)** | "Notify me when ingest completes / errors occur" | SMTP configuration, email templates, notification preferences, push infrastructure. Adds significant surface area for an internal tool. | Simple: admin panel shows job status via polling. Critical: webhook integration (slack/discord) for job completion/errors — already in Open WebUI model. |

## Feature Dependencies

```
Streamable HTTP Transport
    └──requires──> MCP server initialization (existing)
    └──requires──> Starlette app with CORS middleware (existing)
    └──requires──> Auth middleware (existing auth.py)
    └──requires──> Rate limiting (existing)

Auth & User Management API
    └──requires──> SQLAlchemy models (User, ApiKey, AuditLog, ErasureRequest)
    └──requires──> FastAPI Depends() guards
    └──requires──> JWT token generation (python-jose or PyJWT)
    └──requires──> Existing auth.py (API key verification)
    └──enhances──> Streamable HTTP Transport (adds session auth)

Admin SPA Panel
    └──requires──> Auth & User Management API (login flow)
    └──requires──> Jinja2 FastAPI backend (existing)
    └──requires──> Alpine.js + HTMX + Bootstrap 5 (CDN, no build step)
    └──requires──> Config API (for admin config tab)
    └──requires──> Health endpoint (existing, for monitor lights)
    └──enhances──> Browse UI (adds cleanup controls)

Config API + Hot-reload
    └──requires──> SQLite kb_metadata.db (existing)
    └──requires──> Config table schema (key, value, type, group, description)
    └──requires──> ConfigLoader (SQLite → .env → env defaults chain)
    └──requires──> REST endpoints (GET/PUT/reset)
    └──requires──> Hot-reload event system with reload_if_changed() hooks

Grafana Dashboard Embedding
    └──requires──> Grafana instance (already deployed, dashboard exists)
    └──requires──> Grafana config: allow_embedding = true
    └──requires──> CSP frame-src configuration
    └──requires──> Grafana anonymous Viewer role (or API token auth)
    └──enhances──> Monitoring tab in admin SPA

Observability Backlog
    └──requires──> Health check improvements (Grafana check)
    └──requires──> Request ID middleware (Starlette middleware)
    └──requires──> HDR histogram for percentile metrics
    └──requires──> Prometheus /metrics endpoint (existing)

Provider Alias
    └──requires──> Config table (key pattern: provider_alias.*)
    └──requires──> EmbedClient provider resolution hook
    └──requires──> Hot-reload support

Document Export (CSV/JSON)
    └──requires──> Document browse endpoint with filter params
    └──requires──> CSV and JSON serialization
    └──requires──> Download trigger in browser

Advanced Filters
    └──requires──> Document metadata with date fields, file_type, vendor, product
    └──requires──> list_documents endpoint with filter query params
    └──requires──> UI filter controls (date picker, dropdowns)

Ingestion Tab + Scheduler
    └──requires──> JobManager.create_job() (existing, modify for programmatic use)
    └──requires──> JobManager with progress tracking (existing)
    └──requires──> Scheduler background task
    └──requires──> Schedules config table
    └──enhances──> Admin SPA (admin configs in UI)

RAGAS Evaluation Tab
    └──requires──> RAGASEvaluator (existing)
    └──requires──> Golden set CRUD (JSON file or DB)
    └──requires──> Results history storage
    └──enhances──> Admin SPA (run eval from UI)
```

### Dependency Notes

- **Streamable HTTP is foundational** — it enables the whole "browser-compatible MCP" story. Auth builds on top of it.
- **Auth & User API is gating** — the Admin SPA cannot work without it. Login flow, role gating, API key management all depend on it.
- **Config API enables hot-reload** — Provider aliases, embedding backend selection, and many settings flow through it.
- **Grafana embed is standalone** — no dependency on auth or config APIs, just needs Grafana running.
- **Export and Filters are SPA features** — they enhance the document browse experience but don't block other features.
- **RAGAS tab is independent** — depends on existing `RAGASEvaluator`, not on new auth/config infrastructure.
- **Ingestion scheduler is nice-to-have** — manual ingest via job create works without it; scheduler adds convenience.

## MVP Definition

### Launch With (Phase 28, 28b, 28c, 38, 39, 40, 41 — v0.1.5)

What's minimally needed for the admin platform to be useful:

- [x] **Streamable HTTP Transport** — Phase 28 Plan 28-01 already done. Enables browser-based MCP clients.
- [ ] **Auth & User Management API** — gating feature. Without it, admin SPA has no auth. Includes User/ApiKey/AuditLog/ErasureRequest models + CRUD endpoints.
- [ ] **Admin SPA shell with login** — tabbed layout, login modal, role gating. Sidebar with Documents, Monitoring, Ingestion, Admin, Profile tabs.
- [ ] **Config API + Admin Config tab** — core UX differentiator. Admin can change settings from browser.
- [ ] **Monitor lights bar** — 7-light health indicator. Low effort, high confidence signal for ops teams.
- [ ] **Profile tab** — API key management, user data export, erasure request. Needed to complete auth story.
- [ ] **Grafana embed in Monitoring tab** — leverages existing investment; closes observability loop.
- [ ] **Document browse with Checkbox + Delete/Re-ingest** — makes the existing browse UI actionable.

### Add After Core Validated (v0.1.x)

- [ ] **Advanced Filters (date range, file type, vendor, product)** — enhance document browse; depends on metadata quality but no new infra.
- [ ] **Document Export (CSV/JSON)** — depends on filter infrastructure; add after filters work.
- [ ] **RAGAS Evaluation Tab** — standalone feature; add when teams ask for eval UI.
- [ ] **Ingestion Tab (manual + monitor)** — depends on `JobManager.create_job()` modification. Adds convenience.
- [ ] **Provider Alias** — config table feature; add when multi-provider teams need it.
- [ ] **Percentile Metrics (p50/p95/p99)** — depends on Prometheus scrape; add when latency tuning begins.
- [ ] **Request ID Middleware** — add when debugging cross-service calls becomes painful.

### Future Consideration (v0.2+)

- [ ] **Ingestion Scheduler Tab** — cron-style scheduled ingest. Defer: manual ingest + file watcher covers most needs.
- [ ] **SSO/OAuth integration** — out of scope for self-hosted internal tool. Document reverse-proxy auth pattern instead.
- [ ] **Password-based auth** — out of scope. API key + JWT is simpler and sufficient.
- [ ] **Chat UI in admin panel** — anti-feature. Admin panel is for management, not for chatting.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Streamable HTTP Transport | HIGH (enables browser MCP clients) | LOW (plan exists) | **P1** |
| Auth & User Management API | HIGH (gates everything) | MEDIUM | **P1** |
| Admin SPA shell with login | HIGH (core UX) | MEDIUM | **P1** |
| Config API + Admin Config tab | HIGH (differentiator) | MEDIUM | **P1** |
| Monitor lights bar | MEDIUM (ops confidence) | LOW | **P1** |
| Profile tab (API key mgmt) | HIGH (user self-service) | LOW | **P1** |
| Grafana embed in Monitoring tab | MEDIUM (single pane) | LOW | **P1** |
| Document browse cleanup (checkbox, delete, re-ingest) | HIGH (actionable browse) | MEDIUM | **P1** |
| Advanced Filters (date/file type/vendor/product) | HIGH (browse at scale) | MEDIUM | **P2** |
| Document Export (CSV/JSON) | MEDIUM (data portability) | LOW | **P2** |
| RAGAS Evaluation Tab | MEDIUM (quality visibility) | MEDIUM | **P2** |
| Ingestion Tab (manual + monitor) | MEDIUM (reduce CLI dependency) | MEDIUM | **P2** |
| Provider Alias | LOW (niche use case) | LOW | **P3** |
| Percentile Metrics (p50/p95/p99) | MEDIUM (ops precision) | MEDIUM | **P3** |
| Request ID Middleware | MEDIUM (debugging) | LOW | **P3** |
| Ingestion Scheduler Tab | LOW (nice-to-have) | MEDIUM | **P3** |

**Priority key:**
- P1: Must have for v0.1.5 MVP — admin platform is incomplete without these
- P2: Should have — adds real value but can ship in follow-up
- P3: Nice to have — future consideration

## Competitor Feature Analysis

| Feature | Open WebUI | Dify | AnythingLLM | kb-rag-mcp (planned) |
|---------|------------|------|-------------|----------------------|
| **Admin panel** | ✅ Full admin settings (connections, features, security, models) | ✅ App management, datasets, monitoring | ⚠️ Basic workspace + user mgmt | ✅ Tabbed SPA (Alpine.js+HTMX) |
| **Auth model** | API key + session (passwordless signup) | Email/password, OAuth, SSO | API key | API key (MCP) + JWT session (browser) |
| **User management** | ✅ Admin/User/Pending roles, invite | ✅ Full RBAC, workspace roles | ⚠️ Basic | ✅ Admin/User roles, GDPR erasure |
| **API key management** | ✅ Generate, list, revoke | ⚠️ Via settings | ❌ | ✅ Create (show once), list, revoke |
| **Config via UI** | ✅ Admin Settings panel | ✅ Settings UI | ❌ env vars only | ✅ SQLite config table + hot-reload |
| **Health / monitoring** | ⚠️ Basic system info | ⚠️ Basic logs | ❌ | ✅ 7-light monitor bar + health API |
| **Grafana integration** | ❌ | ❌ | ❌ | ✅ Dashboard embed + time range selector |
| **Document export** | ❌ | ⚠️ Via API | ❌ | ✅ CSV/JSON with filters |
| **Advanced filters** | ⚠️ Search only | ⚠️ Basic | ❌ | ✅ Date range, file type, vendor, product |
| **RAGAS evaluation** | ⚠️ Model arena (different) | ⚠️ Basic eval | ❌ | ✅ Golden set CRUD + eval from UI |
| **Ingestion management** | ⚠️ Upload only | ✅ Dataset management | ⚠️ Upload only | ✅ Job create, monitor, schedule |
| **Provider aliases** | ❌ | ❌ | ❌ | ✅ Config table provider_alias.* |
| **GDPR erasure** | ❌ | ❌ | ❌ | ✅ Full Art 17 workflow |
| **Request ID tracing** | ❌ | ❌ | ❌ | ✅ Starlette middleware |
| **Percentile metrics** | ❌ | ❌ | ❌ | ✅ HDR histogram per operation |
| **MCP protocol** | ❌ (chat UI only) | ❌ (API only) | ❌ (chat UI) | ✅ Native (stdio, SSE, Streamable HTTP) |
| **Config hot-reload** | ❌ (restart needed) | ❌ (restart needed) | ❌ (restart needed) | ✅ SQLite→env chain with hooks |

## Anti-Feature Summary for Roadmap

| Anti-Feature | Why Avoid | What to Do Instead | Phase of Risk |
|--------------|-----------|-------------------|---------------|
| Built-in chat UI | Drifts from MCP-server identity, adds huge UI surface | Playground tab showing raw search_kb results | Phase 28c |
| Password auth | Password infra complexity; API key is simpler | Passwordless API key → JWT session | Phase 28b |
| Document editing in admin | Shifts to collaborative editor | Keep docs as source files; manage metadata only | Phase 28c |
| MFA | Overkill for internal self-hosted tool | Document reverse-proxy auth for admin routes | Phase 28b |
| Team collaboration features | Scope creep into Slack territory | Admin panel is for management, not collaboration | All |
| OAuth/SSO | Heavy integration per provider | Document reverse-proxy auth; X-Forwarded-User pattern | Phase 28b |
| Large file upload in browser | Size limits, poor UX for batch | "Ingest from path" + file watcher status | Phase 28c |

## Sources

- **Competitors analyzed:** Open WebUI (open-webui/open-webui, 126k ★), Dify (langgenius/dify, 130k ★), RAGFlow (infiniflow/ragflow), AnythingLLM (Mintplex-Labs/anything-llm, 30k ★)
- **Grafana embedding:** Grafana Labs blog (2023), Last9 blog (2025), Grafana community forums
- **MCP Streamable HTTP:** Official MCP spec (2025-03-26), The New Stack (2025-08-18), stanza.dev MCP fundamentals course
- **Auth patterns:** FastAPI documentation, WorkOS auth comparison (2026), StackPicker auth guide (2026)
- **Document export patterns:** DocumentPro, xeve, Sanity export-data, Genesys export services
- **Admin panel architecture patterns:** Open WebUI docs (Admin Settings, Administration), LiveKit Dashboard (HTMX+Bootstrap pattern)

---
*Feature research for: v0.1.5 Admin Platform features*
*Researched: 2026-06-15*
