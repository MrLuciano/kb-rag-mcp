# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Quality & Operational Excellence** — Phases 5–8 (shipped 2026-05-23) — [archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Tech Debt & Classification** — Phases 9–11.1 (shipped 2026-05-27) — [archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Post-Ship Polish & Infrastructure** — Phases 12–22 (shipped 2026-05-27) — [archive](milestones/v1.3-ROADMAP.md)
- ◆ **v1.4 Platform, Analytics & Enterprise** — Phases 23–37 (active)

## Phases

<details>
<summary>✅ v1.0 Release-Readiness (Phases 1–4) — SHIPPED 2026-05-19</summary>

- [x] Phase 1: Codebase Consolidation (4/4 plans) — completed 2026-05-16
- [x] Phase 2: Data Integrity & Security (3/3 plans) — completed 2026-05-17
- [x] Phase 3: Test Coverage & CI (3/3 plans) — completed 2026-05-19
- [x] Phase 4: Deployment & Release (inline) — completed 2026-05-19

**Delivered:** Deleted legacy `server/` module, implemented real BM25 hybrid search, unified env loading,
file-watcher deletion, secrets remediation, 88% branch coverage (491 tests), GitHub Actions CI,
multi-stage Dockerfile, quickstart.sh, and new README getting-started guide.

</details>

<details>
<summary>✅ v1.1 Quality & Operational Excellence (Phases 5-8) — SHIPPED 2026-05-23</summary>

- [x] Phase 5: SSE Stability & Python 3.13 Compatibility (2/2 plans) — completed 2026-05-21
- [x] Phase 6: Test Coverage & Isolation (3/3 plans) — completed 2026-05-22
- [x] Phase 7: Logging, Quality Gate & Coverage Enforcement (2/2 plans) — completed 2026-05-23
- [x] Phase 8: Ingest Improvements & Documentation (3/3 plans) — completed 2026-05-23

**Delivered:** SSE stability with Python 3.13 support, full test isolation (518 unit tests pass without Qdrant/LM Studio/Redis), 90% branch coverage enforcement on PR-to-master, OTCS auto-tagging for 10 OpenText products, `kb-ingest status` CLI command, English-only codebase with 105 docstring gaps fixed (32 missing + 73 Portuguese → 0), comprehensive documentation refresh.

</details>

<details>
<summary>✅ v1.2 Tech Debt & Classification (Phases 9–11.1) — SHIPPED 2026-05-27</summary>

- [x] Phase 9: Startup Reliability (3/3 plans) — completed 2026-05-25
- [x] Phase 10: CI & Test Infrastructure (3/3 plans) — completed 2026-05-25
- [x] Phase 11: Auto-Classification (2/2 plans) — completed 2026-05-25
- [x] Phase 11.1: Vendor/Subsystem Integration Completion (1/1 plan) — completed 2026-05-27

**Delivered:** Lazy cross-encoder loading (~500MB saved, ~10s faster startup), pre-flight health checks with non-fatal warnings, `kb-ingest check health` CLI, 4 embedding backends documented (OPERATIONS.md), Helm lint CI gate, MagicMock pollution resolved (3 test files), logging coverage CI gate (40% threshold), auto-classification (Vendor/Product/Subsystem/Version), metadata gap-filling from PDF/DOCX, vendor/subsystem fields visible in search results and filterable via MCP tools.

</details>

<details>
<summary>✅ v1.3 Post-Ship Polish & Infrastructure (Phases 12–22) — SHIPPED 2026-05-27</summary>

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

<details open>
<summary>◆ v1.4 Platform, Analytics & Enterprise (Phases 23–37) — ACTIVE</summary>

**Completed:**

- [x] Phase 23: Documentation Overhaul — 3 plans (doc reorganization, README restructuring, CHANGELOG/REFERENCE update) — completed 2026-05-27
- [x] Phase 26: KB Content Discoverability — Dynamic content-summary tool descriptions + `kb://overview` MCP Resource — completed 2026-06-03
- [x] Phase 27: Knowledge Base Registry — SQLite-backed KB registry with public/agent_private scopes, stable `kb_<id>` collection names — completed 2026-06-03
- [x] Phase 28: MCP Streamable HTTP Transport — `/mcp` HTTP endpoint alongside stdio/SSE — completed 2026-06-03

**Deferred (low priority):**

- [ ] Phase 24: RAGAS Evaluation Pipeline — 3 plans created, execution deferred
- [ ] Phase 25: Optimization Experiments — Chunking and scoring experiments

**In Progress (planned, not started):**

- [ ] Phase 29: Enterprise Data Source Connectors — Confluence (Cloud + Data Center), JIRA (Cloud + Data Center), Git repositories
- [ ] Phase 30: Cross-Document Knowledge Graph — similarity clustering, entity extraction, topic modeling
- [ ] Phase 31: MCP Prompt Templates — extract_answer and summarize_documents prompts
- [ ] Phase 32: API Key Authentication — global and per-KB API keys with enabled/allow_anonymous flags
- [ ] Phase 33: Request Rate Limiting — token bucket rate limiter per subject (requests/window + burst)
- [ ] Phase 34: Upload and Index Quotas — configurable limits per KB (files, bytes, chunks, chars)
- [ ] Phase 35: Multi-KB Aggregated Search — kb_ids parameter to search across multiple KBs in one query
- [ ] Phase 36: Provider Budget & Circuit Breaker — per-provider budgets, failure thresholds, automatic fallback
- [ ] Phase 37: Request-level Retrieval Cache — in-memory LRU cache for identical queries

