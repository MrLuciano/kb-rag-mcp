# Features

Complete reference of all implemented features in **kb-rag-mcp**.

---

## Table of Contents

1. [Core Ingest Pipeline](#1-core-ingest-pipeline)
2. [Job Management & Scheduler](#2-job-management--scheduler)
3. [Worker Pool & Rate Limiter](#3-worker-pool--rate-limiter)
4. [Observability & Progress Tracking](#4-observability--progress-tracking)
5. [Embedding Cache (LRU + Redis)](#5-embedding-cache-lru--redis)
6. [CLI (Click + Rich)](#6-cli-click--rich)
7. [Document Validators](#7-document-validators)
8. [Connection Pooling & Batch Optimization](#8-connection-pooling--batch-optimization)
9. [Production Hardening & Grafana Dashboard](#9-production-hardening--grafana-dashboard)
10. [Security Documentation](#10-security-documentation)
11. [Legacy Format Parsers & ZIP Handler](#11-legacy-format-parsers--zip-handler)
12. [Hybrid Search (BM25 + Dense RRF)](#12-hybrid-search-bm25--dense-rrf)
13. [Ingestion Automation (File Watcher)](#13-ingestion-automation-file-watcher)
14. [Observability & Audit (Query Logger + Web UI)](#14-observability--audit-query-logger--web-ui)
15. [Multi-Collection Routing + Kubernetes](#15-multi-collection-routing--kubernetes)
16. [RAG Evaluation Pipeline](#16-rag-evaluation-pipeline)

---

## 1. Core Ingest Pipeline

Ingests documents (PDF, DOCX, TXT, MD, HTML) into a Qdrant vector store via chunking, classification, and embedding. The pipeline avoids re-ingesting unchanged files using a SQLite registry.

**Key files:**
- `ingest/ingest.py` — main CLI entrypoint; orchestrates extraction, chunking, embedding
- `ingest/classifier.py` — infers `product` and `doc_type` from filename/path via regex
- `ingest/registry.py` — SQLite-backed deduplication; tracks file hash and ingestion state
- `kb_server/vector_store.py` — Qdrant wrapper: upsert, search, list, stats

**Status:** ✅ Implemented

---

## 2. Job Management & Scheduler

Tracks each file as a `Job` with priority, status, and retry logic. A scheduler processes the queue in priority order, enabling visibility and control over long ingest runs.

**Key files:**
- `ingest/job/models.py` — `Job`, `JobStatus`, `JobPriority` dataclasses
- `ingest/job/manager.py` — `JobManager`: CRUD + lifecycle transitions
- `ingest/job/scheduler.py` — priority-based job dispatcher

**Status:** ✅ Implemented

---

## 3. Worker Pool & Rate Limiter

Async worker pool that processes jobs concurrently. A token-bucket rate limiter prevents overloading the embedding backend (LM Studio or Ollama).

**Key files:**
- `ingest/worker/pool.py` — `WorkerPool`: manages N async workers
- `ingest/worker/worker.py` — `FileWorker`: processes a single job with retry logic
- `ingest/worker/limiter.py` — token-bucket rate limiter
- `ingest/worker/executor.py` — `JobExecutor`: wires scheduler + pool together

**Status:** ✅ Implemented

---

## 4. Observability & Progress Tracking

Structured JSON logging and a 28-metric Prometheus exporter (`kb_*` prefix). Progress bars with ETA for long ingest runs.

**Key files:**
- `observability/logging.py` — structured JSON log formatter
- `observability/metrics.py` — 28 Prometheus counters/histograms/gauges
- `observability/progress.py` — progress tracking with ETA calculation

**Status:** ✅ Implemented

---

## 5. Embedding Cache (LRU + Redis)

In-memory LRU cache that deduplicates embedding calls for repeated or similar queries. Optional Redis backend for cross-process caching. RAM auto-tunes at startup.

**Key files:**
- `kb_server/cache/lru.py` — LRU cache with configurable RAM limit
- `kb_server/cache/redis.py` — optional Redis backend
- `kb_server/cache/manager.py` — unified interface; falls back to LRU if Redis unavailable

**Status:** ✅ Implemented

**Design note:** RAM limit is auto-detected at startup from available system memory. Redis connection failure is non-fatal — the cache degrades gracefully to in-memory LRU.

---

## 6. CLI (Click + Rich)

Full-featured command-line interface using Click for argument parsing and Rich for formatted output. Backward-compatible with the original positional-argument interface.

**Key files:**
- `ingest/cli/main.py` — top-level Click group
- `ingest/cli/job.py` — `ingest`, `status`, `retry`, `cancel` subcommands
- `ingest/cli/progress.py` — Rich progress bars and status tables
- `ingest/cli/legacy.py` — compatibility shim for old positional interface

**Status:** ✅ Implemented

---

## 7. Document Validators

Pre-ingest validation pipeline that checks format, file size, and content quality before queuing. Invalid files are logged and skipped without crashing the pipeline.

**Key files:**
- `ingest/validation/format.py` — extension and MIME type checks
- `ingest/validation/size.py` — file size limits (configurable per type)
- `ingest/validation/content.py` — minimum word count, encoding detection
- `ingest/validation/pipeline.py` — chains validators; returns structured result

**Status:** ✅ Implemented

---

## 8. Connection Pooling & Batch Optimization

Qdrant client uses a connection pool to avoid per-request overhead. Embeddings are batched in configurable chunks (default 32) to maximise throughput without exceeding backend limits.

**Key files:**
- `kb_server/vector_store.py` — batch upsert logic, pool configuration
- `kb_server/embed_client.py` — batched embedding calls with configurable batch size

**Status:** ✅ Implemented

---

## 9. Production Hardening & Grafana Dashboard

Health check endpoints, systemd service units, and a 18-panel Grafana dashboard for real-time monitoring.

**Key files:**
- `deployment/config/grafana-dashboard.json` — 18-panel dashboard (ingestion, workers, cache, latency)
- `deployment/config/grafana-provisioning/` — datasource + dashboard YAML for auto-provisioning
- `deployment/systemd/` — systemd unit files for bare-metal deployment
- `scripts/health_check.py` — end-to-end health check: embedding → Qdrant → search

**Status:** ✅ Implemented

---

## 10. Security Documentation

Threat model, attack surface analysis, and hardening guide for production deployment.

**Key files:**
- `docs/SECURITY.md` — threat model, hardening checklist, known limitations

**Status:** ✅ Implemented

---

## 11. Legacy Format Parsers & ZIP Handler

Extractors for legacy office formats and recursive ZIP unpacking, wired into the main ingest pipeline.

**Supported formats:** `.doc`, `.xls`, `.ppt`, `.odt`, `.ods`, `.odp`, `.wpd`, `.zip`

**Key files:**
- `ingest/parsers/legacy_office.py` — extractors with fallback chain: python-docx → antiword → LibreOffice CLI
- `ingest/parsers/zip_handler.py` — recursive ZIP extraction up to 2 levels, 500 MB/entry limit

**Status:** ✅ Implemented

---

## 12. Hybrid Search (BM25 + Dense RRF)

Combines dense vector search with BM25 sparse retrieval using Reciprocal Rank Fusion (RRF). Optionally re-ranks top-20 results with a cross-encoder.

**Key files:**
- `kb_server/retrieval/hybrid_search.py` — dense + sparse fusion with RRF
- `kb_server/retrieval/reranker.py` — cross-encoder re-ranking (model: `cross-encoder/ms-marco-MiniLM-L-6-v2`)

**Status:** ✅ Implemented

---

## 13. Ingestion Automation (File Watcher)

`watchdog`-based file watcher that monitors a directory and automatically queues new or modified files for ingestion.

**Key files:**
- `ingest/watcher/file_watcher.py` — `FileWatcher`: monitors path, debounces events, enqueues jobs

**Status:** ✅ Implemented

---

## 14. Observability & Audit (Query Logger + Web UI)

Every search query is logged to SQLite with 12 fields (query, filters, results, scores, latency). A FastAPI + HTMX web UI provides document browsing, search testing, and metadata inspection.

**Key files:**
- `kb_server/telemetry/query_logger.py` — SQLite query log, 90-day auto-rotation, <5 ms overhead
- `kb_server/ui/` — FastAPI + Bootstrap 5 + HTMX web interface (port 8001)
- `ingest/cli/export.py` — export document registry to JSON or CSV

**Status:** ✅ Implemented

**Design note:** Query logging is non-blocking. The web UI has no authentication (internal use only).

---

## 15. Multi-Collection Routing + Kubernetes

Routes MCP tool calls to named Qdrant collections. Collections can be created on demand or resolved strictly. Ships with a Helm chart for Kubernetes deployment.

**Key files:**
- `kb_server/collections/manager.py` — `CollectionManager`: list/create/delete/exists
- `kb_server/collections/router.py` — `CollectionRouter`: `resolve()` (strict) and `ensure()` (auto-create)
- `kb_server/server.py` — `collection=` parameter on `search_kb`, `list_documents`; `list_collections` tool
- `deployment/helm/kb-rag-mcp/` — Helm chart: Deployment, StatefulSet (Qdrant + PVC), HPA, Services, ConfigMap

**Status:** ✅ Implemented

**Design note:** `collection=` is optional — omitting it routes to `QDRANT_COLLECTION` (default: `kb_docs`), preserving backward compatibility.

---

## 16. RAG Evaluation Pipeline

End-to-end evaluation: query log analysis, a versioned golden dataset, RAGAS metrics (precision, recall, faithfulness), and chunk/score optimization experiment stubs.

**Key files:**
- `qa/run_qa.py` — QA pipeline entrypoint; runs eval against `queries.json`
- `qa/metrics.py` — Hit Rate, MRR, p50_score
- `kb_server/analytics/query_analyzer.py` — analyzes query logs for low-score and zero-result patterns
- `kb_server/evaluation/golden_dataset.json` — 10 hand-curated evaluation examples
- `kb_server/evaluation/ragas_pipeline.py` — RAGAS evaluator stub (LLM integration optional)

**Status:** ✅ Implemented

---

## 17. Admin SPA Panel

FastAPI + Jinja2 admin dashboard with: document browser, search tester, Config API management, Auth key management, Document export, Cleanup & re-ingest operations.

**Key files:**
- `kb_server/admin/` — FastAPI + Jinja2 admin dashboard

**Status:** ✅ Implemented

---

## 18. Auth & API Key Management

Optional Bearer token authentication with API key create/list/revoke, scope management, SHA-256 hashed keys.

**Key files:**
- `kb_server/auth/` — Bearer token auth, API key management

**Status:** ✅ Implemented

---

## 19. Config Management REST API

Five CRUD endpoints for server configuration stored in SQLite, with reload support.

**Key files:**
- `kb_server/admin/config_api.py` — Config CRUD endpoints

**Status:** ✅ Implemented

---

## 20. Provider Resilience

Circuit breaker (CLOSED/OPEN/HALF-OPEN) + sliding window budget per provider, auto-fallback between embedding backends.

**Key files:**
- `kb_server/providers/` — Circuit breaker, budget tracking, auto-fallback

**Status:** ✅ Implemented

---

## 21. Rate Limiting

Per-subject token bucket rate limiter with configurable requests/minute and burst capacity.

**Key files:**
- `kb_server/middleware/rate_limiter.py` — Token bucket rate limiter

**Status:** ✅ Implemented

---

## 22. MCP Streamable HTTP Transport

Alternative to stdio/SSE transport using MCP's Streamable HTTP protocol with session management.

**Key files:**
- `kb_server/transport/http_transport.py` — Streamable HTTP transport

**Status:** ✅ Implemented

---

## 23. Advanced Search Filters

Filter by vendor, subsystem, module parameters on search_kb and list_documents tools.

**Key files:**
- `kb_server/retrieval/filters.py` — Search filter logic

**Status:** ✅ Implemented

---

## 24. MCP Prompt Templates

`extract_answer` and `summarize_documents` MCP prompt templates. `PROMPT_DEFINITIONS` registry with `render_prompt()` dispatcher.

**Key files:**
- `kb_server/prompts/prompt_templates.py` — prompt definitions & dispatcher

**Status:** ✅ Implemented

---

## 25. Enterprise Data Source Connectors

`ConnectorBase` ABC with factory pattern for third-party data sources. Confluence (Cloud + DC), JIRA (Cloud + DC), and Git (clone + incremental pull) connectors. CLI staging system for connector management.

**Key files:**
- `ingest/connectors/base.py` — ConnectorBase ABC & factory
- `ingest/connectors/confluence.py` — Confluence connector
- `ingest/connectors/jira.py` — JIRA connector
- `ingest/connectors/git.py` — Git connector
- `ingest/cli/connector.py` — CLI staging system

**Status:** ✅ Implemented

---

## 26. Cross-Document Knowledge Graph

Document graph metadata derivation (`doc_graph_id`, entities, topics). `get_related_documents` and `explore_topic` MCP tools. Payload indexes on graph fields.

**Key files:**
- `kb_server/knowledge_graph/` — Graph metadata derivation & MCP tools

**Status:** ✅ Implemented

---

## 27. Upload & Index Quotas

6 quota fields (documents, chunks, storage, collections, api_calls, concurrent_jobs). SQLite `quota_config` and `quota_usage` tables. CLI: `kb-rag quota show/set/reset`. Ingest enforcement before chunking/embedding.

**Key files:**
- `kb_server/quotas/` — Quota configuration, tracking, and enforcement

**Status:** ✅ Implemented

---

## 28. Multi-KB Aggregated Search

`search_kb(kb_ids=[...])` across multiple collections. RRF fusion with per-collection score normalization. Chunk-level dedup across KB boundaries.

**Key files:**
- `kb_server/retrieval/aggregated_search.py` — Multi-collection search with RRF fusion

**Status:** ✅ Implemented

---

## 29. Provider Budget & Circuit Breaker

Per-provider token/month budgets with sliding window. Circuit breaker CLOSED/OPEN/HALF_OPEN state machine. Auto-fallback chain on budget exhaustion or circuit open.

**Key files:**
- `kb_server/providers/budget.py` — Token budget tracking
- `kb_server/providers/circuit_breaker.py` — Circuit breaker state machine
- `kb_server/providers/fallback.py` — Auto-fallback chain

**Status:** ✅ Implemented

---

## 30. Request-Level Retrieval Cache

SHA-256 deterministic cache keys over retrieval inputs. TTL expiry with invalidation hooks. Hit/miss counters and size monitoring.

**Key files:**
- `kb_server/cache/retrieval_cache.py` — Request-level retrieval cache

**Status:** ✅ Implemented

---

## 31. Document Tag Management

Per-document tag editing via CLI (list/update/delete/reingest). Tag filter on `search_kb` and `list_documents`. Tag display in admin document browser.

**Key files:**
- `kb_server/tags/` — Document tag management
- `ingest/cli/tag.py` — CLI tag subcommands

**Status:** ✅ Implemented

---

## 32. Ingestion Schedule Management

CRON-based schedule CRUD via REST API and admin UI. Background scheduler loop (30s interval). Schedule status display in admin monitor tab.

**Key files:**
- `ingest/scheduler/` — CRON schedule management & background loop
- `kb_server/admin/schedule.py` — Schedule REST API

**Status:** ✅ Implemented

---

## 33. Query Analytics Dashboard

Query volume, popular queries, slow queries visualizations. Zero-result analysis. Collection-specific filtering. Integrated into Admin SPA.

**Key files:**
- `kb_server/admin/analytics.py` — Query analytics endpoints
- `kb_server/admin/templates/analytics.html` — Analytics dashboard template

**Status:** ✅ Implemented

---

## 34. Chunk Preview in Document Detail

Inline chunk viewer with keyword highlighting. HTMX accordion-based chunk browser. Metadata display (score, source, position).

**Key files:**
- `kb_server/admin/chunks.py` — Chunk preview endpoints
- `kb_server/admin/templates/chunks.html` — Chunk browser template

**Status:** ✅ Implemented

---

## 35. Grafana Dashboard Embedding

Embedded Grafana iframe in admin monitor tab. Configurable dashboard UID. Direct link fallback.

**Key files:**
- `kb_server/admin/grafana.py` — Grafana embedding endpoints
- `kb_server/admin/templates/grafana.html` — Grafana embed template

**Status:** ✅ Implemented

---

## 36. Auth Security Hardening

JWT session cookie with HMAC signing. Secure cookie flags (HttpOnly, Secure, SameSite=Lax). API key ownership checks. Erasure separation for GDPR compliance.

**Key files:**
- `kb_server/auth/session.py` — JWT session management
- `kb_server/auth/middleware.py` — Auth middleware with secure cookies

**Status:** ✅ Implemented

---

## 37. Login Rate Limiting

5 attempts per 60s sliding window. Configurable via `LOGIN_RATE_LIMIT_WINDOW` and `LOGIN_RATE_LIMIT_MAX` env vars.

**Key files:**
- `kb_server/middleware/login_limiter.py` — Login rate limiter

**Status:** ✅ Implemented

---

## 38. Performance Optimizations

`croniter` for O(1) cron matching. `joinedload` single-query JOIN for `verify_key`. ConfigLoader 1s TTL cache.

**Key files:**
- `ingest/scheduler/cron.py` — O(1) cron matching with croniter
- `kb_server/auth/keys.py` — Optimized key verification
- `kb_server/config/loader.py` — TTL-cached ConfigLoader

**Status:** ✅ Implemented

---

## 39. E2E Test Suite

14 E2E tests across auth, admin, and schedule flows. Integration test patterns in `test_admin_ui.py`.

**Key files:**
- `tests/e2e/test_auth_flows.py` — Auth E2E tests
- `tests/e2e/test_admin_ui.py` — Admin UI integration tests
- `tests/e2e/test_schedule_flows.py` — Schedule E2E tests

**Status:** ✅ Implemented
