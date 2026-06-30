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
- ✅ **1541+ tests** — Full mock isolation, no external deps needed
- ✅ **CI/CD pipeline** — 90% branch coverage gate, logging audit, Helm lint
- ✅ **Auto-classification** — Vendor, product, subsystem, version inference
- ✅ **Kubernetes/Helm** — Helm chart for multi-replica deployment
- 📊 **Real-time monitoring** — Grafana + Prometheus with 6-tab dashboard
- 🔄 **Cache system** — LRU with RAM auto-tuning or Redis (80%+ hit rate)
- 🔧 **Multi-backend** — LM Studio, Ollama, or OpenAI-compatible APIs
- 🛠️ **Operations** — Automated install, backup/restore, updates
- 🛡️ **Auth system** — API key authentication with scope management
- ⚙️ **Config API** — REST CRUD for server configuration
- 🔄 **Streamable HTTP** — Alternative MCP transport with session management
- 🛡️ **Rate limiting** — Per-subject token bucket with burst protection
- ⚡ **Provider resilience** — Circuit breaker + budget system with auto-fallback
- 🖥️ **Admin SPA** — Full admin panel at `/admin/` with Alpine.js frontend for managing config, documents, schedules, users, API keys, and monitoring
- ⏰ **Ingestion Schedule** — CRON-based schedule management via UI and REST API; background scheduler loop checks every 30s
- 🏷️ **Document Tags** — Edit per-document tags via the admin panel; trigger re-ingest with tag changes
- 📊 **Analytics Dashboard** — Query logging visualization and usage statistics in the admin panel

---

### 🚀 Quickstart

Choose your deployment mode:

