# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Quality & Operational Excellence** — Phases 5–8 (shipped 2026-05-23) — [archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Tech Debt & Classification** — Phases 9–11.1 (shipped 2026-05-27) — [archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Post-Ship Polish & Infrastructure** — Phases 12–22 (shipped 2026-05-27) — [archive](milestones/v1.3-ROADMAP.md)

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
| 13. Docs Sync & Readme Languages | v1.3 | 4/4 | Complete    | 2026-05-26 |
| 14. Health Dashboard | v1.3 | 6/6 | Complete   | 2026-05-26 |
| 15. PowerShell Ports Script | v1.3 | 2/2 | Complete   | 2026-05-26 |
| 16. Reclassification | v1.3 | 3/3 | Complete   | 2026-05-27 |
| 17. Capability Negotiation | v1.3 | 3/3 | Complete | 2026-05-27 |
| 18. Grafana Datasource Fix | v1.3 | 1/1 | Complete | 2026-05-27 |
| 19. VERIFICATION.md Backfill | v1.3 | 1/1 | Complete | 2026-05-27 |
| 20. Test Environment Fixes | v1.3 | 1/1 | Complete | 2026-05-27 |
| 21. Codebase Hygiene Sweep | v1.3 | 1/1 | Complete | 2026-05-27 |
| 22. Integration Checker CI Gate | v1.3 | 1/1 | Complete | 2026-05-27 |

## Backlog

### Phase 999.1: Update documentation in root and docs folder (BACKLOG)

**Goal:** Organize README.md, INSTRUCTIONS.md, OPERATIONS.md, TROUBLESHOOTING.md to group the various modes of operation (Docker Compose, Helm, systemd, manual). Update CHANGELOG, REFERENCE.md and all documentation regarding the last changes to the project. Captured for future planning.

**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: Implement RAGAS evaluation (BACKLOG)

**Goal:** Implement RAGAS evaluation at `kb_server/evaluation/ragas_pipeline.py:47` (TODO placeholder). Captured for future planning.

**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.3: Implement optimization experiments (BACKLOG)

**Goal:** Implement optimization experiments at `kb_server/optimization/chunking_experiments.py:8` and `kb_server/optimization/scoring_experiments.py:8` (TODO placeholders). Captured for future planning.

**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
