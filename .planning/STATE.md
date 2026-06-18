---
gsd_state_version: 1.0
milestone: v0.1.5
milestone_name: Streamable HTTP & Management Platform
status: executing
last_updated: "2026-06-17T16:00:00.000Z"
progress:
  total_phases: 17
  completed_phases: 16
  total_plans: 28
  completed_plans: 28
  percent: 94
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-15)

**Core value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.
**Current focus:** Milestone v0.1.5 completion — all backlog phases done, ready to ship

## Current Position

Milestone: v0.1.5 (Streamable HTTP & Management Platform) — ACTIVE
Phase: All backlog phases COMPLETE — 43-47, 50
Status: 16/16 phases complete, 28/28 plans executed
Next: Milestone v0.1.5 completion — all 17 phases complete, ready to ship

## Phase 28c-fixes Outcomes

### Status

- **Phase:** 28c-fixes (admin-spa-gap-closure)
- **Status:** Complete — 4 plans, 43 admin UI tests pass
- **Completed:** 2026-06-17

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 28c-fixes-01 | Auth flow rewrite, doc browse, CSP/SRI fixes | 3 | Complete |
| 28c-fixes-02 | Monitor lights, config editor, partials refactor, route ordering | 4 | Complete |
| 28c-fixes-03 | Auth infrastructure: router mount, Alpine.js CDN, auth gating, admin seeding | 4 | Complete |
| 28c-fixes-04 | Session management, credentials UI, configurable timeout | 2 | Complete |

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Admin login with API key via Alpine.js overlay | ✅ | `shell.html` Alpine.js `x-show` login modal; `POST /auth/session` JWT cookie exchange |
| Document browse with checkboxes, bulk actions | ✅ | `_documents_table.html` select-all checkbox, bulk toolbar with hx-confirm |
| CSP nonce on inline scripts | ✅ | `tab_ragas.html` script tag has `nonce="{{ get_nonce(request) }}"` |
| Monitor lights with 7 components | ✅ | `_monitor_lights.html` bar with latency display, click-to-expand |
| Config editor with HTMX PUT save, Reset All | ✅ | `_config_table.html` inline Alpine.js editor, `:hx-put`, Reset with hx-confirm |
| Ingestion + RAGAS sub-tab navigation | ✅ | `tab_ingestion.html` Manual/Schedule/Monitor; `tab_ragas.html` Editor/Results |
| Route ordering: specific /tabs/ paths before generic | ✅ | `routes_admin.py` reordered: all specific routes registered before `{tab_name}` |
| Auth router mounted on UI app | ✅ | `app.py` includes `auth_router`; `GET /api/v1/auth/session` works on port 8001 |
| Alpine.js CSP-safe build loads | ✅ | `base.html` now loads `@alpinejs/csp@3.13.3/dist/cdn.min.js` with SRI |
| Server-side auth gating on all tab endpoints | ✅ | 13 endpoints use `Depends(get_current_user)` |
| Default admin account seeded on startup | ✅ | `ensure_admin_account()` in `AuthService`, API key logged with banner |
| Session cookie validation in get_current_user | ✅ | HMAC signature verify, expiry check, `get_user_session()` validity check |
| Configurable session timeout (default 30 min) | ✅ | `_SESSION_TIMEOUT` env var in `auth/router.py` |
| Session management UI (list/revoke) | ✅ | `GET /auth/sessions`, `POST /auth/sessions/{id}/revoke`, `_sessions_table.html` |
| Credential management UI (generate/revoke API keys) | ✅ | `_credentials_section.html` with key list, Generate New Key, Revoke buttons |

### Key Changes

