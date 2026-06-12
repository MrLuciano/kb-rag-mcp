# Milestone v0.1.3 — Project Summary

**Generated:** 2026-05-27
**Purpose:** Team onboarding and project review
**Status:** ✅ COMPLETE (2026-05-27)

---

## 1. Project Overview

### What This Is

kb-rag-mcp is a production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation.

### Core Value

AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

### Milestone v0.1.3 Goal

Complete the v0.1.3 Post-Ship Polish & Infrastructure cycle: deliver English-only codebase enforcement, multilingual README (Spanish), Grafana health dashboard, PowerShell Windows LAN access script, document reclassification capability, capability negotiation for MCP attribute advertising, fix Grafana datasource error, backfill process debt (VERIFICATION.md), resolve test environment issues, codebase hygiene sweep, and wire integration checker CI gate.

### Completion Status

**All 11 phases complete (2026-05-25 → 2026-05-27):**

| Phase | Name | Status | Completed |
|-------|------|--------|-----------|
| 12 | English Comments & Docstrings | ✅ Complete | 2026-05-25 |
| 13 | Docs Sync & README Languages | ✅ Complete | 2026-05-26 |
| 14 | Health Dashboard | ✅ Complete | 2026-05-26 |
| 15 | PowerShell Ports Script | ✅ Complete | 2026-05-26 |
| 16 | Reclassification Capability | ✅ Complete | 2026-05-27 |
| 17 | Capability Negotiation | ✅ Complete | 2026-05-27 |
| 18 | Grafana Datasource Fix | ✅ Complete | 2026-05-27 |
| 19 | VERIFICATION.md Backfill | ✅ Complete | 2026-05-27 |
| 20 | Test Environment Fixes | ✅ Complete | 2026-05-27 |
| 21 | Codebase Hygiene Sweep | ✅ Complete | 2026-05-27 |
| 22 | Integration Checker CI Gate | ✅ Complete | 2026-05-27 |

---

## 2. Architecture & Technical Decisions

### Key Technical Choices

- **Decision:** Portuguese-to-English codebase sweep with CI enforcement
  - **Why:** Open-source readiness requires a single language for all source comments, docstrings, and log messages
  - **Phase:** 12 — English Comments & Docstrings
  - **Pattern:** Extended `scripts/docstring-audit.py` with `--check-inline --fail-under 0` flag; `english-audit` CI job runs on every push/PR
  - **Result:** 0 Portuguese docstrings, 0 Portuguese inline comments — verified by automated audit

- **Decision:** Grafana-centric monitoring dashboard (not custom HTML/FastAPI)
  - **Why:** Leverages existing Grafana + Prometheus investment; avoids building a second dashboard
  - **Phase:** 14 — Health Dashboard
  - **Pattern:** Extended existing `grafana-dashboard.json` with 6-row structure (Server, Ingestion, Jobs, Embedding, Cache, Qdrant) and 28 panels
  - **Impact:** 4-service Docker Compose stack (Qdrant, kb-rag-mcp, Prometheus, Grafana); dual-server entrypoint script; UAT verified on dev + production

- **Decision:** In-place metadata updates for reclassification (no re-embedding)
  - **Why:** Preserves embeddings and vectors; updates only Qdrant payload fields — avoids expensive re-indexing
  - **Phase:** 16 — Reclassification
  - **Pattern:** SQLite backup/audit tables for rollback; classification detection compares current vs. expected; session-based + selective rollback

- **Decision:** Three-layer capability negotiation (dynamic descriptions + no enum constraints + new `list_filter_options` tool)
  - **Why:** Token-budget optimization — tool descriptions show top-20 values while `list_filter_options` enables full enumeration without bloating every negotiation
  - **Phase:** 17 — Capability Negotiation
  - **Pattern:** `FilterTermsCache` with cache-bust marker file; `infer_module()` classification axis; 33 new tests

