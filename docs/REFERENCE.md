# KB-RAG-MCP Reference

> Living reference for developers and onboarders. For the project roadmap see
> [PLAN.md](PLAN.md). For navigation see [INDEX.md](INDEX.md).

---

## What This Is

KB-RAG-MCP is a production-grade RAG (Retrieval-Augmented Generation) pipeline
that ingests OpenText product documentation, stores it as vector embeddings in
Qdrant, and exposes it as an MCP (Model Context Protocol) server for use by AI
assistants such as Claude. It runs entirely on-premises: embeddings are generated
by a local LM Studio instance, no data leaves the network.

The system is designed for bare-metal deployment on Linux with systemd. It
supports multi-format ingestion (PDF, DOCX, XLSX, PPTX, TXT, legacy Office),
job-based async processing, LRU+Redis caching, hybrid dense+sparse search,
cross-encoder reranking, a web UI for document browsing, query telemetry, and a
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
  ┌─────────────┐                            │
  │   Qdrant    │  (local Docker)            │
  │  vector DB  │                            │
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

**Data flow (search):** MCP tool call → embed query → vector_store.search →
optional hybrid (BM25+dense RRF) → optional reranker → return ranked chunks

---

## Component Map

| Component | Package | Key Files | Purpose |
|---|---|---|---|
| MCP server | `kb_server` | `server.py` | Exposes `search_kb`, `list_kb_stats`, `get_chunk` MCP tools |
| Vector store | `kb_server` | `vector_store.py` | Qdrant async client, search, batch insert, payload indexes |
| Embed client | `kb_server` | `embed_client.py` | LM Studio / Ollama / OpenAI-compat embedding, batch, cache |
| LRU cache | `kb_server/cache` | `lru.py`, `manager.py`, `redis.py` | In-memory LRU with optional Redis fallback |
| Hybrid search | `kb_server/retrieval` | `hybrid_search.py` | Dense + BM25 sparse with RRF fusion |
| Reranker | `kb_server/retrieval` | `reranker.py` | Cross-encoder reranking (ms-marco-MiniLM-L-6-v2) |
| Web UI | `kb_server/ui` | `app.py`, `routes.py` | FastAPI+HTMX browse/search UI |
| Query telemetry | `kb_server/telemetry` | `query_logger.py` | SQLite query log, 90-day retention |
| Health server | `kb_server` | `health_server.py`, `health.py` | HTTP health endpoint for systemd/monitoring |
| Ingest pipeline | `ingest` | `ingest.py`, `registry.py`, `classifier.py` | File scan, classify, chunk, embed, upsert |
| Job system | `ingest/job` | `manager.py`, `scheduler.py`, `models.py` | SQLite-backed async job queue with priorities |
| Worker pool | `ingest/worker` | `pool.py`, `worker.py`, `limiter.py` | Async workers with token-bucket rate limiting |
| Validators | `ingest/validation` | `pipeline.py`, `format.py`, `size.py`, `content.py` | Pre-ingest file validation |
| File watcher | `ingest/watcher` | `file_watcher.py` | watchdog-based auto-ingest on file changes |
| QA pipeline | `qa` | `run_qa.py`, `metrics.py`, `embedder.py`, `report.py` | End-to-end retrieval quality evaluation |
| Evaluation | `kb_server/evaluation` | `dataset.py`, `golden_dataset.json` | Golden dataset management |

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
| `QDRANT_COLLECTION` | `kb_docs` | Default collection name |
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
| `SSE_HOST` | `0.0.0.0` | MCP SSE transport host |
| `SSE_PORT` | `8000` | MCP SSE transport port |

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

Or via docker-compose if available in the repo.

### 3. Ingest documents

```bash
# Ingest a directory tree
PYTHONPATH=. python -m ingest.cli.main ingest --path /path/to/docs --product MyProduct

# Or use the job system
PYTHONPATH=. kb-rag ingest --path /path/to/docs --product MyProduct --workers 4
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
```

---

## QA Results (OTCS Corpus)

