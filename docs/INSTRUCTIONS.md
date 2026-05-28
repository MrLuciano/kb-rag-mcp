# KB RAG MCP Server — Project Instructions

> Reference document for project evolution via LLM-based code generation.
> Describes current architecture, technical decisions, interface contracts, and improvement directions.

---

## Common

This technical reference covers architecture, environment, ingestion pipeline, and MCP tool configuration.
Content applies across all deployment modes unless noted.

For mode-specific instructions:

- **Docker Compose** → [↓ Docker Compose](#docker-compose)
- **Helm (Kubernetes)** → [↓ Helm](#helm)
- **Systemd (Bare Metal)** → [↓ Systemd](#systemd)
- **Manual (Source)** → [↓ Manual](#manual)

---

## 1. Overview

MCP (Model Context Protocol) server that exposes semantic search over a local knowledge base
of technical documentation and product manuals.

The server is consumed by **Claude Code** and **OpenCode** via the MCP protocol, allowing the
LLM to automatically retrieve relevant documentation snippets during development tasks.

### Data Flow

```
Local documents (PDF, DOCX, XLSX, PPTX, TXT, legacy formats, ZIP, code)
    │
    ▼  ingest/ingest.py
Text extraction  →  Chunking  →  Embedding (LM Studio / Ollama)
    │
    ▼
Qdrant (local vector store, Docker)
    │
    ▼  kb_server/server.py  [MCP protocol]
Claude Code / OpenCode
```

---

## 2. Runtime Environment

### Local Machine (primary)
- **Hardware:** Local machine with GPU or iGPU
- **OS:** Windows 11 Pro
- **Embedding:** LM Studio running on native Windows with Vulkan acceleration
- **MCP Server:** Python in WSL2 (Ubuntu 24.04)
- **Vector store:** Qdrant in Docker on WSL2
- **Access:** LM Studio accessible via `http://<LM_STUDIO_HOST>:1234` (fixed IP on local network)
- **MCP Transport:** stdio via `wsl.exe` invoked by Claude Code on Windows

### LXC Server (secondary / always-on)
- **Hardware:** LXC Ubuntu 24.04, 6 vCPU, 8–12 GB RAM, CPU only
- **Embedding:** Local Ollama (`nomic-embed-text`)
- **MCP Transport:** SSE at `http://<ip-lxc>:8765/sse`
- **Service:** systemd (`kb-mcp.service`)

---

## 3. File Structure

```
kb-rag-mcp/
├── kb_server/
│   ├── server.py          # MCP entrypoint — registers tools, routes calls
│   ├── embed_client.py    # Embedding abstraction (multi-backend)
│   ├── vector_store.py    # Qdrant abstraction (search, upsert, list, stats)
│   ├── collections/       # Multi-collection routing (Phase 15)
│   │   ├── manager.py     # CollectionManager — CRUD for Qdrant collections
│   │   └── router.py      # CollectionRouter — resolve/ensure by parameter
│   ├── cache/             # LRU cache + optional Redis
│   ├── retrieval/         # Hybrid search (BM25+dense RRF) + reranker
│   ├── ui/                # FastAPI+HTMX Web UI
│   └── telemetry/         # SQLite query logger
├── ingest/
│   ├── ingest.py          # Ingestion pipeline — main CLI
│   ├── classifier.py      # Product/doc_type inference via regex
│   ├── registry.py        # State control (SQLite) — prevents re-ingestion
│   ├── parsers/
│   │   ├── legacy_office.py  # .doc, .xls, .ppt, .odt, .ods, .odp, .wpd
│   │   └── zip_handler.py    # Recursive ZIP extraction
│   ├── job/               # SQLite job system with priorities
│   ├── worker/            # Async pool + token bucket rate limiter
│   ├── validation/        # Format, size, content validators
│   └── watcher/           # Watchdog file watcher for auto-ingestion
├── qa/
│   ├── run_qa.py          # QA evaluation pipeline
│   ├── metrics.py         # Hit rate, MRR, p50_score
│   └── queries.json       # Query evaluation dataset
├── observability/
│   └── metrics.py         # 28 Prometheus metrics (kb_* prefix)
├── scripts/
│   ├── migrate/           # Migration tools (Phase 1.5)
│   │   ├── export.py      # Exports Qdrant snapshot + sanitized env
│   │   ├── import_.py     # Imports with SHA256 validation
│   │   └── validate.py    # Validates SHA256 manifest
│   ├── kb-migrate.sh      # Shell wrapper: export/import/validate
│   ├── setup.sh           # Dependency installation by profile
│   ├── health_check.py    # Tests embedding + Qdrant + end-to-end search
│   └── start-kb-rag.ps1   # WSL2 autostart on Windows (PowerShell)
├── deployment/
│   ├── systemd/           # systemd units for bare-metal
│   ├── config/
│   │   ├── grafana-dashboard.json          # 18-panel Grafana dashboard
│   │   └── grafana-provisioning/           # Datasource + dashboard YAML
│   └── helm/kb-rag-mcp/   # Kubernetes Helm chart (Phase 15)
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/     # Deployment, StatefulSet, HPA, Services, ConfigMap
├── config/
│   ├── .env.local         # Environment variables for local machine
│   ├── .env.lxc           # Environment variables for LXC Server
│   └── mcp-clients.json   # Ready-to-use configs for Claude Code and OpenCode
├── docs/
│   ├── REFERENCE.md       # Main technical reference
│   ├── INSTRUCTIONS.md    # This file (English)
│   ├── INSTRUCTIONS.pt-BR.md  # This file (Portuguese)
│   ├── LEGACY_FORMATS.md  # Legacy formats and ZIP extraction rules
│   └── ...
├── data/
│   └── registry.db        # SQLite — auto-generated on first ingestion
├── docker-compose.yml     # Qdrant
├── requirements.txt
└── .env                   # Active copy of .env.local or .env.lxc
```

---

## 4. Environment Variables

All read via `.env` at the project root. `load_dotenv` is called **before any import**
that reads `os.getenv()` — a critical pattern maintained in all entrypoints.

| Variable | Default | Description |
|---|---|---|
| `EMBED_BACKEND` | `openai-compat` | Embedding backend: `lmstudio-sdk`, `lmstudio-rest`, `openai-compat`, `ollama` |
| `EMBED_MODEL` | `text-embedding-nomic-embed-text-v1.5-embedding` | Exact model name as listed by the server |
| `LMS_BASE_URL` | `http://localhost:1234` | LM Studio base URL — **without** path (`/v1` or `/api/v0` are added automatically per backend) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama URL |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant REST port |
| `QDRANT_PATH` | _(empty)_ | If set, uses Qdrant embedded (no Docker) |
| `QDRANT_COLLECTION` | `kb_docs` | Qdrant collection name |
| `SCORE_THRESHOLD` | `0.35` | Minimum relevance score (0.0–1.0) to return results |
| `MCP_TRANSPORT` | `stdio` | `stdio` (local Claude Code) or `sse` (URL access) |
| `SSE_HOST` | `0.0.0.0` | Bind address for SSE mode |
| `SSE_PORT` | `8765` | Port for SSE mode |
| `DEFAULT_TOP_K` | `5` | Default result count per search |
| `LOG_PATH` | `/tmp/kb-mcp.log` | Log file path |
| `REGISTRY_DB` | `data/registry.db` | SQLite path for ingest state control |

### URL Normalization (embed_client.py)

The code normalizes `LMS_BASE_URL` by stripping any trailing path:
```python
LMS_BASE_URL = re.sub(r"/(api/v\d+|v\d+)/?$", "", raw_url).rstrip("/")
# "http://<LM_STUDIO_HOST>:1234/api/v1"  →  "http://<LM_STUDIO_HOST>:1234"
# "http://<LM_STUDIO_HOST>:1234/v1"      →  "http://<LM_STUDIO_HOST>:1234"
```
Each backend then adds the correct path:
- `openai-compat` → `{LMS_BASE_URL}/v1/embeddings`
- `lmstudio-rest`  → `{LMS_BASE_URL}/api/v0/embeddings`
- `lmstudio-sdk`   → WebSocket `ws://{LMS_HOST}:{LMS_PORT}`

---

## 5. Exposed MCP Tools

### `search_kb`
Main semantic search. Parameters:

| Parameter | Type | Required | Description |
|---|---|---|---|---|
| `query` | string | ✓ | Question or term |
| `top_k` | integer | — | Results (1–20, default: 5) |
| `product` | string | — | Product filter (inferred by classifier) |
| `doc_type` | string | — | Filter: see taxonomy below |
| `filter_type` | string | — | File format: `pdf`, `docx`, `xlsx`, `pptx`, `txt`, `code` |

**Returns:** list of chunks with `chunk_id`, `score`, `text`, `source_file`, `product`, `doc_type`, `file_type`, `page`.

### `list_documents`
Lists indexed documents. Accepts the same filters as `search_kb` except `query` and `top_k`. Returns documents grouped by `doc_type`.

### `get_chunk`
Returns the full chunk with neighboring context.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `chunk_id` | string | ✓ | ID returned by `search_kb` |
| `context_window` | integer | — | Neighboring chunks to include (0–3, default: 1) |

### `kb_stats`
KB statistics: total documents and chunks, breakdown by `doc_type` and file format.

---

## 6. Content Taxonomy (doc_type)

Automatically inferred by `ingest/classifier.py` via regex on the file name and path.
No folder reorganization is needed.

| doc_type | Description | Example patterns |
|---|---|---|
| `admin_guide` | Administration guides | Administration Guide, ACN, AGD |
| `install_guide` | Installation guides | Installation Guide, IGW, IASW, IGU |
| `upgrade_guide` | Upgrade/migration guides | Upgrading, Update Installation, Migration |
| `config_guide` | Configuration guides | Configuration Guide, CGD, STORM, Cookbook |
| `user_guide` | User guides | User Guide, UGD |
| `api_guide` | APIs / SDKs / programming | Programming Guide, API, SDK, PSA, Endpoints |
| `release_notes` | Release notes | Release Notes, What's New, Changelog |
| `howto` | Tutorials / case studies | How-to, Case Study, Troubleshoot, KB\d+ |
| `training` | Training / webinars | Training, VILT, Webinar, Module N, Study Guide |
| `overview` | Overview / introduction | Overview, What is, Understanding, Architecture |
| `standard` | Standards and regulations | ISO, 15489, LGPD, Lei Geral |
| `reference` | Technical reference | Technical Paper, Terminology, Spec |
| `meeting` | Meeting recordings | Meeting Recording, Knowledge Sharing |
| `release_artifact` | Binary artifacts | .zip, .patch, pat\d{9} |
| `document` | Generic fallback | Any unclassified file |

### Product mapping (root folder → product)

| Folder | product |
|---|---|
| `Archive/` | `product_archive` |
| `AppServer/` | `product_content` |
| `ECM/` | `product_ecm` |
| `DirectoryServices/` | `product_directory` |
| `wem/` | `product_wem` |
| `Adobe/` | `Adobe` |
| `RecordsManagement/` | `RecordsManagement` |
| `varios/`, root | `geral` |

Products are also inferred from the file name when the file is in `varios/` or at the root.

---

## 7. Ingestion Pipeline

### Per-file flow

```
1. classifier.classify(file_path) → {product, doc_type}
2. registry.needs_ingest(file_path) → (bool, reason)
   ├── False → skip (same SHA256, status ok)
   └── True  → continue
3. EXTRACTOR[file_type](file_path) → [{text, page}]
4. chunk_text(text, file_type) → [chunks]
5. embed_client.get_embeddings_batch(chunks) → [vectors]
6. store.delete_document(source_file)  # remove previous version
7. store.upsert_chunks(chunks + vectors + metadata)
8. registry.mark_ok(...)  # saves SHA256 + timestamp + doc_type
```

### Extratores por tipo

| file_type | Extensions | Library | Fallback |
|---|---|---|---|
| `pdf` | .pdf | docling ^ | PyMuPDF (fitz) |

> ^ `docling` é opcional — requer instalação separada. Veja [Instalação do docling](#instalação-do-docling) abaixo.
| `docx` | .docx | python-docx | — |
| `doc` | .doc | docx2txt | python-docx |
| `xlsx` | .xlsx | openpyxl | — |
| `xls` | .xls | xlrd | — |
| `pptx` | .pptx | python-pptx | — |
| `ppt` | .ppt | python-pptx (best-effort) | — (fails with binary .ppt) |
| `odt` | .odt | odfpy | — |
| `ods` | .ods | odfpy | — |
| `odp` | .odp | odfpy | — |
| `wpd` | .wpd | heuristic latin-1 | — (low quality) |
| `txt` | .txt, .md, .rst | built-in | — |
| `code` | .py .ts .js .java .go .rs .cpp .c .cs .yaml .yml .json .xml .sh .sql | built-in | — |
| `zip` | .zip | stdlib zipfile (recursive) | — (max 2 levels, 500 MB/entry) |

See [LEGACY_FORMATS.md](LEGACY_FORMATS.md) for details on legacy formats and ZIP extraction.

Ignored files: `.mp4`, `.avi`, `.jpg`, `.png`, `.ini`, `.exe`, `.dll`.

### Chunking configuration by type

| file_type | chunk_size | overlap |
|---|---|---|
| pdf | 800 | 100 |
| docx | 700 | 80 |
| xlsx | 500 | 50 |
| pptx | 600 | 80 |
| txt | 600 | 80 |
| code | 400 | 60 |

Implementado com `RecursiveCharacterTextSplitter` do LangChain com separadores `["\n\n", "\n", ". ", " ", ""]`.

### Registry (SQLite)

Tabela `files` em `data/registry.db`:

```sql
CREATE TABLE files (
    path        TEXT PRIMARY KEY,  -- relative to docs_root
    sha256      TEXT NOT NULL,     -- content hash
    file_type   TEXT,              -- pdf | docx | xlsx | pptx | txt | code
    product     TEXT,              -- produto inferido
    doc_type    TEXT,              -- inferred content type
    chunks      INTEGER,           -- chunks gerados
    status      TEXT,              -- ok | error | deleted
    error_msg   TEXT,
    indexed_at  REAL,              -- Unix timestamp
    file_mtime  REAL,
    file_size   INTEGER
);
```

**Auto-migration:** if the table already existed without `doc_type`, the column is added via `ALTER TABLE`.

### ingest.py CLI

```bash
# Incremental ingestion (new and modified only)
python ingest/ingest.py --docs /path/to/docs

# With explicit product (classifier override)
python ingest/ingest.py --docs /path --product AppServer

# Single file
python ingest/ingest.py --file /path/to/doc.pdf

# Force re-ingestion
python ingest/ingest.py --docs /path --force

# Clears KB and registry, starts fresh
python ingest/ingest.py --docs /path --clean

# Marks files removed from disk as deleted
python ingest/ingest.py --docs /path --sync

# Parallelism (default: 2 workers)
python ingest/ingest.py --docs /path --workers 4

# Registry status
python ingest/ingest.py --status
python ingest/ingest.py --status --errors   # errors only
python ingest/ingest.py --status --list     # list all
```

---

## 8. MCP Client Configuration

### Claude Code — Local Machine (WSL2)

File: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "wsl.exe",
      "args": [
        "-d", "Ubuntu-24.04",
        "--",
        "/home/SEU_USER/kb-rag-mcp/.venv/bin/python",
        "/home/SEU_USER/kb-rag-mcp/kb_server/server.py"
      ]
    }
  }
}
```

### Claude Code — LXC Server (SSE)

File: `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://<LXC_SERVER_HOST>:8765/sse"
    }
  }
}
```

### OpenCode

File: `opencode.json` (project root or `~/.config/opencode/`)

```json
{
  "mcp": {
    "kb-rag": {
      "type": "local",
      "command": ["wsl.exe", "-d", "Ubuntu-24.04", "--",
        "/home/SEU_USER/kb-rag-mcp/.venv/bin/python",
        "/home/SEU_USER/kb-rag-mcp/kb_server/server.py"]
    }
  }
}
```

---

## 9. Dependencies

```
# Core
mcp>=1.0.0
qdrant-client>=1.9.0       # API: query_points() — NÃO search() (deprecated)
httpx>=0.27.0
python-dotenv>=1.0.0

