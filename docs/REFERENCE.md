# KB-RAG-MCP Reference

> Living reference for developers and onboarders. For the project roadmap see
> [PLAN.md](PLAN.md). For navigation see [INDEX.md](INDEX.md).

---

## What This Is

KB-RAG-MCP is a production-grade RAG (Retrieval-Augmented Generation) pipeline
that ingests technical documentation, stores it as vector embeddings in
Qdrant, and exposes it as an MCP (Model Context Protocol) server for use by AI
assistants such as Claude. It runs entirely on-premises: embeddings are generated
by a local LM Studio instance, no data leaves the network.

The system is designed for bare-metal deployment on Linux with systemd or
Kubernetes. It supports multi-format ingestion (PDF, DOCX, XLSX, PPTX, TXT,
legacy Office, ZIP), job-based async processing, LRU+Redis caching, hybrid
dense+sparse search, cross-encoder reranking, multi-collection routing, a web UI
for document browsing, query telemetry, Prometheus/Grafana observability, and a
QA evaluation pipeline.

---

## Architecture

```
  Documents on disk
       │
       ▼
  ┌─────────────┐     SQLite jobs/registry
  │  ingest/    │────────────────────────────┐
  │  pipeline   │                            │
  │  job system │   LM Studio (remote)       │
  │  worker pool│◄──── embeddings ───────────┤
  └──────┬──────┘                            │
         │ vectors + metadata                │
         ▼                                   │
  ┌─────────────┐    CollectionManager       │
  │   Qdrant    │◄── multi-collection        │
  │  vector DB  │    routing (PHASE 15)       │
  └──────┬──────┘                            │
         │ search                            │
         ▼                                   │
  ┌──────────────┐    LRU / Redis cache      │
  │  kb_server/  │◄──────────────────────────┘
  │  MCP server  │
  │  hybrid srch │
  │  reranker    │
  │  web UI      │
  └──────┬───────┘
         │ MCP protocol (stdio or SSE)
         ▼
    AI Assistant (Claude / OpenCode)
```

**Data flow (ingest):** file scanner → classifier → chunker → embed_client →
vector_store → Qdrant

**Data flow (search):** MCP tool call → CollectionRouter.resolve → embed query →
vector_store.search → optional hybrid (BM25+dense RRF) → optional reranker →
return ranked chunks

---

## Component Map