1. **`kb_server/ui/templates/admin/shell.html`** — Alpine.js `x-data` login overlay, hamburger toggle, emoji icons, sidebar state
2. **`kb_server/ui/templates/admin/tab_documents.html`** — HTMX loading for `_documents_table.html` partial
3. **`kb_server/ui/templates/admin/tab_ingestion.html`** — Sub-tab nav (Manual/Schedule/Monitor) with HTMX partial loads
4. **`kb_server/ui/templates/admin/tab_ragas.html`** — Sub-tab nav (Editor/Results) with HTMX partial loads
5. **`kb_server/ui/templates/admin/tab_admin.html`** — Config table + sessions + credentials HTMX sections
6. **`kb_server/ui/templates/admin/_monitor_lights.html`** — 7-component health bar with latency, expand, degraded/warning
7. **`kb_server/ui/templates/admin/_config_table.html`** — HTMX inline editor with group badges, Reset All
8. **`kb_server/ui/templates/admin/_profile_content.html`** — Revoke confirmation + badge classes
9. **`kb_server/ui/templates/admin/_documents_table.html`** — Checkboxes, bulk toolbar, select-all
10. **`kb_server/ui/templates/admin/_ingestion_manual.html`** — Manual form partial
11. **`kb_server/ui/templates/admin/_ingestion_schedule.html`** — Schedule partial
12. **`kb_server/ui/templates/admin/_ingestion_monitor.html`** — Monitor partial
13. **`kb_server/ui/templates/admin/_ragas_editor.html`** — Evaluation dataset + Run Evaluation button
14. **`kb_server/ui/templates/admin/_ragas_results.html`** — Empty state placeholder
15. **`kb_server/ui/templates/admin/_sessions_table.html`** — Session list with Alpine.js data fetch + Revoke
16. **`kb_server/ui/templates/admin/_credentials_section.html`** — API key management with Generate/Revoke
17. **`kb_server/ui/templates/admin/_job_status.html`** — Job status summary partial (pre-existing)
18. **`kb_server/ui/templates/base.html`** — Alpine.js CSP build URL, SRI hash, status-code-specific error handler
19. **`kb_server/ui/static/styles.css`** — Sidebar responsive (280px / 60px icon-only / hamburger)
20. **`kb_server/ui/routes_admin.py`** — Route reordering + 8 new partial routes + 13x `Depends(get_current_user)`
21. **`kb_server/ui/app.py`** — Auth router mounted, startup auth init, `/login` + `/auth/login` routes removed
22. **`kb_server/auth/deps.py`** — Session cookie validation, HMAC verify, `get_user_session()` check, `last_used_at` update
23. **`kb_server/auth/router.py`** — `_SESSION_TIMEOUT`, `create_session_record()`, session list/revoke endpoints
24. **`kb_server/auth/service.py`** — `ensure_admin_account()`, session CRUD methods
25. **`kb_server/auth/models.py`** — `UserSession` table
26. **`kb_server/ui/templates/admin/login.html`** — **DELETED** (replaced by Alpine.js overlay)

### Commits (9)

1. `bd44ef7` feat(admin): Plan 01 auth flow rewrite, document browse, CSP/SRI fixes
2. `37cb6d8` test(28c-fixes): UAT results
3. `5c17da2` feat(admin): Task 1 - complete monitor lights bar
4. `9618f6d` feat(admin): Task 2 - improve config inline editor
5. `5b30411` feat: Plan 02 Task 3-4 — partials refactor, route reordering, 5 new partial routes
6. `a67083d` feat: Plan 03 — auth router mount, server-side gating, Alpine.js CDN fix, admin seeding
7. `5202846` feat: Plan 04 — session timeout, session management, credentials page

### Verification

- Admin UI tests: 43 passed, 0 failed (43 errors = pre-existing `/app` PermissionError from TestClient teardown)
- All tab content endpoints return real content (no 401 "Failed to load content")
- Auth flow: API key → JWT cookie → session validation → 13 gated endpoints
- Default admin account seeded on startup with banner-logged API key
- Session timeout configurable via `SESSION_TIMEOUT` env var (default 1800s)
- Login overlay triggers on 401 via CustomEvent('show-login')

## Phase 25 Outcomes

### Status

- **Phase:** 25 (optimization-experiments)
- **Status:** Complete — 4 plans, 56 tests
- **Completed:** 2026-06-11

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 25-01 | Core infrastructure: config, metric_computer, result_store | 3 | Complete |
| 25-02 | Chunking experiments: fixed, recursive, semantic strategies | 3 | Complete |
| 25-03 | Scoring experiments: dense, hybrid, reranked variants | 3 | Complete |
| 25-04 | Experiment runner + CLI: `kb-rag optimize` command | 3 | Complete |

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| ExperimentConfig + strategy/variant registries | ✅ | `kb_server/optimization/config.py` — ExperimentConfig, CHUNK_STRATEGIES, SCORING_VARIANTS |
| IR metrics: Recall@K, MRR, NDCG@K | ✅ | `metric_computer.py` — sklearn-backed, 12 deterministic unit tests |
| Results persisted to CSV/JSON | ✅ | `result_store.py` — ExperimentResultStore.save(), to_csv(), compare() |
| Chunking strategies (fixed, recursive, semantic) | ✅ | `chunking_experiments.py` — 3 strategy classes + ChunkingEngine |
| Scoring variants (dense, hybrid, reranked) | ✅ | `scoring_experiments.py` — 3 variant classes + ScoringEngine |
| ExperimentRunner orchestrator | ✅ | `experiment_runner.py` — end-to-end pipeline |
| `kb-rag optimize` CLI with 4 subcommands | ✅ | `ingest/cli/optimize.py` — chunk, scoring, compare, list |

### Key Changes