# Embedding (instalar conforme backend)
lmstudio>=1.0.0             # lmstudio>=1.0.0 (local machine with LM Studio)
# ollama>=0.2.0             # lxc server

# Extratores
python-docx>=1.1.0
openpyxl>=3.1.0
python-pptx>=0.6.23
pymupdf>=1.24.0             # fallback PDF

# Advanced PDF (optional, extra ~400 MB)
# Instale com:
#   pip install -e ".[pdf]"                                    # todos os sistemas
#   ou
#   ./scripts/install-pdf-extras.sh                            # Linux — detecta GPU
#   .\scripts\install-pdf-extras.ps1                           # Windows — detecta GPU (via PowerShell)
#
# Sem docling instalado, o sistema usa PyMuPDF (fitz) como fallback automático.
# Em máquinas AMD/Intel sem GPU NVIDIA, use o script para evitar instalar
# ~1 GB de pacotes CUDA desnecessários (torch com CUDA toolkit).
# docling>=2.0.0

# SSE transport (only if MCP_TRANSPORT=sse)
uvicorn>=0.30.0
starlette>=0.37.0
```

---

## 10. Technical Decisions and Known Constraints

### Qdrant client API
`qdrant-client` ≥1.7 removed `client.search()`. Always use:
```python
# CORRECT
response = await client.query_points(collection_name=..., query=vector, ...)
results = response.points  # list of ScoredPoint