| Component | Package | Key Files | Purpose |
|---|---|---|---|
| MCP server | `kb_server` | `server.py` | Exposes `search_kb`, `list_documents`, `get_chunk`, `kb_stats`, `list_collections` MCP tools |
| Collection routing | `kb_server/collections` | `manager.py`, `router.py` | CollectionManager (CRUD) + CollectionRouter (resolve/ensure), PHASE 15 |
| Vector store | `kb_server` | `vector_store.py` | Qdrant async client, search, batch insert, payload indexes, collection_name override |
| Embed client | `kb_server` | `embed_client.py` | LM Studio / Ollama / OpenAI-compat embedding, batch, cache |
| LRU cache | `kb_server/cache` | `lru.py`, `manager.py`, `redis.py` | In-memory LRU with optional Redis fallback |
| Hybrid search | `kb_server/retrieval` | `hybrid_search.py` | Dense + BM25 sparse with RRF fusion |
| Reranker | `kb_server/retrieval` | `reranker.py` | Cross-encoder reranking (ms-marco-MiniLM-L-6-v2) |
| Web UI | `kb_server/ui` | `app.py`, `routes.py` | FastAPI+HTMX browse/search UI |
| Query telemetry | `kb_server/telemetry` | `query_logger.py` | SQLite query log, 90-day retention |
| Health server | `kb_server` | `health_server.py`, `health.py` | HTTP health endpoint for systemd/monitoring |
| Ingest pipeline | `ingest` | `ingest.py`, `registry.py`, `classifier.py` | File scan, classify, chunk, embed, upsert |
| Legacy parsers | `ingest/parsers` | `legacy_office.py`, `zip_handler.py` | .doc, .xls, .ppt, .odt, .ods, .odp, .wpd, .zip |
| Job system | `ingest/job` | `manager.py`, `scheduler.py`, `models.py` | SQLite-backed async job queue with priorities |
| Worker pool | `ingest/worker` | `pool.py`, `worker.py`, `limiter.py` | Async workers with token-bucket rate limiting |
| Validators | `ingest/validation` | `pipeline.py`, `format.py`, `size.py`, `content.py` | Pre-ingest file validation |
| File watcher | `ingest/watcher` | `file_watcher.py` | watchdog-based auto-ingest on file changes |
| Migration tools | `scripts/migrate` | `export.py`, `import_.py`, `validate.py` | Export/import/validate Qdrant snapshots + env |
| QA pipeline | `qa` | `run_qa.py`, `metrics.py`, `embedder.py`, `report.py` | End-to-end retrieval quality evaluation |
| Evaluation | `kb_server/evaluation` | `dataset.py`, `golden_dataset.json` | Golden dataset management |
| Reclassification engine | `ingest` | `reclassify_engine.py`, `cli/reclassify.py` | Detect, backup, and rollback reclassification (PHASE 16) |
| FilterTermsCache | `kb_server` | `filter_terms_cache.py` | Dynamic top-20 filter values with cache (PHASE 17) |
| Integration checker | `scripts` | `check-integration-gaps.py` | CI gate: 3 integration gap checks (PHASE 22) |
| Grafana dashboard | `deployment/config` | `grafana-dashboard.json` | 18-panel dashboard: ingestion, workers, cache, embedding API |
| Helm chart | `deployment/helm/kb-rag-mcp` | `Chart.yaml`, `values.yaml`, `templates/` | Kubernetes deployment (Deployment, StatefulSet, HPA, Services) |
| Enterprise Connectors | `ingest/connectors` | `factory.py`, `confluence.py`, `jira.py`, `git.py` | Remote source ingest (Confluence, JIRA, Git) |
| Knowledge Graph | `ingest` | `graph_builder.py` | Document graph metadata derivation |
| MCP Prompts | `kb_server` | `prompts.py` | `extract_answer` + `summarize_documents` |
| Auth | `kb_server` | `auth.py`, `auth_registry.py` | Optional Bearer token auth on SSE |
| Rate Limiter | `kb_server` | `rate_limiter.py` | Per-subject token bucket for servers |
| Circuit Breaker | `kb_server` | `circuit_breaker.py` | Provider resilience state machine |
| Provider Budget | `kb_server` | `provider_budget.py` | Sliding window budget tracking |
| Retrieval Cache | `kb_server/cache` | `request_cache.py` | Request-level search caching |

---

## MCP Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `search_kb` | Semantic search over the knowledge base | `query`, `top_k`, `product`, `doc_type`, `version`, `filter_type`, `hybrid`, `rerank`, `collection`, `kb_ids` |
| `list_documents` | List indexed documents with optional filters | `product`, `doc_type`, `filter_type`, `limit`, `collection` |
| `get_chunk` | Return a specific chunk with context window | `chunk_id`, `context_window` |
| `kb_stats` | Collection statistics (doc count, breakdown by product/type) | — |
| `list_collections` | List all available Qdrant collections | — |
| `get_related_documents` | Find documents related to a given doc or chunk | `chunk_id`, `collection` |
| `explore_topic` | Discover documents by topic/cluster | `topic`, `collection` |

The `collection` parameter on `search_kb` and `list_documents` is optional;
omitting it routes to `QDRANT_COLLECTION` (default: `kb_docs`).

The `kb_ids` parameter on `search_kb` enables multi-KB aggregated search: pass an
array of Qdrant collection names to search across all of them simultaneously with
RRF-fused results. Omitting `kb_ids` routes to the single `collection` (or
`QDRANT_COLLECTION`) for backward compatibility.

---

## Configuration

All config is via environment variables. Create a `.env` file at the project
root — it is loaded automatically before `kb_server` is imported.

**Core (required)**