1. **`kb_server/optimization/`** — New package: config, metric_computer, result_store, chunking_experiments, scoring_experiments, experiment_runner
2. **`ingest/cli/optimize.py`** — `kb-rag optimize` CLI with chunk/scoring/compare/list subcommands
3. **`tests/test_metric_computer.py`** — 12 tests for IR metrics (Recall@K, MRR, NDCG@K)
4. **`tests/test_chunking_experiments.py`** — Tests for 3 chunking strategies + ChunkingEngine
5. **`tests/test_scoring_experiments.py`** — Tests for 3 scoring variants + ScoringEngine
6. **`tests/test_optimization.py`** — Integration tests for ExperimentRunner + CLI

### Commits (12)

1. `b44544f` feat(25-01): add ExperimentConfig, MetricComputer stubs (config + metric_computer)
2. `735692e` feat(25-01): add ExperimentResultStore + load_results
3. `3911dd1` chore(25-01): add 25-01-SUMMARY.md
4. `b1dd946` feat(25-02): add chunking strategy classes + ChunkingEngine
5. `8de5c45` test(25-02): add chunking experiment tests
6. `70f535c` chore(25-02): add 25-02-SUMMARY.md
7. `0ae08d0` feat(25-03): add scoring variant classes + ScoringEngine
8. `3fce64e` test(25-03): add scoring experiment tests
9. `6daaac7` chore(25-03): add 25-03-SUMMARY.md
10. `7341950` feat(25-04): add ExperimentRunner + kb-rag optimize CLI
11. `9babf41` test(25-04): add optimization runner + CLI tests
12. `a00d86c` chore(25-04): add 25-04-SUMMARY.md

### Verification

- 56/56 Phase 25 tests pass
- `kb-rag optimize --help` shows chunk, scoring, compare, list subcommands
- gsd-verifier score: 12/12 must-haves
- Full suite: 1165 passed, 2 pre-existing failures (test_cli_reclassify.py — needs Qdrant), 1 skipped

## Phase 24 Outcomes

### Status

- **Phase:** 24 (ragas-evaluation-pipeline)
- **Status:** Complete — 4 plans, 57 tests, VERIFICATION.md confirmed
- **Completed:** 2026-06-11

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 24-01 | Core evaluator — 4 custom metrics (faithfulness, answer_relevancy, context_precision, context_recall) | 3 | Complete |
| 24-02 | Dataset loading — CSV/JSON golden dataset loader with auto-delimiter detection | 3 | Complete |
| 24-03 | CLI + exporter — `kb-rag evaluate` CLI, CSV/JSON/console output, rich tables | 4 | Complete |
| 24-04 | LLM wrappers — 4 backend wrappers (LM Studio REST, OpenAI-compat, Ollama, SDK) + RAGAS adapter | 3 | Complete |

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| EVAL-01: 4 custom RAGAS metrics | ✅ | `kb_server/evaluation/metrics.py` — Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall |
| EVAL-02: Dataset loading from CSV/JSON | ✅ | `kb_server/evaluation/csv_loader.py` — auto-delimiter detection, golden format validation |
| EVAL-03: CLI evaluation runner | ✅ | `ingest/cli/evaluate.py` — `kb-rag evaluate` with dataset, single-query, and batch modes |
| EVAL-04: LLM backend abstraction | ✅ | `kb_server/evaluation/llm_wrapper.py` — 4 backends + RAGAS adapter for ragas.metrics |

### Key Files Created

1. **`kb_server/evaluation/metrics.py`** — 4 custom RAGAS metrics
2. **`kb_server/evaluation/csv_loader.py`** — CSV/JSON dataset loader
3. **`kb_server/evaluation/dataset.py`** — Dataset model
4. **`kb_server/evaluation/exporter.py`** — Results exporter (CSV, JSON, console)
5. **`ingest/cli/evaluate.py`** — `kb-rag evaluate` CLI
6. **`kb_server/evaluation/llm_wrapper.py`** — 4 LLM backends + RAGAS adapter

### Verification

- 57 Phase 24 tests pass
- VERIFICATION.md: 10/10 must-haves satisfied
- Full suite: 1165 passed, 2 pre-existing failures, 12 skipped

## Phase 35 Outcomes

### Status

- **Phase:** 35 (multi-kb-aggregated-search)
- **Status:** Complete — 1 plan, 22 tests, UAT verified
- **Completed:** 2026-06-10

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 35-01 | Multi-KB aggregated search: resolve_multi, multi_search, merge + dedup | 2 | Complete |

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| MULTIKB-01: search_kb accepts multiple KB identifiers | ✅ | `kb_ids` parameter in `search_kb` handler (server.py:640-712) |
| MULTIKB-02: Aggregated results preserve provenance, normalize, deduplicate | ✅ | `merge_multi_collection_results()` in hybrid_search.py with min-max normalization, RRF fusion, chunk_id dedup |
| MULTIKB-03: Existing single-KB search remains backward compatible | ✅ | Empty `kb_ids` defaults to single-KB path; all 983 existing tests pass unchanged |