Last run: 2026-05-18 against the ingested `kb_docs` collection.

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
PYTHONPATH=. python -m qa.run_qa --eval --output ./QA_REPORT_OTCS.md
```

### Re-run full pipeline (ingest + eval)

```bash
PYTHONPATH=. python -m qa.run_qa \
  --otcs-path /path/to/OTCS \
  --workers 4 \
  --output ./QA_REPORT_OTCS.md
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

**Current status:** 252 passing, 38 failing (pre-existing, non-critical), 9 skipped  
**Coverage target:** 70%+ overall, critical paths prioritized  
**Key test files:**

| File | What it tests |
|---|---|
| `tests/test_smoke.py` | Import and basic startup smoke tests |
| `tests/test_vector_store.py` | VectorStore search and upsert |
| `tests/test_hybrid_search.py` | Hybrid search RRF fusion |
| `tests/test_reranker.py` | Cross-encoder reranking |
| `tests/test_qa_metrics.py` | QA pipeline metrics (hit rate, MRR) |
| `tests/test_job_system.py` | Job queue lifecycle |
| `tests/e2e/` | End-to-end deployment and health workflows |

---

## Roadmap Status

All planned phases are complete. See [PLAN.md](PLAN.md) for full specifications.

| FASE | Title | Status | Key Deliverable |
|---|---|---|---|
| 1 | Foundation & Testing Infrastructure | ✅ Complete | pytest setup, pip-tools, type hints |
| 1.5 | Migration Tools | ✅ Complete | export/import .tar.gz, SHA256 manifest |
| 2 | Job Management & Scheduler | ✅ Complete | SQLite job queue, priority scheduler |
| 3 | Worker Pool & Rate Limiter | ✅ Complete | Async worker pool, token bucket limiter |
| 4 | Progress Tracking & Observability | ✅ Complete | Prometheus metrics, structured logging |
| 5 | Cache System | ✅ Complete | LRU cache, optional Redis, RAM auto-tune |
| 6 | CLI Refactor & Job Control | ✅ Complete | Click CLI, job commands, legacy wrapper |
| 7 | Document Validators & Quality | ✅ Complete | Format/size/content validators |
| 8 | Connection Pooling & Batch Optimization | ✅ Complete | Batch embeddings, batch Qdrant inserts |
| 9 | Production Hardening | ✅ Complete | systemd services, health checks, backup |
| 10 | Documentation & Final QA | ✅ Complete | E2E tests, benchmarks, docs |
| 11 | Expanded Ingestion | ✅ Complete | Legacy Office, ZIP recursive extraction |
| 12 | Search Quality Enhancement | ✅ Complete | Hybrid search (BM25+dense), reranker |
| 13 | Ingestion Automation | ✅ Complete | File watcher, version extractor, _meta.json |
| 14 | Observability & Audit | ✅ Complete | Query logger, registry export, web UI |
| 15 | Advanced Infrastructure | ✅ Complete | Multi-collection, Kubernetes/Helm |
| 16 | RAG Performance & Accuracy | ✅ Complete | RAGAS pipeline, golden dataset, experiments |
| QA | OTCS QA Pipeline | ✅ Complete | End-to-end eval, Hit Rate 100%, MRR 0.78 |

---

## Known Issues & Constraints

**LM Studio must be reachable before any kb_server import**  
`embed_client.py` reads `LMS_BASE_URL` at module import time. Load `.env` before
importing `kb_server` — `qa/run_qa.py` does this correctly. If you write new
entry points, follow the same pattern.

**QDRANT_COLLECTION must be set before VectorStore() is constructed**  
`VectorStore.__init__` reads `QDRANT_COLLECTION` via `os.getenv`. Setting it
after construction has no effect. Always set the env var before instantiating
the store.

**38 pre-existing test failures**  
The failing tests are in `test_reranker.py` (requires model download) and
`test_payload_indexes.py` (requires live Qdrant with data). They do not affect
production behavior.

**QA golden dataset has 3 queries**  
`qa/queries.json` contains 3 queries against the OTCS corpus. For a more
rigorous evaluation, add more queries with verified chunk IDs from the ingested
collection.

**No authentication**  
The MCP server, web UI, and health endpoint have no auth. Deploy on a trusted
internal network only.
