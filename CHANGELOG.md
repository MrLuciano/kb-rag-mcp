# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


## [0.1.5] 2026-06-15

### Fixed

- **Phase 44: Auth Security Hardening** (2026-06-15)
  - SEC-01: Mount auth router to fix unauthenticated SSE access
  - SEC-02: Erasure separation — `revoke_key` deletes only caller's keys
  - SEC-03: API key ownership checks on CRUD operations
  - SEC-04: Secure cookie flags (HttpOnly, Secure, SameSite=Lax)
  - SEC-05: `verify_key` batch dedup to prevent timing oracle
  - SEC-06: Rate-limit hashing uses SHA-256 of prefix, never raw keys

- **Phase 45: DB Reliability** (2026-06-15)
  - Consistent context manager usage for all SQLite connections
  - Foreign key enforcement enabled on all databases
  - Missing indexes added for query performance
  - Migration DDL hardened with IF NOT EXISTS / IF EXISTS guards

- **Phase 46: Code Quality** (2026-06-15)
  - `datetime.utcnow()` → `datetime.now(timezone.utc)` across 24 sites
  - Removed 16 unused imports (F401)
  - Tagged 5 tests with `@pytest.mark.integration`

- **Phase 50: SSE Test Consolidation** (2026-06-15)
  - Removed module-level stubs from `test_smoke.py` that polluted global state
  - Consolidated SSE transport tests into dedicated test module

- **REVIEW.md Resolution** (2026-06-15)
  - All 33 REVIEW.md findings resolved (25→28→30→33 across 4 passes)
  - Split dev dependencies from production requirements (HW-17)
  - Exposed session via property instead of `_session` direct access (INF-04)

### Added

- **Phase 28 Extensions: Session Management & Admin SPA** (2026-06-03)
  - 28-02: Session lifecycle management, max concurrent session enforcement with oldest-idle eviction, Prometheus session metrics (`active_sessions`, `session_evictions_total`), 60-second background sweep
  - 28c: Admin SPA panel — shell/auth/CSP, tab-based content layout, advanced search filters, document export/cleanup

- **Phase 40: Config API** (2026-06-10)
  - SQLite-backed config table with nonce-based locking
  - `ConfigLoader` with env override and live reload support
  - REST API endpoints for config CRUD

- **Phase 41: Provider Alias** (2026-06-10)
  - PROV-01: Embedding provider alias resolution (nickname → backend URL)
  - PROV-02: CLI support for provider alias create/list/delete

- **Phase 42: Query Logging Analytics Dashboard** (2026-06-15)
  - Analytics dashboard integrated into Admin SPA
  - Query volume, latency, top queries, and error rate visualizations
  - Date range filtering and export
  - 1284 passing tests, 0 failures

- **Phase 43: Chunk Preview with HTMX** (2026-06-15)
  - Accordion-based chunk browser with keyword highlighting
  - HTMX progressive loading for large result sets
  - Inline metadata display (score, source, position)

- **Phase 47: LM Studio Deprecation — Graceful Fallback** (2026-06-15)
  - Graceful embedding backend fallback with clear error message when LM Studio is unavailable
  - Fallback chain configuration

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



