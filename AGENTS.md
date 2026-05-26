<!-- GSD:project-start source:PROJECT.md -->
## Project

**kb-rag-mcp**

A production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation.

**Core Value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

### Constraints

- **Tech stack**: Python 3.11+, Qdrant, MCP protocol, FastAPI, asyncio — no runtime changes
- **Dependencies**: pip-tools (`requirements.in` → `requirements.txt`), `.venv/` virtual env
- **Compatibility**: CLI interface must remain backward-compatible; deprecation warnings for removed flags
- **Deployment**: Must support bare metal (systemd), Docker Compose, and Kubernetes/Helm
- **No auth**: Internal use only — no authentication layer planned
- **Test baseline**: 268 passing tests; no regressions allowed
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11+ — entire application (server, ingestion, QA, observability)
- SQL — SQLite queries for metadata and query logging (`data/kb_metadata.db`, `data/registry.db`)
## Runtime
- CPython 3.11 (minimum; 3.12 supported per setup.py classifiers)
- pip + pip-tools (`requirements.in` → `requirements.txt`)
- Lockfile: `requirements.txt` (pinned versions present)
- Virtual env: `.venv/` (present in repo)
## Frameworks
- `mcp==1.27.1` — Model Context Protocol server; exposes `search_kb`, `list_documents`, `get_chunk`, `kb_stats` tools
- `fastapi==0.136.1` — Health check HTTP API (`server/health_server.py`)
- `starlette==1.0.0` — SSE transport layer for MCP (`server/server.py`)
- `uvicorn==0.47.0` — ASGI server for SSE and health endpoints
- `PyMuPDF==1.27.2.3` — PDF extraction
- `python-docx==1.2.0` — DOCX extraction
- `openpyxl==3.1.5` — XLSX extraction
- `python-pptx==1.0.2` — PPTX extraction
- `docx2txt==0.8` — Legacy `.doc` extraction
- `xlrd==2.0.1` — Legacy `.xls` extraction
- `odfpy==1.4.1` — ODF formats (`.odt`, `.ods`, `.odp`)
- `langchain-text-splitters==1.1.2` — Document chunking
- `qdrant-client==1.18.0` — Async Qdrant vector database client
- `fastembed==0.8.0` — BM25 sparse vectors for hybrid search
- `sentence-transformers==5.5.0` — Cross-encoder reranking
- `pytest==9.0.3` — Test runner
- `pytest-asyncio==1.3.0` — Async test support (strict mode per `pyproject.toml`)
- `black==26.3.1` — Code formatter (line-length 79, target py311)
- `flake8==7.3.0` — Linting (`.flake8` config present)
- `isort==8.0.1` — Import sorting (black profile)
- `mypy==2.1.0` — Type checking (Python 3.11, lenient: `disallow_untyped_defs=false`)
## Key Dependencies
- `mcp==1.27.1` — Core protocol; all AI client integrations depend on this
- `qdrant-client==1.18.0` — Vector store; entire retrieval pipeline depends on this
- `httpx==0.28.1` — Async HTTP client for embedding backends (LM Studio, Ollama, OpenAI-compat)
- `python-dotenv==1.2.2` — Environment config loading (`.env` at project root)
- `pydantic==2.13.4` — Data validation throughout
- `pydantic-settings==2.14.1` — Settings management
- `prometheus_client==0.25.0` — Metrics export (`observability/metrics.py`)
- `watchdog==6.0.0` — File system monitoring for auto-ingestion
- `diskcache==5.6.3` — Disk-backed cache (used in embedding cache layer)
- `psutil==7.2.2` — System monitoring for cache auto-tuning
- `SQLAlchemy==2.0.49` — ORM/DB access layer
- `rich==14.3.4` — CLI output formatting
- `typer==0.25.1` — CLI framework (`ingest/cli/main.py`)
- `click==8.3.3` — CLI dependency
- `datasets==4.8.5` — HuggingFace datasets
- `scikit-learn==1.8.0` — Clustering and metrics
- `matplotlib==3.10.9` — Evaluation visualizations
## Configuration
- Primary config file: `.env` (loaded by server at startup via `python-dotenv`)
- Example configs: `config/.env.local`, `config/.env.lxc`
- Key env vars:
- `pyproject.toml` — Black, isort, mypy, pytest configuration
- `setup.py` — Package definition, entry points, install_requires
- `.flake8` — Flake8 linting configuration
## Platform Requirements
- Python 3.11+
- Qdrant (Docker via `docker-compose.yml` or embedded mode)
- Embedding backend: LM Studio, Ollama, or any OpenAI-compat server
- `docker-compose.yml` — Qdrant container (`qdrant/qdrant:latest`, ports 6333/6334)
- `scripts/kb-mcp.service` — systemd unit for Linux deployment
- `deployment/` directory — Kubernetes manifests (`docs/KUBERNETES.md`)
- Supports LXC Linux server (`config/.env.lxc`)
- Windows scripts: `scripts/start-kb-rag.ps1`
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- `snake_case` for all Python modules: `hybrid_search.py`, `batch_processor.py`, `query_analyzer.py`
- Package names in `snake_case` directories: `kb_server/`, `ingest/`, `kb_server/retrieval/`
- Test files prefixed with `test_`: `test_hybrid_search.py`, `test_validation.py`
- `PascalCase`: `HybridSearcher`, `FileWorker`, `ValidationPipeline`, `CollectionManager`
- Exceptions suffixed with `Error`: `CollectionNotFoundError`, `ValidationError`
- Abstract base classes use ABC: `class Validator(ABC):`
- `snake_case` for all functions and methods: `_rrf_fusion()`, `_load_sparse_model()`, `check_all_components()`
- Private/internal methods prefixed with `_`: `_rrf_fusion`, `_load_sparse_model`
- Factory functions prefixed with `create_`: `create_default_pipeline()`, `create_strict_pipeline()`, `create_lenient_pipeline()`
- `snake_case` for local variables and module-level config
- `UPPER_SNAKE_CASE` for module-level constants read from env: `TOP_K`, `HYBRID_RRF_K`, `QUERY_LOG_ENABLED`
- Module logger always named `log`: `log = logging.getLogger("kb-mcp")`
- `PascalCase` for enum class, `UPPER_SNAKE_CASE` for values: `ValidationSeverity.ERROR`
- Enums inherit from `str, Enum` for JSON serialization
## Code Style
- Black, line length 79 (`[tool.black]` in `pyproject.toml`)
- Target: Python 3.11+
- isort with black profile, line length 79 (`[tool.isort]`)
- `from __future__ import annotations` NOT used (py3.11)
- flake8, max line 79, extends-ignore E203/W503 (`.flake8`)
- mypy with `warn_return_any=true`, `ignore_missing_imports=true`
## Import Organization
- Grouped with blank lines between stdlib, third-party, and local
- Seen in `server.py`: stdlib → third-party → kb_server imports
## Module Documentation
## Type Hints
- Type hints on all function signatures in production code
- `Optional[str]` for nullable params (pre-3.10 style, not `str | None`)
- New-style union syntax used in some places: `SparseTextEmbedding | None`
- `mypy` configured with `disallow_untyped_defs = false` — hints encouraged but not enforced
## Error Handling
- Try/except with explicit exception types, never bare `except:`
- Errors logged with `log.error(f"...")` before re-raise or graceful degradation
- Custom exception classes extend `Exception` and carry context objects:
- Graceful degradation on optional integrations (query logger, dotenv):
## Logging
## Configuration
- `.env` file loaded at server startup via `python-dotenv`
- Environment variables use `UPPER_SNAKE_CASE`
## Data Classes
- Factory class methods (`@classmethod`) for common construction: `ValidationResult.success()`, `ValidationResult.failure()`
## FASE Comments
- Module docstrings include phase tag: `FASE 12: Search Quality Enhancement`
- Inline comments mark phase-specific features: `# FASE 14: Query logging configuration`
- Test files marked with `pytestmark = pytest.mark.fase12`
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Two independent subsystems: **Ingest Pipeline** and **Query Server**
- Vector store abstraction over Qdrant (dense + sparse hybrid search)
- MCP protocol compliance (stdio or SSE transport) for LLM client integration
- Async Python (asyncio) throughout, with sync SQLite registry for ingest tracking
- Dual package layout: `server/` (legacy) and `kb_server/` (current) — `kb_server/` is canonical
## Layers
- Purpose: Expose RAG tools to LLM clients via MCP protocol
- Location: `kb_server/server.py`
- Contains: Tool registration (`list_tools`), dispatch (`call_tool`), tool handlers
- Depends on: `VectorStore`, `EmbedClient`, `CollectionRouter`, `QueryLogger`
- Used by: MCP clients (Claude Code, OpenCode, etc.)
- Purpose: Semantic search with optional hybrid and reranking modes
- Location: `kb_server/retrieval/`
- Contains: `hybrid_search.py` (dense+BM25 RRF fusion), `reranker.py` (cross-encoder)
- Depends on: `VectorStore`, `fastembed` (sparse), cross-encoder model
- Used by: `server.py` `_search_kb` handler
- Purpose: Qdrant abstraction for CRUD and search operations
- Location: `kb_server/vector_store.py`
- Contains: `VectorStore` class — connect, upsert_chunks, search, list_documents, get_stats
- Depends on: `qdrant_client` (AsyncQdrantClient), `embed_client`
- Used by: server, ingest pipeline
- Purpose: Backend-agnostic embedding generation with caching
- Location: `kb_server/embed_client.py`
- Contains: Multi-backend support: `lmstudio-sdk`, `lmstudio-rest`, `openai-compat`, `ollama`
- Depends on: `httpx`, `CacheManager`, `MetricsCollector`
- Used by: `VectorStore`, `ingest/ingest.py`
- Purpose: Qdrant collection lifecycle and multi-collection routing
- Location: `kb_server/collections/`
- Contains: `CollectionManager` (CRUD), `CollectionRouter` (request routing, default resolution)
- Depends on: `qdrant_client.AsyncQdrantClient`
- Used by: `server.py` main() initialization and tool handlers
- Purpose: Document ingestion — extraction, chunking, embedding, indexing
- Location: `ingest/`
- Contains: `ingest.py` (orchestrator), `parsers/` (file extractors), `registry.py` (SQLite dedup), `classifier.py` (metadata detection), `validation/` (pipeline validation), `worker/` (async workers), `job/` (job scheduling), `watcher/` (filesystem watch)
- Depends on: `VectorStore`, `EmbedClient`, `langchain_text_splitters`, document libs
- Used by: CLI, file watcher, job scheduler
- Purpose: Metrics, logging, telemetry
- Location: `observability/`, `kb_server/telemetry/`, `kb_server/analytics/`
- Contains: `MetricsCollector`, `QueryLogger` (SQLite), `query_analyzer.py`
- Depends on: Prometheus metrics (optional)
- Used by: All layers
- Purpose: Embedding caching to reduce LLM API calls
- Location: `kb_server/cache/`
- Contains: `CacheManager`, `lru.py` (in-memory LRU), `redis.py` (optional Redis)
- Depends on: Optional Redis
- Used by: `embed_client.py`
## Data Flow
- Qdrant: persistent vector store for all indexed chunks and metadata
- SQLite (`data/registry.db`): ingest registry (file hashes, chunk counts, status)
- SQLite (`data/kb_metadata.db`): query logs for analytics
- In-memory LRU + optional Redis: embedding cache
## Key Abstractions
- Purpose: Single interface to Qdrant — search, upsert, list, stats
- Examples: `kb_server/vector_store.py`
- Pattern: Async class with lazy `connect()`, supports HTTP/gRPC/embedded modes
- Purpose: Track which files have been indexed and their SHA256 hash
- Examples: `ingest/registry.py`
- Pattern: SQLite-backed class with `needs_ingest()` / `mark_ok()` / `mark_error()` / `mark_deleted()`
- Purpose: Backend-agnostic embedding, returns float vectors
- Examples: `kb_server/embed_client.py`
- Pattern: Module-level functions `get_embedding(text)` and `get_embeddings_batch(texts)`, backend selected by `EMBED_BACKEND` env var
- Purpose: Resolve collection parameter to actual Qdrant collection name
- Examples: `kb_server/collections/router.py`
- Pattern: Async `resolve(name_or_None)` with default fallback
- Purpose: Combine dense vector search with BM25 sparse via RRF
- Examples: `kb_server/retrieval/hybrid_search.py`
- Pattern: Singleton via `get_hybrid_searcher()`, lazy sparse model loading
## Entry Points
- Location: `kb_server/server.py` → `main()` / `if __name__ == "__main__": asyncio.run(main())`
- Triggers: `python -m kb_server.server` or via MCP client config
- Responsibilities: Connect VectorStore, init CollectionManager/Router, serve MCP tools via stdio or SSE
- Location: `ingest/ingest.py` → `main()`
- Triggers: `python ingest/ingest.py --docs /path` or `python ingest/ingest.py --file /path`
- Responsibilities: Process files, chunk, embed, upsert to Qdrant
- Location: `ingest/cli/main.py`
- Triggers: via `kb-ingest` entrypoint (defined in `setup.py`)
- Responsibilities: New structured CLI with subcommands (job, db, export, progress, legacy)
- Location: `ingest/watcher/file_watcher.py`
- Triggers: Filesystem events
- Responsibilities: Watch a directory, auto-ingest on file changes
- Location: `kb_server/health_server.py`
- Triggers: Started alongside MCP server
- Responsibilities: HTTP health check endpoint for deployment probes
## Error Handling
- Tool calls wrapped in try/except in `server.py:call_tool()` → returns error TextContent
- Ingest: per-file try/except with `registry.mark_error(file, msg)`
- Embedding failures: propagate up to caller (critical path)
- Hybrid search / reranking: fallback to non-hybrid / original results on failure
- Query logging: non-fatal; logged but never raises
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