| Variable | Default | Description |
|---|---|---|
| `LMS_BASE_URL` | `http://localhost:1234` | LM Studio base URL for embeddings |
| `EMBED_BACKEND` | `openai-compat` | Embedding backend: `openai-compat`, `ollama`, `fastembed` |
| `EMBED_MODEL` | `text-embedding-nomic-embed-text-v1.5-embedding` | Model name |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_COLLECTION` | `kb_docs` | Default collection name (multi-collection default) |
| `SCORE_THRESHOLD` | `0.35` | Minimum relevance score for search results |
| `MCP_TRANSPORT` | `stdio` | MCP transport: `stdio` or `sse` |
| `LOG_PATH` | `/tmp/kb-mcp.log` | Log file path |

**Embedding performance**

| Variable | Default | Description |
|---|---|---|
| `EMBED_BATCH_SIZE` | `32` | Batch size for embedding requests |
| `HTTP_POOL_CONNECTIONS` | `10` | HTTP connection pool size |
| `HTTP_POOL_MAXSIZE` | `20` | HTTP connection pool max size |
| `HTTP_TIMEOUT` | `30` | HTTP request timeout (seconds) |

**Qdrant tuning**

| Variable | Default | Description |
|---|---|---|
| `QDRANT_BATCH_SIZE` | `100` | Batch size for Qdrant upserts |
| `QDRANT_GRPC` | `false` | Use gRPC transport |
| `QDRANT_GRPC_PORT` | `6334` | gRPC port |
| `QDRANT_TIMEOUT` | `60.0` | Qdrant request timeout (seconds) |

**Chunking (per file type)**

| Variable | Default | Description |
|---|---|---|
| `INGEST_CHUNK_SIZE_PDF` | `1000` | Chunk size for PDF files |
| `INGEST_CHUNK_SIZE_DOCX` | `800` | Chunk size for DOCX files |
| `INGEST_CHUNK_SIZE_XLSX` | `500` | Chunk size for XLSX files |
| `INGEST_CHUNK_SIZE_PPTX` | `600` | Chunk size for PPTX files |
| `INGEST_CHUNK_SIZE_TXT` | `1000` | Chunk size for TXT files |
| `INGEST_CHUNK_OVERLAP_*` | `100–200` | Overlap per file type |

**Hybrid search**

| Variable | Default | Description |
|---|---|---|
| `HYBRID_DENSE_WEIGHT` | `0.7` | Dense vector weight in RRF fusion |
| `HYBRID_SPARSE_WEIGHT` | `0.3` | BM25 sparse weight in RRF fusion |
| `HYBRID_RRF_K` | `60` | RRF k constant |

**Reranker**

| Variable | Default | Description |
|---|---|---|
| `RERANKER_BATCH_SIZE` | `20` | Cross-encoder batch size |
| `RERANKER_CACHE_TTL` | `3600` | Reranker result cache TTL (seconds) |

**Query telemetry**

| Variable | Default | Description |
|---|---|---|
| `QUERY_LOG_ENABLED` | `true` | Enable query logging |
| `QUERY_LOG_PATH` | `./query_log.db` | SQLite log path |
| `QUERY_LOG_RETENTION_DAYS` | `90` | Days to keep logs |

**File watcher**

| Variable | Default | Description |
|---|---|---|
| `WATCH_PATH` | — | Directory to watch for new files |
| `WATCH_DEBOUNCE_SECONDS` | `30` | Debounce delay before triggering ingest |
| `WATCH_RECURSIVE` | `true` | Watch subdirectories recursively |
| `WATCH_IGNORE_PATTERNS` | `.tmp,.swp` | Comma-separated patterns to ignore |

**Web UI / Health**

| Variable | Default | Description |
|---|---|---|
| `UI_HOST` | `0.0.0.0` | Web UI bind host |
| `UI_PORT` | `8080` | Web UI port |
| `HEALTH_HOST` | `0.0.0.0` | Health server bind host |
| `HEALTH_PORT` | `8081` | Health server port |

**PDF extraction**

| Variable | Default | Description |
|---|---|---|
| `PDF_EXTRACTOR` | `auto` | Backend: `auto` (docling→PyMuPDF), `docling` (force), `pymupdf` (force) |
| `DOCLING_ARTIFACTS_PATH` | — | Persistent model cache directory (avoids re-download) |
| `DOCLING_DEVICE` | `auto` | Accelerator: `auto`, `cpu`, `cuda`, `mps` |
| `DOCLING_NUM_THREADS` | `os.cpu_count()` | CPU threads for ONNX inference |
| `RECLASSIFY_BACKUP_RETENTION_DAYS` | `30` | Days to keep reclassification backups |
| `SSE_HOST` | `0.0.0.0` | MCP SSE transport host |
| `SSE_PORT` | `8765` | MCP SSE transport port |

**Auth**

| Variable | Default | Description |
|---|---|---|
| `AUTH_ENABLED` | `false` | Enable Bearer token authentication on SSE |
| `AUTH_DB_PATH` | `./auth.db` | Path to auth SQLite database |

**Rate Limiting**

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_ENABLED` | `false` | Enable per-subject token bucket rate limiting |
| `RATE_LIMIT_REQUESTS` | `100` | Maximum requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |

