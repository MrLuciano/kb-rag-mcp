---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Quality & Operational Excellence
status: executing
last_updated: "2026-05-25T22:52:34.766Z"
last_activity: 2026-05-25
progress:
  total_phases: 12
  completed_phases: 4
  total_plans: 25
  completed_plans: 18
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.
**Current focus:** Phase 13 — Docs sync, README languages, Spanish README

## Current Position

Phase: 13 (Docs sync, README languages, Spanish README) — EXECUTING
Plan: 4 of 4
Status: Ready to execute
Last activity: 2026-05-25

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

### Key Decisions

- Test assertions checking for Portuguese output strings were updated to English alongside the source translations
- All `kb_server/` tool descriptions, parameter descriptions, section headers, docstrings, inline comments, log messages, error messages, and user-facing output labels are consistently in English

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
