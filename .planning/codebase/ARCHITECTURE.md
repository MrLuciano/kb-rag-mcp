# Architecture

**Analysis Date:** 2026-05-19

## Pattern Overview

**Overall:** Pipeline-based RAG (Retrieval-Augmented Generation) system with MCP (Model Context Protocol) server interface.

**Key Characteristics:**
- Two independent subsystems: **Ingest Pipeline** and **Query Server**
- Vector store abstraction over Qdrant (dense + sparse hybrid search)
- MCP protocol compliance (stdio or SSE transport) for LLM client integration
- Async Python (asyncio) throughout, with sync SQLite registry for ingest tracking
- Dual package layout: `server/` (legacy) and `kb_server/` (current) — `kb_server/` is canonical

## Layers

**MCP Server Layer:**
- Purpose: Expose RAG tools to LLM clients via MCP protocol
- Location: `kb_server/server.py`
- Contains: Tool registration (`list_tools`), dispatch (`call_tool`), tool handlers
- Depends on: `VectorStore`, `EmbedClient`, `CollectionRouter`, `QueryLogger`
- Used by: MCP clients (Claude Code, OpenCode, etc.)

**Retrieval Layer:**
- Purpose: Semantic search with optional hybrid and reranking modes
- Location: `kb_server/retrieval/`
- Contains: `hybrid_search.py` (dense+BM25 RRF fusion), `reranker.py` (cross-encoder)
- Depends on: `VectorStore`, `fastembed` (sparse), cross-encoder model
- Used by: `server.py` `_search_kb` handler

**Vector Store Layer:**
- Purpose: Qdrant abstraction for CRUD and search operations
- Location: `kb_server/vector_store.py`
- Contains: `VectorStore` class — connect, upsert_chunks, search, list_documents, get_stats
- Depends on: `qdrant_client` (AsyncQdrantClient), `embed_client`
- Used by: server, ingest pipeline

**Embedding Client Layer:**
- Purpose: Backend-agnostic embedding generation with caching
- Location: `kb_server/embed_client.py`
- Contains: Multi-backend support: `lmstudio-sdk`, `lmstudio-rest`, `openai-compat`, `ollama`
- Depends on: `httpx`, `CacheManager`, `MetricsCollector`
- Used by: `VectorStore`, `ingest/ingest.py`

**Collection Management Layer:**
- Purpose: Qdrant collection lifecycle and multi-collection routing
- Location: `kb_server/collections/`
- Contains: `CollectionManager` (CRUD), `CollectionRouter` (request routing, default resolution)
- Depends on: `qdrant_client.AsyncQdrantClient`
- Used by: `server.py` main() initialization and tool handlers

**Ingest Pipeline Layer:**
- Purpose: Document ingestion — extraction, chunking, embedding, indexing
- Location: `ingest/`
- Contains: `ingest.py` (orchestrator), `parsers/` (file extractors), `registry.py` (SQLite dedup), `classifier.py` (metadata detection), `validation/` (pipeline validation), `worker/` (async workers), `job/` (job scheduling), `watcher/` (filesystem watch)
- Depends on: `VectorStore`, `EmbedClient`, `langchain_text_splitters`, document libs
- Used by: CLI, file watcher, job scheduler

**Observability Layer:**
- Purpose: Metrics, logging, telemetry
- Location: `observability/`, `kb_server/telemetry/`, `kb_server/analytics/`
- Contains: `MetricsCollector`, `QueryLogger` (SQLite), `query_analyzer.py`
- Depends on: Prometheus metrics (optional)
- Used by: All layers

**Cache Layer:**
- Purpose: Embedding caching to reduce LLM API calls
- Location: `kb_server/cache/`
- Contains: `CacheManager`, `lru.py` (in-memory LRU), `redis.py` (optional Redis)
- Depends on: Optional Redis
- Used by: `embed_client.py`

## Data Flow

**Query Flow (MCP Tool Call):**
1. MCP client sends `call_tool("search_kb", {...})` over stdio or SSE
2. `server.py` dispatches to `_search_kb(args)`
3. `embed_client.get_embedding(query)` → vector (with cache check)
4. If `hybrid=True`: `HybridSearcher.search()` → RRF fusion of dense + BM25
5. Else: `VectorStore.search(vector, filters)` → Qdrant dense search
6. If `rerank=True`: `Reranker.rerank(query, results)` → cross-encoder rerank
7. `QueryLogger.log_query(...)` → async write to SQLite
8. Format markdown response → `TextContent` list returned to MCP client

