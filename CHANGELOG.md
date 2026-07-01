# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Phase 54: UI Polish Fixes** — 13 fixes resolving all UI-REVIEW.md findings
  - Copywriting: "RAGAS Evaluation" → "Evaluation", "Search Tester" → "Semantic Search", expanded K/BM25/Rerank labels, user-friendly error messages
  - Typography: Fixed heading hierarchy (h4.h6 → h4, h3.h5 → h3) for valid outline
  - Layout: Removed double container nesting, clean pagination hrefs, centered job status counters, mobile spacing
  - UX: Dismissible HTMX error alerts, animated RAGAS progress bar, Bootstrap search pagination (HTMX)
  - Nyquist: 13 validation tests (1554 suite baseline, all green)

- **docs/PROVISIONING.md** — Provisioning reference with VM SKUs, pricing, and sizing for small (10 users) and medium (100 users) teams

### Fixed

- **Docker: croniter dependency** — Added `croniter==6.2.2` to `requirements.core.txt` to fix `web-ui` crash on startup (ModuleNotFoundError from `ingest.core.cron`)

### Changed

- **Root directory cleanup** — Moved 5 documentation files to `docs/` (FEATURES, TRANSITION, UI-REVIEW, REVIEW, REVIEW-DBA), removed stale empty `package-lock.json`
- **Updated `.gitignore`** — Added `logs/` and `.mypy_cache/`

### Security

- **Phase 29: Nyquist validation retrofill** — 18 new tests across 8 connector test files covering schema migration coexistence, rate limiting, incremental checkpoint wiring, SSH auth, workspace cleanup, and pipeline end-to-end flows (1572 suite baseline, all green)

## [0.1.5] 2026-06-29

### Fixed

- **Phase 44: Auth Security Hardening**
  - SEC-01: Mount auth router to fix unauthenticated SSE access
  - SEC-02: Erasure separation — `revoke_key` deletes only caller's keys
  - SEC-03: API key ownership checks on CRUD operations
  - SEC-04: Secure cookie flags (HttpOnly, Secure, SameSite=Lax)
  - SEC-05: `verify_key` batch dedup to prevent timing oracle
  - SEC-06: Rate-limit hashing uses SHA-256 of prefix, never raw keys

- **Phase 45: Database Reliability**
  - Consistent context manager for all SQLite connections
  - Foreign key enforcement on all databases
  - Missing indexes for query performance
  - Migration DDL hardened with IF NOT EXISTS / IF EXISTS guards

- **Phase 46: Code Quality & Coverage**
  - `datetime.utcnow()` → `datetime.now(timezone.utc)` across 24 sites
  - 16 unused imports removed (F401)
  - 5 tests tagged with `@pytest.mark.integration`
  - Flake8 cleanup
  - Test tagging for all skipped tests

- **Phase 50: SSE Test Consolidation**
  - Removed module-level stubs from `test_smoke.py` (120+ lines)
  - All SSE tests run in same pytest process
  - Per-function `@patch` decorators instead of module-level stubs

- **Phase 53: Bug Fixes**
  - `test_admin_ui` config save test fixed for Alpine.js CSP compat

- **REVIEW.md Resolution**
  - All 33 REVIEW.md findings resolved (25→28→30→33 across 4 passes)
  - Split dev dependencies from production requirements (HW-17)
  - Exposed session via property instead of `_session` direct access (INF-04)

### Added

- **Phase 28: MCP Streamable HTTP Transport**
  - `/mcp` HTTP POST endpoint alongside existing stdio/SSE
  - Session lifecycle management with max concurrent session enforcement
  - Prometheus session metrics (`active_sessions`, `session_evictions_total`)
  - Three transport modes: stdio, SSE, Streamable HTTP

- **Phase 28b: Auth & User Management API**
  - SQLAlchemy users table with password hashing
  - POST /auth/login with username+password
  - POST /auth/session for API key → session cookie exchange
  - User CRUD (GET/POST/PUT/DELETE /users)
  - API Key CRUD (GET/POST/DELETE /api-keys)
  - JWT session cookie with HMAC signing
  - Default admin account seeded on startup
  - Session create/list/revoke

- **Phase 28c: Admin SPA Panel**
  - Alpine.js + HTMX admin panel at /admin/
  - Tab-based layout: Documents, Ingestion, RAGAS, Admin tabs
  - Document browser with filters, pagination, export
  - Search tester with parameter controls
  - Login overlay with API key authentication
  - Hamburger sidebar with responsive design (280px/icon-only)
  - CSP nonce on inline scripts for security
  - Route ordering (specific /tabs/ paths before generic)
  - Auth router mounted on UI app

