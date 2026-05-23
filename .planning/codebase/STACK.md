# Technology Stack

**Analysis Date:** 2026-05-19

## Languages

**Primary:**
- Python 3.11+ — entire application (server, ingestion, QA, observability)

**Secondary:**
- SQL — SQLite queries for metadata and query logging (`data/kb_metadata.db`, `data/registry.db`)

## Runtime

**Environment:**
- CPython 3.11 (minimum; 3.12 supported per setup.py classifiers)

**Package Manager:**
- pip + pip-tools (`requirements.in` → `requirements.txt`)
- Lockfile: `requirements.txt` (pinned versions present)
- Virtual env: `.venv/` (present in repo)

## Frameworks

**Core:**
- `mcp==1.27.1` — Model Context Protocol server; exposes `search_kb`, `list_documents`, `get_chunk`, `kb_stats` tools
- `fastapi==0.136.1` — Health check HTTP API (`server/health_server.py`)
- `starlette>=1.0.0` — SSE transport layer for MCP (`server/server.py`)
- `uvicorn==0.47.0` — ASGI server for SSE and health endpoints

**Ingestion / Parsing:**
- `PyMuPDF==1.27.2.3` — PDF extraction
- `python-docx==1.2.0` — DOCX extraction
- `openpyxl==3.1.5` — XLSX extraction
- `python-pptx==1.0.2` — PPTX extraction
- `docx2txt==0.8` — Legacy `.doc` extraction
- `xlrd==2.0.1` — Legacy `.xls` extraction
- `odfpy==1.4.1` — ODF formats (`.odt`, `.ods`, `.odp`)
- `langchain-text-splitters==1.1.2` — Document chunking

**Vector Search:**
- `qdrant-client==1.18.0` — Async Qdrant vector database client
- `fastembed==0.8.0` — BM25 sparse vectors for hybrid search
- `sentence-transformers==5.5.0` — Cross-encoder reranking

**Testing:**
- `pytest==9.0.3` — Test runner
- `pytest-asyncio==1.3.0` — Async test support (strict mode per `pyproject.toml`)

**Build/Dev:**
- `black==26.3.1` — Code formatter (line-length 79, target py311)
- `flake8==7.3.0` — Linting (`.flake8` config present)
- `isort==8.0.1` — Import sorting (black profile)
- `mypy==2.1.0` — Type checking (Python 3.11, lenient: `disallow_untyped_defs=false`)

## Key Dependencies

**Critical:**
- `mcp==1.27.1` — Core protocol; all AI client integrations depend on this
- `qdrant-client==1.18.0` — Vector store; entire retrieval pipeline depends on this
- `httpx==0.28.1` — Async HTTP client for embedding backends (LM Studio, Ollama, OpenAI-compat)
- `python-dotenv==1.2.2` — Environment config loading (`.env` at project root)
- `pydantic==2.13.4` — Data validation throughout
- `pydantic-settings==2.14.1` — Settings management

**Infrastructure:**
- `prometheus_client==0.25.0` — Metrics export (`observability/metrics.py`)
- `watchdog==6.0.0` — File system monitoring for auto-ingestion
- `diskcache==5.6.3` — Disk-backed cache (used in embedding cache layer)
- `psutil==7.2.2` — System monitoring for cache auto-tuning
- `SQLAlchemy==2.0.49` — ORM/DB access layer
- `rich==14.3.4` — CLI output formatting
- `typer==0.25.1` — CLI framework (`ingest/cli/main.py`)
- `click==8.3.3` — CLI dependency

**Evaluation (optional, `requirements-eval.txt`):**
- `datasets==4.8.5` — HuggingFace datasets
- `scikit-learn==1.8.0` — Clustering and metrics
- `matplotlib==3.10.9` — Evaluation visualizations

## Configuration

**Environment:**
- Primary config file: `.env` (loaded by server at startup via `python-dotenv`)
- Example configs: `config/.env.local`, `config/.env.lxc`
- Key env vars:
  - `EMBED_BACKEND` — `openai-compat` (default) | `lmstudio-sdk` | `lmstudio-rest` | `ollama`
  - `EMBED_MODEL` — embedding model name (default: `text-embedding-nomic-embed-text-v1.5-embedding`)
  - `LMS_BASE_URL` — LM Studio base URL (default: `http://localhost:1234`)
  - `OLLAMA_HOST` — Ollama URL (default: `http://localhost:11434`)
  - `QDRANT_HOST` / `QDRANT_PORT` — Qdrant server (default: `localhost:6333`)
  - `QDRANT_PATH` — Enable embedded Qdrant mode
  - `QDRANT_GRPC` — Use gRPC transport for Qdrant
  - `MCP_TRANSPORT` — `stdio` (default) | `sse`
  - `SSE_HOST` / `SSE_PORT` — SSE server binding (default: `127.0.0.1:8765`)
  - `HEALTH_HOST` / `HEALTH_PORT` — Health server (default: `127.0.0.1:8000`)
  - `LOG_PATH` — Log file path (default: `/tmp/kb-mcp.log`)
  - `QUERY_LOG_ENABLED` — Enable query logging to SQLite (default: `true`)
  - `QUERY_LOG_PATH` — SQLite path (default: `data/kb_metadata.db`)
  - `QUERY_LOG_RETENTION_DAYS` — Log retention (default: 90 days)

**Build:**
- `pyproject.toml` — Black, isort, mypy, pytest configuration
- `setup.py` — Package definition, entry points, install_requires
- `.flake8` — Flake8 linting configuration

## Platform Requirements

**Development:**
- Python 3.11+
- Qdrant (Docker via `docker-compose.yml` or embedded mode)
- Embedding backend: LM Studio, Ollama, or any OpenAI-compat server

**Production:**
- `docker-compose.yml` — Qdrant container (`qdrant/qdrant:latest`, ports 6333/6334)
- `scripts/kb-mcp.service` — systemd unit for Linux deployment
- `deployment/` directory — Kubernetes manifests (`docs/KUBERNETES.md`)
- Supports LXC Linux server (`config/.env.lxc`)
- Windows scripts: `scripts/start-kb-rag.ps1`

---

*Stack analysis: 2026-05-19*