# WRONG — raises AttributeError
results = await client.search(query_vector=vector, ...)
```

For filtered delete, use `FilterSelector`:
```python
await client.delete(
    collection_name=...,
    points_selector=qmodels.FilterSelector(filter=Filter(must=[...]))
)
```

### load_dotenv must be the first import
In any entrypoint (`server.py`, `ingest.py`, `health_check.py`), `load_dotenv` must
run **before** importing project modules, because `embed_client.py` and `vector_store.py`
read `os.getenv()` at module level (outside functions).

```python
# CORRECT PATTERN — always at the top, before project imports
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# Only after:
from embed_client import get_embedding
from vector_store import VectorStore
```

### LM Studio remote vs local
- `lmstudio-sdk` connects via WebSocket to the LM Studio daemon. Only works if the daemon
  is on the same machine or accessible via WebSocket (not plain HTTP).
- For LM Studio on another IP on the network: use `openai-compat` with `LMS_BASE_URL=http://ip:port`.
- The model name must match exactly what appears in `/v1/models` — verify before configuring.

### WSL2 → Windows networking
WSL2 accesses the Windows host via the IP in `/etc/resolv.conf` (nameserver) or the local network IP.
If `localhost` does not work for LM Studio, use the actual Windows machine IP on the local network.

### Parallel ingestion
The worker semaphore limits simultaneous calls to the embedding server.
With LM Studio on CPU, keep `--workers 1` or `2`. With GPU: up to `4`.
Ingesting 7 GB takes approximately 3–6 hours on CPU only.

