# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Quality & Operational Excellence** — Phases 5–8 (shipped 2026-05-23) — [archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Tech Debt & Classification** — Phases 9–11.1 (shipped 2026-05-27) — [archive](milestones/v1.2-ROADMAP.md)
- 🔄 **v1.3 Post-Ship Polish & Infrastructure** — Phases 12–16 (planning)

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

### Phase 12: English comments & docstrings sweep (COMPLETED)

**Goal:** Ensure all inline comments, docstrings, log messages, and internal documentation across Python source files are written in English for consistency and open-source readiness.

**Milestone:** v1.3
**Requirements:** TBD
**Depends on:** — (independent)
**Plans:** 3 plans — all executed 2026-05-25

**Delivered:**

- All Portuguese content translated to English across ~35 files in `kb_server/` and `ingest/`
- `scripts/docstring-audit.py` extended with `--check-inline`, `--fail-under`, expanded Portuguese word list
- `.github/workflows/ci.yml` has `english-audit` job (`--check-inline --fail-under 0`) on every push/PR
- False positives fixed: English technical terms (cache, chunk, hash, log, pipeline, query, etc.) removed from Portuguese detection set
- **0 Portuguese docstrings, 0 Portuguese inline comments** — verified by audit script

Plans:

- [x] 12-01-PLAN.md — kb_server/ English sweep (server.py, embed_client.py, vector_store.py)
- [x] 12-02-PLAN.md — ingest/ English sweep (classifier.py, ingest.py)
- [x] 12-03-PLAN.md — Verification audit script + CI gate

---

### Phase 13: Docs sync, README all languages, Spanish README

**Goal:** Sync the `docs/` folder with all changes shipped since v1.0, update README.md and README.pt-BR.md to reflect current state, and add a new README.es.md in Spanish.

**Milestone:** v1.3
**Requirements:** DOCS-01, DOCS-02, DOCS-03
**Depends on:** — (independent)
**Plans:** 4/4 plans complete

Plans:

- [x] 13-01-PLAN.md — README.md core sections refresh (header through Usage)
- [x] 13-02-PLAN.md — README.md advanced sections refresh (Health Checks through Contributing)
- [x] 13-03-PLAN.md — README.pt-BR.md sync + README.es.md creation
- [x] 13-04-PLAN.md — Stale docs updates (AUTO_INGESTION, TROUBLESHOOTING, TESTING, KUBERNETES)

---

### Phase 14: Health Dashboard

**Goal:** Consolidate health/status access to all subsystems (Qdrant health, kb-rag-mcp server, ingestion status) into a unified Grafana dashboard with Prometheus metrics.

**Milestone:** v1.3
**Requirements:** DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Depends on:** — (independent)
**Plans:** 6/6 plans complete
**Completed:** 2026-05-26

**Delivered:**

- `/metrics` endpoint at port 8080 exposing 28 Prometheus metrics
- Grafana dashboard extended with 6-row structure (Server, Ingestion, Jobs, Embedding, Cache, Qdrant)
- Docker Compose stack with 4 services (Qdrant, kb-rag-mcp, Prometheus, Grafana)
- Kubernetes Helm chart with monitoring toggle (StatefulSet + Deployment)
- Docker entrypoint script for dual-server startup (health + MCP)
- Healthcheck fixes (GET method, 120s start_period, wget)
- Comprehensive documentation (OPERATIONS.md Health Dashboard section)

Plans:

- [x] 14-01-PLAN.md — Add /metrics endpoint to health_server.py (Prometheus scraping)
- [x] 14-02-PLAN.md — Extend Grafana dashboard with 6-tab structure (28+ panels)
- [x] 14-03-PLAN.md — Docker Compose integration (Prometheus + Grafana services)
- [x] 14-04-PLAN.md — Kubernetes/Helm integration (StatefulSet + Deployment)
- [x] 14-05-PLAN.md — Documentation update (OPERATIONS.md, screenshots)
- [x] 14-06-PLAN.md — Docker Compose fixes (healthchecks, entrypoint, ports)

---

### Phase 15: PowerShell script opens ports for all subsystems

**Goal:** Ensure `scripts/start-kb-rag.ps1` opens the required ports for all subsystems (Qdrant, MCP server, health server, Prometheus, Grafana) automatically during local/dev setup.

**Milestone:** v1.3
**Requirements:** WIN-01, WIN-02, WIN-03, DOCS-04, DOCS-05
**Depends on:** Phase 14 (defines port 8080 for health/metrics)
**Plans:** 2/2 plans complete
**Status:** ✅ Complete
**Completed:** 2026-05-26

**Delivered:**

- `-ConfigureFirewall` switch added to `scripts/start-kb-rag.ps1`
- Elevation detection with auto-elevation prompt
- Idempotent firewall rule creation for 6 ports (Qdrant, MCP, Health, Prometheus, Grafana)
- Comprehensive documentation (README.md, README.pt-BR.md, README.es.md, OPERATIONS.md)
- Manual and group policy deployment guidance
- All Portuguese comments translated to English

Plans:

- [x] 15-01-PLAN.md — Enhance start-kb-rag.ps1 with firewall configuration — completed 2026-05-26
- [x] 15-02-PLAN.md — Documentation updates (READMEs + OPERATIONS.md) — completed 2026-05-26

---

### Phase 16: Reclassification capability for document database

**Goal:** Provide a mechanism to reclassify already-ingested documents when classification logic improves. Updates metadata (vendor/product/subsystem/doc_type/version) in Qdrant without re-processing or re-embedding.

**Milestone:** v1.3
**Requirements:** RECLASSIFY-01 through RECLASSIFY-07
**Depends on:** Phase 11 (auto-classification)
**Plans:** 3/3 plans complete
**Estimated effort:** 18 hours (6h + 8h + 4h)

Plans:

- [x] **16-01:** Core Reclassification Engine (6h) — VectorStore updates, SQLite backup/audit tables, classification detection, backup/log functions
- [x] **16-02:** CLI Commands (8h) — reclassify, verify, rollback, sessions subcommands with Rich progress/preview
- [x] **16-03:** Documentation (4h) — README.md/pt-BR/es sections, OPERATIONS.md procedures

### Phase 17: Improve capability negotiation on the MCP server to advertise classified attributes

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 16
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd:plan-phase 17 to break down)

---

### Phase 17: Improve capability negotiation on the MCP server to advertise classified attributes

**Goal:** Advertise OTCS auto-tagging attributes (vendor, product, module, subsystem, version) during MCP tool negotiation so clients can discover available filter values. Maintain a compact terms table indexed from the knowledge base — token-size controlled to avoid excessive context consumption.

**Milestone:** v1.3
**Requirements:** TBD
**Depends on:** Phase 11 (auto-classification stores vendor/product/subsystem/version in Qdrant)
**Plans:** 0 plans

Plans:
- [ ] TBD

---

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
| 17. Capability Negotiation | v1.3 | 0/0 | Planned    | —

## Backlog

### Phase 999.1: Fix Grafana "Datasource ${DS_PROMETHEUS} was not found" error (BACKLOG)

**Goal:** Fix the Prometheus datasource variable resolution error in the "KB-RAG MCP Health Dashboard" Grafana dashboard when loaded via `docker compose up -d`. Ensure the datasource name or variable reference matches what's provisioned in the Grafana datasource configuration.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with `/gsd-review-backlog` when ready)