- **Decision:** Stable UID approach for Grafana datasource fix
  - **Why:** Replacing `${DS_PROMETHEUS}` template variables with hardcoded `"prometheus"` references + stable `uid: prometheus` in datasource provisioning resolves dashboard load errors without template variable resolution
  - **Phase:** 18 — Grafana Datasource Fix
  - **Pattern:** Applied identically across Docker Compose and Helm paths

- **Decision:** All gaps hard-fail in integration checker (no warnings-only mode)
  - **Why:** Documentation drift must be caught immediately in CI; warning-only modes allow silent accumulation
  - **Phase:** 22 — Integration Checker CI Gate
  - **Pattern:** 3 checks (VERIFICATION.md presence, REQUIREMENTS.md traceability, SUMMARY.md file references); Rich stdout + JSON results; `needs: test` in CI

### Tech Stack Evolution

**Added in v0.1.3:**
- `unittest.mock` fixtures — `mock_objects` fixture pattern for test isolation (Phase 20)
- `FilterTermsCache` — cache-bust marker file pattern (Phase 17)
- `scripts/check-integration-gaps.py` — Python CI gate with Rich + JSON (Phase 22)
- `scripts/check-verification-gaps.sh` — shell gap detection (Phase 19)
- `deployment/config/grafana-provisioning/datasources/` — datasource YAML provisioning (Phase 14, 18)
- `deployment/helm/kb-rag-mcp/templates/prometheus.yaml` — Prometheus StatefulSet (Phase 14)
- `deployment/helm/kb-rag-mcp/templates/grafana.yaml` — Grafana Deployment (Phase 14)
- `ingest/cli/reclassify.py` — 4 subcommands: run, verify, sessions, rollback (Phase 16)
- `ingest/reclassify_engine.py` — 4 core engine functions (Phase 16)
- `kb_server/filter_terms_cache.py` — FilterTermsCache singleton (Phase 17)
- `ingest/utils.py` — `write_filter_cache_bust()` helper (Phase 17)

**Patterns Established:**
- CI gate pattern: standalone Python script in `scripts/` with argparse, Rich output, non-zero exit on failure
- Reclassification engine: in-place metadata update + SQLite backup/rollback + session tracking
- Capability negotiation: FilterTermsCache + cache-bust marker + dynamic tool descriptions
- English enforcement: `docstring-audit.py --check-inline --fail-under 0` in CI
- Grafana provisioning: datasource YAML with stable UID, no template variables

---

## 3. Phases Delivered

| Phase | Name | Plans | One-Liner |
|-------|------|-------|-----------|
| 12 | English Comments & Docstrings | 3 | All Portuguese comments/docstrings translated to English across ~35 files; CI gate with `english-audit` job |
| 13 | Docs Sync & README Languages | 4 | README.md/pt-BR/es refreshed; stale docs (AUTO_INGESTION, TROUBLESHOOTING, TESTING, KUBERNETES) updated |
| 14 | Health Dashboard | 6 | `/metrics` endpoint (28 metrics), Grafana 6-tab dashboard, Docker Compose + Helm monitoring stack, dual-server entrypoint |
| 15 | PowerShell Ports Script | 2 | `-ConfigureFirewall` switch, elevation detection, idempotent rules for 6 ports, comprehensive docs in 3 languages |
| 16 | Reclassification | 3 | In-place metadata updates, SQLite backup/rollback, CLI subcommands (run/verify/sessions/rollback), ~820 lines new docs |
| 17 | Capability Negotiation | 3 | `infer_module()` classification axis, FilterTermsCache, dynamic `list_tools()`, `list_filter_options` tool, 33 new tests |
| 18 | Grafana Datasource Fix | 1 | Stable `uid: prometheus`, hardcoded `"prometheus"` refs, `__inputs` removal in both Docker Compose and Helm paths |
| 19 | VERIFICATION.md Backfill | 1 | 13 VERIFICATION.md files created for phases 05-13, 16-18; `scripts/check-verification-gaps.sh` detection script |
| 20 | Test Environment Fixes | 1 | LOG_PATH PermissionError guard, `test_reranker_lazy.py` fixture isolation, stale artifact cleanup |
| 21 | Codebase Hygiene Sweep | 1 | 13 unused imports removed, 3 TODOs resolved, 6 f-string logs standardized, 2 dead code instances removed |
| 22 | Integration Checker CI Gate | 1 | `scripts/check-integration-gaps.py` with 3 checks; `integration-check` CI job with `needs: test` |

