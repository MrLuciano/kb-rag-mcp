---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Post-Ship Polish & Infrastructure
status: executing
last_updated: "2026-05-27T00:28:05.471Z"
last_activity: 2026-05-27 -- Phase 16 execution started
progress:
  total_phases: 13
  completed_phases: 7
  total_plans: 36
  completed_plans: 27
  percent: 54
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.
**Current focus:** Phase 16 — reclassification-ingested-docs

## Current Position

Phase: 16 (reclassification-ingested-docs) — EXECUTING
Plan: 1 of 3
Status: Executing Phase 16
Last activity: 2026-05-27 -- Phase 16 execution started

## Phase 16 Outcomes

### Status

**Planning complete** — 3 plans created (16-01, 16-02, 16-03), estimated 18 hours total

### Plans Defined

- **16-01**: Core Reclassification Engine (6h) — VectorStore metadata update method, SQLite backup/audit tables, classification detection, backup/log functions
- **16-02**: CLI Commands (8h) — `kb-ingest reclassify` subcommands (reclassify, verify, sessions, rollback) with Rich progress/preview
- **16-03**: Documentation (4h) — README.md/pt-BR/es sections, OPERATIONS.md "Reclassification Management" procedures

### Key Design Decisions (from 16-CONTEXT.md)

- **In-place metadata update (D-01)**: Preserves embeddings and vectors, updates only Qdrant payload fields
- **Classification detection (D-04)**: Compares current Qdrant metadata vs. `classify()` output, updates only changed documents
- **Hybrid selection (D-05)**: Supports file glob patterns AND metadata filters (can combine)
- **Interactive confirmation (D-06)**: Shows aggregated summary by field before applying changes
- **SQLite backup (D-13)**: Writes old metadata to `reclassify_backups` table for rollback capability
- **Session-based rollback (D-15)**: Full session undo OR selective pattern+timestamp restore
- **30-day retention (D-16)**: Auto-cleanup of old backups (configurable via env var)

### Requirements Defined

| Requirement | Plan | Description |
|-------------|------|-------------|
| RECLASSIFY-01 | 16-01 | In-place metadata updates preserve embeddings |
| RECLASSIFY-02 | 16-01 | SQLite backup/audit tables for rollback |
| RECLASSIFY-03 | 16-01 | Classification detection compares current vs. expected |
| RECLASSIFY-04 | 16-02 | CLI subcommand with interactive preview |
| RECLASSIFY-05 | 16-02 | Verify subcommand shows mismatches |
| RECLASSIFY-06 | 16-02 | Session-based and selective rollback |
| RECLASSIFY-07 | 16-03 | Documentation in README and OPERATIONS.md |

### Context Files Created

- `.planning/phases/16-reclassification-ingested-docs/16-CONTEXT.md` — 16 design decisions (D-01 through D-16)
- `.planning/phases/16-reclassification-ingested-docs/16-DISCUSSION-LOG.md` — Audit trail with alternatives considered
- `.planning/phases/16-reclassification-ingested-docs/16-01-PLAN.md` — Core engine plan (6h, 5 implementation steps, +25 tests)
- `.planning/phases/16-reclassification-ingested-docs/16-02-PLAN.md` — CLI commands plan (8h, 6 implementation steps, +30 tests)
- `.planning/phases/16-reclassification-ingested-docs/16-03-PLAN.md` — Documentation plan (4h, 5 implementation steps, validation script)

### Expected Test Growth

- Baseline: 585 tests
- Plan 16-01: +25 tests (610 total)
- Plan 16-02: +30 tests (640 total)
- Plan 16-03: N/A (documentation only, validated via example script)

**Expected final: ~640 tests**

### Canonical References Identified

- `ingest/classifier.py` — Reuse `classify()` for reclassification detection
- `kb_server/vector_store.py` — Add `update_chunk_metadata()` method
- `ingest/registry.py` — Add `reclassify_backups` and `reclassify_history` tables
- `ingest/cli/main.py` — Register `reclassify` subcommand
- `ingest/ingest.py:410-459` — Reference for how metadata is stored in chunk payloads

## Phase 15 Outcomes

### Plans Executed

- **15-01**: Windows Firewall configuration added to `start-kb-rag.ps1` — opt-in `-ConfigureFirewall` switch, elevation detection, idempotent rules for 6 ports, English translation
- **15-02**: Documentation updates — comprehensive Windows Firewall sections added to README.md (EN/PT/ES) and OPERATIONS.md with troubleshooting, enterprise deployment, and security guidance

### Key Decisions

