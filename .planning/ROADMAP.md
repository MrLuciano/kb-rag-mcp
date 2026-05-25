# Roadmap: kb-rag-mcp

## Milestones

- ✅ **v1.0 Release-Readiness** — Phases 1–4 (shipped 2026-05-19) — [archive](.planning/milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Quality & Operational Excellence** — Phases 5–8 (shipped 2026-05-23)
- 🔄 **v1.2 Tech Debt & Classification** — Phases 9–11 (planning)

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

**Plans:** 3 plans

Plans:
- [ ] 06-01-PLAN.md — Mock infrastructure: conftest fixtures + registered pytest markers
- [ ] 06-02-PLAN.md — kb_server test classifier + integration tagging audit
- [ ] 06-03-PLAN.md — ingest integration tagging + full isolation verification

### Wave Dependencies
**Wave 2** *(blocked on Wave 1 completion)*

**Cross-cutting constraints:**
- Every Python module has a dedicated unit test file (TEST-01)
- `pytest -m "not integration"` requires no Qdrant, LM Studio, or Redis (TEST-02)
- All integration tests are tagged `@pytest.mark.integration` (TEST-03)

---

### Phase 7: Logging, Quality Gate & Coverage Enforcement

**Goal:** All public methods emit structured logs; CI enforces ≥90% branch coverage on `kb_server/` and `ingest/` and fails the build on regression.

**Milestone:** v1.1
**Requirements:** LOG-01, LOG-02, QUAL-01, QUAL-02

**Success criteria:**
1. `pytest --cov=kb_server --cov=ingest --cov-fail-under=90` exits 0 on CI
2. `pyproject.toml` `fail_under = 90` is set and a deliberate coverage regression causes CI to fail
3. Every public method in `kb_server/` has at least one log entry (verified by audit script)
4. Logging audit report committed to `docs/logging-audit.md`

**Plans:** 2 plans

Plans:
- [ ] 07-01-PLAN.md — Quality gate: set `fail_under = 90` in `pyproject.toml`, update CI workflow with coverage enforcement on PR-to-master
- [ ] 07-02-PLAN.md — Logging coverage audit + gap fill: audit all public methods, add missing log calls to kb_server/ and ingest/, commit audit report

### Wave Dependencies
**Wave 1** *(both plans are independent — no blocking dependencies)*

**Cross-cutting constraints:**
- Quality gate must cover both `kb_server/` and `ingest/` (D-01, D-02)
- Coverage exclusions are inline `# pragma: no cover` only — no centralized excludes (D-05)
- Both `pyproject.toml` `fail_under` and CI `--cov-fail-under` must be set (D-06)
- Coverage enforcement runs on PR to master only (D-07)
- CI coverage step covers both `--cov=kb_server --cov=ingest` (D-08)

---

### Phase 8: Ingest Improvements & Documentation (COMPLETED)

**Goal:** OTCS documents are auto-tagged by product area; operators have a CLI status command; key documentation is updated for v1.1.

**Milestone:** v1.1
**Requirements:** INGEST-01, INGEST-02, DOC-01, DOC-02

**Success criteria — all met:**
1. ✅ `3-0117 Content Server WebReport Design.pdf` auto-assigns `product=WebReports`
2. ✅ `kb-ingest status` prints per-source file/chunk/error counts with `--source` filter
3. ✅ All public functions/classes have English Google-style docstrings (0 gaps, 0 Portuguese)
4. ✅ `docs/` updated: ARCHITECTURE.md (Mermaid), OPERATIONS.md (remote deploy), INDEX.md, REFERENCE.md

**Plans:** 3 plans — all executed 2026-05-23

**Delivered:**
- 10 OTCS product areas auto-detectable (WebReports, xECM, Workflow, CSIDE, ContentServer, Brava, OT2, DocumentViewer, APIGateway, ArchiveCenter)
- `kb-ingest status` with Rich table (Source/Files/Chunks/Errors/Last Ingest)
- `scripts/docstring-audit.py` — AST-based docstring coverage scanner
- 105 docstring gaps fixed (32 MISSING + 73 PORTUGUESE → 0)
- All 4 main docs refreshed for v1.1 accuracy

---

### Phase 9: Startup Reliability

**Goal:** Reduce server startup latency, add pre-flight health checks, and document embedding dependencies so operators know when the system is healthy before accepting queries.

**Milestone:** v1.2
**Requirements:** DEBT-01, DEBT-04, DEBT-06

**Success criteria:**
1. Server starts without loading the cross-encoder model — first inference loads it lazily (~500MB saved, ~10s faster startup)
2. Server logs a warning at startup if Qdrant or LM Studio are unreachable
3. Operators can run `kb-ingest check` (or equivalent) to validate external dependency health
4. LM Studio dependency and startup options documented in OPERATIONS.md

**Plans:** 3 plans

Plans:
- [ ] 09-01-PLAN.md — Cross-encoder lazy loading verification & hardening (DEBT-01)
- [ ] 09-02-PLAN.md — Pre-flight health checks + `kb-ingest check health` CLI (DEBT-04)
- [ ] 09-03-PLAN.md — LM Studio embedding dependency documentation (DEBT-06)

### Phase 10: CI & Test Infrastructure

**Goal:** Fix MagicMock pollution in the test suite, validate Helm charts in CI, and enforce logging coverage to prevent quality regression.

**Milestone:** v1.2
**Requirements:** DEBT-02, DEBT-03, DEBT-05

**Success criteria:**
1. `helm lint` runs in CI and catches structural errors — no more manual-only chart review
2. All `qdrant_client` enum comparisons in tests work without `getattr(x, 'value', x)` workaround
3. Logging audit script has `--fail-under` flag; CI enforces threshold on PR-to-master
4. Full test suite passes with zero pre-existing failures

**Plans:** 3 plans

### Phase 11: Auto-Classification

**Goal:** Extend document classifier to extract Vendor, Product, Subsystem, and Version from filename patterns, directory hierarchy, and document metadata — no LLM dependency.

**Milestone:** v1.2
**Requirements:** CLASSIFY-01, CLASSIFY-02, CLASSIFY-03

**Success criteria:**
1. A file in `WebReports/` directory or named `OpenText WebReport Administrator Guide 23.4.pdf` is classified with `vendor=OpenText`, `product=WebReports`, `version=23.4`, `doc_type=admin_guide`
2. Classification fills gaps from PDF/DOCX metadata (title, subject, author, keywords) when filename is ambiguous
3. Existing `infer_product()`, `infer_doc_type()`, `classify()` signatures unchanged — backward compatible
4. All tests pass; OTCS product detection still works as before

**Plans:** 2 plans

---

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
| 5. SSE Stability & Python 3.13 | v1.1 | 2/2 | Complete | 2026-05-21 |
| 6. Test Coverage & Isolation | v1.1 | 3/3 | Complete | 2026-05-22 |
| 7. Logging, Quality Gate & Coverage | v1.1 | 2/2 | Complete | 2026-05-23 |
| 8. Ingest Improvements & Docs | v1.1 | 3/3 | Complete | 2026-05-23 |
| 9. Startup Reliability | v1.2 | 0/3 | Planning | — |
| 10. CI & Test Infrastructure | v1.2 | 0/3 | Planning | — |
| 11. Auto-Classification | v1.2 | 0/2 | Planning | — |