- **Phase 28c-fixes: Admin SPA Gap Closure**
  - Auth flow rewrite with Alpine.js login overlay
  - Document browse with checkboxes and bulk actions
  - Monitor lights panel (7 health components with latency)
  - Config inline editor with HTMX PUT save and Reset All
  - Session management UI (list/revoke)
  - Credential management UI (generate/revoke API keys)
  - CSP-safe Alpine.js build (@alpinejs/csp) with SRI hash

- **Phase 38: Grafana Dashboard Embedding**
  - Embed Grafana iframe in Admin monitor tab
  - Dashboard UID configuration via env var
  - Responsive iframe sizing
  - Direct link fallback when iframe blocked

- **Phase 39: Observability Backlog**
  - Request ID middleware for distributed tracing
  - Percentile latency metrics (P50, P95, P99)
  - Component-level health status in monitor lights
  - Logging for auth operations and config changes

- **Phase 40: Configuration Backlog**
  - SQLite config table with nonce-based locking
  - ConfigLoader with env override chain and live reload
  - REST API: GET/PUT/DELETE /config endpoints
  - Type validation (string, int, bool, float) with coercion
  - Config change log with before/after values
  - Observer model for hot-reload subscriptions

- **Phase 41: Provider Alias**
  - Embedding provider alias resolution (nickname → backend URL)
  - Config-based alias storage and lookup
  - CLI support for alias create/list/delete

- **Phase 42: Query Analytics Dashboard**
  - Admin dashboard with query volume chart (past 7 days)
  - Top 10 most popular queries table
  - Slow queries (P95 latency) identification
  - Zero-result query analysis
  - Collection-specific filtering

- **Phase 43: Chunk Preview in Document Detail**
  - Inline chunk viewer in document detail modal
  - Keyword highlighting for matched search terms
  - Accordion-based chunk browser with HTMX progressive loading
  - Inline metadata display (score, source, position)

- **Phase 47: LM Studio Dependency Handling**
  - Graceful fallback when LM Studio is unreachable
  - Clear error message when embedding backend unavailable
  - Fallback chain configuration

- **Phase 51: Document Tag Management**
  - Per-document tags via `kb-rag tags` CLI (list/update/delete/reingest)
  - Tag filter in `search_kb` and `list_documents`
  - Tag display in admin document browser
  - Re-ingest trigger on tag changes

- **Phase 52: Ingestion Schedule Management**
  - CRON-based schedule CRUD via UI and REST API
  - Background scheduler loop (every 30s checks for cron match)
  - Scheduler runs async, doesn't block server
  - Schedule status display in admin ingestion monitor tab

- **Phase 53: Features**
  - 14 E2E tests across auth, admin, and schedule flows
  - Login rate limiting: 5 attempts per 60s window
  - Startup security warnings for AUTH_ENABLED=false in HTTP mode

### Changed

- **Phase 53: Quality & Polish**
  - Security audit report with 12 findings (1 Critical accepted, 2 High fixed)
  - Performance: croniter for O(1) cron matching (was O(n) iteration)
  - Performance: joinedload single-query JOIN for `verify_key`
  - Performance: ConfigLoader 1s TTL cache to reduce SQLite reads
  - Documentation: API.md, README, OPERATIONS.md updated

## [0.1.4]

### Changed
- **Version retag**: Renamed 11 git tags (v0.7.0–v1.3 → v0.0.7–v0.1.3) at same commits;
  renamed 17 planning files with `v1.x` → `v0.1.x` in filenames;
  updated version strings (`setup.py: 1.0.0 → 0.1.0`, `cli: 0.10.0-dev → 0.0.10-dev`);
  replaced ~350 `v1.x` content references across 50 files
  
### Added

- **Phase 23: Documentation Overhaul** (2026-05-27)
  - 23-01: Add deployment-mode navigation sections to OPERATIONS.md, TROUBLESHOOTING.md, INSTRUCTIONS.md, INDEX.md
  - 23-02: Restructure README.md, README.pt-BR.md, README.es.md (two-tier format: quickstart + docs/)
  - 23-03: Update CHANGELOG with v0.1.3/v0.1.4 sections; audit and update REFERENCE.md

- **Phase 24: RAGAS Evaluation Pipeline** (2026-06-10)
  - 24-01: 4 custom RAGAS metrics (faithfulness, answer_relevancy, context_precision, context_recall) — replaced incompatible ragas library with zero-dependency prompt-based metrics via LLM-as-judge
  - 24-02: CSV/JSON dataset loading with auto-delimiter detection, extending GoldenDataset
  - 24-03: `kb-rag evaluate` CLI command with CSV/JSON/console results export
  - 24-04: 4 backend LLM wrappers (LM Studio REST/SDK, OpenAI-compat, Ollama) + RAGASLLMAdapter
  - 57 tests, all passing