### Key Changes

1. **`kb_server/collections/router.py`** — Added `resolve_multi()` to resolve list of KB IDs to collection names
2. **`kb_server/vector_store.py`** — Added `multi_search()` with parallel collection dispatch and `_collection` provenance tag
3. **`kb_server/retrieval/hybrid_search.py`** — Added `merge_multi_collection_results()` (per-collection min-max normalization + RRF fusion + chunk_id dedup) and `_min_max_normalize()` helper
4. **`kb_server/server.py`** — Added `kb_ids` parameter to `search_kb`, multi-KB dispatch with `resolve_multi()` and `multi_search()`, rerank disabled for multi-KB

### Commits (2)

1. `086efb0` feat(phase-35): implement multi-KB aggregated search with resolve_multi, multi_search, and merge_multi_collection_results
2. `50a068b` test(phase-35): add tests for multi-KB aggregated search

### Verification

- 22 Phase 35 tests pass across 4 test files
- UAT: 8/14 pass, 1 issue fixed (connector auto-registration, commit cb42dab), 5 blocked (server-dependent)
- Full suite: 1006 passed at completion (now 1165 after later phases)

## Phase 29-34, 36-37 Outcomes

### Summary

All remaining v0.1.4 phases executed and verified. Features span enterprise connectivity, knowledge graph, prompt templates, authentication, rate limiting, quotas, resilience, and caching.

| Phase | Plans | Key Deliverables | Completed |
|-------|-------|-----------------|-----------|
| 29. Enterprise Data Source Connectors | 4 | ConnectorBase ABC, Confluence connector (Cloud + DC), JIRA connector, Git connector, CLI staging, SQLite connector_state | 2026-06-10 |
| 30. Cross-Document Knowledge Graph | 2 | Graph metadata derivation (doc_graph_id, entities, topics, related), MCP tools (get_related_documents, explore_topic), payload indexes | 2026-06-10 |
| 31. MCP Prompt Templates | 1 | `extract_answer` and `summarize_documents` prompts, PROMPT_DEFINITIONS registry, list_prompts/get_prompt | 2026-06-10 |
| 32. API Key Authentication | 1 | SQLite key registry (SHA-256 hashed), SSE Bearer token middleware, CLI create/list/revoke | 2026-06-10 |
| 33. Request Rate Limiting | 1 | Token bucket per subject, HTTP 429 SSE rejection, tool-level error, prometheus metrics | 2026-06-10 |
| 34. Upload and Index Quotas | 1 | 6 quota fields, quota_config/quota_usage tables, CLI show/set/reset, ingest enforcement | 2026-06-10 |
| 36. Provider Budget & Circuit Breaker | 1 | Circuit breaker state machine, sliding window budget, embed client fallback chain, 7 prometheus metrics | 2026-06-11 |
| 37. Request-level Retrieval Cache | 1 | LRU cache wrapping CacheManager, deterministic SHA-256 keys, TTL expiry, invalidation hooks | 2026-06-11 |

### Milestone Summary

All 15 phases (23-37) of v0.1.4 "Platform, Analytics & Enterprise" are complete with 28 plans, 200+ tests, and zero regressions. The milestone transforms kb-rag-mcp from a single-collection RAG server into a multi-tenant, enterprise-ready platform with streaming HTTP transport, knowledge graph, authentication, rate limiting, quotas, circuit breakers, and retrieval caching.

## Phase 23 Outcomes

### Status

- **Phase:** 23 (documentation-overhaul)
- **Status:** Executing Phase 25
- **Completed:** 2026-05-27

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 23-01 | Deployment-mode sections in OPERATIONS.md, TROUBLESHOOTING.md, INSTRUCTIONS.md, INDEX.md | DOCS-01, DOCS-02 | Complete |
| 23-02 | Restructure README.md, README.pt-BR.md, README.es.md (two-tier format) | DOCS-01, DOCS-02 | Complete |
| 23-03 | Update CHANGELOG with v0.1.3/v0.1.4 sections; audit/update REFERENCE.md | DOCS-03, DOCS-04 | Complete |

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| DOCS-01: Deployment-mode navigation sections | ✅ | OPERATIONS.md, TROUBLESHOOTING.md, INSTRUCTIONS.md have Common + Docker Compose/Helm/Systemd/Manual H2 sections |
| DOCS-02: Per-mode source of truth in INDEX.md | ✅ | INDEX.md has Deployment Modes section with file-level links per mode |
| DOCS-03: CHANGELOG update | ✅ | `## [1.3] 2026-05-27` and `## [1.4]` sections with per-plan bullet points for all v0.1.3/v0.1.4 phases |
| DOCS-04: REFERENCE update | ✅ | Audit applied (stale entries corrected); v0.1.3/v0.1.4 components documented; Deployment Modes subsection added |

