# kb-rag-mcp

## What This Is

A production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation.

## Core Value

AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## Shipped: v0.1.5 Streamable HTTP & Management Platform

**Goal:** MCP Streamable HTTP transport, Auth & User Management API, Admin SPA Panel, Grafana dashboard embedding, observability, config with hot-reload, provider aliases, query analytics, chunk preview, document tags, ingestion schedules, and quality polish.

**18 phases shipped (28–53):** Streamable HTTP transport with session lifecycle and auth middleware; full Auth API with SQLAlchemy models, RBAC, GDPR erasure; Admin SPA (Alpine.js+HTMX) with login, documents, config, monitoring, schedules, tags; Grafana dashboard embedding; request ID middleware and percentile latency metrics; SQLite config with hot-reload; provider aliases; query analytics dashboard; chunk preview; auth security hardening; database reliability; code quality cleanup; LM Studio graceful fallback; SSE test consolidation; document tag management; cron-based ingestion scheduler; E2E tests (14), security audit, performance optimization.

## Current State (v0.1.5 shipped)

- **Tests:** 1541 passing, 14 skipped, 26 warnings
- **Coverage:** 90% branch target enforced (kb_server/ + ingest/)
- **Codebase:** ~57k LOC Python; single canonical module `kb_server/`
- **Deployment:** Docker Compose + bare metal systemd + Kubernetes/Helm
- **CI:** GitHub Actions on every push/PR to `master` — English audit, Helm lint, integration checks
- **Monitoring:** Grafana + Prometheus with 6-tab dashboard, 28 metrics
- **Auth:** API key + JWT session cookie for MCP and Admin SPA
- **Admin SPA:** Alpine.js+HTMX+Bootstrap 5 on Jinja2 FastAPI backend (port 8001)
- **Config:** SQLite config table with hot-reload, layered chain: SQLite → `.env` → env defaults

## Requirements

### Validated