**Delivered so far:** Documentation restructuring + KB content discoverability + KB Registry with SQLite scoping (3 MCP CRUD tools, ingest `--kb-id` flag, legacy migration) + MCP Streamable HTTP transport (stdio + SSE + Streamable HTTP, 3 transports). Competitive intelligence from mcp-rag, qdrant-loader, local_faiss_mcp informed phases 29–37.

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Codebase Consolidation | v1.0 | 4/4 | Complete | 2026-05-16 |
| 2. Data Integrity & Security | v1.0 | 3/3 | Complete | 2026-05-17 |
| 3. Test Coverage & CI | v1.0 | 3/3 | Complete | 2026-05-19 |
| 4. Deployment & Release | v1.0 | 3/3 | Complete | 2026-05-19 |
| 5. SSE Stability & Python 3.13 | v1.1 | 2/2 | Complete | 2026-05-21 |
| 6. Test Coverage & Isolation | v1.1 | 3/3 | Complete | 2026-05-22 |
| 7. Logging, Quality Gate & Coverage | v1.1 | 2/2 | Complete | 2026-05-23 |
| 8. Ingest Improvements & Docs | v1.1 | 3/3 | Complete | 2026-05-23 |
| 9. Startup Reliability | v1.2 | 3/3 | Complete | 2026-05-25 |
| 10. CI & Test Infrastructure | v1.2 | 3/3 | Complete | 2026-05-25 |
| 11. Auto-Classification | v1.2 | 2/2 | Complete | 2026-05-25 |
| 11.1. Vendor/Subsystem Integration | v1.2 | 1/1 | Complete | 2026-05-27 |
| 12. English Comments & Docstrings | v1.3 | 3/3 | Complete | 2026-05-25 |
| 13. Docs Sync & Readme Languages | v1.3 | 4/4 | Complete | 2026-05-26 |
| 14. Health Dashboard | v1.3 | 6/6 | Complete | 2026-05-26 |
| 15. PowerShell Ports Script | v1.3 | 2/2 | Complete | 2026-05-26 |
| 16. Reclassification | v1.3 | 3/3 | Complete | 2026-05-27 |
| 17. Capability Negotiation | v1.3 | 3/3 | Complete | 2026-05-27 |
| 18. Grafana Datasource Fix | v1.3 | 1/1 | Complete | 2026-05-27 |
| 19. VERIFICATION.md Backfill | v1.3 | 1/1 | Complete | 2026-05-27 |
| 20. Test Environment Fixes | v1.3 | 1/1 | Complete | 2026-05-27 |
| 21. Codebase Hygiene Sweep | v1.3 | 1/1 | Complete | 2026-05-27 |
| 22. Integration Checker CI Gate | v1.3 | 1/1 | Complete | 2026-05-27 |
| 23. Documentation Overhaul | v1.4 | 3/3 | Complete | 2026-05-27 |
| 24. RAGAS Evaluation Pipeline | v1.4 | 0/0 | Deferred | — |
| 25. Optimization Experiments | v1.4 | 0/0 | Deferred | — |
| 26. KB Content Discoverability | v1.4 | 1/1 | Complete | 2026-06-03 |
| 27. Knowledge Base Registry | v1.4 | 3/3 | Complete | 2026-06-03 |
| 28. MCP Streamable HTTP | v1.4 | 1/1 | Complete | 2026-06-03 |
| 29. Enterprise Data Source Connectors | v1.4 | 0/1 | Planned | — |
| 30. Cross-Document Knowledge Graph | v1.4 | 0/1 | Planned | — |
| 31. MCP Prompt Templates | v1.4 | 0/1 | Planned | — |
| 32. API Key Authentication | v1.4 | 0/1 | Planned | — |
| 33. Request Rate Limiting | v1.4 | 0/1 | Planned | — |
| 34. Upload and Index Quotas | v1.4 | 0/1 | Planned | — |
| 35. Multi-KB Aggregated Search | v1.4 | 0/1 | Planned | — |
| 36. Provider Budget & Circuit Breaker | v1.4 | 0/1 | Planned | — |
| 37. Request-level Retrieval Cache | v1.4 | 0/1 | Planned | — |

*Earlier milestones (v1.0–v1.3): see archived roadmaps in [milestones/](milestones/).*

## Backlog

Items derived from competitive analysis and future planning. Each item is a candidate for v1.5 or later.

### Low Priority

- **CONF-01: Hot-reload Configuration** — JSON/env config changes take effect without restart. `reload_if_changed()` polling on config file mtime.
- **CONF-02: Configuration API Endpoints** — `GET /config`, `POST /config`, `POST /config/bulk`, `POST /config/reset`, `POST /config/reload` for runtime configuration management.
- **METRICS-01: Per-operation Percentile Metrics** — p50/p95/p99 latency tracking per operation and per embedding/LLM provider. Complements existing Prometheus metrics with in-memory histograms.
- **OBS-01: Health/Readiness Endpoints** — `/health` (summary with runtime snapshot), `/ready` (503 when not bootstrapped), `/metrics` (operational metrics) as HTTP endpoints alongside existing MCP server. Reuses the health endpoint already setup to improve upon it.
- **SPA-01: Management SPA Panel** — Built-in web UI (`/app`) for document management, knowledge base admin, and configuration. Requires frontend build toolchain. Reuses / merge web-ui created before, adding the Classification items to the data table and allowing sorting of columns. Provides a link to grafana Dashboard.
- **PROV-01: Provider Aliases** — Normalize provider names (e.g., `dashscope` → `aliyun`) for easier configuration.
- **OBS-02: Request Identity Middleware** — `X-Request-Id` and `X-Trace-Id` headers propagated through all operations for distributed tracing.