- **Hybrid opt-in approach**: Default behavior unchanged (backward compatible); `-ConfigureFirewall` switch enables LAN access
- **Auto-elevation with user prompt**: Non-admin users prompted to re-launch as Administrator
- **Idempotent rule management**: Safe to run multiple times, checks for existing rules
- **Non-fatal failures**: Script continues with service startup even if firewall config fails
- **Three-language parity**: Firewall documentation added to all three README variants with accurate translations
- **Comprehensive OPERATIONS.md**: 180-line section covering automatic/manual config, troubleshooting (5+ scenarios), GPO deployment, security best practices

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| WIN-01: Auto firewall config | ✅ | `start-kb-rag.ps1` `-ConfigureFirewall` switch creates 6 rules |
| WIN-02: Idempotency | ✅ | Existing rules detected and skipped |
| WIN-03: Elevation detection | ✅ | `Test-IsAdministrator` + auto-elevation prompt |
| DOCS-04: Windows firewall docs | ✅ | README.md/pt-BR/es + OPERATIONS.md sections added |
| DOCS-05: Troubleshooting guidance | ✅ | 5+ troubleshooting scenarios in OPERATIONS.md |

## Phase 6 Outcomes

### Plans Executed

- **06-01**: Mock infrastructure (3 session fixtures in conftest.py) + pytest marker registration (integration, fase12, cli)
- **06-02**: 26-unit test_classifier.py + kb_server integration audit (no tags needed — all mock-isolated)
- **06-03**: Ingest integration audit (no tags needed) + full isolation verification

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| TEST-01: Every module has test file | ✅ | ingest/classifier.py → tests/test_classifier.py (26 tests) |
| TEST-02: Unit tests require no external services | ✅ | `pytest -m "not integration"` — 518 passed, 3 skipped, 2 deselected |
| TEST-03: Clear integration test tagging | ✅ | 2 integration-tagged tests in test_payload_indexes.py; 520 unit tests pass without them |

### Test Baseline

| Metric | Count |
|--------|-------|
| Total (core) | 525 |
| Unit (`-m "not integration"`) | 520 |
| Integration-tagged | 2 |
| SSE handler (separate process) | 3 |
| E2E (deployment) | 51 |
| **Grand total** | **576** |
| Unit pass rate | 100% |

### Key Decisions

- `mock_embed_client` and `mock_redis_cache` must NOT be `autouse` — they conflict with test files that manage their own mocking (`test_batch.py`, `test_cache_redis.py`, `test_embed_client_unit.py`)
- `mock_qdrant_client` is `autouse=True` — critical safety guard against accidental localhost:6333 connections
- All existing test files were audited: every one is fully mock-isolated; no integration tags needed beyond the 2 already in `test_payload_indexes.py`

## Accumulated Context

## Phase 7 Outcomes

### Plans Executed

- **07-01**: Quality Gate — `pyproject.toml` coverage config (`fail_under=90`, `branch=true`, `show_missing=true`); CI coverage enforcement step on PR-to-master (`--cov=kb_server --cov=ingest --cov-branch --cov-fail-under=90`)
- **07-02**: Logging Coverage — `scripts/logging-audit.py` (AST-based scanner); log calls added to 10 kb_server modules + `ingest/core/metadata.py`; `docs/logging-audit.md` report

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| QUAL-01: Coverage threshold config | ✅ | `[tool.coverage.report] fail_under=90` in pyproject.toml; `--cov-branch --cov-fail-under=90` in CI PR-to-master |
| QUAL-02: Enforcement gate | ✅ | CI step only on `github.event_name == 'pull_request' && github.base_ref == 'master'` |
| LOG-01: Logging audit script | ✅ | `scripts/logging-audit.py` — scans `kb_server/` + `ingest/` for public methods with log calls |
| LOG-02: Gap-fill 10 modules | ✅ | 10 kb_server modules + ingest registry; 7 modules at 100%, 3 at 71-86% (utility methods skip) |

### Key Decisions

- Inline `# pragma: no cover` with justification comments (no centralized excludes)
- Coverage enforcement on PR-to-master only (not every push)
- Stdlib logging (`kb-mcp.{module}` loggers) — no structlog
- Audit script handles both `log.*` and `logger.*` naming conventions
- Utility/accessor methods (`hash_key`, `backend_type`, `conn`, `sha256`) exempt from log calls (noise without value)

### Coverage Baseline

| Module | Branch Coverage |
|--------|----------------|
| `kb_server/` | ~88% (baseline) |
| `ingest/` | TBD (first CI enforcement run) |
| Logging audit | 50.6% overall; 119/235 public methods with log calls |

## Phase 10 Wave 1 Outcomes

### Plans Executed

- **10-01**: Helm chart validation in CI — added `helm-lint` job to `.github/workflows/ci.yml` using `azure/setup-helm@v4` with `helm lint --strict` and `helm template` dry-run
- **10-02**: Replaced `sys.modules` qdrant_client stubs with real imports in `tests/test_smoke.py`, `tests/test_vector_store.py`, `tests/test_vector_store_unit.py` — removed `_patch_vs_callables()`, `_ORIGINAL_VS_ATTRS`, and `_qm.FilterSelector = MagicMock()` workarounds

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| DEBT-02: Helm chart validated in CI | ✅ | `.github/workflows/ci.yml` has `helm-lint` job with `helm lint --strict` |
| DEBT-03: Real qdrant model imports | ✅ | No `type(name, (), {})()` stubs for qdrant symbols; full suite 551/556 passed, 0 failed |

### Key Decisions

