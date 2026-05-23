# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](.planning/milestones/v1.0-ROADMAP.md)
- 🔄 **v1.1 Quality & Operational Excellence** — Phases 5–8 (in progress)

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

### v1.1 Quality & Operational Excellence

- [ ] Phase 5: SSE Stability & Python 3.13 Compatibility (2/2 plans)
- [ ] Phase 6: Test Coverage & Isolation (0/3 plans)
- [ ] Phase 7: Logging, Quality Gate & Coverage Enforcement (0/2 plans)
- [ ] Phase 8: Ingest Improvements & Documentation (0/3 plans)

---

### Phase 5: SSE Stability & Python 3.13 Compatibility

**Goal:** Ensure the MCP SSE server works correctly on starlette 1.0.0 and Python 3.13, with regression tests that prevent the NoneType crash from recurring.

**Milestone:** v1.1
**Requirements:** SSE-01, SSE-02, COMPAT-01, COMPAT-02

**Success criteria:**
1. `GET /sse` followed by client disconnect produces no `TypeError: NoneType` crash in server logs
2. `POST /messages/` (with trailing slash) returns `202 Accepted` with no redirect chain
3. Full test suite passes on Python 3.11 and Python 3.13 in CI matrix
4. No `DeprecationWarning` from Python 3.13 in the test run

**Plans:** 2 plans

Plans:
- [ ] 05-01-PLAN.md — SSE regression tests (unit + integration), starlette version pin
- [ ] 05-02-PLAN.md — CI matrix (3.11, 3.12, 3.13), dependency compatibility audit

---

### Phase 6: Test Coverage & Isolation

**Goal:** Every Python module has a unit test file; all external dependencies (Qdrant, LM Studio, Redis) are mocked so tests run in any environment without infrastructure.

**Milestone:** v1.1
**Requirements:** TEST-01, TEST-02, TEST-03

**Success criteria:**
1. `pytest -m "not integration"` completes successfully with no Qdrant, LM Studio, or Redis running
2. Every module under `kb_server/` and `ingest/` has at least one `tests/unit/test_<module>.py`
3. Integration tests are tagged `@pytest.mark.integration` and excluded from unit run
4. Test count increases by ≥50 new unit tests vs v1.0 baseline (491)

**Plans:**
- [ ] 6-01: Mock infrastructure — `conftest.py` fixtures for Qdrant, embed client, Redis; remove all live-service assumptions from unit tests
- [ ] 6-02: Unit test gap fill — write missing test files for all uncovered modules in `kb_server/`
- [ ] 6-03: Unit test gap fill — write missing test files for all uncovered modules in `ingest/`

---

### Phase 7: Logging, Quality Gate & Coverage Enforcement

**Goal:** All public methods emit structured logs; CI enforces ≥90% branch coverage on `kb_server/` and fails the build on regression.

**Milestone:** v1.1
**Requirements:** LOG-01, LOG-02, QUAL-01, QUAL-02

**Success criteria:**
1. `pytest --cov=kb_server --cov-fail-under=90` exits 0 on CI
2. `pyproject.toml` `fail_under = 90` is set and a deliberate coverage regression causes CI to fail
3. Every public method in `kb_server/` has at least one log entry (verified by audit script)
4. Logging audit report committed to `docs/logging-audit.md`

**Plans:**
- [ ] 7-01: Quality gate — set `fail_under = 90` in `pyproject.toml`, update CI workflow, verify enforcement
- [ ] 7-02: Logging coverage audit + gap fill — audit all public methods, add missing log calls, commit audit report

---

### Phase 8: Ingest Improvements & Documentation

**Goal:** OTCS documents are auto-tagged by product area; operators have a CLI status command; key documentation is updated for v1.1.

**Milestone:** v1.1
**Requirements:** INGEST-01, INGEST-02, DOC-01, DOC-02

**Success criteria:**
1. Ingesting a file named `3-0117 Content Server WebReport Design.pdf` auto-assigns `product=WebReports` without `--product` flag
2. `kb-ingest status` prints last run time, total docs, total chunks, error count
3. All public functions and classes in `kb_server/` and `ingest/` have English docstrings
4. `docs/` contains updated architecture, ingest workflow, and remote deployment guide

**Plans:**
- [ ] 8-01: OTCS auto-tagging — filename/path heuristic classifier for WebReports, xECM, Workflow, CSIDE, etc.
- [ ] 8-02: `kb-ingest status` CLI command — query `kb_metadata.db` and Qdrant for live stats
- [ ] 8-03: Documentation pass — English docstrings for all public APIs; update `docs/` with v1.1 runbook

## Backlog

### Phase 999.1: Source code comments and documentation all in English (BACKLOG)

**Goal:** Ensure all inline comments, docstrings, log messages, and internal documentation across Python source files are written in English for consistency and open-source readiness.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

---

### Phase 999.2: Update docs folder, README all languages, add Spanish README (BACKLOG)

**Goal:** Sync the `docs/` folder with all changes shipped since v1.0, update README.md and README.pt-BR.md to reflect current state, and add a new README.es.md in Spanish.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

---

### Phase 999.3: System health dashboard — single page served via httpd pod (BACKLOG)

**Goal:** Consolidate health/status access to all subsystems (Qdrant health, kb-rag-mcp server, ingestion status) into a single beautiful dashboard page served in a httpd pod.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

---

### Phase 999.4: PowerShell script opens ports for all subsystems (BACKLOG)

**Goal:** Ensure `scripts/start-kb-rag.ps1` opens the required ports for all subsystems (Qdrant, MCP server, health server) automatically during local/dev setup.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

---

### Phase 999.5: Automatic document classification — Vendor/Product/Subsystem/Version (BACKLOG)

**Goal:** During ingestion, auto-classify documents with attributes: Vendor, Product, Subsystem, Module, Document Type, Version. Classification inferred from filename, folder path, and first-page content (title, header, footer). Pattern: `OpenText Documentum Webtop Administrator Guide 23.4.pdf`.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

---

### Phase 999.6: Reclassification capability for document database (BACKLOG)

**Goal:** When automatic classification (999.5) is ready, provide a mechanism to reclassify already-ingested documents — either reclassify in-place in the database, or re-ingest with updated metadata.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Codebase Consolidation | v1.0 | 4/4 | Complete | 2026-05-16 |
| 2. Data Integrity & Security | v1.0 | 3/3 | Complete | 2026-05-17 |
| 3. Test Coverage & CI | v1.0 | 3/3 | Complete | 2026-05-19 |
| 4. Deployment & Release | v1.0 | 3/3 | Complete | 2026-05-19 |
| 5. SSE Stability & Python 3.13 | v1.1 | 2/2 | Ready | — |
| 6. Test Coverage & Isolation | v1.1 | 0/3 | Pending | — |
| 7. Logging, Quality Gate & Coverage | v1.1 | 0/2 | Pending | — |
| 8. Ingest Improvements & Docs | v1.1 | 0/3 | Pending | — |