---

## 4. Requirements Coverage

### All v0.1.3 Requirements Met (26 total)

**English Comments & Docstrings (Phase 12):**
- ✅ Goal: All Python source files in English — 0 accented Portuguese characters, 0 Portuguese phrase matches
- ✅ CI enforcement via `english-audit` job with `--check-inline --fail-under 0` on every push/PR

**Docs Sync & README Languages (Phase 13):**
- ✅ DOCS-01: README.md core sections refreshed (header through Usage, 13-01)
- ✅ DOCS-02: README.md advanced sections refreshed (Health Checks through Contributing, 13-02)
- ✅ DOCS-03: README.pt-BR.md sync + README.es.md creation (13-03)
- ✅ DOCS-04: Stale docs updated (AUTO_INGESTION, TROUBLESHOOTING, TESTING, KUBERNETES, 13-04)

**Health Dashboard (Phase 14):**
- ✅ DASH-01: `/metrics` endpoint at port 8080 — 28 Prometheus metrics
- ✅ DASH-02: Grafana dashboard with 6 rows, 28 panels
- ✅ DASH-03: Docker Compose integration — 4 services healthy on dev + production
- ✅ DASH-04: Kubernetes/Helm integration — Prometheus StatefulSet + Grafana Deployment with toggle
- ✅ DASH-05: Comprehensive documentation (OPERATIONS.md + README.md links)
- ✅ Blocker resolved: healthcheck method (GET), start_period (120s), entrypoint script

**PowerShell Ports (Phase 15):**
- ✅ WIN-01: Auto firewall config — `-ConfigureFirewall` switch creates 6 rules
- ✅ WIN-02: Idempotency — existing rules detected and skipped
- ✅ WIN-03: Elevation detection — `Test-IsAdministrator` + auto-elevation prompt
- ✅ DOCS-04: Windows firewall docs in README.md/pt-BR/es + OPERATIONS.md
- ✅ DOCS-05: Troubleshooting guidance — 5+ scenarios in OPERATIONS.md

**Reclassification (Phase 16):**
- ✅ RECLASSIFY-01: In-place metadata updates preserve embeddings
- ✅ RECLASSIFY-02: SQLite backup/audit tables for rollback
- ✅ RECLASSIFY-03: Classification detection compares current vs. expected
- ✅ RECLASSIFY-04: CLI subcommand with interactive preview
- ✅ RECLASSIFY-05: Verify subcommand shows mismatches
- ✅ RECLASSIFY-06: Session-based and selective rollback
- ✅ RECLASSIFY-07: Documentation in README and OPERATIONS.md

**Capability Negotiation (Phase 17):**
- ✅ CAPNEG-01: MCP server advertises classified attributes (vendor, product, subsystem, version, module)
- ✅ CAPNEG-02: Tokens compact — top-20 values in descriptions, FilterTermsCache controls context
- ✅ CAPNEG-03: Extends existing `search_kb`/`list_documents` tool descriptions
- ✅ CAPNEG-04: Backend indexes KB for unique attribute values via `get_distinct_values()`

**Grafana Datasource Fix (Phase 18):**
- ✅ DSFIX-01: Dashboard loads without "Datasource ${DS_PROMETHEUS} was not found" errors
- ✅ DSFIX-02: Stable UID (`uid: "prometheus"`) added to datasource provisioning
- ✅ DSFIX-03: Hardcoded `"prometheus"` references replace `${DS_PROMETHEUS}` in both deployment JSONs
- ✅ DSFIX-04: `__inputs` sections removed
- ✅ DSFIX-05: Helm chart produces same fix

