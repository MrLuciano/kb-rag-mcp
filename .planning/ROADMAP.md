# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Quality & Operational Excellence** — Phases 5–8 (shipped 2026-05-23) — [archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Tech Debt & Classification** — Phases 9–11 (shipped 2026-05-25)
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

---

### Phase 9: Startup Reliability (COMPLETED)

**Goal:** Reduce server startup latency, add pre-flight health checks, and document embedding dependencies so operators know when the system is healthy before accepting queries.

**Milestone:** v1.2
**Requirements:** DEBT-01, DEBT-04, DEBT-06

**Success criteria — all met:**

1. ✅ Server starts without loading the cross-encoder model — first inference loads it lazily (~500MB saved, ~10s faster startup)
2. ✅ Server logs a warning at startup if Qdrant or LM Studio are unreachable
3. ✅ Operators can run `kb-ingest check` (or equivalent) to validate external dependency health
4. ✅ LM Studio embedding dependency and documented in OPERATIONS.md

**Plans:** 3 plans

Plans:

- [x] 09-01-PLAN.md — Cross-encoder lazy loading verification & hardening (DEBT-01)
- [x] 09-02-PLAN.md — Pre-flight health checks + `kb-ingest check health` CLI (DEBT-04)
- [x] 09-03-PLAN.md — LM Studio embedding dependency documentation (DEBT-06)

### Phase 10: CI & Test Infrastructure

**Goal:** Fix MagicMock pollution in the test suite, validate Helm charts in CI, and enforce logging coverage to prevent quality regression.

**Milestone:** v1.2
**Requirements:** DEBT-02, DEBT-03, DEBT-05

**Success criteria:**

1. ✅ `helm lint` runs in CI and catches structural errors — no more manual-only chart review
2. ✅ All `qdrant_client` enum comparisons in tests work without `getattr(x, 'value', x)` workaround
3. ✅ Logging audit script has `--fail-under` flag; CI enforces threshold on PR-to-master
4. ✅ Full test suite passes with zero pre-existing failures

**Plans:** 3 plans

Plans:

- [x] 10-01-PLAN.md — Helm chart validation in CI with `helm lint --strict` (DEBT-02)
- [x] 10-02-PLAN.md — Replace MagicMock-polluted qdrant_client stubs with real model imports (DEBT-03)
- [x] 10-03-PLAN.md — Logging audit `--fail-under` flag + CI enforcement gate (DEBT-05)

### Wave Dependencies

**Wave 1** *(2/2 plans complete)*
**Wave 2** *(10-03)*

**Cross-cutting constraints:**

- All 3 plans must ship together to satisfy DEBT-02, DEBT-03, DEBT-05
- Full test suite (576+ tests) must pass at each plan completion
- CI workflow file must remain valid YAML after each modification

**Delivered (2026-05-25):**

- 10-01: `helm-lint` job added to CI (azure/setup-helm@v4, `helm lint --strict`, `helm template`)
- 10-02: Real qdrant_client imports in 3 test files — no MagicMock stubs for model classes
- 10-03: `--fail-under` flag in logging-audit.py; CI enforcement step on PR-to-master

### Phase 11: Auto-Classification (COMPLETED)

**Goal:** Extend document classifier to extract Vendor, Product, Subsystem, and Version from filename patterns, directory hierarchy, and document metadata — no LLM dependency.

**Milestone:** v1.2
**Requirements:** CLASSIFY-01, CLASSIFY-02, CLASSIFY-03

**Success criteria — all met:**

1. ✅ A file named `OpenText WebReport Administrator Guide 23.4.pdf` is classified with `vendor=OpenText`, `product=WebReports`, `version=23.4`, `doc_type=admin_guide`
2. ✅ Classification fills gaps from PDF/DOCX metadata (title, subject, author, keywords) when filename is ambiguous
3. ✅ Existing `infer_product()`, `infer_doc_type()`, `classify()` signatures unchanged — backward compatible
4. ✅ All 585 tests pass; OTCS product detection still works as before

**Plans:** 2 plans — both executed 2026-05-25

**Delivered:**

- `infer_vendor()`: Detects OpenText from filename patterns, directory names, and product-to-vendor mapping (15 products mapped)
- `infer_subsystem()`: Detects subsystem from directory hierarchy (8 functional categories via filename patterns)
- `extract_document_metadata()`: Extract title/author/subject/keywords from PDF (PyMuPDF) and DOCX (python-docx)
- `enrich_classification()`: Gap-fills vendor/product/doc_type from document metadata (lowest precedence, never overrides explicit classification)
- Ingest pipeline stores vendor/subsystem in Qdrant chunk payload
- Bug fix: `DOC_TYPE_RULES` standard patterns now use word boundaries — no longer false-positive matches on "nist" substring in "Administrator"
- 72 classifier tests (58 existing + 7 metadata + 7 enrichment), all passing

Plans:

- [x] 11-01-PLAN.md — Vendor & subsystem inference + SC1 end-to-end classification
- [x] 11-02-PLAN.md — Document metadata extraction, gap-filling enrichment, ingest pipeline integration

---

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
| 12. English Comments & Docstrings | v1.3 | 3/3 | Complete | 2026-05-25 |
| 13. Docs Sync & Readme Languages | v1.3 | 4/4 | Complete    | 2026-05-26 |
| 14. Health Dashboard | v1.3 | 6/6 | Complete   | 2026-05-26 |
| 15. PowerShell Ports Script | v1.3 | 2/2 | Complete   | 2026-05-26 |
| 16. Reclassification | v1.3 | 3/3 | Complete   | 2026-05-27 |