- **Import real qdrant before stubs:** Adding `import qdrant_client` at top of `_ensure_stubs()` ensures real package loads before `setdefault` loop — preserves real modules instead of anonymous stubs
- **Separate helm-lint job:** Not part of test matrix — runs once per push/PR, not per Python version
- **Keep non-qdrant stubs:** MCP, fastembed, and other heavy dependency stubs remain for test-process performance
- **WSL DrvFs filesystem bug:** Write/Edit tools fail silently on WSL mounts — use Bash heredocs as workaround

### Test Baseline

| Metric | Count |
|--------|-------|
| Total (core) | 551 |
| Unit pass rate | 100% |

## Phase 12 Outcomes

### Plans Executed

- **12-01**: English sweep — `kb_server/server.py`, `embed_client.py`, `vector_store.py` fully translated to English (165 changes across MCP tool descriptions, docstrings, comments, log/error messages, output labels)
- **12-02**: English sweep — `ingest/classifier.py` and `ingest/ingest.py` fully translated to English (100+ inline comments, 15+ log messages, section headers, docstrings, help text, error messages)

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Phase 12 goal: All Python source files in English | ✅ | All `kb_server/` and `ingest/` files have 0 accented Portuguese characters; 0 Portuguese phrase matches |

### Test Baseline

| Metric | Count |
|--------|-------|
| Core tests (excl. e2e, SSE) | 585 passed, 5 skipped |
| SSE handler tests | 3 passed |
| **Grand total** | **585** |

### Key Decisions

- Test assertions checking for Portuguese output strings were updated to English alongside the source translations
- All `kb_server/` tool descriptions, parameter descriptions, section headers, docstrings, inline comments, log messages, error messages, and user-facing output labels are consistently in English

## Phase 14 Outcomes

### Plans Executed

- **14-01**: Metrics endpoint — added `/metrics` route to `kb_server/health_server.py` exposing 28 Prometheus metrics at port 8080
- **14-02**: Grafana dashboard — extended `deployment/config/grafana-dashboard.json` with 6-row structure (Server, Ingestion, Jobs, Embedding, Cache, Qdrant) and 28 panels
- **14-03**: Docker Compose integration — added `prometheus` and `grafana` services, created provisioning configs
- **14-04**: Kubernetes/Helm integration — created Prometheus StatefulSet and Grafana Deployment with monitoring toggle
- **14-05**: Documentation — added Health Dashboard section to OPERATIONS.md (~178 lines), updated README.md with monitoring links
- **14-06**: Docker Compose fixes — created entrypoint script for dual-server startup, fixed healthchecks (GET method, 120s start_period), removed duplicate datasource

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| DASH-01: /metrics endpoint | ✅ | `kb_server/health_server.py` line 55-61; 6 tests pass |
| DASH-02: Grafana dashboard 6 tabs | ✅ | `deployment/config/grafana-dashboard.json` 6 rows, 28 panels; 5 tests pass |
| DASH-03: Docker Compose integration | ✅ | 4 services healthy (Qdrant, kb-rag-mcp, Prometheus, Grafana); UAT verified |
| DASH-04: Kubernetes/Helm integration | ✅ | Prometheus StatefulSet + Grafana Deployment; 12 tests pass, helm lint passes |
| DASH-05: Documentation | ✅ | OPERATIONS.md Health Dashboard section, README.md monitoring links |

### Test Baseline

| Metric | Count |
|--------|-------|
| Core tests | 585 passed, 5 skipped |
| New tests added | 29 (6+6+5+12 across 4 plans) |
| Expected total | ~614 |

### Key Decisions

- **Grafana-centric approach:** Extend existing Grafana dashboard instead of building custom HTML/FastAPI dashboard
- **Dual-server architecture:** Health server (port 8080) + MCP server (port 8765) run in same container via entrypoint script
- **Healthcheck method:** Changed from HEAD to GET (`wget -O -`) — FastAPI /health only accepts GET
- **Start period:** Increased to 120s for large Qdrant database initialization
- **Port separation:** Health/metrics on 8080, MCP SSE on 8765 (configurable via env vars)
- **Blocker resolution:** Entrypoint script starts health server in background (PID 7), then MCP server in foreground (via `exec`)
- **Production validation:** Verified on both dev (WSL Ubuntu) and production (acemagic) machines

## Accumulated Context

### Key Decisions (v1.0)

- `kb_server/` is single canonical module; `server/` deleted
- `bootstrap_env()` in `config/` — single env-loading entry point
- `IngestRegistry` → `ingest/core/metadata.py`
- fastembed BM25 for sparse vectors (embedded, no separate server)
- `asyncio_mode = STRICT` — all async tests need `@pytest.mark.asyncio`
- MagicMock pollution from qdrant_client stubs — use `getattr(x, 'value', x)` pattern for enum comparisons (DEBT-03 resolved — no longer needed)

### Known Tech Debt

- `PayloadSchemaType` assertion weakened in `test_payload_indexes.py`
- ~~`helm lint` not validated (helm not installed in WSL dev)~~ ✅ Resolved by DEBT-02
- LM Studio must be running locally for live ingest/eval
- Cross-encoder model lazy-loading deferred to post-Phase 6 (decided D-06)