**VERIFICATION.md Backfill (Phase 19):**
- ✅ VERBACK-01: 13 VERIFICATION.md files for phases 05-13, 16-18
- ✅ VERBACK-02: Each documents verification criteria, commands, and results
- ✅ VERBACK-03: Backfill uses git log + test history
- ✅ VERBACK-04: Gap detection script at `scripts/check-verification-gaps.sh`

**Test Environment Fixes (Phase 20):**
- ✅ TESTFIX-01: Fixture isolation — mocks in fixture scope, 4 tests pass
- ✅ TESTFIX-02: LOG_PATH PermissionError eliminated — `os.makedirs` guard
- ✅ TESTFIX-03: Clean environment — stale artifacts removed

**Codebase Hygiene (Phase 21):**
- ✅ HYGIENE-01: 13 unused imports removed across 7 files
- ✅ HYGIENE-02: 3 TODOs resolved
- ✅ HYGIENE-04: 6 f-string log messages standardized in embed_client.py
- ✅ HYGIENE-05: 2 dead code instances removed
- ❌ HYGIENE-03: Cancelled — `Any` legitimately used in generic cache/collections layers

**Integration Checker CI Gate (Phase 22):**
- ✅ CICHECK-01: CI job runs after tests (`needs: test`)
- ✅ CICHECK-02: Validates 3 gap types (VERIFICATION.md, REQUIREMENTS traceability, SUMMARY.md file refs)
- ✅ CICHECK-03: CI fails on unresolved gaps (exit code 1)
- ✅ CICHECK-04: Rich stdout table + JSON results for debugging

### Success Criteria Verification

**Phase 12:**
- ✅ `scripts/docstring-audit.py --check-inline --fail-under 0` exits 0 — 0 Portuguese comments/docstrings
- ✅ False positives fixed — 15 technical terms removed from Portuguese detection set

**Phase 14:**
- ✅ `curl localhost:8080/metrics` returns Prometheus format with `kb_` metrics
- ✅ All 4 Docker Compose services healthy on dev + production
- ✅ Grafana dashboard loads with all 6 rows and 28 panels
- ✅ Helm lint passes: `1 chart(s) linted, 0 chart(s) failed`

**Phase 16:**
- ✅ `kb-ingest reclassify run --files '**/*.pdf'` detects changed classifications
- ✅ `kb-ingest reclassify verify --files '**/*.pdf'` shows mismatches without applying
- ✅ `kb-ingest reclassify sessions` lists all reclassification sessions
- ✅ `kb-ingest reclassify rollback --session <id>` restores metadata
- ✅ 33 passing tests across 6 test files

**Phase 17:**
- ✅ MCP `list_tools` response includes filter values in description (top-20)
- ✅ `list_filter_options(field="vendor")` returns all distinct vendor values
- ✅ Module field in Qdrant payload and search filters
- ✅ Cache-bust marker file written after ingest/reclassify
- ✅ 33 new tests + 1 integration test

**Phase 18:**
- ✅ `uid: prometheus` in Docker Compose and Helm datasource YAML
- ✅ 63 `${DS_PROMETHEUS}` → `"prometheus"` replacements in each dashboard JSON
- ✅ All `__inputs` sections removed
- ✅ Same fix applied across both config and helm paths

**Phase 19:**
- ✅ `scripts/check-verification-gaps.sh` reports missing phases
- ✅ 13 VERIFICATION.md files exist with consistent format and ✅ status

**Phase 20:**
- ✅ `LOG_PATH=/tmp/kb-mcp.log .venv/bin/python -c 'import kb_server.server'` succeeds
- ✅ `pytest tests/test_reranker_lazy.py -q` → 4 passed
- ✅ No stale `.pyc` in project source

