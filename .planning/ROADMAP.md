# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v0.1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](milestones/v0.1.0-ROADMAP.md)
- ✅ **v0.1.1 Quality & Operational Excellence** — Phases 5–8 (shipped 2026-05-23) — [archive](milestones/v0.1.1-ROADMAP.md)
- ✅ **v0.1.2 Tech Debt & Classification** — Phases 9–11.1 (shipped 2026-05-27) — [archive](milestones/v0.1.2-ROADMAP.md)
- ✅ **v0.1.3 Post-Ship Polish & Infrastructure** — Phases 12–22 (shipped 2026-05-27) — [archive](milestones/v0.1.3-ROADMAP.md)
- ✅ **v0.1.4 Platform, Analytics & Enterprise** — Phases 23–37 (shipped 2026-06-11) — [archive](milestones/v0.1.4-ROADMAP.md)
- ✅ **v0.1.5 Streamable HTTP & Management Platform** — Phases 28–53 (shipped 2026-06-29) — [archive](milestones/v0.1.5-ROADMAP.md)

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

<details>
<summary>✅ v0.1.5 Phase Overview — SHIPPED 2026-06-29 — [archive](milestones/v0.1.5-ROADMAP.md)</summary>

**All 19 phases (28-53) complete:**

- [x] Phase 28: MCP Streamable HTTP Transport — 2 plans — completed 2026-06-15
- [x] Phase 28b: Auth & User Management API — 2 plans — completed 2026-06-16
- [x] Phase 28c: Admin SPA Panel — 4 plans — completed 2026-06-16
- [x] Phase 28c-fixes: Admin SPA Gap Closure — 4 plans — completed 2026-06-16
- [x] Phase 38: Grafana Dashboard Embedding — 1 plan — completed 2026-06-16
- [x] Phase 39: Observability Backlog — 1 plan — completed 2026-06-16
- [x] Phase 40: Configuration Backlog — 2 plans — completed 2026-06-16
- [x] Phase 41: Provider Alias — 1 plan — completed 2026-06-16
- [x] Phase 42: Query Analytics Dashboard — 1 plan — completed 2026-06-17
- [x] Phase 43: Chunk Preview in Document Detail — 1 plan — completed 2026-06-17
- [x] Phase 44: Auth Security Hardening — 1 plan — completed 2026-06-17
- [x] Phase 45: Database Reliability — 1 plan — completed 2026-06-17
- [x] Phase 46: Code Quality & Coverage — 1 plan — completed 2026-06-17
- [x] Phase 47: LM Studio Dependency Handling — 1 plan — completed 2026-06-17
- [x] Phase 50: SSE Test Consolidation — 1 plan — completed 2026-06-17
- [x] Phase 51: Document Tag Management — 1 plan — completed 2026-06-17
- [x] Phase 52: Ingestion Schedule Management — 1 plan — completed 2026-06-17
- [x] Phase 53: Quality & Polish — 1 plan — completed 2026-06-29

**Delivered:** Streamable HTTP transport with session lifecycle, auth middleware, and Prometheus metrics; full Auth API with SQLAlchemy models, RBAC, GDPR erasure, API key CRUD; Admin SPA (Alpine.js+HTMX) with login, documents, config, monitoring, schedules, tags; Grafana dashboard embedding; observability (request ID, percentile latency); SQLite config with hot-reload; provider aliases; query analytics dashboard; chunk preview with search term highlighting; auth security hardening; database reliability fixes; code quality cleanup; LM Studio graceful fallback; SSE test consolidation; document tag management; cron-based ingestion scheduler; E2E tests; security audit; performance optimization.

</details>

---

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
| 28b. Auth & User Management API | v0.1.5 | 2/2 | Complete | 2026-06-16 |
| 28c. Admin SPA Panel + Fixes | v0.1.5 | 9/9 | Complete | 2026-06-16 |
| 38. Grafana Dashboard Embedding | v0.1.5 | 1/1 | Complete | 2026-06-16 |
| 39. Observability Backlog | v0.1.5 | 1/1 | Complete | 2026-06-16 |
| 40. Configuration Backlog | v0.1.5 | 2/2 | Complete | 2026-06-16 |
| 41. Provider Alias | v0.1.5 | 1/1 | Complete | 2026-06-16 |
| 42. Query Analytics Dashboard | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 43. Chunk Preview in Document Detail | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 44. Auth Security Hardening | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 45. Database Reliability | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 46. Code Quality & Coverage | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 47. LM Studio Dependency Handling | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 48. Cross-Encoder Lazy Loading | v0.1.5 | — | Complete (v0.1.3) | — |
| 49. Qdrant Mock Cleanup | v0.1.5 | — | Complete (v0.1.3) | — |
| 50. SSE Test Consolidation | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 51. Document Tag Management | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 52. Ingestion Schedule Management | v0.1.5 | 1/1 | Complete | 2026-06-17 |
| 53. Quality & Polish | v0.1.5 | 1/1 | Complete | 2026-06-29 |

*Earlier milestones (v0.1.0–v0.1.3): see archived roadmaps in [milestones/](milestones/).*

## Backlog

### Phase 999.1: UI Polish — Copywriting & Messaging (BACKLOG)

**Goal:** Fix jargon-heavy and technical labels across admin UI templates for clearer user-facing copy.
**Requirements:** TBD
**Plans:** 0 plans

Sub-tasks:
- [ ] Rename "RAGAS Evaluation" sidebar label to "Evaluation" (`shell.html:32`)
- [ ] Expand technical abbreviations "K", "BM25", "Rerank" to full labels (`tab_profile.html:7,15,23`)
- [ ] Rename "Search Tester" to a product-facing name (`search.html:6`)
- [ ] Rephrase "Chunk Loading Failed" to user-friendly message (`document.html:114`)

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

---

### Phase 999.2: UI Polish — Typography & Layout (BACKLOG)

**Goal:** Fix heading hierarchy inconsistencies, container nesting, and visual alignment in UI templates.
**Requirements:** TBD
**Plans:** 0 plans

Sub-tasks:
- [ ] Fix `h4.h6` outline skip on profile config section (`tab_profile.html:5`)
- [ ] Fix `h3.h5` data section headings under `h2.h3` on analytics (`tab_analytics.html:20,41,63`)
- [ ] Remove double `container` nesting on error page (`error.html:6`)
- [ ] Clean up whitespace/newlines in pagination `href` attributes (`browse.html:138-146`)
- [ ] Center/distribute job status counters in admin card (`_job_status.html:4`)
- [ ] Add `mt-3` spacing on mobile search results area (`search.html:86`)

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

---

### Phase 999.3: UI Polish — UX Experience (BACKLOG)

**Goal:** Add dismissible alerts, RAGAS progress feedback, and search result pagination.
**Requirements:** TBD
**Plans:** 0 plans

Sub-tasks:
- [ ] Add close/dismiss buttons to alert banners (base.html + admin templates)
- [ ] Add progress indication for RAGAS evaluation runs (`tab_ragas.html:12-19`)
- [ ] Add pagination to search results page (`search_results.html:6-26`)

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

