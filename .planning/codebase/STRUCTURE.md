# Codebase Structure

**Analysis Date:** 2026-05-19

## Directory Layout

```
kb-rag-mcp/
├── kb_server/              # MCP query server (canonical, current)
│   ├── server.py           # MCP server entry point — tools + handlers
│   ├── vector_store.py     # Qdrant abstraction
│   ├── embed_client.py     # Multi-backend embedding client
│   ├── health.py           # Health check logic
│   ├── health_server.py    # HTTP health server
│   ├── retrieval/          # Search quality enhancements
│   │   ├── hybrid_search.py    # Dense + BM25 RRF fusion
│   │   └── reranker.py         # Cross-encoder reranking
│   ├── collections/        # Multi-collection support
│   │   ├── manager.py          # Qdrant collection CRUD
│   │   └── router.py           # Collection name resolution
│   ├── cache/              # Embedding cache
│   │   ├── manager.py          # Cache manager (LRU + Redis)
│   │   ├── lru.py              # In-memory LRU implementation
│   │   └── redis.py            # Redis backend (optional)
│   ├── telemetry/          # Query logging
│   │   └── query_logger.py     # SQLite query log writer
│   ├── analytics/          # Usage analytics
│   │   └── query_analyzer.py   # Query pattern analysis
│   ├── evaluation/         # RAG evaluation pipeline
│   │   ├── dataset.py          # Evaluation dataset helpers
│   │   └── ragas_pipeline.py   # RAGAS evaluation integration
│   ├── optimization/       # Chunking/scoring experiments
│   │   ├── chunking_experiments.py
│   │   └── scoring_experiments.py
│   └── ui/                 # Optional web UI
│       ├── app.py              # FastAPI/Starlette app
│       ├── routes.py           # UI routes
│       ├── run_ui.py           # UI launcher
│       └── templates/          # Jinja2 HTML templates
│
├── server/                 # Legacy server package (mirrors kb_server/)
│   │                       # Kept for backwards compat; kb_server/ is canonical
│   │                       # NOTE: server/ lacks collections/ subpackage
│
├── ingest/                 # Document ingestion pipeline
│   ├── ingest.py           # Main ingestion orchestrator + CLI
│   ├── registry.py         # SQLite registry for dedup/state tracking
│   ├── classifier.py       # Product/doc_type/version classifier
│   ├── parsers/            # Legacy format extractors
│   │   ├── legacy_office.py    # DOC/XLS/PPT/ODT/ODS/ODP/WPD extractors
│   │   └── zip_handler.py      # ZIP archive handler
│   ├── validation/         # Ingest validation pipeline
│   │   ├── base.py             # Base validator class
│   │   ├── format.py           # File format validation
│   │   ├── size.py             # File size limits
│   │   ├── content.py          # Content quality validation
│   │   └── pipeline.py         # Validation pipeline orchestrator
│   ├── core/               # Core metadata + version utilities
│   │   ├── metadata.py         # MetadataStore (SQLite)
│   │   ├── meta_loader.py      # Metadata loading helpers
│   │   └── version_extractor.py# Version string extraction from filenames
│   ├── job/                # Job scheduling and management
│   │   ├── models.py           # Job, JobStatus, JobPriority dataclasses
│   │   ├── manager.py          # Job CRUD lifecycle manager
│   │   └── scheduler.py        # Job scheduling logic
│   ├── worker/             # Async worker pool for parallel ingestion
│   │   ├── worker.py           # Worker implementation
│   │   ├── pool.py             # Worker pool
│   │   ├── executor.py         # Task execution
│   │   ├── batch_processor.py  # Batch file processing
│   │   └── limiter.py          # Rate/concurrency limiter
│   ├── watcher/            # Filesystem watching for auto-ingest
│   │   └── file_watcher.py     # Watchdog-based file watcher
│   └── cli/                # New-style CLI commands
│       ├── main.py             # CLI entry point with subcommands
│       ├── job.py              # Job management commands
│       ├── db.py               # Database commands
│       ├── export.py           # Export commands
│       ├── progress.py         # Progress display
│       └── legacy.py           # Legacy CLI compatibility
│
├── observability/          # Cross-cutting observability
│   ├── logging.py          # Logging configuration
│   ├── metrics.py          # MetricsCollector (Prometheus)
│   └── progress.py         # Progress bar utilities
│
├── qa/                     # Quality assurance / evaluation
│   ├── run_qa.py           # QA pipeline runner
│   ├── embedder.py         # Embedding utilities for QA
│   ├── metrics.py          # Retrieval quality metrics
│   ├── report.py           # Report generation
│   └── fixtures/           # QA test fixtures/queries
│
├── config/                 # Configuration
│   └── batch_config.py     # Batch processing configuration
│
├── scripts/                # Operational scripts
│   ├── health_check.py     # Health check script
│   ├── migrate/            # Data migration (export/import/validate)
│   └── migrations/         # Qdrant index migrations
│
├── tests/                  # Unit + integration tests
│   ├── conftest.py         # Shared fixtures
│   ├── e2e/                # End-to-end tests
│   └── test_*.py           # Unit/integration test files
│
├── deployment/             # Deployment configurations
│   ├── helm/               # Helm chart for Kubernetes
│   ├── config/             # Grafana provisioning config
│   ├── scripts/            # Deployment scripts
│   └── systemd/            # systemd service files
│
├── docs/                   # Documentation
│   ├── superpowers/        # AI planning docs (plans + specs)
│   └── archive/            # Archived docs
│
├── data/                   # Runtime data (gitignored content)
│   │                       # registry.db, kb_metadata.db live here
│
├── docker-compose.yml      # Local development stack (Qdrant + server)
├── pyproject.toml          # Build config + tool settings
├── setup.py                # Package installation + entry points
├── requirements.txt        # Pinned dependencies
└── requirements.in         # Direct dependency declarations
```