**Phase 21:**
- ✅ Flake8: zero F401/F841 warnings
- ✅ Zero leftover TODOs from hygiene scope
- ✅ 656 tests pass (9 pre-existing failures unchanged)

**Phase 22:**
- ✅ `scripts/check-integration-gaps.py` produces Rich table output
- ✅ Detects VERIFICATION.md gaps correctly
- ✅ JSON results written to gitignored file
- ✅ CI YAML validates with `integration-check` job

---

## 5. Key Decisions Log

| ID | Decision | Rationale | Phase | Outcome |
|----|----------|-----------|-------|---------|
| D-12-01 | CI-enforced English audit with --fail-under 0 | Zero tolerance for non-English source content in open-source project | 12 | ✅ CI blocks any PR with Portuguese comments |
| D-12-02 | Remove false positives from Portuguese detection | Technical terms (cache, chunk, hash, log, pipeline, query) are not Portuguese | 12 | ✅ Clean detection: 0 false positives |
| D-14-01 | Grafana-centric dashboard (not custom HTML) | Leverages existing Grafana investment; avoids fragmented monitoring | 14 | ✅ Single dashboard; 28 panels in 6 rows |
| D-14-02 | Dual-server architecture (health 8080 + MCP 8765) | Both servers run in same container via entrypoint script | 14 | ✅ Verified on dev + production |
| D-14-03 | Healthcheck GET method with wget -O - | FastAPI /health only accepts GET | 14 | ✅ All 4 services healthy |
| D-14-04 | 120s start_period | Large Qdrant database needs time to initialize | 14 | ✅ Boot timeout eliminated |
| D-15-01 | Hybrid opt-in -ConfigureFirewall | Backward-compatible; default behavior unchanged | 15 | ✅ Existing scripts unaffected |
| D-15-02 | Auto-elevation with user prompt | Non-admin users prompted before firewall changes | 15 | ✅ User-friendly; secure by default |
| D-15-03 | Non-fatal firewall failures | Script continues with service start even if firewall config fails | 15 | ✅ Graceful degradation |
| D-16-01 | In-place metadata update (no re-embedding) | Preserves embeddings and vectors; updates only Qdrant payload | 16 | ✅ Fast, efficient reclassification |
| D-16-02 | SQLite backup + session tracking | Full audit trail with rollback capability | 16 | ✅ Session-based undo; 30-day auto-cleanup |
| D-16-03 | Interactive confirmation with aggregated preview | Shows summary by field before applying changes | 16 | ✅ Safe by default; --yes bypass for automation |
| D-17-01 | Three-layer injection (descriptions + tool + no enums) | Token optimization: top-20 in descriptions, full via tool | 17 | ✅ Compact negotiation, full enumeration available |
| D-17-02 | Event-driven cache refresh (startup + marker file) | No periodic polling; cache mismatch detected via file timestamp | 17 | ✅ Efficient; negligible overhead |
| D-17-03 | Module classification axis added | Extends classifier.py, Qdrant payload, MCP tools | 17 | ✅ Consistent metadata model |
| D-18-01 | Stable UID + hardcoded references | Eliminates template variable resolution failure | 18 | ✅ Dashboard loads cleanly on docker-compose up |
| D-19-01 | Backfill from git log + test history | Source ground truth from actual commit and test artifacts | 19 | ✅ Accurate, auditable verification docs |
| D-20-01 | os.makedirs(exist_ok=True) for LOG_PATH | Handles any LOG_PATH value without pre-existing directory | 20 | ✅ No crash; idempotent |
| D-20-02 | Fixture-scoped mocks for test isolation | Prevents mock state leakage across test files | 20 | ✅ Clean per-test state |
| D-21-01 | Skip HYGIENE-03 (type annotations) | `Any` is legitimately used in generic cache/collections layers | 21 | ✅ Cancelled with rationale documented |
| D-22-01 | All gaps hard-fail (no warnings-only) | Documentation drift must be caught immediately in CI | 22 | ✅ CI blocks merge if any gap exists |
| D-22-02 | Rich stdout + JSON results | Dual format for CI readability and machine parsing | 22 | ✅ Human-readable tables + machine-parseable JSON |