### Key Changes

1. **docs/OPERATIONS.md** — Added Common + Docker Compose/Helm/Systemd/Manual H2 sections with see-also footers (DOCS-01)
2. **docs/TROUBLESHOOTING.md** — Added mode sections with troubleshooting guidance (DOCS-01)
3. **docs/INSTRUCTIONS.md** — Portuguese; added mode sections with instruction pointers (DOCS-01)
4. **docs/INDEX.md** — Enhanced with Deployment Modes section (DOCS-02)
5. **README.md** — Restructured EN section (~160 lines with quickstart mode table + docs/ links); PT-BR section condensed from ~800 to ~30 lines (DOCS-01)
6. **README.pt-BR.md** — Restructured standalone file from 1551 to ~60 lines with same two-tier format (DOCS-01)
7. **README.es.md** — Restructured standalone file from 1551 to ~60 lines with same two-tier format (DOCS-01)
8. **CHANGELOG.md** — Added `## [1.3] 2026-05-27` with all 11 phases (12-22) per-plan + `## [1.4]` with Phase 23 (DOCS-03)
9. **docs/REFERENCE.md** — Added 3 Component Map entries (Reclassification, FilterTermsCache, Integration checker), Deployment Modes subsection, updated Roadmap Status with v0.1.3/v0.1.4 phases (DOCS-04)

### Commits (3)

1. `e77d9d6` docs(23): add deployment-mode sections to OPERATIONS.md, TROUBLESHOOTING.md, INSTRUCTIONS.md, INDEX.md (DOCS-01, DOCS-02)
2. `0f2f245` docs(23): restructure README.md, README.pt-BR.md, README.es.md to two-tier format (DOCS-01)
3. *(pending)* docs(23): update CHANGELOG with v0.1.3/v0.1.4 milestones and audit REFERENCE.md (DOCS-03, DOCS-04)

### Verification

- CHANGELOG.md: `## [1.3]` present, `## [1.4]` present, all 11 v0.1.3 phases listed with per-plan detail
- REFERENCE.md: Reclassification engine referenced, Deployment Modes subsection present, v0.1.3/v0.1.4 entries in Roadmap Status
- 3 README files restructured with deployment-mode quickstart tables and docs/ link sections

## Phase 22 Outcomes

### Status

- **Phase:** 22 (integration-checker-ci-gate)
- **Status:** Complete
- **Completed:** 2026-05-27

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 22-01 | Integration checker CI gate: script + CI job + reqs update | 3 | Complete |

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| CICHECK-01 | ✅ | `integration-check` CI job with `needs: test` in `.github/workflows/ci.yml` |
| CICHECK-02 | ✅ | `scripts/check-integration-gaps.py` validates VERIFICATION.md presence, REQUIREMENTS traceability, SUMMARY.md file refs |
| CICHECK-03 | ✅ | Script exits 1 on any gap; CI job inherits exit code |
| CICHECK-04 | ✅ | Rich stdout table + JSON summary at `scripts/check-integration-gaps-results.json` |

### Key Changes

1. `scripts/check-integration-gaps.py` — New Python script (350 lines) with 3 gap checks: VERIFICATION.md presence (D-01), REQUIREMENTS.md traceability (D-02), SUMMARY.md file references (D-03)
2. `.github/workflows/ci.yml` — New `integration-check` job with `needs: test`, runs on every push/PR (D-06, D-07)
3. `.planning/REQUIREMENTS.md` — CICHECK-01 through CICHECK-04 marked complete

### Commits (2)

1. `6486efe` feat(22): create integration gap checker script with 3 checks (CICHECK-02, CICHECK-03, CICHECK-04)
2. `983105f` feat(22): wire integration checker into CI job (CICHECK-01) and mark requirements complete

### Verification

- Script runs without errors: `python3 scripts/check-integration-gaps.py`
- CI YAML parses cleanly: `yaml.safe_load` validated
- 2/3 initial checks pass (VERIFICATION.md gaps pre-existing: phases 19, 20, 22, stale 14 dir)

## Phase 21 Outcomes

### Status

- **Phase:** 21 (codebase-hygiene-sweep)
- **Status:** Complete — 1 plan, 6 commits
- **Completed:** 2026-05-27

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 21-01 | Codebase hygiene sweep: unused imports, TODOs, log fmt, dead code, types | 5 | Complete (1 cancelled) |

### Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| HYGIENE-01: Remove unused imports | ✅ | 13 unused imports removed across 7 files |
| HYGIENE-02: Resolve stale TODOs | ✅ | 3 TODOs resolved (1 deleted, 2 converted to checkboxes) |
| HYGIENE-03: Standardize type annotations | ❌ Cancelled | `Any` legitimately used in generic cache/collections layers |
| HYGIENE-04: Convert f-string logs | ✅ | 6 f-string log messages standardized in embed_client.py |
| HYGIENE-05: Remove dead code | ✅ | 2 dead code instances removed (orphan imports and constants) |