## Directory Purposes

**`kb_server/`:**
- Purpose: The MCP server package — tools exposed to LLM clients
- Contains: Server entry point, vector store, embedding client, retrieval logic
- Key files: `server.py`, `vector_store.py`, `embed_client.py`

**`server/`:**
- Purpose: Legacy package mirror of `kb_server/` without `collections/`
- Contains: Same structure as `kb_server/` minus collection management
- Key files: `server.py` — use `kb_server/server.py` for new features

**`ingest/`:**
- Purpose: All document ingestion logic — extract, chunk, embed, index
- Contains: Pipeline orchestrator, file parsers, job system, workers, watcher
- Key files: `ingest.py` (main pipeline), `registry.py` (dedup state), `classifier.py`

**`observability/`:**
- Purpose: Shared metrics and logging utilities
- Contains: `MetricsCollector`, logging config, progress bar
- Key files: `metrics.py`, `logging.py`

**`tests/`:**
- Purpose: Automated test suite
- Contains: Unit tests, integration tests, e2e workflow tests
- Key files: `conftest.py`, `tests/e2e/`

**`deployment/`:**
- Purpose: Kubernetes/Helm, systemd, and Grafana config for production
- Contains: Helm chart, systemd unit, Grafana dashboards
- Generated: No — manually maintained

## Key File Locations

**Entry Points:**
- `kb_server/server.py`: MCP server — `asyncio.run(main())`
- `ingest/ingest.py`: Ingest CLI — `main()` function
- `ingest/cli/main.py`: New CLI entry — registered as `kb-ingest` in `setup.py`
- `kb_server/health_server.py`: HTTP health endpoint
- `kb_server/ui/run_ui.py`: Optional web UI launcher

**Configuration:**
- `.env`: Runtime environment variables (not committed)
- `pyproject.toml`: Build/tool config (black, pytest, mypy)
- `config/batch_config.py`: Batch processing tunables

**Core Logic:**
- `kb_server/vector_store.py`: Qdrant abstraction — search, upsert, stats
- `kb_server/embed_client.py`: Embedding backend selection and caching
- `kb_server/retrieval/hybrid_search.py`: Dense+BM25 hybrid search with RRF
- `kb_server/retrieval/reranker.py`: Cross-encoder reranking
- `kb_server/collections/router.py`: Multi-collection routing
- `ingest/registry.py`: File dedup and status tracking (SQLite)
- `ingest/classifier.py`: Automatic product/doc_type/version detection

**Testing:**
- `tests/conftest.py`: Shared pytest fixtures
- `tests/e2e/`: Full workflow tests requiring running services
- `tests/test_*.py`: Unit/integration tests (majority of coverage)

## Naming Conventions

**Files:**
- Snake_case: `hybrid_search.py`, `query_analyzer.py`, `vector_store.py`
- Test files: `test_<module_name>.py` pattern (e.g., `test_hybrid_search.py`)

**Directories:**
- Snake_case for packages: `kb_server`, `ingest`, `observability`
- Functional subdirectories: `retrieval/`, `collections/`, `workers/`

**Classes:**
- PascalCase: `VectorStore`, `IngestRegistry`, `HybridSearcher`, `CollectionManager`

**Functions:**
- Snake_case: `get_embedding()`, `chunk_text()`, `run_ingest()`
- Private handlers prefixed with `_`: `_search_kb()`, `_list_documents()`

## Where to Add New Code

**New MCP Tool:**
- Implementation: `kb_server/server.py` — add to `list_tools()` and `call_tool()` dispatch, add `_handler()` function
- Tests: `tests/test_smoke.py` or new `tests/test_<tool_name>.py`

**New Document Format Support:**
- Extractor function: `ingest/ingest.py` or `ingest/parsers/` for complex formats
- Register in: `ingest/ingest.py:EXTRACTORS` dict and `EXT_TYPE_MAP`

**New Retrieval Feature:**
- Implementation: `kb_server/retrieval/<feature>.py`
- Integration: `kb_server/server.py:_search_kb()`

**New Embedding Backend:**
- Implementation: `kb_server/embed_client.py` — add backend in `get_embedding()` function
- Config: Add to `EMBED_BACKEND` env var docs

**Utilities:**
- Shared observability: `observability/`
- Ingest utilities: `ingest/core/`
- Server utilities: `kb_server/` root level

## Special Directories

**`.planning/`:**
- Purpose: AI-assisted planning documents (codebase maps, specs, plans)
- Generated: Yes (by GSD commands)
- Committed: Yes

**`data/`:**
- Purpose: Runtime SQLite databases and document store
- Generated: Yes (at runtime)
- Committed: No (data files gitignored)

**`.worktrees/`:**
- Purpose: Git worktrees for isolated feature branches
- Generated: Yes (by git)
- Committed: No

**`kb_rag_mcp.egg-info/`:**
- Purpose: Python package metadata from `pip install -e .`
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-05-19*