**Upload Quotas**

| Variable | Default | Description |
|---|---|---|
| `STORAGE_QUOTA_ENABLED` | `false` | Enable ingestion storage quotas |
| `STORAGE_QUOTA_LIMIT_MB` | `1000` | Default per-collection quota (MB) |

**Circuit Breaker**

| Variable | Default | Description |
|---|---|---|
| `CIRCUIT_BREAKER_THRESHOLD` | `5` | Consecutive failures before opening circuit |
| `CIRCUIT_BREAKER_COOLDOWN` | `30` | Seconds before attempting half-open recovery |

**Provider Budget**

| Variable | Default | Description |
|---|---|---|
| `PROVIDER_BUDGET_ENABLED` | `false` | Enable sliding-window budget tracking |
| `PROVIDER_BUDGET_MAX_TOKENS` | `1000000` | Max tokens per window |
| `PROVIDER_BUDGET_WINDOW_SECONDS` | `3600` | Budget window duration |

**Retrieval Cache**

| Variable | Default | Description |
|---|---|---|
| `RETRIEVAL_CACHE_ENABLED` | `true` | Enable request-level search caching |
| `RETRIEVAL_CACHE_TTL` | `300` | Cache TTL in seconds |

---

## Supported File Formats

| Extension(s) | Type | Parser | Notes |
|---|---|---|---|
| `.pdf` | PDF | docling ^ → PyMuPDF fallback | Best quality; extracts text per page |

> ^ `docling` is optional — requires `pip install -e ".[pdf]"` or use `scripts/install-pdf-extras.sh`. Falls back to PyMuPDF when not installed.
> ^^ PDF backend is selectable via `PDF_EXTRACTOR` env var or `--pdf-extractor` CLI flag (`auto` | `docling` | `pymupdf`).
| `.docx` | Word 2007+ | python-docx | — |
| `.doc` | Word 97-2003 | docx2txt → python-docx fallback | Compatibility mode files work well |
| `.xlsx` | Excel 2007+ | openpyxl | All sheets extracted |
| `.xls` | Excel 97-2003 | xlrd | All sheets as separate chunks |
| `.pptx` | PowerPoint 2007+ | python-pptx | Per-slide extraction |
| `.ppt` | PowerPoint 97-2003 | python-pptx (best-effort) | Binary `.ppt` may fail; save as `.pptx` |
| `.odt` | OpenDocument Text | odfpy | Full paragraph extraction |
| `.ods` | OpenDocument Spreadsheet | odfpy | All sheets extracted |
| `.odp` | OpenDocument Presentation | odfpy | Per-slide extraction |
| `.wpd` | WordPerfect | heuristic text strip | Low quality; latin-1 decode only |
| `.txt` `.md` `.rst` | Plain text | built-in | — |
| `.py` `.ts` `.js` `.java` `.go` `.rs` `.cpp` `.c` `.cs` `.yaml` `.yml` `.json` `.xml` `.sh` `.sql` | Code | built-in | — |
| `.zip` | ZIP archive | stdlib + recursive | Up to 2 nesting levels; 500 MB/entry limit |