| Mode | Best for | Get started |
|------|----------|-------------|
| Docker Compose | Local dev / small teams | `docker compose up -d` → [docs/INSTRUCTIONS.md → Docker Compose](docs/INSTRUCTIONS.md#docker-compose) |
| Helm (Kubernetes) | Production clusters | `helm install` → [docs/KUBERNETES.md](docs/KUBERNETES.md) |
| Systemd | Bare metal / VMs | `sudo ./deployment/scripts/install.sh` → [docs/INSTRUCTIONS.md → Systemd](docs/INSTRUCTIONS.md#systemd) |
| Manual (Source) | Development / customization | `python -m kb_server.server` → [docs/INSTRUCTIONS.md → Manual](docs/INSTRUCTIONS.md#manual) |

**Prerequisites:** Python 3.11+, Docker (for Qdrant), and an embedding backend (LM Studio, Ollama, or OpenAI-compatible).

**Next:** [docs/INDEX.md](docs/INDEX.md) — full documentation index by deployment mode.

---

### 📚 Detailed Documentation

| Topic | Reference |
|-------|-----------|
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Operations (daily ops, backup, monitoring) | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Troubleshooting | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Setup instructions | [docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md) |
| Technical reference | [docs/REFERENCE.md](docs/REFERENCE.md) |
| Kubernetes deployment | [docs/KUBERNETES.md](docs/KUBERNETES.md) |
| Configuration (env vars) | [docs/INSTRUCTIONS.md → §4](docs/INSTRUCTIONS.md#4-vari%C3%A1veis-de-ambiente) |
| MCP tools reference | [docs/INSTRUCTIONS.md → §5](docs/INSTRUCTIONS.md#5-mcp-tools-expostas) |
| Ingestion pipeline | [docs/INSTRUCTIONS.md → §7](docs/INSTRUCTIONS.md#7-pipeline-de-ingest%C3%A3o) |
| MCP client setup (Claude, OpenCode) | [docs/INSTRUCTIONS.md → §8](docs/INSTRUCTIONS.md#8-configura%C3%A7%C3%A3o-dos-clientes-mcp) |
| Health checks | [docs/OPERATIONS.md → Health Dashboard](docs/OPERATIONS.md#health-dashboard) |
| Reclassification | [docs/OPERATIONS.md → Reclassification](docs/OPERATIONS.md#reclassification-management) |
| Search quality | [docs/SEARCH_QUALITY.md](docs/SEARCH_QUALITY.md) |
| Version filtering | [docs/VERSION_FILTERING.md](docs/VERSION_FILTERING.md) |
| Metadata overrides | [docs/METADATA_OVERRIDES.md](docs/METADATA_OVERRIDES.md) |
| Auto-ingestion (file watcher) | [docs/AUTO_INGESTION.md](docs/AUTO_INGESTION.md) |
| RAG evaluation | [docs/RAG_EVALUATION.md](docs/RAG_EVALUATION.md) |
| Web UI | [docs/WEB_UI.md](docs/WEB_UI.md) |
| Security | [docs/SECURITY.md](docs/SECURITY.md) |
| API Reference | [docs/API.md](docs/API.md) | REST API documentation for all endpoints |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

### 👨‍💻 Development

```bash
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
# Start Qdrant: docker compose up -d qdrant
# Run: python -m kb_server.server
```

See [docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md) for full setup details.

### 📝 License

This project is licensed under the [MIT License](LICENSE).

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

# Tag management (Phase 51)
kb-rag tags list
kb-rag tags list --product MyApp
kb-rag tags update --add "legacy,needs-review" --filter "product=OldApp" --dry-run
kb-rag tags reingest --filter "type=legacy" --yes
kb-rag tags delete-tag "obsolete" --dry-run

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

#### Reclassifying Documents

When classification rules improve (e.g., better vendor detection patterns), you can update metadata for already-ingested documents without re-processing or re-embedding:

##### Basic Usage

```bash
# Reclassify specific files
kb-ingest reclassify "docs/OpenText/*.pdf"

# Reclassify by metadata filter
kb-ingest reclassify "**/*.pdf" --filter 'vendor=""'

# Combine pattern and filter
kb-ingest reclassify "docs/OT*.pdf" --filter 'subsystem=""'

# Skip confirmation (automation)
kb-ingest reclassify "docs/**/*" --yes
```

##### Verification Workflow

Before reclassifying, verify what would change:

```bash
# Check for mismatches
kb-ingest reclassify verify "docs/**/*.pdf"

# Shows:
# - Documents with metadata mismatches
# - Current vs. expected values
# - Per-document detail
```

After reclassification, verify the changes were applied:

```bash
kb-ingest reclassify verify "docs/**/*.pdf"
# Should show: "All documents match expected classifications"
```

##### Rollback

If reclassification produces unexpected results, rollback to previous metadata:

```bash
# List backup sessions
kb-ingest reclassify sessions

# Rollback entire session
kb-ingest reclassify rollback --session 2026-05-26T15-30-00

# Selective rollback (pattern + timestamp)
kb-ingest reclassify rollback "docs/OT*.pdf" --before 2026-05-26T16-00-00
```

Backups are kept for 30 days by default (configurable via `RECLASSIFY_BACKUP_RETENTION_DAYS`).

##### How It Works

1. **Detect Changes:** Runs `classify()` on matched documents, compares to current Qdrant metadata
2. **Preview:** Shows aggregated summary by field (e.g., "vendor: 47 docs ('' → 'OpenText')")
3. **Backup:** Writes old metadata to SQLite (`data/registry.db`) for rollback
4. **Update:** Updates Qdrant payload fields in-place (preserves vectors)
5. **Audit:** Logs changes to `reclassify_history` table for tracking

##### Options

| Flag | Description |
|------|-------------|
| `--collection <name>` | Target specific Qdrant collection |
| `--filter <expr>` | Metadata filter (e.g., `vendor=""`) |
| `--yes` / `-y` | Skip confirmation prompt |
| `--allow-missing` | Process documents even if source file missing |
| `--include-custom` | Update custom fields beyond classification fields |
| `--no-progress` | Disable progress bar (for scripting) |

##### Safety Features

- **Interactive confirmation:** Shows preview before making changes (use `--yes` to skip)
- **Automatic backup:** Old metadata saved to SQLite before updates
- **Session tracking:** All backups linked to session timestamp for full rollback
- **Audit log:** All changes logged to `reclassify_history` table
- **30-day retention:** Backups auto-cleaned after 30 days (configurable)

##### Common Workflows

**Scenario 1: Improved vendor detection**

Phase 11 shipped with basic vendor inference, leaving many documents with empty `vendor` field. After improving `VENDOR_MAP` patterns:

```bash
# Verify what would change
kb-ingest reclassify verify "**/*" --filter 'vendor=""'

# Shows 47 documents would change vendor → "OpenText"

# Apply changes
kb-ingest reclassify "**/*" --filter 'vendor=""' --yes
```

**Scenario 2: Fixing misclassified documents**

Some PDFs were incorrectly classified as `doc_type="overview"` when they should be `"admin_guide"`:

```bash
# Verify current state
kb-ingest reclassify verify "docs/admin/*.pdf"

# Reclassify (after updating doc_type rules in classifier.py)
kb-ingest reclassify "docs/admin/*.pdf"

# Verify fixed
kb-ingest reclassify verify "docs/admin/*.pdf"
```

**Scenario 3: Rollback after classification regression**

Classification rule change introduced incorrect subsystem values:

```bash
# Check recent sessions
kb-ingest reclassify sessions

# Shows session 2026-05-26T15-30-00 with 50 docs changed

# Rollback entire session
kb-ingest reclassify rollback --session 2026-05-26T15-30-00
```

##### Troubleshooting

**"No classification changes detected"**

Possible causes:
- Classification rules haven't changed since last ingest
- Pattern doesn't match any documents in Qdrant
- Metadata filter too restrictive

Solution: Run `verify` to see current vs. expected values

**"Source file not found on disk"**

By default, reclassify skips documents where source file is missing (source file needed to run `classify()`). If files moved or you want to reclassify using Qdrant metadata only:

```bash
kb-ingest reclassify "**/*" --allow-missing
```

**Rollback session not found**

Sessions older than 30 days are auto-cleaned. Adjust retention:

```bash
export RECLASSIFY_BACKUP_RETENTION_DAYS=90
kb-ingest reclassify "**/*"
```

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
- `module` (optional): Filter by module
- `collection` (optional): Target specific Qdrant collection
- `kb_ids` (optional): Specific KB document IDs to search
- `hybrid` (optional): Enable hybrid search (dense + sparse) (default: true)
- `rerank` (optional): Enable cross-encoder reranking (default: false)
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
- `module` (optional): Filter by module
- `collection` (optional): Target specific Qdrant collection
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

#### `list_collections`

List available Qdrant collections.

**Parameters:**
- `detail` (optional): Include collection details and stats (default: false)

**Returns:** List of collection names with optional metadata.

#### `invalidate_retrieval_cache`

Clear the retrieval cache for a specific collection or all collections.

**Parameters:**
- `collection` (optional): Collection to invalidate (default: all collections)

**Returns:** Confirmation of cache invalidation.

#### `kb_graph_tools`

Knowledge graph integration tools for exploring document relationships.

See [docs/SEARCH_QUALITY.md](docs/SEARCH_QUALITY.md) for full documentation.

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

**Test baseline:** 1541 core tests (excluding SSE handler and e2e tests)

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
- [OPERATIONS.md](docs/OPERATIONS.md) - Production deployment, operations, and **[health dashboard](docs/OPERATIONS.md#health-dashboard)**
- [TESTING.md](docs/TESTING.md) - Testing strategy
- [INDEX.md](docs/INDEX.md) - Documentation index
- [REFERENCE.md](docs/REFERENCE.md) - API reference
- [KUBERNETES.md](docs/KUBERNETES.md) - Kubernetes deployment guide

---

### 📊 Monitoring

KB-RAG provides comprehensive monitoring through Prometheus metrics, health checks, and structured logging.

#### Prometheus Metrics

Metrics are exposed at `http://localhost:8000/metrics` (health server).

**Available Metrics (42 total):**

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

# Rate Limiting (4 metrics)
kb_rag_rate_limit_tokens_available   # Available tokens per subject
kb_rag_rate_limit_tokens_refilled    # Tokens refilled counter
kb_rag_rate_limit_requests_burst     # Burst request counter
kb_rag_rate_limit_requests_throttled # Throttled request counter

# Provider Resilience (6 metrics)
kb_rag_provider_requests_total       # Provider request counter
kb_rag_provider_errors_total         # Provider error counter
kb_rag_provider_circuit_state        # Circuit breaker state gauge
kb_rag_provider_fallbacks_total      # Fallback provider counter
kb_rag_provider_budget_remaining     # Provider budget remaining gauge
kb_rag_provider_skipped_total        # Skipped requests due to budget/circuit

# Retrieval Cache (4 metrics)
kb_rag_retrieval_cache_hits_total    # Retrieval cache hit counter
kb_rag_retrieval_cache_misses_total  # Retrieval cache miss counter
kb_rag_retrieval_cache_entries       # Retrieval cache entry count gauge
kb_rag_retrieval_cache_size_bytes    # Retrieval cache size gauge
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
sudo ./deployment/scripts/update.sh v0.1.3
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
- ✅ **1284+ testes** — Isolamento completo com mocks, sem dependências externas
- ✅ **Pipeline CI/CD** — Gate de cobertura (72%), lint Helm, auditoria de inglês
- 🎯 **Classificação automática** — Vendor, produto, subsistema, versão
- 📊 **Monitoramento em tempo real** — Grafana + Prometheus (6 abas)
- 🔧 **Multi-backend** — LM Studio, Ollama ou APIs compatíveis com OpenAI
- 🚀 **Implantação flexível** — Docker Compose, Helm (Kubernetes), systemd, manual

---

### 🚀 Início Rápido

Escolha seu modo de implantação:

| Modo | Ideal para | Comece aqui |
|------|-----------|-------------|
| Docker Compose | Desenvolvimento local / equipes pequenas | `docker compose up -d` → [docs/INSTRUCTIONS.md → Docker Compose](docs/INSTRUCTIONS.md#docker-compose) |
| Helm (Kubernetes) | Clusters de produção | `helm install` → [docs/KUBERNETES.md](docs/KUBERNETES.md) |
| Systemd | Servidores bare metal / VMs | `sudo ./deployment/scripts/install.sh` → [docs/INSTRUCTIONS.md → Systemd](docs/INSTRUCTIONS.md#systemd) |
| Manual (Source) | Desenvolvimento / customização | `python -m kb_server.server` → [docs/INSTRUCTIONS.md → Manual](docs/INSTRUCTIONS.md#manual) |

**Pré-requisitos:** Python 3.11+, Docker (para Qdrant), backend de embedding (LM Studio, Ollama ou OpenAI).

**Documentação completa por modo de implantação:** [docs/INDEX.md](docs/INDEX.md)

---

### 📚 Documentação Detalhada

| Tópico | Documento |
|--------|-----------|
| Arquitetura | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Operações (backup, monitoramento) | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Solução de problemas | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Instruções técnicas | [docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md) |
| Referência técnica | [docs/REFERENCE.md](docs/REFERENCE.md) |
| Implantação Kubernetes | [docs/KUBERNETES.md](docs/KUBERNETES.md) |
| Qualidade de busca | [docs/SEARCH_QUALITY.md](docs/SEARCH_QUALITY.md) |
| Filtragem por versão | [docs/VERSION_FILTERING.md](docs/VERSION_FILTERING.md) |
| Web UI | [docs/WEB_UI.md](docs/WEB_UI.md) |
| Segurança | [docs/SECURITY.md](docs/SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

### 📝 Licença

Distribuído sob licença MIT.