### Key Changes

1. **13 unused imports** removed from `embed_client.py`, `query_logger.py`, `router.py`, `reranker.py`, `test_embed_client_unit.py`, `test_hybrid_search.py`, `test_reranker_lazy.py`
2. **3 TODOs resolved:** `filter_by_module()` added (CAPNEG-03 complete annotation), `CollectionRouter.__init__` cache_bust parameter cleanup, SSE handler redirect TODO verified complete
3. **6 f-string logs** standardized in `embed_client.py` (HYGIENE-04, scoped to this file only)
4. **2 dead code** instances removed: orphan `Mapping` import in `query_logger.py`, orphan `DEFAULT_TERMS_CACHE_TTL` constant in `router.py`

### Commits (6)

1. `1b7ec48` fix(hygiene): remove 6 unused imports from test files (HYGIENE-01)
2. `8dca365` fix(hygiene): remove 7 unused imports from production modules (HYGIENE-01)
3. `f78cb20` chore(hygiene): resolve 3 stale TODOs (HYGIENE-02)
4. `35a68e1` fix(hygiene): standardize 6 f-string log messages in embed_client.py (HYGIENE-04)
5. `33732fd` fix(hygiene): remove 2 dead code instances (HYGIENE-05)
6. `0e58e96` chore(hygiene): document HYGIENE-03 (type annotations) cancellation rationale

### Verification

- Flake8: zero F401/F841 warnings
- Zero leftover TODOs from hygiene scope
- 656 tests pass (9 pre-existing failures unchanged)

## Phase 20 Outcomes

### Status

- **Phase:** 22
- **Status:** Ready to plan
- **Completed:** 2026-05-27

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 20-01 | Fix LOG_PATH PermissionError, fixture isolation, clean env | 3 | Complete |

### Key Changes

1. `kb_server/server.py` — Added `os.makedirs(os.path.dirname(log_path), exist_ok=True)` before FileHandler init (TESTFIX-02)
2. `tests/test_reranker_lazy.py` — Moved module-level MagicMock objects into fixture scope (TESTFIX-01)
3. Stale `.pyc`/`__pycache__` artifacts cleaned

### Commits (2)

1. `b381556` fix(20): ensure log directory exists before FileHandler init (TESTFIX-02)
2. `14a0ae2` fix(20): move module-level mocks to fixture scope in test_reranker_lazy (TESTFIX-01)

## Phase 19 Outcomes

### Status

- **Phase:** 19 (VERIFICATION.md Backfill)
- **Status:** Complete — 1 plan, 6 tasks
- **Completed:** 2026-05-27

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 19-01 | Backfill VERIFICATION.md for all missing shipped phases | 6 | Complete |

### Key Deliverables

- `scripts/check-verification-gaps.sh` — Gap detection script (VERBACK-04)
- 13 VERIFICATION.md files created across phases 05-13, 16-18 (VERBACK-01/02/03)
- Each file documents verification approach sourced from plans, summaries, and git history

### Commits (2)

1. `d75813f` feat(19): add VERIFICATION.md gap detection script (VERBACK-04)
2. `8448c50` docs(19): backfill VERIFICATION.md for all 13 shipped phases (VERBACK-01/02/03)

## Phase 18 Outcomes

### Status

- **Phase:** 18 (fix-grafana-datasource-error)
- **Status:** Complete — 1 plan, 4 tasks
- **Completed:** 2026-05-27

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 18-01 | Fix Grafana datasource error across Docker Compose and Helm paths | 4 tasks | Complete |

### Key Changes

1. `deployment/config/grafana-provisioning/datasources/prometheus.yml` — Added `uid: prometheus`
2. `deployment/config/grafana-dashboard.json` — Replaced 63 `${DS_PROMETHEUS}` → `"prometheus"`, removed `__inputs`
3. `deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml` — Added `uid: prometheus`
4. `deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json` — Replaced 63 `${DS_PROMETHEUS}` → `"prometheus"`, removed `__inputs`

### Commits (4)

1. `1a51555` fix(deployment): add uid prometheus to Docker Compose datasource provisioning
2. `d1bf774` fix(deployment): replace DS_PROMETHEUS refs and remove __inputs in Docker Compose dashboard
3. `4cfc0ed` fix(deployment): add uid prometheus to Helm datasource provisioning
4. `9ca0be3` fix(deployment): replace DS_PROMETHEUS refs and remove __inputs in Helm dashboard

## Phase 17 Outcomes

### Status

- **Phase:** 17 (improve-capability-negotiation)
- **Status:** Complete — all 3 plans fully executed
- **Completed:** 2026-05-27