- **Phase 25: Optimization Experiments** (2026-06-11)
  - 25-01: Core infrastructure — config, metric_computer, result_store
  - 25-02: Chunking experiments — fixed, recursive, semantic strategies
  - 25-03: Scoring experiments — dense, hybrid, reranked variants
  - 25-04: Experiment runner + CLI: `kb-rag optimize` command

- **Phase 26: KB Content Discoverability** (2026-06-03)
  - Dynamic content-summary tool descriptions for `search_kb`, `list_documents`, `get_chunk`
  - `kb://overview` MCP Resource returning knowledge base description, document count, top products
  - `kb_resource_handler` registered in MCP server

- **Phase 27: Knowledge Base Registry** (2026-06-03)
  - SQLite-backed KB registry (`data/kb_registry.db`) with public/agent_private scopes
  - Stable `kb_<id>` collection naming with version tracking
  - 3 MCP CRUD tools: `create_kb`, `list_kbs`, `delete_kb`
  - Ingest `--kb-id` flag for routing documents to specific KBs
  - Legacy single-KB migration path (env var → registry entry)
  - 100% test coverage on registry operations

- **Phase 28: MCP Streamable HTTP Transport** (2026-06-03)
  - `/mcp` HTTP POST endpoint alongside existing stdio/SSE
  - Three transport modes: stdio, SSE, Streamable HTTP
  - Backward compatible — existing clients continue unchanged
  - Health check endpoint ready for load balancer probes

- **Phase 29: Enterprise Data Source Connectors** (2026-06-10)
  - 29-01: Connector foundation — `ConnectorBase` ABC, factory pattern, staging system, `kb-rag connectors` CLI, connector-aware ingest path. 34 tests
  - 29-02: Confluence connector — Server/DC (Basic auth, offset pagination) and Cloud (Bearer, cursor pagination), CQL filters, html2text→Markdown. 21 tests
  - 29-03: JIRA connector — Cloud and DC, JQL builder, ADF→Markdown extraction, project iteration. 16 tests
  - 29-04: Git connector — full sync (clone), incremental sync (pull --ff-only + diff), content type detection for 30+ extensions. 23 tests
  - Suite: 894 passed, 2 pre-existing failures

- **Phase 30: Cross-Document Knowledge Graph** (2026-06-10)
  - 30-01: Graph metadata derivation — `compute_document_id()` (SHA-256), `extract_entities()` (frequency-based, no NLP deps), `extract_topics()`, payload indexes on `doc_graph_id`/`graph_topics`/`graph_related`. 19+ tests
  - 30-02: Two new MCP tools — `get_related_documents(doc_graph_id)` and `explore_topic(topic)` for graph-based discovery. 10 tests
  - Suite: 923 passed, 2 pre-existing failures

- **Phase 31: MCP Prompt Templates** (2026-06-10)
  - `kb_server/prompts.py` — `PROMPT_DEFINITIONS` registry with `extract_answer` (grounded answer + citations) and `summarize_documents` (structured summary + section headers)
  - `render_prompt()` dispatcher, MCP `list_prompts()` and `get_prompt()` handlers
  - 16 tests, all passing; Suite: 939 passed

- **Phase 32: API Key Authentication** (2026-06-10)
  - `kb_server/auth_registry.py` — SQLite-backed API key store with SHA-256 hashed keys (never stored/logged plaintext)
  - `kb_server/auth.py` — Bearer token extraction, `verify_request()`, `is_auth_enabled()`
  - SSE middleware returns 401 on invalid key
  - CLI: `kb-rag auth create`/`list`/`revoke`
  - Disabled by default (`AUTH_ENABLED=false`) — backward compatible
  - 21 tests, all passing; Suite: 960 passed

