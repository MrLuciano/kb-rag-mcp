# External Integrations

**Analysis Date:** 2026-05-19

## APIs & External Services

**Embedding Backends (pluggable via `EMBED_BACKEND` env var):**
- **LM Studio (SDK native)** — `lmstudio-sdk` backend
  - SDK/Client: `lmstudio==1.5.0`
  - Auth: None (local WebSocket, or `LMS_HOST`/`LMS_PORT` for remote)
  - Endpoint: WebSocket `ws://{LMS_HOST}:{LMS_PORT}`
  - Notes: Only works if LM Studio daemon accessible; falls back to `openai-compat`

- **LM Studio (REST API)** — `lmstudio-rest` backend
  - SDK/Client: `httpx` with `POST /api/v0/embeddings`
  - Auth: None
  - Config: `LMS_BASE_URL` (default: `http://localhost:1234`)

- **OpenAI-compatible API** — `openai-compat` backend (DEFAULT)
  - SDK/Client: `httpx` with `POST /v1/embeddings`
  - Auth: Static bearer token `"Bearer lm-studio"` (hardcoded for LM Studio; change for real OpenAI)
  - Config: `LMS_BASE_URL` (default: `http://localhost:1234`)
  - Notes: Works with LM Studio, Ollama, or actual OpenAI API

- **Ollama** — `ollama` backend
  - SDK/Client: `httpx` with `POST /api/embeddings`
  - Auth: None
  - Config: `OLLAMA_HOST` (default: `http://localhost:11434`)
  - Notes: Recommended for LXC/Linux server without GPU

**Implementation:** `server/embed_client.py`

## Data Storage

**Vector Database:**
- **Qdrant** — primary vector store for document embeddings
  - Mode 1 (HTTP): `QDRANT_HOST:QDRANT_PORT` (default: `localhost:6333`)
  - Mode 2 (gRPC): `QDRANT_HOST:QDRANT_GRPC_PORT` (default: `localhost:6334`), enabled via `QDRANT_GRPC=true`
  - Mode 3 (Embedded): local file storage via `QDRANT_PATH`
  - Client: `qdrant-client==1.18.0` (`AsyncQdrantClient`)
  - Collection: configured via `QDRANT_COLLECTION` (default: `kb_docs`)
  - Data dir: `data/qdrant/` (Docker volume)
  - Implementation: `server/vector_store.py`

**SQLite Databases:**
- `data/kb_metadata.db` — document metadata and query logs
  - Used by: query logger (`server/telemetry/query_logger.py`), KB metadata
- `data/registry.db` — ingestion registry
  - Used by: `ingest/registry.py`
- `kb_metadata.db` — legacy file at project root (appears to be migrated to `data/`)

**Embedding Cache:**
- In-memory LRU cache (default: 512 MB, 1-hour TTL)
- Optional disk cache via `diskcache==5.6.3`
- Cache manager: `server/cache/manager.py`
- Config: `CacheManager(backend="lru", max_size_mb=512, default_ttl=3600)`

## Authentication & Identity

**Auth Provider:**
- None — no user authentication system
- Embedding backends use static tokens or no auth
- MCP protocol provides no built-in auth; clients are implicitly trusted

## Monitoring & Observability

**Metrics:**
- **Prometheus** — metrics export via `prometheus_client==0.25.0`
  - Implementation: `observability/metrics.py`
  - Metrics exposed: jobs, workers, ingestion pipeline, cache hits/misses
  - Endpoint: served via FastAPI health server

**Logging:**
- Python stdlib `logging` — structured to stderr + file (`LOG_PATH`)
- Query logging to SQLite — search queries, latencies, result counts
  - Config: `QUERY_LOG_ENABLED`, `QUERY_LOG_PATH`, `QUERY_LOG_RETENTION_DAYS`
  - Implementation: `server/telemetry/query_logger.py`

**Health Checks:**
- FastAPI health server on `HEALTH_HOST:HEALTH_PORT` (default: `127.0.0.1:8000`)
- Implementation: `server/health_server.py`, `server/health.py`
- Docker healthcheck: `curl -f http://localhost:6333/healthz` (Qdrant)

## CI/CD & Deployment

**Hosting:**
- Docker (Qdrant only): `docker-compose.yml`
- Linux systemd: `scripts/kb-mcp.service`
- Kubernetes: `deployment/` directory (see `docs/KUBERNETES.md`)
- Windows: `scripts/start-kb-rag.ps1` (PowerShell)
- LXC Linux container: `config/.env.lxc`

**CI Pipeline:**
- Not detected (no `.github/workflows/`, `.gitlab-ci.yml`, etc.)

## Environment Configuration

**Required env vars (for production):**
- `EMBED_BACKEND` — embedding backend selection
- `LMS_BASE_URL` or `OLLAMA_HOST` — embedding server URL
- `QDRANT_HOST` + `QDRANT_PORT` — Qdrant connection (or `QDRANT_PATH` for embedded)
- `EMBED_MODEL` — embedding model identifier

**Optional env vars:**
- `MCP_TRANSPORT` — `stdio` | `sse` (defaults to `stdio` for Claude/AI client use)
- `SSE_HOST` / `SSE_PORT` — SSE transport binding
- `HEALTH_HOST` / `HEALTH_PORT` — Health API binding
- `LOG_PATH` — Log file location
- `QUERY_LOG_ENABLED` / `QUERY_LOG_PATH` / `QUERY_LOG_RETENTION_DAYS` — Query analytics
- `DEFAULT_TOP_K` — Default search result count (default: 5)
- `SCORE_THRESHOLD` — Minimum similarity score (default: 0.35)
- `QDRANT_GRPC` / `QDRANT_GRPC_PORT` — Enable gRPC for Qdrant
- `HTTP_POOL_CONNECTIONS` / `HTTP_POOL_MAXSIZE` / `HTTP_TIMEOUT` — HTTP client tuning
- `EMBED_BATCH_SIZE` — Batch size for embedding (default: 32)

**Secrets location:**
- `.env` file at project root (never committed; `.env` listed in `.gitignore`)
- `config/.env.local`, `config/.env.lxc` — environment-specific templates

## MCP Protocol

**Transport Modes:**
- `stdio` (default) — standard I/O for Claude Code, OpenCode, and other AI clients
- `sse` — Server-Sent Events over HTTP for web-based MCP clients

**MCP Tools Exposed:**
- `search_kb` — semantic search with optional hybrid (dense+BM25) and reranking
- `list_documents` — list indexed documents with filtering
- `get_chunk` — retrieve specific chunk with context window
- `kb_stats` — knowledge base statistics

**Compatible Clients:**
- Claude Code, OpenCode, and any MCP-compatible client
- Config example: `config/mcp-clients.json`

## File System Monitoring

**Watchdog:**
- `watchdog==6.0.0` — monitors directories for new files to auto-ingest
- Implementation: `server/` or `ingest/` (see `docs/AUTO_INGESTION.md`)

## HuggingFace Integration

**Sentence Transformers:**
- `sentence-transformers==5.5.0` — cross-encoder models for reranking
  - Implementation: `server/retrieval/reranker.py`
  - Downloads models from HuggingFace Hub on first use
- `huggingface_hub==1.15.0` — model download utilities
- `fastembed==0.8.0` — BM25 sparse vectors (also downloads models)

---

*Integration audit: 2026-05-19*