---

## 6. Tech Debt & Deferred Items

### Tech Debt Resolved in v0.1.3

- ✅ **Portuguese comments/dockstrings** — all translated; CI gate prevents regression
- ✅ **Stale docs** — AUTO_INGESTION, TROUBLESHOOTING, TESTING, KUBERNETES refreshed
- ✅ **No monitoring dashboard** — Grafana + Prometheus deployed in Docker Compose and Helm
- ✅ **No /metrics endpoint** — 28 Prometheus metrics exposed at port 8080
- ✅ **Docker Compose healthcheck failures** — entrypoint script, GET method, 120s start_period
- ✅ **No reclassification capability** — in-place metadata updates + SQLite backup + CLI
- ✅ **Grafana DS_PROMETHEUS error** — stable UID + hardcoded refs
- ✅ **Missing VERIFICATION.md files** — 13 phases backfilled; gap detection in place
- ✅ **LOG_PATH PermissionError** — `os.makedirs` guard
- ✅ **test_reranker_lazy.py fixture pollution** — module-level mocks moved to fixture scope
- ✅ **Unused imports / TODOs / dead code** — 13 imports removed, 3 TODOs resolved, 2 dead code instances removed

### Deferred to Future Milestones

- **Higher logging coverage threshold** — 40% baseline is conservative; aspirational target (70%+) deferred
- **SSE handler test process merge** — SSE tests run in separate `python -m pytest` process due to `test_smoke.py` module-level stubs
- **`asyncio_mode = STRICT` documentation** — frequent source of CI confusion; await better docs or explore `asyncio_mode = AUTO`
- **Utility method logging exemption docs** — add `EXEMPT_METHODS` constant to `scripts/logging-audit.py`
- **Quickstart.sh clean-machine test** — Docker-based clean-room test would catch env assumptions

### Lessons Learned (from RETROSPECTIVE.md context)

- **Grafana-centric dashboards require datasource stability** — template variables (`${DS_PROMETHEUS}`) fail in automated provisioning; use stable UIDs and hardcoded references
- **Process debt grows silently** — VERIFICATION.md backfill took 1 plan but spanned 13 files; creating them inline during each phase would have cost less total effort
- **Test isolation needs fixture scope, not module level** — module-level `MagicMock` objects persist across test files; fixture-scoped mocks prevent state leakage
- **CI gates should hard-fail, not warn** — warning-only modes allow silent accumulation of gaps; hard-fail prevents documentation drift immediately
- **Dual-server containers need entrypoint scripts** — running two services (health + MCP) in one container requires careful `exec` ordering and background/foreground management

---

## 7. Getting Started

### Run the Project

**Prerequisites:**
- Python 3.11+
- Qdrant (Docker via `docker-compose.yml` or embedded mode)
- LM Studio or Ollama (embedding backend)

**Quick Start:**
```bash
# Clone and setup
git clone https://github.com/MrLuciano/kb-rag-mcp.git
cd kb-rag-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start Qdrant
docker-compose up -d

# Configure environment
cp config/.env.template .env
# Edit .env: set QDRANT_URL, EMBED_BACKEND, MODEL_NAME

# Health check
kb-ingest check health

# Ingest documents
kb-ingest ingest --docs /path/to/docs --product MyProduct

# Start MCP server
python -m kb_server.server
```

**Full monitoring stack:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
# Or rebuild fully:
docker-compose build --no-cache && docker-compose up -d
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

### Key Directories