See [LEGACY_FORMATS.md](LEGACY_FORMATS.md) for full details on legacy and ZIP extraction rules.

---

## Running the System

### Prerequisites

- Python 3.11+
- Docker (for Qdrant)
- LM Studio running with `nomic-embed-text-v1.5` model loaded
- `.env` file at project root (see Configuration above)

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Qdrant

```bash
docker run -d -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

### 3. Ingest documents

```bash
# Ingest a directory tree
PYTHONPATH=. python -m ingest.cli.main ingest --path /path/to/docs --product MyProduct

# Ingest into a named collection (multi-collection, PHASE 15)
PYTHONPATH=. python -m ingest.cli.main ingest --path /path/to/docs --product MyProduct \
  --collection custom_kb
```

### 4. Start the MCP server

```bash
# stdio (for Claude Desktop / OpenCode)
PYTHONPATH=. python -m kb_server.server

# SSE (for HTTP access)
MCP_TRANSPORT=sse PYTHONPATH=. python -m kb_server.server
```

### 5. Start the Web UI (optional)

```bash
PYTHONPATH=. python -m kb_server.ui.run_ui
# Open http://localhost:8080/ui
```

### 6. Start the Health server (optional)

```bash
PYTHONPATH=. python -m kb_server.health_server
# GET http://localhost:8081/health
# GET http://localhost:8081/metrics  (Prometheus)
```

### Kubernetes (optional)

See [KUBERNETES.md](KUBERNETES.md) for full Helm-based deployment guide.

```bash
helm install kb-rag-mcp ./deployment/helm/kb-rag-mcp
```

### Deployment Modes

The system supports four deployment modes:

| Mode | Description | Quick Start |
|------|-------------|-------------|
| Docker Compose | Single-machine deployment with containers. Ideal for development and small teams. | `docker compose up -d` |
| Helm (Kubernetes) | Multi-replica, auto-scaling cluster deployment. Ideal for production. | `helm install kb-rag-mcp ./deployment/helm/kb-rag-mcp` |
| Systemd | Bare metal / VM deployment with systemd services. Ideal for dedicated servers. | `sudo ./deployment/scripts/install.sh` |
| Manual (Source) | Run from source with `python -m` commands. Ideal for development and customization. | `python -m kb_server.server` |

See [INDEX.md](INDEX.md) for per-mode navigation. Each deployment mode has dedicated subsections in [INSTRUCTIONS.md](INSTRUCTIONS.md),
[OPERATIONS.md](OPERATIONS.md), and [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Migration (backup/restore)

See [MIGRATION.md](MIGRATION.md) for export/import/validate guide.

```bash
bash scripts/kb-migrate.sh export ./backup-$(date +%Y%m%d).tar.gz
bash scripts/kb-migrate.sh import ./backup-20260518.tar.gz
```

---

## QA Results

Last run: 2026-06-11 against the ingested `kb_docs` collection.

| Metric | Result | Threshold | Status |
|---|---|---|---|
| Hit Rate | 100% | ≥ 70% | PASS |
| MRR | 0.78 | ≥ 0.50 | PASS |
| Zero-result % | 0% | ≤ 10% | PASS |
| Score p50 | 0.75 | ≥ 0.45 | PASS |
| Total queries | 3 | — | — |

**Overall verdict: PASS**

### Re-run QA eval (skip re-ingest)

```bash
PYTHONPATH=. python -m qa.run_qa --eval --output ./QA_REPORT.md
```

---

## Test Suite

```bash
# Run all tests
PYTHONPATH=. pytest

# Run with coverage
PYTHONPATH=. pytest --cov=kb_server --cov=ingest --cov=qa --cov-report=term-missing