### Plans Executed

| Plan | Description | Tasks | Status |
|------|-------------|-------|--------|
| 17-01 | Module Classification Axis | 4 tasks | Complete |
| 17-02 | Terms Table & Dynamic Descriptions | 4 tasks | Complete |
| 17-03 | list_filter_options Tool | 3 tasks | Complete |

### Key Artifacts

- `ingest/classifier.py` — `MODULE_PATTERNS`, `infer_module()`
- `ingest/utils.py` — `write_filter_cache_bust()`
- `kb_server/filter_terms_cache.py` — `FilterTermsCache`
- `kb_server/vector_store.py` — `get_distinct_values()`, module filter
- `kb_server/server.py` — dynamic `list_tools()`, `list_filter_options` tool
- Tests: `test_classifier_module.py` (16), `test_vector_store_terms.py` (7), `test_cache_bust_marker.py` (3), `test_server_terms.py` (2), `test_server_filter_options.py` (5) — 33 new tests total + 1 integration

### Commits (10)

1. `9de51c1` feat(classifier): add infer_module() with MODULE_PATTERNS table
2. `3541e8d` feat(ingest): integrate module field into classify() and chunk payload
3. `537e6e4` feat(server): add module filter to search_kb, list_documents, VectorStore
4. `e48b40d` feat(reclassify): add module field to reclassification scope
5. `c25b2aa` feat(store): add get_distinct_values() for terms table scanning
6. `018630c` feat(cache): add FilterTermsCache with cache-bust marker refresh
7. `2b44c14` feat(pipeline): write filter cache-bust marker after ingest/reclassify
8. `ee7c102` feat(server): dynamic list_tools() descriptions with top-20 filter values
9. `5c96d6b` feat(server): register and implement list_filter_options tool
10. `ae66280` test: add integration smoke test for list_filter_options

## Phase 16 Outcomes

### Status

**Phase 16 COMPLETE** — All 3 plans implemented: Core engine (Wave 1), CLI commands (Wave 2), and comprehensive documentation (Wave 3). 33 passing tests, 4 documentation files updated (~820 lines added).

**Plan 16-01 complete**: 5 core engine functions implemented (detect_changed_classifications, backup_metadata, log_changes, cleanup_old_backups, VectorStore.update_chunk_metadata) + SQLite schema migration with 15 passing tests.

**Plan 16-02 complete**: 4 CLI subcommands implemented (run, verify, sessions, rollback) with Rich UI, filter expressions, confirmation prompts, progress bars. 18 passing tests.

**Plan 16-03 complete**: Documentation added to README.md (EN/PT/ES) with "Reclassifying Documents" section (~170 lines each) and OPERATIONS.md "Reclassification Management" section (~315 lines). All bash examples validated against CLI implementation.

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
- Plan 16-01: +15 tests (600 total) — schema + engine functions
- Plan 16-02: +18 tests (618 total) — CLI subcommands
- Plan 16-03: N/A (documentation only, validated via example script)

**Current: 618 tests (585 baseline + 33 new)**
**Expected final: ~618 tests** (no more test additions planned)

### Plan 16-01 Progress (Complete)

**All 5 steps COMPLETE** (2026-05-27, 4h 15min):

- Step 1: SQLite schema migration (11min, 5 tests)
- Step 2: VectorStore.update_chunk_metadata() method (35min, 5 tests)
- Step 3: Classification detection engine (1h 10min, 2 tests)
- Step 4: Backup and audit logging (1h 25min, 2 tests)
- Step 5: Integration and error handling (45min, 1 test)

**Deliverables**:

- `kb_server/vector_store.py`: `update_chunk_metadata()` method for bulk metadata updates
- `ingest/reclassify_engine.py`: 4 core functions (detect, backup, log, cleanup)
- `ingest/core/metadata.py`: SQLite schema v2 with reclassify_backups and reclassify_history tables
- 15 passing tests across 4 test files

**Commits**: 6 atomic commits (d7e4a2a through 6fb69d5)

### Plan 16-02 Progress (Complete)

**All 6 steps COMPLETE** (2026-05-27, 2h 30min):

- Step 1: CLI module structure (6 tests)
- Step 2: Reclassify run command (5 tests)
- Step 3: Verify command (2 tests)
- Step 4: Sessions command (2 tests)
- Step 5: Rollback command (3 tests)
- Step 6: Integration testing

**Deliverables**:

- `ingest/cli/reclassify.py`: 4 subcommands (run, verify, sessions, rollback) with async implementations
- Rich UI: aggregated preview tables, per-document mismatch tables, progress bars
- Filter expression parser: supports `field="value"` and `field=value` syntax
- Interactive confirmation prompts with --yes bypass
- 18 passing tests

**Commits**: 5 atomic commits (d7e4a2a through 6fb69d5)