- **Phase 33: Request Rate Limiting** (2026-06-10)
  - `kb_server/rate_limiter.py` — per-subject token buckets, non-blocking `check(subject)`, auto-creation + idle sweep
  - Two-layer enforcement: SSE connection (HTTP 429 + Retry-After) and tool call (structured error TextContent)
  - Subject derivation: API key prefix (auth'd SSE), IP (unauthed SSE), "stdio" (stdio transport)
  - 3 new Prometheus metrics: `rate_limit_allowed_total`, `rate_limit_rejected_total`, `rate_limit_subjects`
  - Disabled by default — backward compatible
  - 18 tests, all passing; Suite: 978 passed

- **Phase 34: Upload and Index Quotas** (2026-06-10)
  - Schema v3→v4 migration: `quota_config` and `quota_usage` tables with 6 quota fields
  - CRUD: `set_quotas()`, `get_quotas()`, `get_quota_usage()`, `check_quota()`, `update_quota_usage()`, `reset_quota_usage()`
  - Ingest integration: early rejection before chunking/embedding
  - CLI: `kb-rag quota show`/`set`/`reset`
  - All fields default to `None` (unlimited) — backward compatible
  - 21 tests, all passing; Suite: 999 passed

- **Phase 35: Multi-KB Aggregated Search** (2026-06-10)
  - `search_kb(kb_ids=[...])` — search across multiple KBs in a single call
  - Parallel collection dispatch via `VectorStore.multi_search()`
  - Score normalization across collections before merging
  - RRF fusion for combined result ranking
  - Chunk-level deduplication across KB boundaries
  - Graceful degradation on individual KB failures

- **Phase 36: Provider Budget & Circuit Breaker** (2026-06-11)
  - Per-provider embedding budgets with configurable token/month limits
  - Circuit breaker: CLOSED/OPEN/HALF_OPEN state machine, exponential backoff cooldown, per-provider isolation
  - Fallback provider chain on budget exhaustion or circuit open
  - 7 new Prometheus metrics for provider resilience
  - Configuration via `EMBED_BACKEND=primary;secondary` semicolon chain
  - 69 new tests; Suite: 1095 passed, 0 failures

- **Phase 37: Request-Level Retrieval Cache** (2026-06-11)
  - `kb_server/cache/request_cache.py` — deterministic cache key via SHA-256 over sorted JSON of all retrieval inputs
  - TTL expiry, `invalidate_all()` hook
  - Server integration: cache hit skips embedding + vector search + reranking
  - New `kb_rag_retrieval_cache_ops_total` counter with hit/miss labels
  - 29 tests; Suite: 1095 passed, 12 skipped, 0 failures

## [0.1.3] 2026-05-27

### Added

- Phase 12: English Comments & Docstrings
  - 12-01: Translate kb_server/ modules to English (165 changes)
  - 12-02: Translate ingest/ modules to English (100+ changes)
  - 12-03: English-only CI gate
- Phase 13: Docs Sync & Readme Languages
  - 13-01: Sync features/readme for OTCS
  - 13-02: Sync features/readme for Content Server
  - 13-03: README.pt-BR.md translation
  - 13-04: README.es.md translation
- Phase 14: Health Dashboard
  - 14-01: /metrics endpoint with 28 Prometheus metrics
  - 14-02: Grafana dashboard with 6-row, 28-panel layout
  - 14-03: Docker Compose Prometheus/Grafana integration
  - 14-04: Kubernetes/Helm monitoring stack
  - 14-05: Health Dashboard documentation (OPERATIONS.md)
  - 14-06: Docker Compose fixes (entrypoint, healthchecks)
- Phase 15: PowerShell Ports Script
  - 15-01: Windows firewall configuration in start-kb-rag.ps1
  - 15-02: Windows firewall documentation (EN/PT-BR/ES + OPERATIONS.md)
- Phase 16: Reclassification
  - 16-01: Core reclassification engine (detect, backup, rollback)
  - 16-02: kb-ingest reclassify CLI (run, verify, sessions, rollback)
  - 16-03: Reclassification documentation (~820 lines across 4 files)
- Phase 17: Capability Negotiation
  - 17-01: Module classification axis (infer_module, MODULE_PATTERNS)
  - 17-02: FilterTermsCache with dynamic descriptions (top-20 values)
  - 17-03: list_filter_options MCP tool
- Phase 18: Grafana Datasource Fix
  - 18-01: Stable Prometheus UID across Docker Compose and Helm paths
- Phase 19: VERIFICATION.md Backfill
  - 19-01: Backfill VERIFICATION.md for 13 shipped phases + gap detection script
- Phase 20: Test Environment Fixes
  - 20-01: Fix LOG_PATH PermissionError, fixture isolation, clean env
- Phase 21: Codebase Hygiene Sweep
  - 21-01: Remove 13 unused imports, resolve 3 TODOs, remove 2 dead code instances
- Phase 22: Integration Checker CI Gate
  - 22-01: Integration gap checker script (3 checks) + CI job

## [0.1.0] - Initial Release

### Added

- **MCP Server**
  - FastAPI-based MCP server for RAG queries
  - Qdrant vector store integration
  - OpenAI embeddings support
  - Document ingestion pipeline

- **Document Processing**
  - Support for 25+ file formats (PDF, DOCX, code files, etc.)
  - Text extraction and chunking
  - Product classification
  - File registry for tracking processed documents

- **Vector Search**
  - Semantic search with OpenAI embeddings
  - Qdrant collection management
  - Configurable similarity thresholds
  - Batch operations support

- **Configuration**
  - Environment-based configuration
  - Docker Compose setup
  - Systemd service files
  - Health check scripts

- **Documentation**
  - Installation guide
  - Usage examples
  - Architecture overview
  - API reference