# Run only fast unit tests (skip integration)
PYTHONPATH=. pytest -m "not integration"
```

**Current status:** 1095 passing, 0 failing, 12 skipped  
**Coverage target:** 90% branch, enforced on kb_server/ + ingest/  
**Key test files:**

| File | What it tests |
|---|---|
| `tests/test_smoke.py` | Import and basic startup smoke tests |
| `tests/test_vector_store.py` | VectorStore search and upsert |
| `tests/test_hybrid_search.py` | Hybrid search RRF fusion |
| `tests/test_reranker.py` | Cross-encoder reranking |
| `tests/test_collection_manager.py` | CollectionManager CRUD (PHASE 15) |
| `tests/test_collection_router.py` | CollectionRouter resolve/ensure (PHASE 15) |
| `tests/test_qa_metrics.py` | QA pipeline metrics (hit rate, MRR) |
| `tests/test_job_system.py` | Job queue lifecycle |
| `tests/test_legacy_parsers.py` | Legacy Office format extractors (.doc, .xls, .odt, etc.) |
| `tests/test_zip_handler.py` | ZIP recursive extraction (depth, size limits) |
| `tests/test_migration.py` | Migration export/import/validate (SHA256 manifests) |
| `tests/test_confluence_connector.py` | Confluence remote source connector |
| `tests/test_jira_connector.py` | JIRA remote source connector |
| `tests/test_git_connector.py` | Git remote source connector |
| `tests/test_knowledge_graph.py` | Knowledge graph metadata derivation |
| `tests/test_server_graph_tools.py` | Graph-based MCP tools (get_related, explore_topic) |
| `tests/test_server_prompts.py` | extract_answer and summarize_documents prompts |
| `tests/test_auth_registry.py` | Auth registry CRUD and key management |
| `tests/test_rate_limiter.py` | Token bucket rate limiter |
| `tests/test_provider_budget.py` | Sliding window budget tracking |
| `tests/test_circuit_breaker.py` | Circuit breaker state machine |
| `tests/test_request_retrieval_cache.py` | Request-level retrieval cache |
| `tests/test_cache_manager.py` | Cache manager with invalidation |
| `tests/e2e/` | End-to-end deployment and health workflows |

---

## Roadmap Status

Phases 1–28 (v0.1.3–v0.1.4) are complete. See [PLAN.md](PLAN.md) for full specifications.

| PHASE | Title | Status | Key Deliverable |
|---|---|---|---|
| 1 | Foundation & Testing Infrastructure | ✅ Complete | pytest setup, pip-tools, type hints |
| 1.5 | Migration Tools | ✅ Complete | export/import .tar.gz, SHA256 manifest, kb-migrate.sh |
| 2 | Job Management & Scheduler | ✅ Complete | SQLite job queue, priority scheduler |
| 3 | Worker Pool & Rate Limiter | ✅ Complete | Async worker pool, token bucket limiter |
| 4 | Progress Tracking & Observability | ✅ Complete | 28 Prometheus metrics, structured logging |
| 5 | Cache System | ✅ Complete | LRU cache, optional Redis, RAM auto-tune |
| 6 | CLI Refactor & Job Control | ✅ Complete | Click CLI, job commands, legacy wrapper |
| 7 | Document Validators & Quality | ✅ Complete | Format/size/content validators |
| 8 | Connection Pooling & Batch Optimization | ✅ Complete | Batch embeddings, batch Qdrant inserts |
| 9 | Production Hardening | ✅ Complete | systemd services, Grafana dashboard, health checks, backup |
| 10 | Documentation & Final QA | ✅ Complete | E2E tests, benchmarks, SECURITY.md |
| 11 | Expanded Ingestion | ✅ Complete | Legacy Office parsers, ZIP recursive extraction |
| 12 | Search Quality Enhancement | ✅ Complete | Hybrid search (BM25+dense), cross-encoder reranker |
| 13 | Ingestion Automation | ✅ Complete | File watcher, version extractor, _meta.json |
| 14 | Observability & Audit | ✅ Complete | Query logger, registry export, web UI |
| 15 | Advanced Infrastructure | ✅ Complete | Multi-collection routing, Kubernetes/Helm chart |
| 16 | Reclassification | ✅ Complete | Reclassification engine (detect/backup/rollback), CLI |
| 17 | Capability Negotiation | ✅ Complete | Module classification, FilterTermsCache, list_filter_options |
| 18 | Grafana Datasource Fix | ✅ Complete | Stable Prometheus UID across Docker Compose and Helm |
| 19 | VERIFICATION.md Backfill | ✅ Complete | Backfill verification docs for 13 shipped phases |
| 20 | Test Environment Fixes | ✅ Complete | LOG_PATH fix, fixture isolation, clean env |
| 21 | Codebase Hygiene Sweep | ✅ Complete | Remove unused imports, resolve TODOs, dead code |
| 22 | Integration Checker CI Gate | ✅ Complete | Gap checker script + CI job |
| 23 | Documentation Overhaul | ✅ Complete | Deployment-mode navigation, README restructure, CHANGELOG/REFERENCE update |
| 24 | FastAPI & CLI Integration | ✅ Complete | Docling CLI, FastAPI status, CI stabilization |
| 25 | Observability Phase 2 | ✅ Complete | Anomaly detection, host dashboard templates |
| 26 | Capability Negotiation Phase 2 | ✅ Complete | Collection awareness refinement |
| 27 | Embedding Provider Resilience | ✅ Complete | Auto-retry, circuit breaker, budget tracking |
| 28 | Reclassification Phase 2 | ✅ Complete | Multi-doc reclass, bulk operations, curated list |
| 29 | Enterprise Connectors | ✅ Complete | Confluence, JIRA, Git + factory |
| 30 | Knowledge Graph | ✅ Complete | Graph metadata, get_related/explore_topic tools |
| 31 | MCP Prompts | ✅ Complete | extract_answer, summarize_documents |
| 32 | API Key Auth | ✅ Complete | Optional Bearer auth on SSE, CLI management |
| 33 | Rate Limiting | ✅ Complete | Per-subject token bucket, HTTP 429 |
| 34 | Upload Quotas | ✅ Complete | Quota CLI, schema v3→v4 |
| 35 | Multi-KB Aggregated Search | ✅ Complete | kb_ids, resolve_multi, merge RRF |
| 36 | Provider Budget & Circuit Breaker | ✅ Complete | Provider resilience, fallback chain |
| 37 | Request-level Retrieval Cache | ✅ Complete | Request cache with invalidation |
| QA | QA Evaluation Pipeline | ✅ Complete | End-to-end eval, Hit Rate 100%, MRR 0.78 |

---

## Security

See [SECURITY.md](SECURITY.md) for the full threat model, hardening checklist, and
known limitations.

**Summary:** KB-RAG-MCP is an internal, trusted-network service with no
authentication. For production deployments exposed beyond localhost, apply the
hardening steps in SECURITY.md (Qdrant API key, nginx auth, TLS, systemd
sandboxing).

---

## Known Issues & Constraints

**LM Studio must be reachable before any kb_server import**  
`embed_client.py` reads `LMS_BASE_URL` at module import time. Load `.env` before
importing `kb_server`. If you write new entry points, follow the same pattern.

**QDRANT_COLLECTION must be set before VectorStore() is constructed**  
`VectorStore.__init__` reads `QDRANT_COLLECTION` via `os.getenv`. Setting it
after construction has no effect. Always set the env var before instantiating
the store.

**QA golden dataset has 3 queries**  
For a more rigorous evaluation, add more queries with verified chunk IDs from the
ingested collection to `qa/queries.json`.

**Qdrant required for integration tests (12 skipped)**  
Tests marked `integration` require a live Qdrant instance. Run `docker compose up -d`
before `pytest -m integration`.

**Authentication is optional (disabled by default)**  
The MCP server, web UI, and health endpoint have no auth by default. Set
`AUTH_ENABLED=true` and configure keys via `kb-ingest auth` CLI to enable Bearer
auth on SSE. See [SECURITY.md](SECURITY.md).