- **`kb_server/`** — MCP server, retrieval pipeline, vector store abstraction
  - `server.py` — MCP tool handlers (search_kb, list_documents, get_chunk, kb_stats, list_filter_options)
  - `retrieval/` — Hybrid search (BM25+dense), reranking, query analysis
  - `vector_store.py` — Qdrant abstraction layer (includes `update_chunk_metadata()`, `get_distinct_values()`)
  - `embed_client.py` — Multi-backend embedding (LM Studio, Ollama, OpenAI-compat)
  - `collections/` — Collection routing and lifecycle management
  - `filter_terms_cache.py` — FilterTermsCache for capability negotiation
  - `health_server.py` — FastAPI health + metrics server (port 8080)

- **`ingest/`** — Document ingestion pipeline
  - `ingest.py` — Main ingestion orchestrator
  - `classifier.py` — Document classification (vendor/product/subsystem/doc_type/version/module)
  - `reclassify_engine.py` — Reclassification detection, backup, rollback engine
  - `parsers/` — File extractors (PDF, DOCX, XLSX, PPTX, ODT, markdown, text)
  - `core/metadata.py` — IngestRegistry (SQLite dedup, status tracking, reclassify tables)
  - `cli/` — CLI commands (ingest, status, check health, reclassify, export, progress)
  - `utils.py` — `write_filter_cache_bust()` helper

- **`tests/`** — 656 passing tests
  - `conftest.py` — Mock fixtures (Qdrant, embed client, Redis)
  - `test_*.py` — Unit tests for all modules
  - `e2e/` — End-to-end integration tests

- **`deployment/`** — Deployment configurations
  - `config/` — Grafana dashboard JSON, Prometheus config, datasource provisioning
  - `helm/` — Kubernetes/Helm chart with monitoring toggle

- **`scripts/`** — Utility scripts
  - `check-integration-gaps.py` — CI integration gap checker (VERIFICATION.md, REQUIREMENTS, SUMMARY refs)
  - `check-verification-gaps.sh` — Shell gap detection
  - `docstring-audit.py` — English enforcement audit
  - `logging-audit.py` — Logging coverage audit
  - `docker-entrypoint.sh` — Dual-server container entrypoint

- **`.planning/`** — Project planning artifacts
  - `phases/*/` — Per-phase plans, summaries, VERIFICATION.md, UAT results
  - `REQUIREMENTS.md` — Active requirements with traceability table
  - `ROADMAP.md` — Phase roadmap with milestone tracking
  - `reports/` — Milestone summaries and tech debt tracking

### Tests

```bash
# Run all unit tests (no external services required)
pytest -m "not integration"

# Run full suite (requires Qdrant + LM Studio running)
pytest tests/ --ignore=tests/e2e --ignore=tests/test_sse_handler.py

# Run SSE tests (separate process due to stub conflicts)
pytest tests/test_sse_handler.py

# Run E2E tests (requires full stack)
pytest tests/e2e/

# Coverage report
pytest --cov=kb_server --cov=ingest --cov-report=html

# Run integration gap checker
python3 scripts/check-integration-gaps.py
```

### Where to Look First

**New contributors should start here:**

1. **Entry point:** `kb_server/server.py` — MCP tool registration and dispatch
2. **Search flow:** `kb_server/retrieval/hybrid_search.py` — Dense + BM25 RRF fusion
3. **Ingestion flow:** `ingest/ingest.py` → `ingest/classifier.py` → `kb_server/vector_store.py`
4. **Classification logic:** `ingest/classifier.py` — Vendor/product/subsystem/doc_type/version/module
5. **Reclassification:** `ingest/reclassify_engine.py` + `ingest/cli/reclassify.py` — Run/verify/sessions/rollback
6. **Monitoring:** `deployment/config/grafana-dashboard.json` + `kb_server/health_server.py`
7. **CI gates:** `.github/workflows/ci.yml` — `integration-check`, `english-audit`, `helm-lint` jobs