- ✓ Semantic search over ingested documents (dense vector search via Qdrant) — existing
- ✓ MCP server exposing `search_kb`, `list_documents`, `get_chunk`, `kb_stats` tools — existing
- ✓ Async ingest pipeline (PDF, markdown, text) with metadata extraction — existing
- ✓ Hybrid search (dense + sparse BM25 RRF fusion) — validated v0.1.0
- ✓ Cross-encoder reranking — existing (PHASE 12)
- ✓ Multi-collection routing via `CollectionRouter` and `CollectionManager` — validated v0.1.0
- ✓ Product/version metadata filtering — existing
- ✓ Query logging and analytics — existing
- ✓ LRU + optional Redis caching — existing
- ✓ Batch ingest with job tracking and progress reporting — existing
- ✓ File watcher for automatic re-ingest on doc changes — existing
- ✓ Migration tooling (export/import/validate) — existing
- ✓ Grafana observability dashboard — existing
- ✓ Kubernetes/Helm deployment — existing
- ✓ Security hardening documentation — existing
- ✓ RAG evaluation framework (golden dataset, hit rate, MRR) — existing
- ✓ Single `kb_server/` canonical module; `server/` legacy deleted — v0.1.0
- ✓ Real SHA-256 batch deduplication — v0.1.0
- ✓ Single `bootstrap_env()` entry point — v0.1.0
- ✓ File watcher deletion removes stale Qdrant vectors — v0.1.0
- ✓ Secrets removed from git tracking; `config/.env.template` only — v0.1.0
- ✓ `CONTRIBUTING.md` with secret remediation guide — v0.1.0
- ✓ ≥80% branch coverage on `kb_server/` (achieved 88%) — v0.1.0
- ✓ Integration tests: ingest → search_kb → verify; multi-collection routing — v0.1.0
- ✓ GitHub Actions CI on push/PR to master — v0.1.0
- ✓ Multi-stage Dockerfile (builder + slim runtime) — v0.1.0
- ✓ `scripts/quickstart.sh` one-command setup — v0.1.0
- ✓ README end-to-end getting-started guide — v0.1.0
- ✓ SSE handler returns `Response()` on disconnect; 3 regression tests — v0.1.1
- ✓ No `307 Temporary Redirect` on POST to `/messages/` — v0.1.1
- ✓ CI matrix tests Python 3.11, 3.12, 3.13 — v0.1.1
- ✓ OTCS auto-tagging (10 product areas) via directory name or filename — v0.1.1
- ✓ `kb-ingest status` CLI with Rich table + `--source` filter — v0.1.1
- ✓ Every Python module has a dedicated unit test file — v0.1.1
- ✓ All unit tests run without Qdrant, LM Studio, or Redis (full mocking) — v0.1.1
- ✓ Integration tests marked with `@pytest.mark.integration` — v0.1.1
- ✓ Every public method in `kb_server/` emits structured log entries — v0.1.1
- ✓ Logging coverage audit produced via `scripts/logging-audit.py` — v0.1.1
- ✓ CI enforces ≥90% branch coverage on kb_server/ + ingest/ (PR-to-master) — v0.1.1
- ✓ `pyproject.toml` `fail_under = 90` set and verified — v0.1.1
- ✓ All public functions/classes in kb_server/ + ingest/ have English Google-style docstrings — v0.1.1
- ✓ `docs/` updated: ARCHITECTURE.md (Mermaid), OPERATIONS.md (remote deploy), INDEX.md, REFERENCE.md — v0.1.1
- ✓ **PH28**: MCP Streamable HTTP Transport — browser-compatible `/mcp` endpoint with session lifecycle and auth middleware — v0.1.5
- ✓ **PH28b**: Auth & User Management API — SQLAlchemy models, CRUD REST endpoints, GDPR erasure — v0.1.5
- ✓ **PH28c**: Admin SPA Panel — Alpine.js+HTMX tabbed UI at `/admin/`, login modal, role gating — v0.1.5
- ✓ **PH28c-fixes**: Admin SPA Gap Closure — UAT fixes: auth flow, document browse, CSP/SRI, monitor lights, config editor, partials, session management — v0.1.5
- ✓ **PH38**: Grafana Dashboard Embedding — iframe embed, time range selector, Jinja2 globals — v0.1.5
- ✓ **PH39**: Observability Backlog — health checks, request ID middleware, percentile metrics — v0.1.5
- ✓ **PH40**: Configuration Backlog — SQLite config table + ConfigLoader + REST API — v0.1.5
- ✓ **PH41**: Provider Alias — provider alias resolution + hot-reload — v0.1.5
- ✓ **PH42**: Query Analytics Dashboard — popular queries, no-results queries, latency distribution — v0.1.5
- ✓ **PH43**: Chunk Preview in Document Detail — inline chunk viewer with term highlighting — v0.1.5
- ✓ **PH44**: Auth Security Hardening — erasure separation, ownership checks, secure cookies — v0.1.5
- ✓ **PH45**: Database Reliability — SQLite connection management, FK enforcement, indexes — v0.1.5
- ✓ **PH46**: Code Quality & Coverage — utcnow migration, unused import cleanup, integration tags — v0.1.5
- ✓ **PH47**: LM Studio Dependency Handling — graceful fallback, startup health-check — v0.1.5
- ✓ **PH50**: SSE Test Consolidation — per-function @patch instead of module-level stubs — v0.1.5
- ✓ **PH51**: Document Tag Management — CLI + Web UI tag editor, re-ingest control — v0.1.5
- ✓ **PH52**: Ingestion Schedule Management — cron-based scheduler, Admin UI, background jobs — v0.1.5
- ✓ **PH53**: Quality & Polish — bug bash, E2E tests, security audit, docs, performance tuning — v0.1.5
- ✓ **SPA-04**: Export Filtered Results — CSV/JSON export from document browse in SPA — v0.1.5
- ✓ **SPA-05**: Advanced Filters — date range, file type, vendor, product filters in SPA — v0.1.5

### Active

*(Next milestone features to be determined)*

### Out of Scope

- Cloud-managed vector store — self-hosted Qdrant only for data sovereignty
- Real-time streaming ingest from external APIs — file-based ingest only
- Real-time chat / collaborative editing — not related to doc RAG

## Context

