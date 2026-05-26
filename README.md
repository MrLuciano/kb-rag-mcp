# KB RAG MCP Server

**[English](#english) | [Português (Brasil)](#português-brasil) | [Español](#español)**

---

<a name="english"></a>
## 🇬🇧 English

Production-grade MCP (Model Context Protocol) server for semantic search over
local knowledge bases. Supports PDF, DOCX, XLSX, PPTX, TXT, Markdown, and
source code. Compatible with **Claude Code**, **OpenCode**, and any
MCP client.

### ✨ Features

- 🔍 **Semantic search** over technical documentation
- 📚 **Multi-format support**: PDF, DOCX, XLSX, PPTX, TXT, code
- ✅ **585 tests** — Full mock isolation, no external deps needed for unit tests
- ✅ **CI/CD pipeline** — Coverage gate (90% branch), logging audit, Helm lint, English audit
- ✅ **SSE transport** — Starlette 1.0.0 with stable disconnect handling
- ✅ **Python 3.13** — CI matrix tests on 3.11, 3.12, 3.13
- ✅ **Auto-classification** — Vendor, product, subsystem, and version inference from filenames and metadata
- ✅ **Lazy cross-encoder** — ~10s faster server startup, model loads on first reranking query
- ✅ **Kubernetes/Helm** — Helm chart for multi-replica deployment
- 🎯 **Smart classification**: automatic product and doc type detection
- 🚀 **Production-ready**: systemd services, health checks, auto-restart
- 💾 **Incremental ingestion**: only processes new/modified files
- 📊 **Monitoring**: Prometheus metrics, alerting rules, health endpoints
- 🔄 **Cache system**: LRU with RAM auto-tuning or Redis (80%+ hit rate)
- 🔧 **Multi-backend**: LM Studio, Ollama, or OpenAI-compatible APIs
- ⚡ **Batch processing**: 3-5x faster ingestion with connection pooling
- 🛠️ **Operations**: Automated install, backup/restore, updates
- 👁️ **Auto-ingestion**: File watcher for automatic document updates
- 🏷️ **Version filtering**: Search by document version (22.3, CE 24.4)
- 📝 **Metadata overrides**: Per-directory/file classification control

---

### 📋 Table of Contents

- [Quick Start](#quick-start)
- [Production Deployment](#production-deployment)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Health Checks](#health-checks)
- [Service Management](#service-management)
- [MCP Tools](#mcp-tools)
- [Architecture](#architecture)
- [Monitoring](#monitoring)
- [Operations](#operations)
- [Development](#development)
- [Documentation](#documentation)
- [License](#license)

---

### 🚀 Quick Start

> **Prerequisites:** Python 3.11+, 3.12, 3.13 supported, Docker (for Qdrant), and an embedding backend
> (LM Studio, Ollama, or any OpenAI-compatible server).

#### Option 1: One-command setup (recommended)

```bash
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp

# Starts Qdrant, installs deps, launches the MCP server
bash scripts/quickstart.sh --docs /path/to/your/docs
```

The script:
1. Copies `config/.env.template` → `.env` (edit `EMBED_URL`, `EMBED_MODEL` before re-running)
2. Creates `.venv/` and installs all Python dependencies
3. Starts Qdrant via Docker Compose
4. Launches the MCP server in the background (`logs/kb-rag-mcp.log`)
5. Ingests documents from the path you provide

#### Option 2: Docker Compose (full stack)

```bash
cp config/.env.template .env   # fill in EMBED_URL and EMBED_MODEL
docker compose up -d
```

#### Option 3: Manual setup

```bash
# 1. Start Qdrant
docker compose up -d qdrant

# 2. Install Python deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# 3. Configure
cp config/.env.template .env
#    → edit .env: set EMBED_URL, EMBED_MODEL, DOCS_PATH

# 4. Start MCP server
python -m kb_server.server

# 5. Ingest your docs
python ingest/ingest.py --docs /path/to/your/docs
```

#### Connect your AI assistant

Add to your MCP client configuration (Claude, OpenCode, Cursor, Copilot):

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

For **stdio mode** (no SSE, default for Claude Code):

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "python",
      "args": ["-m", "kb_server.server"],
      "cwd": "/path/to/kb-rag-mcp",
      "env": { "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

#### Verify everything is working

```bash
# Qdrant
curl http://localhost:6333/healthz

# MCP server health
curl http://localhost:8080/health

# Or use the CLI health check
kb-rag check health

# Ask your AI assistant:
# "Search the knowledge base for <topic in your docs>"
```

---

### 🏭 Production Deployment

**Automated installation for production Debian/Ubuntu servers with systemd services, health checks, and monitoring.**

#### Quick Production Install

```bash
# 1. Clone repository
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp

# 2. Run automated installer (requires root)
sudo ./deployment/scripts/install.sh

# 3. Configure (edit as needed)
sudo nano /opt/kb-rag/config/kb-rag.env

# 4. Restart services
sudo systemctl restart kb-rag.target

# 5. Verify health
curl http://localhost:8000/health/detailed
```

#### What Gets Installed

The automated installer (`deployment/scripts/install.sh`) performs:

- ✅ System dependencies (Python 3.11+, SQLite, logrotate)
- ✅ User creation (`kb-rag` system user)
- ✅ Directory structure (`/opt/kb-rag/{data,logs,config}`)
- ✅ Python virtual environment with dependencies
- ✅ Configuration file generation
- ✅ systemd services installation:
  - `kb-rag-server.service` - MCP server (stdio/SSE)
  - `kb-rag-health.service` - Health check HTTP server (port 8000)
  - `kb-rag-scheduler.service` - Job scheduler
  - `kb-rag-watcher.service` - File watcher
  - `kb-rag.target` - Unified service management
- ✅ Log rotation (14-day retention, 100MB max size)
- ✅ Security hardening (user isolation, filesystem protection)
- ✅ Automatic service startup and health verification

#### Service Management

```bash
# Start all services
sudo systemctl start kb-rag.target

# Stop all services
sudo systemctl stop kb-rag.target

# Restart all services
sudo systemctl restart kb-rag.target

# Check status
sudo systemctl status kb-rag.target

# View logs
sudo journalctl -u kb-rag-server -f
sudo journalctl -u kb-rag-health -f
sudo journalctl -u kb-rag-watcher -f  # File watcher logs

# Enable auto-start on boot
sudo systemctl enable kb-rag.target
```

#### Health Checks

The health server (port 8000) provides 4 endpoints:

```bash
# Basic health (load balancers)
curl http://localhost:8000/health

# Detailed component health (monitoring)
curl http://localhost:8000/health/detailed

# Kubernetes-style readiness
curl http://localhost:8000/ready

# Kubernetes-style liveness
curl http://localhost:8000/alive

# Prometheus metrics
curl http://localhost:8000/metrics
```

#### Backup and Restore

```bash
# Create backup
./deployment/scripts/backup.sh

# Restore from backup
sudo ./deployment/scripts/restore.sh /path/to/backup.tar.gz

# Scheduled backups (cron)
# Add to /etc/cron.daily/kb-rag-backup:
#!/bin/bash
/opt/kb-rag/deployment/scripts/backup.sh /backups/kb-rag-$(date +%Y%m%d).tar.gz
```

#### Updates

```bash
# Update to latest version
sudo ./deployment/scripts/update.sh

# Update to specific version
sudo ./deployment/scripts/update.sh v1.3

# Rollback on failure (automatic)
# If services fail to start, update script automatically restores from backup
```

#### Uninstallation

```bash
# Remove everything (including data)
sudo ./deployment/scripts/uninstall.sh

# Remove but keep data
sudo ./deployment/scripts/uninstall.sh --keep-data
```

#### Resource Requirements

| Component | Memory | CPU | Disk | Notes |
|-----------|--------|-----|------|-------|
| MCP Server | 200-500MB | 50-100% | - | Baseline usage (v1.3) |
| Health Server | 30-50MB | 5-10% | - | Lightweight monitoring |
| Scheduler | 50-100MB | 10-20% | - | Job management |
| File Watcher | 50-100MB | 5-15% | - | Auto-ingestion daemon |
| Qdrant | 500MB-2GB | 50-100% | Varies | Vector storage |
| **Total** | **~1-3.5GB** | **150-250%** | **10GB+** | Recommended: 4GB RAM, 4 vCPU |

#### Security Features

- **User Isolation**: Services run as non-root `kb-rag` user
- **Filesystem Protection**: `ProtectSystem=strict`, `ProtectHome=true`
- **Resource Limits**: Memory and CPU quotas prevent resource exhaustion
- **No New Privileges**: `NoNewPrivileges=true` prevents escalation
- **Private /tmp**: `PrivateTmp=true` isolates temporary files
- **Minimal Permissions**: Only data and logs directories writable

#### Production Checklist

- [ ] Qdrant running and accessible
- [ ] Embedding service (LM Studio/Ollama) accessible
- [ ] Configuration customized (`/opt/kb-rag/config/kb-rag.env`)
- [ ] Services enabled and running
- [ ] Health checks passing (`curl localhost:8000/health/detailed`)
- [ ] Prometheus monitoring configured (optional)
- [ ] Alert rules deployed (optional)
- [ ] Backup scheduled (cron)
- [ ] Firewall configured (if external access needed)
- [ ] SSL/TLS via reverse proxy (if external access needed)

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for complete deployment documentation.

---

### 💻 Installation

> **For production deployment**, see [Production Deployment](#production-deployment) section above for automated installation with systemd services.

This section covers manual development installation.

#### Prerequisites

- Python 3.11, 3.12, 3.13 supported
- Docker (for Qdrant) or Qdrant embedded
- LM Studio / Ollama / OpenAI-compatible embedding API
- 8+ GB RAM (16+ GB recommended)

#### Development Installation

**1. Clone the repository**

```bash
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp
```

**2. Create virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

**3. Install dependencies**

```bash
# Using pip-tools (recommended)
pip install pip-tools
pip-sync requirements.txt

# Or directly with pip
pip install -r requirements.txt
```

**4. Configure environment**

```bash
# Copy template
cp deployment/config/kb-rag.env.template .env

# Edit with your settings
vim .env
```

**5. Start Qdrant**

```bash
# Using Docker
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  qdrant/qdrant

# Or with Docker Compose
docker compose up -d
```

**6. Verify installation**

```bash
# Start the MCP server
python -m kb_server.server

# In another terminal, check health
kb-rag check health
curl http://localhost:8000/health/detailed
```

---

### ⚙️ Configuration

#### Environment Variables

Create `.env` file in project root:

```bash
# Embedding Backend
EMBED_BACKEND=openai-compat  # lmstudio-sdk, lmstudio-rest, openai-compat, ollama
EMBED_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
LMS_BASE_URL=http://localhost:1234  # LM Studio URL (without /v1)
OLLAMA_HOST=http://localhost:11434

# Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_PATH=  # Leave empty for Docker, set path for embedded mode
QDRANT_COLLECTION=kb_docs

# Search Settings
SCORE_THRESHOLD=0.35  # Minimum relevance score (0.0-1.0)
DEFAULT_TOP_K=5       # Default search results

# MCP Transport
MCP_TRANSPORT=stdio   # stdio or sse
SSE_HOST=0.0.0.0      # For SSE mode
SSE_PORT=8765

# Cache Settings
CACHE_BACKEND=lru     # lru or redis
CACHE_MAX_SIZE_MB=512 # LRU cache size (auto if not set)
CACHE_TTL=3600        # Cache TTL in seconds

# Batch Processing
EMBED_BATCH_SIZE=32        # Embedding batch size (25-64)
FILE_BATCH_SIZE=50         # File processing batch (50-100)
QDRANT_BATCH_SIZE=100      # Qdrant batch upsert (80-200)
HTTP_POOL_CONNECTIONS=20   # HTTP connection pool size
MAX_CONCURRENT_UPLOADS=3   # Concurrent uploads (1-5)

# Worker Pool
WORKER_POOL_SIZE=4         # Worker count (default: 4)
WORKER_RATE_LIMIT=10       # Requests/sec per worker (default: 10)

# Auto-Ingestion (File Watcher)
WATCH_PATH=                # Directory to watch for changes
WATCH_DEBOUNCE_SECONDS=30  # Debounce interval in seconds
WATCH_RECURSIVE=true       # Watch subdirectories
WATCH_IGNORE_PATTERNS=     # Comma-separated glob patterns to ignore

# Health Server
HEALTH_PORT=8000           # Health check HTTP server port

# General
LOG_LEVEL=INFO             # Logging level (DEBUG, INFO, WARNING, ERROR)
```

#### MCP Client Configuration

**Claude Code (Windows + WSL2)**

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "wsl.exe",
      "args": [
        "-d", "Debian",
        "--",
        "/home/YOUR_USER/kb-rag-mcp/.venv/bin/python",
        "-m", "kb_server.server"
      ]
    }
  }
}
```

**Claude Code (SSE mode)**

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://<LXC_SERVER_HOST>:8765/sse"
    }
  }
}
```

**OpenCode**

`~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "kb-rag": {
      "type": "local",
      "command": [
        "/path/to/kb-rag-mcp/.venv/bin/python",
        "-m", "kb_server.server"
      ]
    }
  }
}
```

---

### 📖 Usage

#### Ingesting Documents

```bash
# Using the kb-rag CLI (recommended)
kb-rag ingest --docs /path/to/docs

# Or directly with Python
source .venv/bin/activate
python ingest/ingest.py --docs /path/to/docs

# With explicit product and vendor
python ingest/ingest.py --docs /path/to/docs --product MyProduct --vendor Acme

# Single file
python ingest/ingest.py --file /path/to/document.pdf

# Clean and re-ingest everything
python ingest/ingest.py --docs /path/to/docs --clean

# More workers (use with GPU)
python ingest/ingest.py --docs /path/to/docs --workers 4

# Check ingestion status via CLI
kb-rag status
kb-rag status --source /path/to/docs

# Or the legacy status commands
python ingest/ingest.py --status
python ingest/ingest.py --status --list    # List all files
python ingest/ingest.py --status --errors  # Only errors
```

#### Recommended Directory Structure

```
docs/
├── product-a/
│   ├── api-reference.pdf
│   ├── getting-started.docx
│   └── examples/
│       └── sample.py
├── product-b/
│   ├── manual.pdf
│   └── config.xlsx
└── general/
    └── architecture.pptx
```

Product is automatically inferred from directory name. Documents are also
auto-classified with **vendor**, **subsystem**, and **version** metadata
extracted from filenames and directory structure (see Phase 11 features).

#### Auto-Ingestion

Monitor directories for changes and automatically trigger ingestion:

```bash
# Start file watcher service
sudo systemctl start kb-rag-watcher

# Or run standalone
python -m ingest.watcher.file_watcher

# Configure in .env
WATCH_PATH=/path/to/docs
WATCH_DEBOUNCE_SECONDS=30
```

**See [AUTO_INGESTION.md](docs/AUTO_INGESTION.md) for full guide.**

#### Version Filtering

Search documents by version (automatically extracted from filenames/paths):

```python
# MCP tool usage
search_kb(
    query="installation steps",
    product="AppServer",
    version="3.2"  # Only search 3.2 docs
)
```

**Supported version patterns:**
- Numeric: `22.3`, `23.1.5`
- CE prefix: `CE 24.4`
- v prefix: `v2.5`
- Version keyword: `version 16.2`

**See [VERSION_FILTERING.md](docs/VERSION_FILTERING.md) for full guide.**

#### Metadata Overrides

Override automatic classification with `_meta.json` files:

```json
{
  "product": "AppServer",
  "doc_type": "admin_guide",
  "files": {
    "install.pdf": {
      "doc_type": "installation_guide"
    }
  }
}
```

**See [METADATA_OVERRIDES.md](docs/METADATA_OVERRIDES.md) for full guide.**

---

### 🏥 Health Checks

KB-RAG includes a comprehensive health check system that monitors all components.

#### Health Endpoints

The health server runs on port 8000 (configurable via `HEALTH_PORT`) and provides:

```bash
# Basic health - for load balancers
GET /health
→ {"status": "ok", "service": "kb-rag"}

# Detailed health - for monitoring dashboards
GET /health/detailed
→ {
  "status": "ok",
  "healthy": true,
  "timestamp": "2026-05-15T12:00:00Z",
  "components": {
    "embedding": {"healthy": true, "latency_ms": 45.2, ...},
    "vector_store": {"healthy": true, "latency_ms": 12.5, ...},
    "cache": {"healthy": true, "latency_ms": 0.1, ...},
    "database": {"healthy": true, "latency_ms": 2.3, ...},
    "filesystem": {"healthy": true, "latency_ms": 1.5, ...}
  }
}

# Readiness probe - Kubernetes style
GET /ready
→ {"ready": true}  # 200 if ready, 503 if not

# Liveness probe - Kubernetes style
GET /alive
→ {"alive": true}  # Always 200 if responding
```

#### Component Checks

| Component | Checks | Critical | Details |
|-----------|--------|----------|---------|
| **embedding** | Service reachable, test embedding | Yes | Backend, model, dimensions |
| **vector_store** | Qdrant connection, collection exists | Yes | Total chunks, documents |
| **cache** | Stats available | No | Backend, entries, hit rate |
| **database** | SQLite accessible, queries work | Yes | Jobs, files counts |
| **filesystem** | Read/write access, disk space | No | Free space (warning < 10%) |

**Note:** Cross-encoder reranking model is lazy-loaded (not checked at health probe) — loads on first reranking query (~10s faster startup).

#### Health Check Scripts

```bash
# Check all services
./deployment/scripts/health-check.sh all

# Check specific service
./deployment/scripts/health-check.sh server
./deployment/scripts/health-check.sh health
./deployment/scripts/health-check.sh scheduler

# Exit codes: 0=healthy, 1=unhealthy, 2=error
```

#### Manual Health Server

For development without systemd:

```bash
# Start health server
python -m kb_server.health_server

# Or use the CLI
kb-rag check health

# In another terminal, check health
curl http://localhost:8000/health/detailed | jq
```

---

### ⚙️ Service Management

> **Note:** Service management requires production deployment with systemd. See [Production Deployment](#production-deployment).

#### Basic Commands

```bash
# Start all KB-RAG services
sudo systemctl start kb-rag.target

# Stop all KB-RAG services
sudo systemctl stop kb-rag.target

# Restart all KB-RAG services
sudo systemctl restart kb-rag.target

# Check overall status
sudo systemctl status kb-rag.target
```

#### Individual Services

```bash
# MCP Server (main service)
sudo systemctl status kb-rag-server
sudo systemctl restart kb-rag-server

# Health Check Server
sudo systemctl status kb-rag-health
sudo systemctl restart kb-rag-health

# File Watcher (auto-ingestion)
sudo systemctl status kb-rag-watcher
sudo systemctl restart kb-rag-watcher

# Job Scheduler
sudo systemctl status kb-rag-scheduler
sudo systemctl restart kb-rag-scheduler
```

#### Viewing Logs

```bash
# Follow all logs
sudo journalctl -u kb-rag-server -u kb-rag-health -f

# MCP server logs only
sudo journalctl -u kb-rag-server -f

# Last 100 lines
sudo journalctl -u kb-rag-server -n 100

# Since specific time
sudo journalctl -u kb-rag-server --since "1 hour ago"

# With log level filtering
sudo journalctl -u kb-rag-server -p err  # Errors only
sudo journalctl -u kb-rag-server -p warning  # Warnings and above
```

#### Service Status Checks

```bash
# Check if service is running
systemctl is-active kb-rag-server  # active or inactive

# Check if service is enabled (auto-start)
systemctl is-enabled kb-rag-server  # enabled or disabled

# Full status with recent logs
sudo systemctl status kb-rag.target --no-pager

# Resource usage
systemd-cgtop -1 | grep kb-rag
```

#### Auto-Restart Configuration

Services automatically restart on failure with these settings:

- **Restart Policy**: `always` (restart on any exit)
- **Restart Delay**: 10 seconds between attempts
- **Burst Limit**: 3 attempts within 5 minutes
- **Recovery**: After 5 minutes, reset failure counter

View restart history:

```bash
# Check restart count
systemctl show kb-rag-server -p NRestarts

# View service failures
systemctl list-units --failed | grep kb-rag
```

---

### 🔧 MCP Tools

#### `search_kb`

Semantic search over knowledge base.

**Parameters:**
- `query` (required): Search query
- `top_k` (optional): Number of results (1-20, default: 5)
- `product` (optional): Filter by product
- `vendor` (optional): Filter by vendor (auto-classified from filenames)
- `subsystem` (optional): Filter by subsystem (auto-classified from filenames)
- `doc_type` (optional): Filter by document type
- `filter_type` (optional): Filter by file format (pdf, docx, xlsx, pptx, txt, code)
- `version` (optional): Filter by document version

**Returns:** List of chunks with `chunk_id`, `score`, `text`, `source_file`,
`product`, `vendor`, `subsystem`, `doc_type`, `file_type`, `page`, `version`.

#### `list_documents`

List indexed documents with optional filters.

**Parameters:**
- `product` (optional): Filter by product
- `vendor` (optional): Filter by vendor
- `subsystem` (optional): Filter by subsystem
- `doc_type` (optional): Filter by document type
- `filter_type` (optional): Filter by file format

**Returns:** Documents grouped by `doc_type`.

#### `get_chunk`

Retrieve full chunk with surrounding context.

**Parameters:**
- `chunk_id` (required): Chunk ID from search results
- `context_window` (optional): Number of neighbor chunks (0-3, default: 1)

**Returns:** Chunk with context.

#### `kb_stats`

Knowledge base statistics.

**Returns:** Total documents, chunks, breakdown by doc_type and file format.

---

### 🏗️ Architecture

```
Documents (PDF, DOCX, XLSX, PPTX, TXT, code)
    ↓  ingest/ingest.py
Text Extraction → Chunking → Embedding (LM Studio / Ollama)
    ↓
Qdrant (vector store)
    ↓
kb_server/server.py ←→ MCP (stdio or SSE)
    ↓
Claude Code / OpenCode
```

**Components:**

- **Job Management**: SQLite-backed job queue with priority scheduling
- **Worker Pool**: Async worker pool with rate limiting
- **Observability**: Prometheus metrics, structured logging, progress tracking
- **Cache System**: LRU cache with RAM auto-tuning or Redis backend
- **Document Extractors**: Multi-format support (PDF via PyMuPDF/docling)
- **Classifier**: Automatic product and doc_type detection via regex
- **Auto-classification**: Vendor, subsystem, version inference from filenames and paths
- **Cross-encoder reranker**: Lazy-loaded on first reranking query (~10s faster startup)

---

### 👨‍💻 Development

#### Requirements

See `requirements.in` for human-readable dependencies.

#### Running Tests

```bash
pytest tests/ -v

# With coverage
pytest tests/ --cov=kb_server --cov=ingest --cov=observability --cov-branch --cov-report=term-missing

# Coverage with threshold enforcement (90% branch coverage required)
pytest tests/ --cov=kb_server --cov=ingest --cov-branch --cov-fail-under=90

# Specific test file
pytest tests/test_job_system.py -v
```

**Test baseline:** 585 core tests (excluding SSE handler and e2e tests)

#### Code Quality

```bash
# Format code
black kb_server/ ingest/ scripts/ tests/
isort kb_server/ ingest/ scripts/ tests/

# Lint
flake8 kb_server/ ingest/ scripts/ tests/

# Type check
mypy kb_server/ ingest/ scripts/

# Logging audit (ensure all public methods have log calls)
python scripts/logging-audit.py

# English audit (enforce zero Portuguese in source files)
python scripts/docstring-audit.py --check-inline
```

#### Adding Dependencies

```bash
# Edit requirements.in
vim requirements.in

# Compile and install
pip-compile requirements.in
pip-sync requirements.txt
```

---

### 📚 Documentation

**User Guides:**
- [AUTO_INGESTION.md](docs/AUTO_INGESTION.md) - Automatic file watching and ingestion
- [METADATA_OVERRIDES.md](docs/METADATA_OVERRIDES.md) - Override classification with _meta.json
- [VERSION_FILTERING.md](docs/VERSION_FILTERING.md) - Search by document version
- [SEARCH_QUALITY.md](docs/SEARCH_QUALITY.md) - Hybrid search and reranking
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions

**Technical Documentation:**
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture and design
- [OPERATIONS.md](docs/OPERATIONS.md) - Production deployment and operations
- [TESTING.md](docs/TESTING.md) - Testing strategy
- [INDEX.md](docs/INDEX.md) - Documentation index
- [REFERENCE.md](docs/REFERENCE.md) - API reference
- [KUBERNETES.md](docs/KUBERNETES.md) - Kubernetes deployment guide

---

### 📊 Monitoring

KB-RAG provides comprehensive monitoring through Prometheus metrics, health checks, and structured logging.

#### Prometheus Metrics

Metrics are exposed at `http://localhost:8000/metrics` (health server).

**Available Metrics (28 total):**

```bash
# Job Management (4 metrics)
kb_rag_jobs_created_total          # Jobs created counter
kb_rag_jobs_completed_total        # Jobs completed counter
kb_rag_jobs_active                 # Currently active jobs gauge
kb_rag_job_duration_seconds        # Job duration histogram

# File Processing (3 metrics)
kb_rag_files_processed_total      # Files processed counter
kb_rag_files_processing_time_seconds  # File processing histogram
kb_rag_chunks_generated_total     # Chunks generated counter

# Worker Pool (6 metrics)
kb_rag_worker_pool_size            # Worker pool size gauge
kb_rag_worker_pool_queue_size     # Queue size gauge
kb_rag_worker_pool_utilization    # Pool utilization gauge
kb_rag_rate_limiter_tokens        # Available tokens gauge
kb_rag_rate_limiter_waits_total   # Rate limit waits counter
kb_rag_rate_limiter_wait_time_seconds  # Wait time histogram

# API Requests (2 metrics)
kb_rag_api_requests_total         # API requests counter
kb_rag_api_latency_seconds        # API latency histogram

# Cache Performance (5 metrics)
kb_rag_cache_hits_total           # Cache hit counter
kb_rag_cache_misses_total         # Cache miss counter
kb_rag_cache_evictions_total      # Cache eviction counter
kb_rag_cache_size_bytes           # Cache size gauge
kb_rag_cache_entries              # Cache entry count gauge

# Batch Processing (8 metrics)
kb_rag_batch_embeddings_total          # Batch embedding operations
kb_rag_batch_embedding_texts_total     # Texts embedded in batches
kb_rag_batch_embedding_duration_seconds  # Batch embedding duration
kb_rag_batch_upserts_total            # Batch upsert operations
kb_rag_batch_upsert_points_total      # Points upserted in batches
kb_rag_batch_upsert_duration_seconds  # Batch upsert duration
kb_rag_http_pool_connections          # HTTP connection pool size
kb_rag_batch_processing_throughput    # Processing throughput gauge
```

#### Prometheus Configuration

```yaml
# Add to prometheus.yml
scrape_configs:
  - job_name: 'kb-rag'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

Or use the provided configuration:

```bash
# Copy to Prometheus config directory
sudo cp deployment/config/prometheus.yml /etc/prometheus/
sudo cp deployment/config/kb-rag-alerts.yml /etc/prometheus/

# Reload Prometheus
sudo systemctl reload prometheus
```

#### Alerting Rules

11 pre-configured alert rules in `deployment/config/kb-rag-alerts.yml`:

**Health Alerts (Critical):**
- Server down for 2+ minutes
- High error rate (>10 errors/sec for 5 min)
- Embedding service unhealthy (3+ min)
- Vector store unhealthy (3+ min)

**Performance Alerts (Warning):**
- High latency (P95 > 5s for 10 min)
- Low cache hit rate (<50% for 15 min)

**Resource Alerts:**
- High memory usage (>90% for 10 min)
- Low disk space (<10% for 5 min)

**Job Alerts:**
- Jobs stuck (running but no progress for 30 min)
- High job failure rate (>0.1/sec for 10 min)

#### Grafana Dashboard

Import dashboard from `deployment/config/grafana-dashboard.json` (coming soon).

Key panels:
- Service health status
- Request rate and latency
- Cache hit rate and size
- Job queue and throughput
- Resource usage (CPU, memory, disk)
- Error rates

#### Structured Logging

Logs are written in JSON format for easy parsing:

```bash
# View structured logs
sudo journalctl -u kb-rag-server -o json-pretty

# Extract specific fields
sudo journalctl -u kb-rag-server -o json | \
  jq -r 'select(.PRIORITY=="3") | .MESSAGE'  # Errors only

# Search by component
sudo journalctl -u kb-rag-server | grep '"component":"cache"'
```

#### Log Rotation

Automatic log rotation configured via `/etc/logrotate.d/kb-rag`:

- **Frequency**: Daily
- **Retention**: 14 days
- **Compression**: gzip (delayed 1 day)
- **Max size**: 100MB per file
- **Access logs**: 7 days, 500MB max

Manual rotation:

```bash
# Force rotation
sudo logrotate -f /etc/logrotate.d/kb-rag

# Test configuration
sudo logrotate -d /etc/logrotate.d/kb-rag
```

---

### 🛠️ Operations

#### Backup and Restore

**Create Backup:**

```bash
# Auto-named backup
./deployment/scripts/backup.sh

# Custom path
./deployment/scripts/backup.sh /backups/kb-rag-20260515.tar.gz
```

Backup includes:
- SQLite databases (job metadata, file registry)
- Configuration files
- Recent logs (last 7 days)

**Restore from Backup:**

```bash
sudo ./deployment/scripts/restore.sh /path/to/backup.tar.gz
```

Safety features:
- Automatic pre-restore backup
- Service stop/start orchestration
- Permission restoration
- Health verification

**Scheduled Backups:**

```bash
# Add to /etc/cron.daily/kb-rag-backup
#!/bin/bash
/opt/kb-rag/deployment/scripts/backup.sh \
  /backups/kb-rag-$(date +%Y%m%d).tar.gz

# Cleanup old backups (keep 30 days)
find /backups -name "kb-rag-*.tar.gz" -mtime +30 -delete
```

#### Updates

**Update to Latest Version:**

```bash
sudo ./deployment/scripts/update.sh
```

Update process:
1. Create pre-update backup
2. Stop services
3. Git pull latest changes
4. Update dependencies
5. Update systemd services
6. Restart services
7. Verify health
8. Rollback on failure (automatic)

**Update to Specific Version:**

```bash
sudo ./deployment/scripts/update.sh v1.3
```

#### Maintenance Tasks

**Clear Old Jobs:**

```bash
# Clear completed jobs older than 30 days
python3 -m ingest.cli job clean --days 30

# Dry run (preview only)
python3 -m ingest.cli job clean --days 30 --dry-run
```

**Rebuild Index:**

```bash
# Re-ingest all documents (slow)
python3 -m ingest.ingest --docs /path/to/docs --clean
```

**Cache Management:**

```bash
# Clear cache (restart service)
sudo systemctl restart kb-rag-server

# Check cache stats
curl http://localhost:8000/health/detailed | jq '.components.cache'
```

#### Performance Tuning

**Batch Processing:**

Tune via environment variables in `/opt/kb-rag/config/kb-rag.env`:

```bash
# Embedding batch size (25-64 recommended)
EMBED_BATCH_SIZE=32

# File processing batch (50-100 recommended)
FILE_BATCH_SIZE=50

# Qdrant batch upsert (80-200 recommended)
QDRANT_BATCH_SIZE=100

# HTTP connections (20-50 recommended)
HTTP_POOL_CONNECTIONS=20

# Concurrent uploads (1-5 recommended)
MAX_CONCURRENT_UPLOADS=3
```

**Worker Pool:**

```bash
# Increase workers for faster ingestion
WORKER_POOL_SIZE=8  # Default: 4

# Adjust rate limit (requests/sec per worker)
WORKER_RATE_LIMIT=20  # Default: 10
```

**Cache:**

```bash
# Increase cache size
CACHE_MAX_SIZE_MB=1024  # Default: auto (10% RAM)

# Use Redis for distributed cache
CACHE_BACKEND=redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### Troubleshooting

**Service Won't Start:**

```bash
# Check service status
sudo systemctl status kb-rag-server

# View recent logs
sudo journalctl -u kb-rag-server -n 100

# Check configuration
sudo cat /opt/kb-rag/config/kb-rag.env | grep -v "^#"

# Verify dependencies
/opt/kb-rag/venv/bin/python3 -m pip check
```

**High Memory Usage:**

```bash
# Check current usage
systemctl show kb-rag-server -p MemoryCurrent

# Reduce cache size
sudo nano /opt/kb-rag/config/kb-rag.env
# Set: CACHE_MAX_SIZE_MB=256

sudo systemctl restart kb-rag-server
```

**Slow Performance:**

```bash
# Check component health and latency
curl http://localhost:8000/health/detailed | jq

# Monitor resource usage
systemd-cgtop | grep kb-rag

# Check cache hit rate (should be >80%)
curl http://localhost:8000/health/detailed | \
  jq '.components.cache.details.hit_rate'
```

**For complete troubleshooting guide with 40+ scenarios, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).**

---

### 🛠️ Troubleshooting

> **📖 See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for the complete troubleshooting guide with 40+ scenarios, diagnostic commands, and solutions.**

**Quick Fixes:**

**Embedding API not responding:**
```bash
# Check LM Studio is running and model loaded
curl http://localhost:1234/v1/models

# Check Ollama
curl http://localhost:11434/api/tags
```

**Qdrant connection error:**
```bash
# Check Qdrant is running
docker ps | grep qdrant
curl http://localhost:6333/healthz
```

**No search results:**
- Check `SCORE_THRESHOLD` (lower if too strict)
- Verify documents are indexed: `kb-rag status` or `python ingest/ingest.py --status`
- Check query is in correct language

**Slow ingestion:**
- Reduce `--workers` if CPU-bound
- Check embedding API is not overloaded
- Consider using GPU for LM Studio

---

### 📝 License

MIT License

Copyright (c) 2026 KB-RAG MCP Server Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

### 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

<a name="português-brasil"></a>
## 🇧🇷 Português (Brasil)

Servidor MCP (Model Context Protocol) pronto para produção para busca
semântica em bases de conhecimento locais. Suporta PDF, DOCX, XLSX, PPTX,
TXT, Markdown e código-fonte (~7 GB+). Compatível com **Claude Code**,
**OpenCode** e qualquer cliente MCP.

### ✨ Funcionalidades

- 🔍 **Busca semântica** em documentação técnica
- 📚 **Suporte multi-formato**: PDF, DOCX, XLSX, PPTX, TXT, código
- 🎯 **Classificação inteligente**: detecção automática de produto e tipo de documento
- 🚀 **Pronto para produção**: gerenciamento de jobs, pool de workers, observabilidade
- 💾 **Ingestão incremental**: processa apenas arquivos novos/modificados
- 📊 **Métricas**: métricas compatíveis com Prometheus para monitoramento
- 🔄 **Sistema de cache**: LRU com auto-ajuste de RAM ou Redis
- 🔧 **Multi-backend**: LM Studio, Ollama ou APIs compatíveis com OpenAI
- 👁️ **Ingestão automática**: Monitoramento de arquivos para atualizações automáticas (NOVO)
- 🏷️ **Filtragem por versão**: Busca por versão de documento (22.3, CE 24.4) (NOVO)
- 📝 **Sobrescrever metadados**: Controle de classificação por diretório/arquivo (NOVO)

---

### 📋 Índice

- [Início Rápido](#início-rápido)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Ferramentas MCP](#ferramentas-mcp)
- [Arquitetura](#arquitetura)
- [Desenvolvimento](#desenvolvimento)
- [Documentação](#documentação)
- [Licença](#licença)

---

### 🚀 Início Rápido

#### Opção 1: Local Machine (Windows + WSL2 + LM Studio)

```bash
# 1. Inicie o LM Studio no Windows com nomic-embed-text-v1.5
# 2. No WSL2:
git clone https://github.com/seususername/kb-rag-mcp ~/kb-rag-mcp
cd ~/kb-rag-mcp
bash scripts/setup.sh local

# 3. Ingira documentos
source .venv/bin/activate
python ingest/ingest.py --docs /mnt/d/seus-docs

# 4. Verificação de saúde
python scripts/health_check.py

# 5. Configure o Claude Code (copie config/mcp-clients.json → bloco local)
```

#### Opção 2: Servidor Linux (Ollama)

```bash
# No Ubuntu 24.04:
git clone https://github.com/seususername/kb-rag-mcp /opt/kb-rag-mcp
cd /opt/kb-rag-mcp
bash scripts/setup.sh lxc

# Ingira documentos
source .venv/bin/activate
python ingest/ingest.py --docs /opt/docs --workers 4

# Instale como serviço systemd
sudo cp scripts/kb-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kb-mcp
```

---

### 💻 Instalação

#### Pré-requisitos

- Python 3.11+
- Docker (para Qdrant) ou Qdrant embedded
- LM Studio / Ollama / API de embedding compatível com OpenAI
- 8+ GB RAM (16+ GB recomendado)

#### Instalação Passo a Passo

**1. Clone o repositório**

```bash
git clone https://github.com/seususername/kb-rag-mcp
cd kb-rag-mcp
```

**2. Execute o script de setup**

```bash
# Para local machine (LM Studio):
bash scripts/setup.sh local

# Para servidor Linux (Ollama):
bash scripts/setup.sh lxc

# Setup manual:
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure o ambiente**

```bash
# Copie a config apropriada
cp config/.env.local .env  # ou .env.lxc

# Edite .env com suas configurações
vim .env
```

**4. Inicie o Qdrant**

```bash
docker-compose up -d
```

**5. Verifique a instalação**

```bash
source .venv/bin/activate
python scripts/health_check.py
```

---

### ⚙️ Configuração

#### Variáveis de Ambiente

Crie o arquivo `.env` na raiz do projeto:

```bash
# Backend de Embedding
EMBED_BACKEND=openai-compat  # lmstudio-sdk, lmstudio-rest, openai-compat, ollama
EMBED_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
LMS_BASE_URL=http://localhost:1234  # URL do LM Studio (sem /v1)
OLLAMA_HOST=http://localhost:11434

# Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_PATH=  # Deixe vazio para Docker, defina caminho para embedded
QDRANT_COLLECTION=kb_docs

# Configurações de Busca
SCORE_THRESHOLD=0.35  # Score mínimo de relevância (0.0-1.0)
DEFAULT_TOP_K=5       # Resultados padrão de busca

# Transporte MCP
MCP_TRANSPORT=stdio   # stdio ou sse
SSE_HOST=0.0.0.0      # Para modo SSE
SSE_PORT=8765

# Configurações de Cache
CACHE_BACKEND=lru     # lru ou redis
CACHE_MAX_SIZE_MB=512 # Tamanho do cache LRU (auto se não definido)
CACHE_TTL=3600        # TTL do cache em segundos
```

#### Configuração do Cliente MCP

**Claude Code (Windows + WSL2)**

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "wsl.exe",
      "args": [
        "-d", "Ubuntu-24.04",
        "--",
        "/home/SEU_USUARIO/kb-rag-mcp/.venv/bin/python",
        "/home/SEU_USUARIO/kb-rag-mcp/server/server.py"
      ]
    }
  }
}
```

**Claude Code (modo SSE)**

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://<LXC_SERVER_HOST>:8765/sse"
    }
  }
}
```

---

### 📖 Uso

#### Ingestão de Documentos

```bash
source .venv/bin/activate

# Ingere diretório inteiro (incremental)
python ingest/ingest.py --docs /caminho/para/docs

# Com produto explícito
python ingest/ingest.py --docs /caminho/para/docs --product MeuProduto

# Arquivo único
python ingest/ingest.py --file /caminho/para/documento.pdf

# Limpa e reingere tudo
python ingest/ingest.py --docs /caminho/para/docs --clean

# Mais workers (use com GPU)
python ingest/ingest.py --docs /caminho/para/docs --workers 4

# Verifica status da ingestão
python ingest/ingest.py --status
python ingest/ingest.py --status --list    # Lista todos os arquivos
python ingest/ingest.py --status --errors  # Somente erros
```

#### Estrutura de Diretórios Recomendada

```
docs/
├── produto-a/
│   ├── referencia-api.pdf
│   ├── primeiros-passos.docx
│   └── exemplos/
│       └── exemplo.py
├── produto-b/
│   ├── manual.pdf
│   └── config.xlsx
└── geral/
    └── arquitetura.pptx
```

O produto é automaticamente inferido pelo nome do diretório.

---

### 🔧 Ferramentas MCP

#### `search_kb`

Busca semântica na base de conhecimento.

**Parâmetros:**
- `query` (obrigatório): Consulta de busca
- `top_k` (opcional): Número de resultados (1-20, padrão: 5)
- `product` (opcional): Filtrar por produto
- `doc_type` (opcional): Filtrar por tipo de documento
- `filter_type` (opcional): Filtrar por formato de arquivo (pdf, docx, xlsx, pptx, txt, code)

**Retorna:** Lista de chunks com `chunk_id`, `score`, `text`, `source_file`,
`product`, `doc_type`, `file_type`, `page`.

#### `list_documents`

Lista documentos indexados com filtros opcionais.

**Parâmetros:**
- `product` (opcional): Filtrar por produto
- `doc_type` (opcional): Filtrar por tipo de documento
- `filter_type` (opcional): Filtrar por formato de arquivo

**Retorna:** Documentos agrupados por `doc_type`.

#### `get_chunk`

Recupera chunk completo com contexto ao redor.

**Parâmetros:**
- `chunk_id` (obrigatório): ID do chunk dos resultados de busca
- `context_window` (opcional): Número de chunks vizinhos (0-3, padrão: 1)

**Retorna:** Chunk com contexto.

#### `kb_stats`

Estatísticas da base de conhecimento.

**Retorna:** Total de documentos, chunks, breakdown por doc_type e formato de arquivo.

---

### 🏗️ Arquitetura

```
Documentos (PDF, DOCX, XLSX, PPTX, TXT, código)
    ↓  ingest/ingest.py
Extração de Texto → Chunking → Embedding (LM Studio / Ollama)
    ↓
Qdrant (vector store)
    ↓
server/server.py ←→ MCP (stdio ou SSE)
    ↓
Claude Code / OpenCode
```

**Componentes:**

- **Gerenciamento de Jobs** (FASE 2): Fila de jobs baseada em SQLite com agendamento por prioridade
- **Pool de Workers** (FASE 3): Pool de workers assíncronos com limitação de taxa
- **Observabilidade** (FASE 4): Métricas Prometheus, logging estruturado, rastreamento de progresso
- **Sistema de Cache** (FASE 5): Cache LRU com auto-ajuste de RAM ou backend Redis
- **Extratores de Documentos**: Suporte multi-formato (PDF via PyMuPDF/docling)
- **Classificador**: Detecção automática de produto e doc_type via regex

---

### 📚 Documentação

- [TESTING.md](docs/TESTING.md) - Estratégia de testes
- [FASE1_COMPLETION.md](docs/FASE1_COMPLETION.md) - Fundação e infraestrutura de testes
- [FASE2_COMPLETION.md](docs/FASE2_COMPLETION.md) - Sistema de gerenciamento de jobs
- [FASE3_COMPLETION.md](docs/FASE3_COMPLETION.md) - Pool de workers e limitador de taxa
- [FASE4_COMPLETION.md](docs/FASE4_COMPLETION.md) - Observabilidade e métricas
- [FASE5_COMPLETION.md](docs/FASE5_COMPLETION.md) - Sistema de cache
- [INSTRUCTIONS.md](docs/INSTRUCTIONS.md) - Instruções técnicas detalhadas
- [PLAN.md](docs/PLAN.md) - Roadmap de implementação

---

### 🛠️ Solução de Problemas

**API de embedding não responde:**
```bash
# Verifique se o LM Studio está rodando e o modelo carregado
curl http://localhost:1234/v1/models

# Verifique o Ollama
curl http://localhost:11434/api/tags
```

**Erro de conexão com Qdrant:**
```bash
# Verifique se o Qdrant está rodando
docker ps | grep qdrant
curl http://localhost:6333/healthz
```

**Sem resultados de busca:**
- Verifique `SCORE_THRESHOLD` (diminua se muito rigoroso)
- Verifique se documentos estão indexados: `python ingest/ingest.py --status`
- Verifique se a consulta está no idioma correto

**Ingestão lenta:**
- Reduza `--workers` se limitado por CPU
- Verifique se a API de embedding não está sobrecarregada
- Considere usar GPU para LM Studio

---

### 📝 Licença

[Sua Licença Aqui]

---

### 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia [CONTRIBUTING.md](CONTRIBUTING.md) primeiro.