**Key interfaces:**
- `VectorStore` — Single abstraction for Qdrant operations (search, upsert, list, stats, update metadata)
- `classify()` — Main classification entry point (filename + metadata → structured dict)
- `get_embedding()` / `get_embeddings_batch()` — Backend-agnostic embedding generation
- `FilterTermsCache` — Singleton for distinct attribute value caching
- `IngestRegistry` — SQLite-backed dedup and status tracking

---

## Stats

- **Timeline:** 2026-05-25 → 2026-05-27 (3 days)
- **Phases:** 11/11 complete (12-22)
- **Plans:** 27/27 complete
- **Commits:** ~187 feature commits across all phases
- **Files changed:** 331 files
- **Tests:** 656 passing, 9 pre-existing failures unchanged
- **Coverage:** 90% branch on kb_server/ + ingest/ (maintained from v0.1.2)
- **Contributors:** 1 (Luciano Marinho)

### Phase Breakdown

| Phase | Plans | Duration | Key Deliverable |
|-------|-------|----------|-----------------|
| 12 | 3 | ~2 days | English-only codebase with CI enforcement |
| 13 | 4 | ~1 day | README.md/pt-BR/es refresh + stale docs update |
| 14 | 6 | ~1 day | Grafana + Prometheus monitoring stack |
| 15 | 2 | ~1 day | PowerShell -ConfigureFirewall switch |
| 16 | 3 | ~1 day | Reclassification engine + CLI (~820 docs) |
| 17 | 3 | ~1 day | Capability negotiation + module axis (33 tests) |
| 18 | 1 | ~1 day | Grafana datasource fix (4 commits) |
| 19 | 1 | ~1 day | 13 VERIFICATION.md files + gap detection script |
| 20 | 1 | ~1 day | LOG_PATH fix + fixture isolation |
| 21 | 1 | ~1 day | 13 unused imports removed, TODOs resolved |
| 22 | 1 | ~1 day | Integration checker CI gate |

### Requirements Traceability

- **Phase 12:** All Python source files in English ✅
- **Phase 13:** DOCS-01 through DOCS-04 complete ✅
- **Phase 14:** DASH-01 through DASH-05 complete ✅
- **Phase 15:** WIN-01 through WIN-03 + DOCS-04/05 complete ✅
- **Phase 16:** RECLASSIFY-01 through RECLASSIFY-07 complete ✅
- **Phase 17:** CAPNEG-01 through CAPNEG-04 complete ✅
- **Phase 18:** DSFIX-01 through DSFIX-05 complete ✅
- **Phase 19:** VERBACK-01 through VERBACK-04 complete ✅
- **Phase 20:** TESTFIX-01 through TESTFIX-03 complete ✅
- **Phase 21:** HYGIENE-01, 02, 04, 05 complete (03 cancelled) ✅
- **Phase 22:** CICHECK-01 through CICHECK-04 complete ✅
- **Total:** 26/26 requirements satisfied (1 cancelled with rationale)

---

## What's Next

**Milestone v0.1.3 is the final planned milestone.** The core product is feature-complete for its target use case (RAG MCP server for closed-source product docs). Future work focuses on:

- **Higher logging coverage threshold** (70%+ aspirational target)
- **SSE handler test process merge** — refactor `test_smoke.py` for single-process test execution
- **`asyncio_mode = AUTO` exploration** — reduce test boilerplate
- **Quickstart.sh clean-machine test** — Docker-based validation
- **Bug fixes and maintenance** as reported by users

**Getting Involved:**
- Review `.planning/ROADMAP.md` for current status
- Check `.planning/REQUIREMENTS.md` for tracking
- Read `.planning/RETROSPECTIVE.md` for lessons learned
- See `CONTRIBUTING.md` for workflow and conventions

---

_Generated from completed milestone artifacts for team onboarding._
_All technical decisions and architecture choices are grounded in actual implementation from phase SUMMARY, CONTEXT, and VERIFICATION files._