- v0.1.5 shipped 2026-06-29: 18 phases (28-53), 28 plans, 1541 passing tests. Full Streamable HTTP + Auth + Admin SPA + Observability + Config + Schedules platform
- v0.1.4 shipped 2026-06-11: 15 phases (23-37) across documentation overhaul, RAGAS evaluation, optimization experiments, enterprise connectors, knowledge graph, auth, rate limiting, quotas, circuit breakers, and retrieval caching
- `kb_server/` is the single canonical package; `server/` deleted; `ingest/core/metadata.py` is the registry
- Embedding model: local LM Studio (`http://<LM_STUDIO_HOST>:1234`); configurable via `EMBED_BACKEND`
- Vector store: Qdrant (local or remote); multi-collection support
- Admin SPA built with Alpine.js + HTMX + Bootstrap 5 on existing Jinja2 FastAPI backend (port 8001)
- All env vars configurable via SQLite config table with hot-reload
- Auth: API key + JWT session cookie; optional AUTH_ENABLED toggle; login rate limiting (5/60s)
- `asyncio_mode = STRICT` in `pyproject.toml` — all async tests need `@pytest.mark.asyncio`
- Phase 53 performance: croniter for O(1) cron matching, joinedload for single-query verify_key, TTL cache on ConfigLoader refresh

## Constraints

- **Tech stack**: Python 3.11+, Qdrant, MCP protocol, FastAPI, asyncio — no runtime changes
- **Dependencies**: pip-tools (`requirements.in` → `requirements.txt`), `.venv/` virtual env
- **Compatibility**: CLI interface must remain backward-compatible; deprecation warnings for removed flags
- **Deployment**: Must support bare metal (systemd), Docker Compose, and Kubernetes/Helm
- **Auth**: API key + JWT session cookie for MCP and Admin SPA
- **Test baseline**: 1541 passing tests; no regressions allowed

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `kb_server/` is canonical, `server/` deleted | Single source of truth; avoid import confusion | ✓ Good — v0.1.0 |
| Local embedding model (LM Studio/Ollama) | Data sovereignty for closed-source doc content | ✓ Good |
| Qdrant for vector store | Production-grade, self-hostable, multi-collection support | ✓ Good |
| MCP protocol for AI tool integration | Standard protocol; works with Claude, Cursor, OpenCode, Copilot | ✓ Good |
| Generic product names in codebase | Enable open-source release without exposing client details | ✓ Good |
| `asyncio_mode = STRICT` in pyproject.toml | Enforce explicit async test marking; prevents silent sync execution | ✓ Good |
| `bootstrap_env()` single entry point | Eliminate 6+ copy-pasted `load_dotenv` blocks | ✓ Good — v0.1.0 |
| fastembed BM25 for sparse vectors | No separate sparse model server needed; embedded in process | ✓ Good |
| Admin SPA via Alpine.js+HTMX+Bootstrap 5 | No build step; leverages existing Jinja2 FastAPI backend | ✓ Good |
| Passwordless API key + JWT session auth | Works for both MCP (Bearer header) and browser (cookie); no password infrastructure needed | ✓ Good |
| SQLite config table with hot-reload | All env vars configurable from admin UI; chain: SQLite → `.env` → env defaults | ✓ Good |
| Weaken `PayloadSchemaType` enum assertion in test | MagicMock pollution across test suite; assertion redundant | — Acceptable tech debt |
| Login rate limiting (5 req / 60s window) | In-memory token bucket, lost on restart; sufficient for internal tool | ✓ Good — v0.1.5 |
| `croniter` for O(1) cron matching | Replaced brute-force minute scan; preserves validate_cron pre-check | ✓ Good — v0.1.5 |
| `verify_key` optimization with `joinedload` | Single-query JOIN instead of two sequential queries | ✓ Good — v0.1.5 |
| ConfigLoader TTL cache (1s default) | In-memory time gate avoids persistent connection overhead for thread safety | ✓ Good — v0.1.5 |
| stdio no-auth accepted as design | Internal tool; auth is deployer's responsibility for stdio transport | — Accepted per security audit |

## Evolution

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-29 — v0.1.5 milestone shipped*
