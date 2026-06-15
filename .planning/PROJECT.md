# kb-rag-mcp

## What This Is

A production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation.

## Core Value

AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## Current Milestone: v0.1.5 Streamable HTTP & Management Platform

**Goal:** Implement MCP Streamable HTTP transport, build the Management SPA with auth, user management, admin panel, Grafana dashboard embedding, document export, and advanced filters.

**Target features:**
- Phase 28 (reopened): MCP Streamable HTTP Transport — browser-compatible `/mcp` endpoint
- Phase 28b: Auth & User Management API — SQLAlchemy models, CRUD REST endpoints, GDPR erasure
- Phase 28c: Admin SPA Panel — Alpine.js+HTMX tabbed UI at `/admin/`, login modal, role gating
- Phase 38: Grafana Dashboard Embedding — iframe embed, time range selector, Jinja2 globals
- Phase 39: Observability Backlog — OBS-01 (health checks), OBS-02 (request ID middleware), METRICS-01 (percentile metrics)
- Phase 40: Configuration Backlog — CONF-01 (SQLite config table + ConfigLoader), CONF-02 (config REST API)
- Phase 41: Provider Alias — PROV-01 (provider alias resolution + hot-reload)
- SPA-04: Export Filtered Results — CSV/JSON export from document browse
- SPA-05: Advanced Filters — date range, file type, vendor, product filters

## Current State (v0.1.5 — active)

- **Tests:** 1165 passing, 5 pre-existing failures, 12 skipped
- **Coverage:** 90% branch target enforced (kb_server/ + ingest/)
- **Codebase:** ~251k LOC Python; single canonical module `kb_server/`
- **Deployment:** Docker Compose + bare metal systemd + Kubernetes/Helm
- **CI:** GitHub Actions on every push/PR to `master` — English audit, Helm lint, integration checks
- **Monitoring:** Grafana + Prometheus with 6-tab dashboard, 28 metrics
- **Phase 28 progress:** Plan 28-01 complete (streamable HTTP transport: server.py + 3 tests + docs)

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

### Active

- [ ] **PH28**: MCP Streamable HTTP Transport — browser-compatible `/mcp` endpoint
- [ ] **PH28b**: Auth & User Management API — SQLAlchemy models, CRUD REST endpoints, GDPR erasure
- [ ] **PH28c**: Admin SPA Panel — Alpine.js+HTMX tabbed UI at `/admin/`, login modal, role gating
- [ ] **PH38**: Grafana Dashboard Embedding — iframe embed, time range selector, Jinja2 globals
- [ ] **PH39**: Observability Backlog — health checks, request ID middleware, percentile metrics
- [ ] **PH40**: Configuration Backlog — SQLite config table + ConfigLoader + REST API
- [ ] **PH41**: Provider Alias — provider alias resolution + hot-reload
- [ ] **SPA-04**: Export Filtered Results — CSV/JSON export from document browse in SPA
- [ ] **SPA-05**: Advanced Filters — date range, file type, vendor, product filters in SPA

### Out of Scope

- Cloud-managed vector store — self-hosted Qdrant only for data sovereignty
- Real-time streaming ingest from external APIs — file-based ingest only
- Real-time chat / collaborative editing — not related to doc RAG

## Context

- v0.1.4 shipped 2026-06-11: 15 phases (23-37) across documentation overhaul, RAGAS evaluation, optimization experiments, enterprise connectors, knowledge graph, auth, rate limiting, quotas, circuit breakers, and retrieval caching
- v0.1.5 active: Streamable HTTP (Phase 28 Plan 28-01 complete), Auth API, Admin SPA, Grafana embed, observability, config, provider aliases
- `kb_server/` is the single canonical package; `server/` deleted; `ingest/core/metadata.py` is the registry
- Embedding model: local LM Studio (`http://<LM_STUDIO_HOST>:1234`); configurable via `EMBED_BACKEND`
- Vector store: Qdrant (local or remote); multi-collection support
- Admin SPA built with Alpine.js + HTMX + Bootstrap 5 on existing Jinja2 FastAPI backend (port 8001)
- All env vars configurable via SQLite config table with hot-reload
- Pre-existing test note: `test_payload_indexes.py` schema type assertion weakened (MagicMock pollution from qdrant_client stub)
- `asyncio_mode = STRICT` in `pyproject.toml` — all async tests need `@pytest.mark.asyncio`

## Constraints

- **Tech stack**: Python 3.11+, Qdrant, MCP protocol, FastAPI, asyncio — no runtime changes
- **Dependencies**: pip-tools (`requirements.in` → `requirements.txt`), `.venv/` virtual env
- **Compatibility**: CLI interface must remain backward-compatible; deprecation warnings for removed flags
- **Deployment**: Must support bare metal (systemd), Docker Compose, and Kubernetes/Helm
- **Auth**: API key + JWT session cookie for MCP and Admin SPA
- **Test baseline**: 1165 passing tests; no regressions allowed

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
*Last updated: 2026-06-15 — v0.1.5 milestone formalized*