---

## 11. Planned Improvements (backlog)

> **Note:** This backlog maps to Phase 11-16 in docs/PLAN.md.  
> Each item contains sufficient technical detail for autonomous implementation.

---

### High priority

#### ✅ Legacy formats (Phase 11 — implemented)

Full legacy format support implemented in `ingest/parsers/`:

- `.doc` — docx2txt → python-docx fallback
- `.xls` — xlrd (Excel 97-2003)
- `.ppt` — python-pptx best-effort
- `.odt`, `.ods`, `.odp` — odfpy (OpenDocument)
- `.wpd` — heuristic latin-1 extraction
- `.zip` — stdlib zipfile, recursive up to 2 levels, 500 MB/entry limit

See [LEGACY_FORMATS.md](LEGACY_FORMATS.md) for full details.

---

#### Reranking (Phase 12)
**Problem:** Vector results include false positives (semantic similarity without 
factual relevance). Top-5 may contain irrelevant documents.

**Technical solution:**
- Create `server/retrieval/reranker.py` with cross-encoder:
  - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`
  - Pipeline: `search_kb` returns top-20 → reranker → top-k to user
  - Batch processing: groups of 20 pairs (query, chunk) at a time
  - Async: do not block main thread
- Add `rerank: bool = False` parameter to `search_kb` tool (opt-in)
- Cache reranked results (key: hash(query + results))

**Affected files:**
- `requirements.in`: add `sentence-transformers>=2.2.0`
- `server/retrieval/reranker.py`: new module
- `server/mcp_server.py`: integrate reranker in `search_kb`
- `server/cache/cache_manager.py`: add reranking cache
- `tests/test_reranker.py`: unit tests
- `tests/e2e/test_reranking_quality.py`: quality tests

**Configuration:**
```bash
# .env
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_BATCH_SIZE=20
RERANKER_CACHE_TTL=3600  # 1 hour
```

**Tests:**
- Golden query dataset with expected top doc
- Metric: NDCG@5 before/after reranking
- Performance test: p95 latency <500ms
- Validation: result order changes correctly

**Acceptance criteria:**
- NDCG@5 improves >20% on test dataset
- Additional latency <200ms (p95)
- Opt-in does not break existing behavior

---

#### Hybrid search (Phase 12)
**Problem:** Pure vector search fails on specific technical terms 
(product names, versions, codes). Example: "Archive Center 22.3" does not
rank documents with that exact term at the top.

**Technical solution:**
- Qdrant `SparseVector` + BM25 via `fastembed`:
  - Dense vector: current embedding (nomic-embed-text)
  - Sparse vector: BM25 tokenization with fastembed
  - Fusion: **RRF (Reciprocal Rank Fusion)** or weighted sum
- Add `hybrid: bool = False` parameter to `search_kb` (opt-in)
- Store sparse vector alongside dense on upsert

**Affected files:**
- `requirements.in`: add `fastembed>=0.2.0` (BM25 support)
- `server/retrieval/hybrid_search.py`: new module
- `ingest/core/document_processor.py`: generate sparse vector during chunking
- `server/vector_store.py`: upsert with sparse vector
- `server/mcp_server.py`: integrate hybrid search
- `tests/test_hybrid_search.py`: unit tests
- `tests/e2e/test_recall_improvement.py`: recall metrics

**RRF implementation:**
```python
def rrf_fusion(dense_results, sparse_results, k=60):
    """Reciprocal Rank Fusion."""
    scores = {}
    for rank, result in enumerate(dense_results):
        scores[result.id] = scores.get(result.id, 0) + 1/(k + rank + 1)
    for rank, result in enumerate(sparse_results):
        scores[result.id] = scores.get(result.id, 0) + 1/(k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])