### Plan 16-03 Progress (Complete)

**All 5 steps COMPLETE** (2026-05-27, 1h 30min):

- Step 1: README.md "Reclassifying Documents" section (~170 lines)
- Step 2: README.pt-BR.md Portuguese translation (~160 lines)
- Step 3: README.es.md Spanish translation (~160 lines)
- Step 4: OPERATIONS.md "Reclassification Management" section (~315 lines)
- Step 5: Review and validation (all examples validated, 33 tests passing)

**Deliverables**:

- `README.md`: "Reclassifying Documents" section with 13 subsections (usage, verification, rollback, how it works, options, safety, 3 scenarios, 3 troubleshooting)
- `README.pt-BR.md`: Portuguese translation of all subsections
- `README.es.md`: Spanish translation of all subsections
- `docs/OPERATIONS.md`: "Reclassification Management" section (architecture, 4 procedures, monitoring, troubleshooting, 6 best practices, CI/CD integration)
- Total: ~820 lines of documentation across 4 files

**Commits**: 4 atomic commits (f5d2d9f, efea47f, a5ee367, 9b036e2)

### Canonical References Identified

- `ingest/classifier.py` — Reuse `classify()` for reclassification detection
- `kb_server/vector_store.py` — Add `update_chunk_metadata()` method
- `ingest/registry.py` — Add `reclassify_backups` and `reclassify_history` tables
- `ingest/cli/main.py` — Register `reclassify` subcommand
- `ingest/ingest.py:410-459` — Reference for how metadata is stored in chunk payloads

## Phase 17 Outcomes

### Status

**Phase 17 CONTEXT GATHERED** — 13 implementation decisions captured covering injection strategy (three-layer hybrid), truncation strategy (top-N = 20), new `list_filter_options` tool design, refresh strategy (startup + cache-bust marker file), and the new "module" classification axis.

### Key Decisions (from 17-CONTEXT.md)

- **Three-layer injection (D-01 to D-03)**: Dynamic descriptions (top-20 values) + no enum constraints (unbounded strings) + new `list_filter_options` tool for full enumeration
- **New tool (D-04 to D-06)**: `list_filter_options(field?, collection?)` — follows existing `list_` pattern
- **Event-driven refresh (D-09 to D-11)**: Startup scan + cache-bust marker file written by ingest pipeline
- **Module attribute (D-12)**: New classification axis — extends classifier.py, Qdrant payload, MCP tools
- **Attributes in scope (D-13)**: vendor, product, doc_type, subsystem, module, version, filter_type

### Context Files Created

- `.planning/phases/17-improve-capability-negotiation-on-the-mcp-server-to-advertis/17-CONTEXT.md` — 13 design decisions (D-01 through D-13)
- `.planning/phases/17-improve-capability-negotiation-on-the-mcp-server-to-advertis/17-DISCUSSION-LOG.md` — Audit trail with 8 discussion areas

### Requirements

| Requirement | Description |
|-------------|-------------|
| CAPNEG-01 | Advertise classified attributes during tool negotiation |
| CAPNEG-02 | Token-compact terms table |
| CAPNEG-03 | Extend existing tool descriptions/annotations |
| CAPNEG-04 | Backend indexes KB for unique attribute values |

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

- **06-01**: Mock infrastructure (3 session fixtures in conftest.py) + pytest marker registration (integration, PHASE12, cli)
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

### Key Decisions (v0.1.0)

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

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 28-mcp-streamable-http P02 | 15 min | 2 tasks | 3 files |

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 20260616-001 | Fix missing SQLAlchemy dependency in Docker | 2026-06-16 | — | | [20260616-fix-sqlalchemy-dep](./quick/20260616-fix-sqlalchemy-dep/) |
| 2 | split-gpu-requirements | Split GPU requirements from core with runtime detection | 2026-06-16 | 3cb2f05 | Verified | [split-gpu-requirements](./quick/2-split-gpu-requirements/) |
| 3 | Add AMD GPU (ROCm) support to entrypoint | 2026-06-16 | edadcf9 | Verified | [amd-gpu-support](./quick/3-amd-gpu-support/) |
| 4 | Fix CLI auth commands failing on read-only Docker auth.db | 2026-06-17 | beb2394 | Verified | [auth-db-fix](./quick/4-auth-db-fix/) |
| 5 | Fix kb-rag CLI entry point (missing kb_server in setup.py) | 2026-06-17 | 035e97d | Verified | [cli-fix](./quick/5-cli-fix/) |
| 6 | Add default admin user with password login and first-time API key | 2026-06-17 | fea95a3 | Verified | [admin-user-bootstrap](./quick/6-admin-user-bootstrap/) |
| 7 | Add missing tags_history table to IngestRegistry migration | 2026-06-17 | 6f91a9c | Verified | — |