**Developer:** Luciano Marinho (luciano.marinho@gmail.com)  
**Role:** Lead Developer / System Architect  
**Experience Level:** Senior

**Full profile:** `.planning/developer-profile.json` (221 lines, comprehensive)

### Quick Reference

**Technical Expertise:**
- **Expert:** Python 3.11+, FastAPI, asyncio, pytest, Docker, Qdrant, MCP protocol
- **Proficient:** Prometheus/Grafana, Kubernetes/Helm, RAG systems, Vector embeddings
- **Familiar:** PowerShell, Starlette, LM Studio/Ollama

**Code Style:**
- **Formatting:** Black (line-length 79), flake8, isort (black profile), mypy (lenient)
- **Conventions:** snake_case modules/functions, PascalCase classes, _private methods
- **Documentation:** English only (zero Portuguese - Phase 12 enforcement), Google-style docstrings
- **Logging:** `log = logging.getLogger('kb-mcp.{module}')`, INFO for operations

**Development Practices:**
- **Testing:** TDD for behavior changes, 90% branch coverage baseline, 585 passing tests
- **Git:** Conventional commits with phase tracking (fix/feat/docs/test/chore/plan)
- **Planning:** GSD framework, phase-based execution, wave parallelization, UAT validation
- **Execution:** Worktree isolation when safe, quality gates enforced, dev+prod testing

**AI Agent Guidance:**
- Follow PEP8/Black strictly, add Google-style docstrings, emit structured logs
- Write English-only comments, commit atomically per task, run pytest after changes
- Reference completed phases 9-14 for patterns, maintain 90%+ branch coverage
- Test on both dev (WSL) and production (acemagic) for deployment changes

> This section is auto-generated from `.planning/developer-profile.json` -- do not edit manually.
<!-- GSD:profile-end -->