```

**Configuration:**
```bash
# .env
HYBRID_DENSE_WEIGHT=0.7
HYBRID_SPARSE_WEIGHT=0.3
HYBRID_RRF_K=60
```

**Tests:**
- Queries with specific technical terms (versions, codes)
- Metric: Recall@10 before/after
- Validation: documents with exact match rank higher

**Acceptance criteria:**
- Recall@10 improves >15% on technical queries
- Compatibility with existing filters (product, doc_type)
- Performance: additional latency <100ms

---

#### Payload indexing (Phase 12)
**Problem:** Filtered queries (`product=X`, `doc_type=Y`) are slow on 
large collections (>100k chunks) because Qdrant scans all payloads.

**Technical solution:**
- Create Qdrant indexes on `product` and `doc_type` fields:
  ```python
  client.create_payload_index(
      collection_name="kb_docs",
      field_name="product",
      field_schema="keyword"  # index as exact string
  )
  ```
- Migration script: `scripts/migrations/create_payload_indexes.py`
  - Idempotent: checks if index already exists
  - Progress bar for large collections
  - Can run in production without downtime
- Integrate index creation into `vector_store.py` when creating collection

**Affected files:**
- `scripts/migrations/create_payload_indexes.py`: new script
- `server/vector_store.py`: add index creation to `create_collection()`
- `docs/MIGRATIONS.md`: document migration
- `tests/test_payload_indexes.py`: validate index creation

**Migration script:**
```python
# scripts/migrations/create_payload_indexes.py
import asyncio
from qdrant_client import QdrantClient