**Ingest Flow:**
1. CLI or file watcher triggers `run_ingest(docs_path, ...)`
2. Files scanned from disk, filtered by `EXT_TYPE_MAP`
3. `IngestRegistry.needs_ingest(file)` → SHA256 dedup check (SQLite)
4. `classifier.classify(file)` → detects product, doc_type, version from path/filename
5. `EXTRACTORS[file_type](file)` → raw text sections (PDF/DOCX/XLSX/PPTX/TXT/code)
6. `chunk_text(text, file_type)` → LangChain `RecursiveCharacterTextSplitter`
7. `embed_client.get_embeddings_batch(texts)` → batch vectors
8. `VectorStore.upsert_chunks(chunks_with_vectors)` → upserted to Qdrant
9. `IngestRegistry.mark_ok(file, chunks)` → update SQLite registry

**State Management:**
- Qdrant: persistent vector store for all indexed chunks and metadata
- SQLite (`data/registry.db`): ingest registry (file hashes, chunk counts, status)
- SQLite (`data/kb_metadata.db`): query logs for analytics
- In-memory LRU + optional Redis: embedding cache

## Key Abstractions

**VectorStore:**
- Purpose: Single interface to Qdrant — search, upsert, list, stats
- Examples: `kb_server/vector_store.py`
- Pattern: Async class with lazy `connect()`, supports HTTP/gRPC/embedded modes

**IngestRegistry:**
- Purpose: Track which files have been indexed and their SHA256 hash
- Examples: `ingest/registry.py`
- Pattern: SQLite-backed class with `needs_ingest()` / `mark_ok()` / `mark_error()` / `mark_deleted()`

**EmbedClient:**
- Purpose: Backend-agnostic embedding, returns float vectors
- Examples: `kb_server/embed_client.py`
- Pattern: Module-level functions `get_embedding(text)` and `get_embeddings_batch(texts)`, backend selected by `EMBED_BACKEND` env var

**CollectionRouter:**
- Purpose: Resolve collection parameter to actual Qdrant collection name
- Examples: `kb_server/collections/router.py`
- Pattern: Async `resolve(name_or_None)` with default fallback

**HybridSearcher:**
- Purpose: Combine dense vector search with BM25 sparse via RRF
- Examples: `kb_server/retrieval/hybrid_search.py`
- Pattern: Singleton via `get_hybrid_searcher()`, lazy sparse model loading

## Entry Points

**MCP Server:**
- Location: `kb_server/server.py` → `main()` / `if __name__ == "__main__": asyncio.run(main())`
- Triggers: `python -m kb_server.server` or via MCP client config
- Responsibilities: Connect VectorStore, init CollectionManager/Router, serve MCP tools via stdio or SSE

**Ingest CLI:**
- Location: `ingest/ingest.py` → `main()`
- Triggers: `python ingest/ingest.py --docs /path` or `python ingest/ingest.py --file /path`
- Responsibilities: Process files, chunk, embed, upsert to Qdrant

**Ingest CLI (new-style):**
- Location: `ingest/cli/main.py`
- Triggers: via `kb-ingest` entrypoint (defined in `setup.py`)
- Responsibilities: New structured CLI with subcommands (job, db, export, progress, legacy)

**File Watcher:**
- Location: `ingest/watcher/file_watcher.py`
- Triggers: Filesystem events
- Responsibilities: Watch a directory, auto-ingest on file changes

**Health Server:**
- Location: `kb_server/health_server.py`
- Triggers: Started alongside MCP server
- Responsibilities: HTTP health check endpoint for deployment probes

## Error Handling

**Strategy:** Catch-and-log at tool handler level; individual components return empty/None on failure; ingest uses registry to track errors per-file.

**Patterns:**
- Tool calls wrapped in try/except in `server.py:call_tool()` → returns error TextContent
- Ingest: per-file try/except with `registry.mark_error(file, msg)`
- Embedding failures: propagate up to caller (critical path)
- Hybrid search / reranking: fallback to non-hybrid / original results on failure
- Query logging: non-fatal; logged but never raises

## Cross-Cutting Concerns

**Logging:** `logging` stdlib, configured at entry points with StreamHandler + FileHandler. Logger names follow `kb-mcp.*` and `kb-ingest.*` hierarchy.

**Validation:** `ingest/validation/` pipeline — format, size, content validators with base class `ingest/validation/base.py`.

**Authentication:** None at MCP protocol level. Embedding API auth via `LMS_BASE_URL` / `OLLAMA_HOST` env vars.

---

*Architecture analysis: 2026-05-19*