async def create_indexes():
    client = QdrantClient(url=QDRANT_URL)
    fields = ["product", "doc_type"]
    
    for field in fields:
        # Check if index exists
        collection_info = client.get_collection("kb_docs")
        if field not in collection_info.config.params.index_fields:
            print(f"Creating index on {field}...")
            client.create_payload_index(
                collection_name="kb_docs",
                field_name=field,
                field_schema="keyword"
            )
            print(f"✓ Index created on {field}")
        else:
            print(f"✓ Index already exists on {field}")

if __name__ == "__main__":
    asyncio.run(create_indexes())
```

**Tests:**
- Benchmark: filter before/after creating indexes
- Validation: filtered query returns correct results
- Performance: filtered queries <50ms on 100k chunk collection

**Acceptance criteria:**
- Indexes created successfully in production
- Filtered queries >10x faster
- Script idempotent (can run multiple times)

---

### Medium priority

#### ✅ ZIP support (Phase 11 — implemented)

Implemented in `ingest/parsers/zip_handler.py`. Recursive extraction up to 2 levels,
500 MB per entry limit, `source_path` preserved in payload.
See [LEGACY_FORMATS.md](LEGACY_FORMATS.md) for full rules.

---

#### Version in payload (Phase 13)
**Problem:** Documents from different versions of the same product are not 
distinguishable. User cannot filter by specific version.

**Technical solution:**
- Version extractor: `ingest/core/version_extractor.py`
  - Regex patterns:
    - `(\d{2}\.\d+)` → "22.3", "16.2"
    - `(CE \d{2}\.\d+)` → "CE 24.4"
    - `(v\d+\.\d+\.\d+)` → "v3.2.1"
    - `(\d{4}R\d)` → "2024R1" (SAP style)
  - Search in: filename, parent directory, first paragraph of text
  - Return first match or `None`
- Add `version: str | None` field to Qdrant payload
- `version` filter in `search_kb` tool

**Affected files:**
- `ingest/core/version_extractor.py`: new module
- `ingest/core/metadata.py`: integrate version extraction
- `server/mcp_server.py`: add `version` parameter to `search_kb`
- `tests/test_version_extractor.py`: tests with various formats

**Implementation:**
```python
import re

class VersionExtractor:
    PATTERNS = [
        r'(\d{2}\.\d+(?:\.\d+)?)',  # 22.3, 16.2.1
        r'(CE \d{2}\.\d+)',          # CE 24.4
        r'(v\d+\.\d+(?:\.\d+)?)',    # v3.2.1, v2.0
        r'(\d{4}R\d)',               # 2024R1
    ]
    
    def extract(self, filename: str, parent_dir: str, 
                text_preview: str) -> str | None:
        """Extract version from filename, directory, or text."""
        sources = [filename, parent_dir, text_preview[:500]]
        
        for source in sources:
            for pattern in self.PATTERNS:
                match = re.search(pattern, source)
                if match:
                    return match.group(1)
        
        return None
```

**Tests:**
- `"ProductName_22.3_Admin_Guide.pdf"` → `"22.3"`
- `"/docs/ecm/CE 24.4/manual.pdf"` → `"CE 24.4"`
- `"Release Notes for version 16.2"` → `"16.2"`
- File without version → `None`

**Acceptance criteria:**
- Correctly extracts version from 90% of test files
- `version` field indexed in Qdrant
- `version` filter works in search_kb

---

#### `_meta.json` per folder (Phase 13)
**Problem:** Automatic classification gets some files wrong. Moving files 
to restructure folders is labor-intensive. Need targeted overrides.

**Technical solution:**
- `_meta.json` file per directory:
  ```json
  {
    "product": "DefaultProductForDir",
    "doc_type": "default_doc_type",
    "files": {
      "specific_file.pdf": {
        "product": "OverrideProduct",
        "doc_type": "api_guide"
      },
      "another_file.docx": {
        "doc_type": "manual"
      }
    }
  }
  ```
- Precedence: file-specific > directory-level > auto-inference
- Validation: reject invalid `product`/`doc_type` (allowlist)
- Load in `FileScanner` before classifying

**Affected files:**
- `ingest/core/meta_loader.py`: new module
- `ingest/core/file_scanner.py`: integrate meta loader
- `ingest/core/metadata.py`: use override if available
- `tests/test_meta_loader.py`: precedence tests

**Implementation:**
```python
import json
from pathlib import Path

class MetaLoader:
    VALID_DOC_TYPES = [
        "admin_guide", "install_guide", "api_guide", 
        "release_notes", "manual", "training", "overview"
    ]
    
    def load_meta(self, directory: Path) -> dict:
        """Load _meta.json from directory."""
        meta_file = directory / "_meta.json"
        if not meta_file.exists():
            return {}
        
        with open(meta_file) as f:
            meta = json.load(f)
        
        # Validate
        if "doc_type" in meta:
            if meta["doc_type"] not in self.VALID_DOC_TYPES:
                raise ValueError(f"Invalid doc_type: {meta['doc_type']}")
        
        if "files" in meta:
            for file, overrides in meta["files"].items():
                if "doc_type" in overrides:
                    if overrides["doc_type"] not in self.VALID_DOC_TYPES:
                        raise ValueError(
                            f"Invalid doc_type for {file}: "
                            f"{overrides['doc_type']}"
                        )
        
        return meta
    
    def get_metadata(self, file_path: Path, meta: dict) -> dict:
        """Get metadata for file considering precedence."""
        filename = file_path.name
        
        # File-specific override
        if "files" in meta and filename in meta["files"]:
            file_meta = meta["files"][filename]
            return {
                "product": file_meta.get("product", meta.get("product")),
                "doc_type": file_meta.get("doc_type", meta.get("doc_type"))
            }
        
        # Directory-level default
        return {
            "product": meta.get("product"),
            "doc_type": meta.get("doc_type")
        }
```

**Tests:**
- `_meta.json` with default → applied to all files
- `_meta.json` with file-specific → override works
- Precedence: file > dir > auto
- Validation: invalid doc_type → error

**Acceptance criteria:**
- `_meta.json` loaded and validated correctly
- Precedence works (file > dir > auto)
- Validation rejects invalid values
- Manual classification takes priority over automatic

---

### Low priority

#### Inspection UI (Phase 14)
**Summary solution:**
- FastAPI in `server/ui/` with HTMX
- Routes: `/ui` (browse), `/ui/search` (tester), `/ui/doc/{id}` (detail)
- Bootstrap 5 or Tailwind for styling
- No authentication (internal only)
- Pagination: 50 documents per page

**Files:** `server/ui/{app.py, templates/, static/}`

---

#### Usage metrics (Phase 14)
**Summary solution:**
- SQLite table `query_log`: query, results, scores, latency_ms, timestamp
- Log after each `search_kb` invocation
- Auto-rotation: keep 90 days, archive monthly
- Stats queries: top queries, low-score queries

**Files:** `server/telemetry/query_logger.py`

---

#### ✅ Multiple collections (Phase 15 — implemented)
**Implemented solution:**
- `CollectionManager` in `kb_server/collections/manager.py` — CRUD (list/create/delete/exists)
  - Mirrors HNSW config and payload indexes from VectorStore
- `CollectionRouter` in `kb_server/collections/router.py`
  - `resolve()` — strict, raises `CollectionNotFoundError` if collection doesn't exist (read paths)
  - `ensure()` — creates automatically if it doesn't exist (ingest paths)
- Optional `collection` parameter on `search_kb` and `list_documents`
- New MCP tool: `list_collections` — lists all available collections
- Backward compatible: without `collection` routes to `QDRANT_COLLECTION` (default `kb_docs`)

**Files:** `kb_server/collections/{__init__.py, manager.py, router.py}`,
              `kb_server/server.py` (modified), `kb_server/vector_store.py` (modified)
**Tests:** `tests/test_collection_manager.py` (10 tests), `tests/test_collection_router.py` (7 tests)

---

#### Registry export (Phase 14)
**Summary solution:**
- Command: `kb-rag registry export --format csv|json`
- Filters: `--product`, `--doc_type`, `--status`
- Streaming export (do not load everything into memory)

**Files:** `ingest/cli/export.py`

---

#### ✅ Kubernetes support (Phase 15 — implemented)
**Implemented solution:**
- Helm chart at `deployment/helm/kb-rag-mcp/`
  - `Deployment` for kb-server with liveness/readiness probes
  - `StatefulSet` for Qdrant + PVC (50 Gi default)
  - `HorizontalPodAutoscaler` (2–10 replicas, 70% CPU target)
  - `Services` for kb-server and Qdrant
  - `ConfigMap` for env vars
  - `_helpers.tpl` with label macros
- `values.yaml` with configurable defaults (replicas, resources, optional Redis, Ingress)
- `ServiceMonitor` support for Prometheus Operator

**Files:** `deployment/helm/kb-rag-mcp/{Chart.yaml, values.yaml, templates/}`
**Docs:** `docs/KUBERNETES.md`

---

#### RAG performance and accuracy (Phase 16)
**Summary solution:**
- Golden dataset: 50+ (query, expected_answer, expected_docs)
- RAGAS pipeline: context_precision, answer_relevancy, faithfulness
- LLM-as-judge via local Ollama or OpenAI API
- Query analyzer: identify patterns, low-score queries
- Optimizations: chunk size, score thresholds, query expansion
- Weekly CI evaluation job

**Files:** `server/evaluation/{ragas_pipeline.py, dataset.py}`, 
            `server/analytics/query_analyzer.py`

---
---

## 12. Operation Commands

```bash
# Initial setup
bash scripts/setup.sh local         # local machine
bash scripts/setup.sh lxc           # LXC Server

# Check component health
python scripts/health_check.py

# Ingestion
cd ~/kb-rag-mcp                     # always run from the root
source .venv/bin/activate
python ingest/ingest.py --docs /mnt/c/Recebedor/learning

# Status
python ingest/ingest.py --status --list

# Start server (manual test)
python kb_server/server.py

# Local machine — autostart
pwsh scripts/start-kb-rag.ps1
pwsh scripts/start-kb-rag.ps1 -Status
pwsh scripts/start-kb-rag.ps1 -Stop

# LXC Server — systemd
sudo systemctl status kb-mcp
sudo journalctl -u kb-mcp -f

# Qdrant
docker ps                           # check if container is running
curl http://localhost:6333/healthz  # health check
curl http://localhost:6333/collections  # list collections
```

---

## 13. Business Context

The KB can contain any technical documentation. Product names and document types are automatically classified via metadata.

Documents include: administration and installation guides, release notes, upgrade guides,
scenario configuration guides, APIs, training materials, presentations,
case studies, standards, and release artifacts.

The main objective is to support **engineers and consultants** in day-to-day
development, configuration, and troubleshooting tasks, using LLMs like Claude Code
to accelerate their work.

---

## Instalação do docling (PDF Extra)

> O docling é um extrator de PDF avançado (tabelas, figuras, layout analysis) que
> substitui o PyMuPDF quando instalado. Sem ele, o sistema usa PyMuPDF como fallback
> automático — nenhuma perda de funcionalidade em PDFs simples.

**Requisito:** ~400 MB adicionais (ou ~1.4 GB se o pip instalar torch com CUDA).

```bash
# Opção 1 — instalação básica (todos os sistemas)
pip install -e ".[pdf]"

# Opção 2 — Linux, com detecção automática de GPU
./scripts/install-pdf-extras.sh

# Opção 3 — Windows (PowerShell), com detecção automática de GPU
.\scripts\install-pdf-extras.ps1
```

**GPU vs CPU:** Em máquinas AMD/Intel sem GPU NVIDIA, o script `install-pdf-extras.sh`
pré-instala `torch` do canal CPU (`download.pytorch.org/whl/cpu`), evitando que o pip
baixe ~1 GB de pacotes CUDA (nvidia-cublas, nvidia-cudnn, etc.) que são inúteis sem GPU.

**Verificação:**
```bash
python -c "from docling.document_converter import DocumentConverter; print('docling OK')"
```

---

## Docker Compose

- **Environment variables** → [§4. Environment Variables](#4-environment-variables) (all modes)
- **MCP client config** → [§8. MCP Client Configuration](#8-mcp-client-configuration) (all modes)
- **Quick start:** `docker compose up -d` from project root (Qdrant + MCP server + monitoring)

Docker Compose manifest: `docker-compose.yml` at project root.

> **See also:** [OPERATIONS.md → Docker Compose](OPERATIONS.md#docker-compose), [TROUBLESHOOTING.md → Docker Compose](TROUBLESHOOTING.md#docker-compose)

---

## Helm

- **Kubernetes deployment** → See [docs/KUBERNETES.md](KUBERNETES.md) for full Helm chart reference
- **Helm values** → `deployment/helm/kb-rag-mcp/values.yaml`
- **Customization:** Set environment variables via Helm `values.yaml` or `--set` flags
- **Monitoring:** Prometheus/Grafana included via Helm sub-charts (toggle with `monitoring.enabled`)

> **See also:** [OPERATIONS.md → Helm](OPERATIONS.md#helm), [TROUBLESHOOTING.md → Helm](TROUBLESHOOTING.md#helm)

---

## Systemd

- **Environment** → [§2. Runtime Environment → LXC Server](#2-runtime-environment) (LXC/systemd setup)
- **Service management** → `sudo systemctl start/stop/status kb-mcp`
- **Logs** → `sudo journalctl -u kb-mcp -f`
- **Unit files** → `scripts/kb-mcp.service`, `scripts/kb-rag.target`

Key commands (from [§12. Operation Commands](#12-operation-commands)):
```
sudo systemctl status kb-mcp
sudo journalctl -u kb-mcp -f
```

> **See also:** [OPERATIONS.md → Systemd](OPERATIONS.md#systemd), [TROUBLESHOOTING.md → Systemd](TROUBLESHOOTING.md#systemd)

---

## Manual

- **Environment** → [§2. Runtime Environment → Local Machine](#2-runtime-environment) (WSL2/manual setup)
- **Python setup** → Create venv, `pip install -r requirements.txt`
- **Run server** → `python kb_server/server.py` (stdio) or with SSE transport
- **Ingestion** → `python ingest/ingest.py --docs <path>` (see [§7. Ingestion Pipeline](#7-ingestion-pipeline))
- **Windows startup** → `pwsh scripts/start-kb-rag.ps1`

> **See also:** [OPERATIONS.md → Manual](OPERATIONS.md#manual), [TROUBLESHOOTING.md → Manual](TROUBLESHOOTING.md#manual)
