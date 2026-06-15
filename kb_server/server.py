"""
KB RAG MCP Server — exposes semantic search tools over the MCP protocol.

Provides search_kb, list_documents, get_chunk, kb_stats, and list_collections
tools for AI assistants (Claude Code, OpenCode, Cursor, Copilot) to query
a local knowledge base of ingested documentation. Supports both stdio and SSE
transports, hybrid search (dense + BM25 sparse), cross-encoder reranking,
multi-collection routing, and query logging.
"""

import asyncio
import contextvars
import hashlib
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# ── Load .env before any os.getenv reads
from config.bootstrap_env import bootstrap_env

bootstrap_env()

import mcp.types as types
from kb_server.embed_client import get_embedding
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from kb_server.vector_store import VectorStore
from kb_server.observability.percentiles import get_percentile_tracker
from kb_server.telemetry.query_logger import QueryLogger
from kb_server.collections.manager import CollectionManager
from kb_server.collections.router import (
    CollectionRouter,
    CollectionNotFoundError,
)
from kb_server.auth.router import router as auth_router
from kb_server.auth.service import AuthService
from kb_server.auth.erasure import ErasureManager
from kb_server.filter_terms_cache import FilterTermsCache  # PHASE 17
from observability.metrics import (
    record_query,
    record_query_error,
    record_rate_limit_allowed,
    record_rate_limit_rejected,
    record_retrieval_cache_op,
    update_rate_limit_subjects,
    record_active_sessions,  # PHASE 28
    record_session_evicted,  # PHASE 28
)
from kb_server.cache.request_cache import RetrievalCache  # PHASE 37

# ── Logging ───────────────────────────────────────────────────────
_log_path = os.getenv("LOG_PATH", "/tmp/kb-mcp.log")
os.makedirs(os.path.dirname(_log_path), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(_log_path),
    ],
)
log = logging.getLogger("kb-mcp")


def _hash_subject(subject: str) -> str:
    """Produce a stable, non-reversible rate-limit subject identifier."""
    return hashlib.sha256(subject.encode()).hexdigest()[:16]

# ── Config ────────────────────────────────────────────────────────
TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")  # stdio | sse
SSE_HOST = os.getenv("SSE_HOST", "127.0.0.1")
SSE_PORT = int(os.getenv("SSE_PORT", "8765"))
TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))

# PHASE 33: Rate limiting config
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() in (
    "true",
    "1",
    "yes",
)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# Per-subject tracking for rate limiting across transport sessions
_current_subject: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_subject", default=None
)
_current_transport: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_transport", default="stdio"
)

# PHASE 37: Retrieval cache configuration
RLCACHE_ENABLED = os.getenv("RLCACHE_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
RLCACHE_TTL = int(os.getenv("RLCACHE_TTL", "300"))
RLCACHE_MAX_ENTRIES = int(os.getenv("RLCACHE_MAX_ENTRIES", "1000"))

# PHASE 14: Query logging configuration
QUERY_LOG_ENABLED = os.getenv("QUERY_LOG_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
QUERY_LOG_PATH = Path(os.getenv("QUERY_LOG_PATH", "data/kb_metadata.db"))
QUERY_LOG_RETENTION_DAYS = int(os.getenv("QUERY_LOG_RETENTION_DAYS", "90"))
QUERY_LOG_CLEANUP_INTERVAL_HOURS = int(
    os.getenv("QUERY_LOG_CLEANUP_INTERVAL_HOURS", "24")
)

# ── Initialization ────────────────────────────────────────────────
app = Server("kb-rag")
store = VectorStore()
collection_manager: CollectionManager | None = None
collection_router: CollectionRouter | None = None
filter_terms_cache: FilterTermsCache | None = None  # PHASE 17

# PHASE 33: Initialize rate limiter (lazy, configured in main())
rate_limiter = None

# PHASE 37: Initialize retrieval cache if enabled
retrieval_cache: RetrievalCache | None = None
if RLCACHE_ENABLED:
    try:
        retrieval_cache = RetrievalCache(
            max_entries=RLCACHE_MAX_ENTRIES,
            ttl=RLCACHE_TTL,
        )
        log.info(
            "Retrieval cache enabled: max_entries=%d ttl=%d",
            RLCACHE_MAX_ENTRIES,
            RLCACHE_TTL,
        )
    except Exception as e:
        log.error(f"Failed to initialise retrieval cache: {e}")
        log.warning("Continuing without retrieval caching")

# PHASE 14: Initialize query logger if enabled
query_logger = None
if QUERY_LOG_ENABLED:
    try:
        query_logger = QueryLogger(db_path=QUERY_LOG_PATH)
        log.info(f"Query logging enabled: {QUERY_LOG_PATH}")
    except Exception as e:
        log.error(f"Failed to initialize query logger: {e}")
        log.warning("Continuing without query logging")


# ──────────────────────────────────────────────────────────────────
# TOOLS
# ──────────────────────────────────────────────────────────────────


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List all available MCP tools exposed by this server.

    Returns tool definitions for search_kb, list_documents, get_chunk,
    kb_stats, and list_collections, each with input schema for the client.

    Returns:
        List of Tool definitions with name, description, and inputSchema.
    """
    # PHASE 17: Get dynamic filter descriptions for tool parameters
    dyn_descs = {}
    if filter_terms_cache:
        await filter_terms_cache.refresh_if_needed()
        dyn_descs = filter_terms_cache.get_all_formatted(top_n=20)

    def _fmt(field: str, default: str) -> str:
        """Return dynamic description if available, else default."""
        return dyn_descs.get(field, default)

    doc_type_enum = [
        "admin_guide",
        "install_guide",
        "upgrade_guide",
        "config_guide",
        "user_guide",
        "api_guide",
        "release_notes",
        "howto",
        "training",
        "overview",
        "reference",
        "standard",
        "meeting",
        "release_artifact",
        "document",
    ]
    return [
        types.Tool(
            name="search_kb",
            description=(
                "Semantic search across the local documentation knowledge base "
                "of technical documentation and standards. "
                "Returns the most relevant chunks with score, source, and "
                "metadata. "
                "Filter by product (e.g. 'AppServer', 'DataSync', 'AdminPortal') "
                "and/or doc_type (e.g. 'install_guide', 'release_notes', "
                "'standard', 'training') for more precise results. "
                "Use whenever you need information about installation, "
                "configuration, APIs, upgrades, ISO standards, "
                "or code examples."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query or term to search in the knowledge base",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results (default: 5, max: 20)",
                        "default": TOP_K,
                        "minimum": 1,
                        "maximum": 20,
                    },
                    "product": {
                        "type": "string",
                        "description": (
                            "Filter by product. "
                            f"{_fmt('product', 'Examples: AppServer, DataSync, AdminPortal, Adobe, SAP, ISO, general')}"
                        ),
                    },
                    "doc_type": {
                        "type": "string",
                        "description": (
                            "Filter by content type. "
                            f"{_fmt('doc_type', 'admin_guide=administration, install_guide=installation, upgrade_guide=upgrade/migration, config_guide=configuration, release_notes=release notes, api_guide=API/SDK, howto=tutorials/case studies, training=training, overview=overview, standard=ISO standards/regulations, reference=technical reference')}"
                        ),
                        "enum": doc_type_enum,
                    },
                    "version": {
                        "type": "string",
                        "description": (
                            "PHASE 13: Filter by product version. "
                            "Examples: 22.3, CE 24.4, v2.5. "
                            "Use to search documentation for a specific version."
                        ),
                    },
                    "vendor": {
                        "type": "string",
                        "description": (
                            "PHASE 11.1: Filter by vendor. "
                            f"{_fmt('vendor', 'Examples: OpenText, Adobe, SAP, ISO, general')}"
                        ),
                    },
                    "subsystem": {
                        "type": "string",
                        "description": (
                            "PHASE 11.1: Filter by subsystem/module within a product. "
                            f"{_fmt('subsystem', '')}"
                        ),
                    },
                    "module": {
                        "type": "string",
                        "description": (
                            "PHASE 17: Filter by module/sub-module within a "
                            "product. "
                            f"{_fmt('module', 'Examples: Administration, Configuration, API, Security, Connectors, User Management')}"
                        ),
                    },
                    "filter_type": {
                        "type": "string",
                        "description": "Filter by file format: pdf, "
                        "docx, xlsx, pptx, txt, code",
                        "enum": ["pdf", "docx", "xlsx", "pptx", "txt", "code"],
                    },
                    "hybrid": {
                        "type": "boolean",
                        "description": (
                            "PHASE 12: Use hybrid search (dense + BM25 sparse). "
                            "Improves recall for specific technical terms "
                            "(versions, codes, exact names)"
                        ),
                        "default": False,
                    },
                    "rerank": {
                        "type": "boolean",
                        "description": (
                            "PHASE 12: Apply cross-encoder reranking. "
                            "Improves top result precision "
                            "(adds ~200ms latency)"
                        ),
                        "default": False,
                    },
                    "collection": {
                        "type": "string",
                        "description": (
                            "PHASE 15: Name of the Qdrant collection to query. "
                            "Omit to use the default collection (QDRANT_COLLECTION)."
                        ),
                    },
                    "kb_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "PHASE 35: Search across multiple knowledge bases. "
                            "Provide a list of KB identifiers (e.g. kb_main, kb_hr). "
                            "Results are merged with RRF fusion and deduplication. "
                            "Omit to search a single KB using the collection parameter "
                            "or default collection."
                        ),
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="list_documents",
            description=(
                "List indexed documents in the knowledge base. "
                "Useful for discovering which documents are available "
                "before searching. "
                "Filter by product and/or doc_type to navigate by category."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "product": {
                        "type": "string",
                        "description": "Filter by product "
                        "(e.g. AppServer, DataSync, AdminPortal)",
                    },
                    "doc_type": {
                        "type": "string",
                        "description": "Filter by content type",
                        "enum": doc_type_enum,
                    },
                    "filter_type": {
                        "type": "string",
                        "description": "Filter by format: "
                        "pdf, docx, xlsx, pptx, txt, code",
                        "enum": ["pdf", "docx", "xlsx", "pptx", "txt", "code"],
                    },
                    "vendor": {
                        "type": "string",
                        "description": (
                            "PHASE 11.1: Filter by vendor "
                            "(e.g. OpenText, Adobe, SAP)"
                        ),
                    },
                    "subsystem": {
                        "type": "string",
                        "description": (
                            "PHASE 11.1: Filter by subsystem/module"
                        ),
                    },
                    "module": {
                        "type": "string",
                        "description": (
                            "PHASE 17: Filter by module/sub-module "
                            "within a product"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return "
                        "(default: 50)",
                        "default": 50,
                    },
                    "collection": {
                        "type": "string",
                        "description": (
                            "PHASE 15: Name of the Qdrant collection to query. "
                            "Omit to use the default collection."
                        ),
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_chunk",
            description=(
                "Returns the full content of a specific chunk "
                "with expanded context. "
                "Use after search_kb when you need the complete text "
                "of a result."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "string",
                        "description": "Chunk ID (returned by " "search_kb)",
                    },
                    "context_window": {
                        "type": "integer",
                        "description": "Neighboring chunks to include for "
                        "context (0-3, default: 1)",
                        "default": 1,
                        "minimum": 0,
                        "maximum": 3,
                    },
                },
                "required": ["chunk_id"],
            },
        ),
        types.Tool(
            name="kb_stats",
            description="KB statistics: total documents, chunks, "
            "breakdown by product and content type.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="list_collections",
            description=(
                "PHASE 15: List all available Qdrant collections. "
                "Use to discover collections before calling search_kb "
                "or list_documents with the collection parameter."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="list_filter_options",
            description=(
                "PHASE 17: List available filter values for knowledge base "
                "attributes. Use to discover valid values for product, vendor, "
                "subsystem, module, version, doc_type, and file_type filters "
                "before searching. Omit field to see all attributes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "Attribute to list values for "
                        "(e.g. product, vendor, subsystem, module, version, "
                        "doc_type, filter_type). Omit to list all attributes.",
                    },
                    "collection": {
                        "type": "string",
                        "description": (
                            "PHASE 15: Qdrant collection name. "
                            "Omit to use the default collection."
                        ),
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_related_documents",
            description=(
                "PHASE 30: Find all chunks belonging to a specific document "
                "by its graph ID. Use to retrieve the full content of a "
                "document that appeared in search results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_graph_id": {
                        "type": "string",
                        "description": (
                            "Graph document ID (returned in search results "
                            "as doc_graph_id field)"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum chunks to return (default: 20)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "collection": {
                        "type": "string",
                        "description": (
                            "Qdrant collection name. Omit to use the "
                            "default collection."
                        ),
                    },
                },
                "required": ["doc_graph_id"],
            },
        ),
        types.Tool(
            name="explore_topic",
            description=(
                "PHASE 30: Search for documents by topic label. Topics "
                "are derived from product, doc_type, vendor, subsystem, "
                "and module classification metadata. Use to discover "
                "documents related to a specific topic or area."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "Topic label to search for. Examples: "
                            "AppServer, Install Guide, REST, API, "
                            "OpenText, DataSync"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum chunks to return (default: 20)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "collection": {
                        "type": "string",
                        "description": (
                            "Qdrant collection name. Omit to use the "
                            "default collection."
                        ),
                    },
                },
                "required": ["topic"],
            },
        ),
    ]


# ── PHASE 31: Prompt templates ────────────────────────────────────────


@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    """List all available MCP prompt templates.

    Returns definitions for extract_answer and summarize_documents
    prompts, each with their argument schemas.
    """
    from kb_server.prompts import PROMPT_DEFINITIONS

    return list(PROMPT_DEFINITIONS.values())


@app.get_prompt()
async def get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """Return rendered prompt content for a named prompt.

    Args:
        name: Prompt name (must be registered in PROMPT_DEFINITIONS).
        arguments: String-keyed arguments for prompt rendering.

    Returns:
        GetPromptResult with rendered messages and description.

    Raises:
        ValueError: If the prompt name is unknown.
    """
    from kb_server.prompts import render_prompt

    return render_prompt(name, arguments)


@app.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    """Dispatch a tool call by name with the given arguments.

    Routes tool names to their handler functions (search_kb, list_documents,
    get_chunk, kb_stats, list_collections). Wraps all exceptions into a
    structured error response.

    Args:
        name: Tool name to invoke.
        arguments: Dictionary of arguments for the tool.

    Returns:
        List of TextContent responses with results or error message.
    """
    start = time.time()

    # PHASE 33: Rate-limit check for tool calls
    if RATE_LIMIT_ENABLED and rate_limiter is not None:
        subject = _hash_subject(
            _current_subject.get() or "unknown"
        )
        transport = _current_transport.get()
        allowed, retry_after = await rate_limiter.check(subject)
        if not allowed:
            record_rate_limit_rejected(transport)
            log.warning(
                "Rate limit exceeded for subject=%s transport=%s tool=%s",
                subject,
                transport,
                name,
            )
            return [
                types.TextContent(
                    type="text",
                    text=(
                        "Rate limit exceeded. "
                        f"Please retry after {retry_after} seconds."
                    ),
                )
            ]
        record_rate_limit_allowed(transport)

    try:
        if name == "search_kb":
            result = await _search_kb(arguments)
        elif name == "list_documents":
            result = await _list_documents(arguments)
        elif name == "get_chunk":
            result = await _get_chunk(arguments)
        elif name == "kb_stats":
            result = await _kb_stats()
        elif name == "list_collections":
            result = await _list_collections()
        elif name == "list_filter_options":
            result = await _list_filter_options(arguments)
        elif name == "get_related_documents":
            result = await _get_related_documents(arguments)
        elif name == "explore_topic":
            result = await _explore_topic(arguments)
        else:
            result = [
                types.TextContent(type="text", text=f"Unknown tool: {name}")
            ]
        elapsed = time.time() - start
        record_query(name, "success", elapsed)
        if name in ("search_kb", "list_documents", "get_chunk", "kb_stats"):
            get_percentile_tracker().record(name, elapsed * 1000)
        return result
    except Exception as e:
        latency = time.time() - start
        log.error(f"Error in {name}: {e}", exc_info=True)
        record_query(name, "error", latency)
        record_query_error(name)
        return [
            types.TextContent(
                type="text", text=f"Error executing {name}: {str(e)}"
            )
        ]


# ──────────────────────────────────────────────────────────────────
# HANDLERS
# ──────────────────────────────────────────────────────────────────


async def _search_kb(args: dict) -> list[types.TextContent]:
    start_time = time.time()

    query = args["query"]
    top_k = args.get("top_k", TOP_K)
    filter_type = args.get("filter_type")
    product = args.get("product")
    doc_type = args.get("doc_type")
    version = args.get("version")  # PHASE 13: Version filter
    vendor = args.get("vendor")  # PHASE 11.1: Vendor filter
    subsystem = args.get("subsystem")  # PHASE 11.1: Subsystem filter
    module = args.get("module")  # PHASE 17: Module filter
    hybrid = args.get("hybrid", False)
    rerank = args.get("rerank", False)
    collection_param = args.get("collection")
    kb_ids = args.get("kb_ids")  # PHASE 35: Multi-KB

    # PHASE 15: resolve target collection (raises CollectionNotFoundError if missing)
    target_collection = getattr(store, "collection", None)
    if collection_router is not None and not kb_ids:
        try:
            target_collection = await collection_router.resolve(
                collection_param
            )
        except CollectionNotFoundError as exc:
            return [types.TextContent(type="text", text=str(exc))]

    # PHASE 35: Resolve multi-KB collection list
    if collection_router is not None and kb_ids:
        try:
            multi_collections = await collection_router.resolve_multi(kb_ids)
        except CollectionNotFoundError as exc:
            return [types.TextContent(type="text", text=str(exc))]
    else:
        multi_collections = []

    log.info(
        f"search_kb: '{query}' top_k={top_k} product={product} "
        f"doc_type={doc_type} version={version} vendor={vendor} "
        f"subsystem={subsystem} module={module} file_type={filter_type} "
        f"hybrid={hybrid} rerank={rerank} kb_ids={kb_ids}"
    )

    # ── PHASE 37: Check retrieval cache ─────────────────────────────────
    results = None
    cache_key = None
    if retrieval_cache is not None and retrieval_cache.enabled:
        cache_key = retrieval_cache.make_key(
            query=query,
            top_k=top_k,
            filter_type=filter_type,
            product=product,
            doc_type=doc_type,
            version=version,
            vendor=vendor,
            subsystem=subsystem,
            module=module,
            hybrid=hybrid,
            rerank=rerank,
            collection_param=collection_param,
            kb_ids=kb_ids,
        )
        cached_results = retrieval_cache.get(cache_key)
        if cached_results is not None:
            results = cached_results
            record_retrieval_cache_op("hit")
            log.info(
                "Retrieval cache hit: key=%s query='%s' results=%d",
                cache_key[:16],
                query,
                len(results),
            )
        else:
            record_retrieval_cache_op("miss")

    if results is None:
        # ── Full search pipeline (cache miss) ─────────────────────
        vector = await get_embedding(query)

        # PHASE 12: Determine retrieve_k for reranking
        retrieve_k = top_k
        if rerank:
            retrieve_k = min(top_k * 4, 20)
            log.info(
                f"Reranking enabled: retrieving {retrieve_k} for reranking to {top_k}"
            )

        # PHASE 35: Multi-KB aggregated search path
        if multi_collections:
            from kb_server.retrieval.hybrid_search import (
                merge_multi_collection_results,
            )

            per_collection = await store.multi_search(
                vector=vector,
                collection_names=multi_collections,
                top_k=retrieve_k,
                filter_type=filter_type,
                product=product,
                doc_type=doc_type,
                version=version,
                vendor=vendor,
                subsystem=subsystem,
                module=module,
            )
            results = merge_multi_collection_results(
                per_collection, top_k=top_k
            )
            log.info(
                "Multi-KB search: %d collections → %d results",
                len(multi_collections),
                len(results),
            )
        # PHASE 12: Route to hybrid search if enabled
        elif hybrid:
            from kb_server.retrieval.hybrid_search import get_hybrid_searcher

            log.info("Using hybrid search (dense + sparse)")
            hybrid_searcher = get_hybrid_searcher()
            results = await hybrid_searcher.search(
                vector_store=store,
                query_vector=vector,
                query_text=query,
                top_k=retrieve_k,
                filter_type=filter_type,
                product=product,
                doc_type=doc_type,
                version=version,
            )
        else:
            # Standard dense vector search
            _search_kwargs: dict = dict(
                vector=vector,
                top_k=retrieve_k,
                filter_type=filter_type,
                product=product,
                doc_type=doc_type,
                version=version,  # PHASE 13
                vendor=vendor,  # PHASE 11.1
                subsystem=subsystem,  # PHASE 11.1
                module=module,  # PHASE 17
            )
            if target_collection is not None:
                _search_kwargs["collection_name"] = (
                    target_collection  # PHASE 15
                )
            results = await store.search(**_search_kwargs)

        # PHASE 12: Apply reranking if enabled (skip for multi-KB — already merged)
        if rerank and results and not multi_collections:
            from kb_server.retrieval.reranker import get_reranker

            log.info(
                f"Applying cross-encoder reranking to {len(results)} results"
            )
            reranker = get_reranker()
            try:
                results = await reranker.rerank(
                    query=query,
                    results=results,
                    top_k=top_k,
                )
                log.info(
                    f"Reranking complete: {len(results)} results returned"
                )
            except Exception as e:
                log.error(f"Reranking failed: {e}", exc_info=True)
                log.warning("Falling back to original results")
                results = results[:top_k]

    # ── PHASE 37: Store results in retrieval cache ────────────────
    if cache_key is not None and retrieval_cache is not None:
        retrieval_cache.put(cache_key, results)

    if not results:
        latency_ms = (time.time() - start_time) * 1000
        if query_logger:
            try:
                filters = {}
                if product:
                    filters["product"] = product
                if doc_type:
                    filters["doc_type"] = doc_type
                if filter_type:
                    filters["file_type"] = filter_type

                query_logger.log_query(
                    query_text=query,
                    top_k=top_k,
                    score_threshold=None,
                    filters=filters if filters else None,
                    version_filter=version,
                    result_count=0,
                    scores=[],
                    latency_ms=latency_ms,
                )
            except Exception as e:
                log.error(f"Failed to log query: {e}")

        return [
            types.TextContent(
                type="text",
                text="No results found in the knowledge base"
                " for this query.",
            )
        ]

    lines = [f'## Results for: "{query}"\n']

    mode_indicators = []
    if multi_collections:
        mode_indicators.append(f"multi-KB ({', '.join(multi_collections)})")
    if hybrid:
        mode_indicators.append("hybrid")
    if rerank:
        mode_indicators.append("reranked")
    if mode_indicators:
        lines.append(f"*Search {' + '.join(mode_indicators)}*\n")

    for i, r in enumerate(results, 1):
        score_pct = f"{r['score'] * 100:.1f}%"
        source = r["source_file"]
        coll_tag = r.get("_collection", "")
        meta = (
            f"**ID:** `{r['chunk_id']}`  |  "
            f"**Product:** {r.get('product','n/a')}  |  "
            f"**Type:** {r.get('doc_type','n/a')}  |  "
            f"**Format:** {r['file_type']}"
        )
        if coll_tag:
            source = f"{source} [KB: {coll_tag}]"
            meta = (
                f"**ID:** `{r['chunk_id']}`  |  "
                f"**KB:** `{coll_tag}`  |  "
                f"**Product:** {r.get('product','n/a')}  |  "
                f"**Type:** {r.get('doc_type','n/a')}"
            )
        lines.append(f"### [{i}] {source}  (relevance: {score_pct})")
        lines.append(meta)
        if r.get("page"):
            lines.append(f"**Page/section:** {r['page']}")
        lines.append("")
        lines.append(r["text"])
        lines.append("\n---")

    lines.append("\n*Use `get_chunk` with the ID to get expanded context.*")

    latency_ms = (time.time() - start_time) * 1000
    if query_logger:
        try:
            filters = {}
            if product:
                filters["product"] = product
            if doc_type:
                filters["doc_type"] = doc_type
            if filter_type:
                filters["file_type"] = filter_type

            scores = [r["score"] for r in results]

            query_logger.log_query(
                query_text=query,
                top_k=top_k,
                score_threshold=None,
                filters=filters if filters else None,
                version_filter=version,
                result_count=len(results),
                scores=scores,
                latency_ms=latency_ms,
            )
        except Exception as e:
            log.error(f"Failed to log query: {e}")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _list_documents(args: dict) -> list[types.TextContent]:
    collection_param = args.get("collection")
    target_collection = getattr(store, "collection", None)
    if collection_router is not None:
        try:
            target_collection = await collection_router.resolve(
                collection_param
            )
        except CollectionNotFoundError as exc:
            return [types.TextContent(type="text", text=str(exc))]

    _list_kwargs: dict = dict(
        filter_type=args.get("filter_type"),
        product=args.get("product"),
        doc_type=args.get("doc_type"),
        vendor=args.get("vendor"),  # PHASE 11.1
        subsystem=args.get("subsystem"),  # PHASE 11.1
        module=args.get("module"),  # PHASE 17
        limit=args.get("limit", 50),
    )
    if target_collection is not None:
        _list_kwargs["collection_name"] = target_collection  # PHASE 15
    docs = await store.list_documents(**_list_kwargs)

    if not docs:
        return [
            types.TextContent(
                type="text", text="No documents indexed in the knowledge base."
            )
        ]

    lines = [f"## Documents in the Knowledge Base ({len(docs)} found)\n"]
    by_dt: dict[str, list] = {}
    for d in docs:
        by_dt.setdefault(d.get("doc_type", "document"), []).append(d)

    for dt, items in sorted(by_dt.items()):
        lines.append(f"### {dt}  ({len(items)} documents)")
        for d in items:
            vendor_info = (
                f" | vendor: {d.get('vendor','n/a')}"
                if d.get("vendor")
                else ""
            )
            subsystem_info = (
                f" | subsystem: {d.get('subsystem','n/a')}"
                if d.get("subsystem")
                else ""
            )
            module_info = (
                f" | module: {d.get('module','n/a')}"
                if d.get("module")
                else ""
            )
            lines.append(
                f"- `{d['source_file']}` — {d['chunk_count']} chunks"
                f" | product: {d.get('product','n/a')}"
                f"{vendor_info}"
                f"{subsystem_info}"
                f"{module_info}"
                f" | format: {d['file_type']}"
            )
        lines.append("")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _get_chunk(args: dict) -> list[types.TextContent]:
    chunk_id = args["chunk_id"]
    context = args.get("context_window", 1)

    chunks = await store.get_chunk_with_context(chunk_id, context)
    if not chunks:
        return [
            types.TextContent(
                type="text", text=f"Chunk `{chunk_id}` not found."
            )
        ]

    lines = [f"## Chunk `{chunk_id}` with context\n"]
    for c in chunks:
        marker = "→ **[requested chunk]**" if c["chunk_id"] == chunk_id else ""
        lines.append(
            f"### {c['source_file']} — chunk {c['chunk_index']} {marker}"
        )
        lines.append(c["text"])
        lines.append("")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _kb_stats() -> list[types.TextContent]:
    stats = await store.get_stats()
    lines = [
        "## Knowledge Base — Statistics\n",
        f"- **Total documents:** {stats['total_documents']}",
        f"- **Total chunks:** {stats['total_chunks']}",
        f"- **Index size:** {stats['index_size_mb']:.1f} MB",
        f"- **Embedding model:** {stats['embed_model']}",
        f"- **Vector dimensions:** {stats['embed_dim']}",
        "\n**By content type (doc_type):**",
    ]
    for dt, count in sorted(stats["by_doc_type"].items(), key=lambda x: -x[1]):
        lines.append(f"  - {dt}: {count} documents")

    lines.append("\n**By file format:**")
    for ft, count in sorted(
        stats["by_file_type"].items(), key=lambda x: -x[1]
    ):
        lines.append(f"  - {ft}: {count} documents")

    return [types.TextContent(type="text", text="\n".join(lines))]


# ──────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ──────────────────────────────────────────────────────────────────


async def _list_collections() -> list[types.TextContent]:
    """PHASE 15: List all Qdrant collections."""
    if collection_manager is None:
        return [
            types.TextContent(
                type="text", text="CollectionManager not initialized."
            )
        ]
    names = await collection_manager.list_collections()
    if not names:
        return [types.TextContent(type="text", text="No collections found.")]
    lines = [f"## Available collections ({len(names)})\n"]
    for name in sorted(names):
        marker = " ← default" if name == store.collection else ""
        lines.append(f"- `{name}`{marker}")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _list_filter_options(args: dict) -> list[types.TextContent]:
    """PHASE 17: List available filter values for KB attributes.

    Returns distinct values with counts for each advertised attribute
    field. Can be filtered to a single field or collection.
    """
    field = args.get("field")
    collection_param = args.get("collection")

    target_collection = getattr(store, "collection", None)
    if collection_router is not None and collection_param:
        try:
            target_collection = await collection_router.resolve(
                collection_param
            )
        except CollectionNotFoundError as exc:
            return [types.TextContent(type="text", text=str(exc))]

    if filter_terms_cache is not None:
        await filter_terms_cache.refresh_if_needed()
        terms = filter_terms_cache.terms
    else:
        terms = {}

    if field:
        values = terms.get(field, [])
        if not values:
            return [
                types.TextContent(
                    type="text",
                    text=f"No values found for field '{field}'.",
                )
            ]
        lines = [f"## Filter Options: {field}\n"]
        if target_collection:
            lines.append(f"Collection: `{target_collection}`  \n")
        lines.append(f"**{len(values)}** distinct values:\n")
        for item in values:
            lines.append(f"- `{item['value']}` - {item['count']} document(s)")
        return [types.TextContent(type="text", text="\n".join(lines))]

    lines = ["## Filter Options\n"]
    if target_collection:
        lines.append(f"Collection: `{target_collection}`  \n")

    for f, values in sorted(terms.items()):
        if values:
            lines.append(
                f"**{f.replace('_', ' ').title()}** "
                f"({len(values)} values):\n"
            )
            for item in values[:10]:
                lines.append(
                    f"- `{item['value']}` - {item['count']} document(s)"
                )
            if len(values) > 10:
                lines.append(
                    f"  *(+{len(values) - 10} more - "
                    f'use `field="{f}"` for full list)*\n'
                )
        else:
            lines.append(
                f"**{f.replace('_', ' ').title()}**: "
                f"(no values ingested)\n"
            )
        lines.append("")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _get_related_documents(
    args: dict,
) -> list[types.TextContent]:
    """PHASE 30: Find chunks by doc_graph_id."""
    doc_graph_id = args["doc_graph_id"]
    limit = min(args.get("limit", 20), 100)
    collection_param = args.get("collection")

    target = getattr(store, "collection", None)
    if collection_router is not None and collection_param:
        try:
            target = await collection_router.resolve(collection_param)
        except CollectionNotFoundError as exc:
            return [types.TextContent(type="text", text=str(exc))]

    chunks = await store.list_documents_by_graph_id(
        doc_graph_id=doc_graph_id,
        limit=limit,
        collection_name=target,
    )
    if not chunks:
        return [
            types.TextContent(
                type="text",
                text=f"No documents found for graph ID `{doc_graph_id}`.",
            )
        ]

    lines = [
        f"## Related documents for `{doc_graph_id}` "
        f"({len(chunks)} chunks)\n"
    ]
    for c in chunks:
        lines.append(
            f"**{c.get('source_file', '?')}** "
            f"— chunk {c.get('chunk_index', '?')} "
            f"[{c.get('product', '?')}]"
        )
        text = c.get("text", "")
        if len(text) > 200:
            text = text[:200] + "..."
        lines.append(text)
        lines.append("")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _explore_topic(
    args: dict,
) -> list[types.TextContent]:
    """PHASE 30: Search for documents by topic label."""
    topic = args["topic"]
    limit = min(args.get("limit", 20), 100)
    collection_param = args.get("collection")

    target = getattr(store, "collection", None)
    if collection_router is not None and collection_param:
        try:
            target = await collection_router.resolve(collection_param)
        except CollectionNotFoundError as exc:
            return [types.TextContent(type="text", text=str(exc))]

    from qdrant_client.models import (
        FieldCondition,
        Filter,
        MatchValue,
    )

    query_filter = Filter(
        must=[
            FieldCondition(
                key="graph_topics",
                match=MatchValue(value=topic),
            )
        ]
    )
    results, _ = await store.client.scroll(
        collection_name=target or store.collection,
        scroll_filter=query_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        return [
            types.TextContent(
                type="text",
                text=f"No documents found for topic `{topic}`.",
            )
        ]

    lines = [f"## Documents for topic `{topic}` " f"({len(results)} chunks)\n"]
    seen: set[str] = set()
    for r in results:
        sf = r.payload.get("source_file", "")
        if sf not in seen:
            seen.add(sf)
            lines.append(
                f"- **{sf}**  "
                f"[{r.payload.get('product', '?')}] — "
                f"{r.payload.get('doc_type', '?')}"
            )

    lines.append(
        f"\n*Total: {len(seen)} unique documents, " f"{len(results)} chunks*"
    )
    return [types.TextContent(type="text", text="\n".join(lines))]


def _auth_header_to_subject_prefix(header: str | None) -> str | None:
    """Derive a rate-limit subject from an Authorization header value.

    Returns the first 8 characters of the bearer token (key prefix)
    or ``None`` if the header is not a valid bearer token.
    """
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    key = parts[1].strip()
    return key[:8] if len(key) >= 8 else key


async def _update_rate_limit_subject_metric() -> None:
    """Update gauge for tracked rate-limit subjects."""
    if rate_limiter is not None:
        count = await rate_limiter.subject_count()
        update_rate_limit_subjects(count)


async def _schedule_metric_updates() -> None:
    """Periodically update rate-limit subject gauge."""
    while True:
        await asyncio.sleep(60)
        await _update_rate_limit_subject_metric()


async def _schedule_log_cleanup() -> None:
    """CR-04: Periodically purge query log entries older than retention window.

    Interval controlled by QUERY_LOG_CLEANUP_INTERVAL_HOURS (default 24h).
    Retention window controlled by QUERY_LOG_RETENTION_DAYS (default 90d).
    """
    interval_seconds = QUERY_LOG_CLEANUP_INTERVAL_HOURS * 3600
    while True:
        await asyncio.sleep(interval_seconds)
        if query_logger:
            try:
                deleted = query_logger.cleanup_old_queries(
                    QUERY_LOG_RETENTION_DAYS
                )
                log.info(
                    f"Query log cleanup: {deleted} entries older than "
                    f"{QUERY_LOG_RETENTION_DAYS}d removed"
                )
            except Exception as e:
                log.error(f"Query log cleanup failed: {e}", exc_info=True)


# ── PHASE 37: Cache invalidation hook ────────────────────────────────────


def invalidate_retrieval_cache() -> None:
    """Clear the retrieval cache on retrieval-affecting state changes.

    Call this function after ingest, reclassification, or any other
    operation that changes the underlying data so subsequent searches
    reflect the new state.
    """
    global retrieval_cache
    if retrieval_cache is not None:
        retrieval_cache.invalidate_all()
        log.info("Retrieval cache invalidated by external signal")


class _SessionTracker:
    """Enforce max session limit via oldest-idle eviction.

    Wraps ``StreamableHTTPSessionManager`` and tracks session
    last-active times. When a new-session request arrives and
    the active count is at ``MCP_MAX_SESSIONS``, the oldest
    tracked session is evicted from the underlying manager's
    ``sessions`` dict. The mcp library automatically returns
    JSON-RPC error ``-32000`` ("Session not found") when an
    evicted client reconnects with its old session ID
    (per D-03).

    This class does NOT add or remove any sessions itself
    outside of ``evict_if_needed``; ``StreamableHTTPSessionManager``
    owns the full session lifecycle.
    """

    __slots__ = ("_mgr", "_max", "_last_active")

    def __init__(
        self,
        mgr: Any,
        max_sessions: int,
    ) -> None:
        self._mgr = mgr
        self._max = max_sessions
        self._last_active: dict[str, float] = {}

    def mark_active(self, session_id: str | None) -> None:
        """Record that *session_id* was active *now*."""
        if session_id:
            self._last_active[session_id] = time.time()

    def evict_if_needed(self) -> str | None:
        """Evict oldest idle session if at capacity.

        Returns the evicted session ID (for logging / metrics)
        or ``None`` if no eviction was needed.
        """
        sessions = self._mgr.sessions
        if len(sessions) < self._max:
            return None

        now = time.time()
        oldest_id: str | None = None
        oldest_time = now

        for sid in sessions:
            last_active = self._last_active.get(sid, now)
            if last_active <= oldest_time:
                oldest_time = last_active
                oldest_id = sid

        if oldest_id is not None:
            del self._mgr.sessions[oldest_id]
            self._last_active.pop(oldest_id, None)
            return oldest_id
        return None

    def cleanup(self) -> int:
        """Remove tracking entries for sessions no longer active.

        Returns the number of stale entries removed.
        """
        sessions = self._mgr.sessions
        stale = [sid for sid in self._last_active if sid not in sessions]
        for sid in stale:
            self._last_active.pop(sid, None)
        return len(stale)

    @property
    def active_count(self) -> int:
        """Number of active sessions in the underlying manager."""
        return len(self._mgr.sessions)


async def main():
    """Main entry point — connect to Qdrant, initialize routing, start server.

    Connects the VectorStore, initializes CollectionManager and
    CollectionRouter, schedules periodic query log cleanup, and starts
    the MCP server on either stdio or SSE transport based on the
    MCP_TRANSPORT environment variable.
    """
    global collection_manager, collection_router, rate_limiter, retrieval_cache
    log.info(f"KB RAG MCP Server starting (transport={TRANSPORT})")
    await store.connect()

    # Initialize auth service
    from pathlib import Path

    auth_db_path = Path(os.getenv("AUTH_DB_PATH", "data/auth.db"))
    auth_service = AuthService(db_path=auth_db_path)
    erasure_manager = ErasureManager(auth_service._session)

    def _build_auth_app():
        """Build a FastAPI sub-app with mounted auth router."""
        from fastapi import FastAPI

        auth_app = FastAPI()
        auth_app.state.auth_service = auth_service
        auth_app.state.erasure_manager = erasure_manager
        auth_app.include_router(auth_router)
        return auth_app

    # PHASE 33: Initialize rate limiter
    if RATE_LIMIT_ENABLED:
        from kb_server.rate_limiter import ServerRateLimiter

        rate_limiter = ServerRateLimiter(
            requests_per_minute=RATE_LIMIT_REQUESTS
            / (RATE_LIMIT_WINDOW / 60.0),
            cleanup_interval=300,
        )
        log.info(
            "Rate limiting enabled: %d requests per %ds window",
            RATE_LIMIT_REQUESTS,
            RATE_LIMIT_WINDOW,
        )

    # Pre-flight health checks
    from kb_server.health import check_embedding_service, check_vector_store

    embedding_status = await check_embedding_service()
    if not embedding_status.healthy:
        log.warning(
            f"Embedding backend unreachable: {embedding_status.message} — "
            f"queries will fail. Configure EMBED_BACKEND or start LM Studio."
        )
    else:
        log.info(f"Embedding backend healthy: {embedding_status.message}")

    vector_status = await check_vector_store()
    if not vector_status.healthy:
        log.warning(
            f"Qdrant unreachable: {vector_status.message} — "
            f"queries will fail. Verify Qdrant is running."
        )
    else:
        log.info(f"Qdrant healthy: {vector_status.message}")

    collection_manager = CollectionManager(store.client, vector_size=store.dim)
    collection_router = CollectionRouter(
        collection_manager, default_collection=store.collection
    )
    log.info(f"CollectionRouter initialized (default='{store.collection}')")

    # PHASE 17: Initialize filter terms cache
    global filter_terms_cache
    filter_terms_cache = FilterTermsCache(store=store)
    await filter_terms_cache.reindex()
    log.info(
        f"Filter terms cache initialized: "
        f"{sum(len(v) for v in filter_terms_cache.terms.values())} "
        f"distinct values across {len(filter_terms_cache.terms)} fields"
    )

    # CR-04: Schedule periodic query log cleanup
    if query_logger:
        asyncio.create_task(_schedule_log_cleanup())
        log.info(
            f"Query log cleanup scheduled every {QUERY_LOG_CLEANUP_INTERVAL_HOURS}h, "
            f"retaining last {QUERY_LOG_RETENTION_DAYS} days"
        )

    # PHASE 33: Schedule periodic rate-limit metric updates
    if RATE_LIMIT_ENABLED:
        asyncio.create_task(_schedule_metric_updates())
        log.info("Rate-limit metric updates scheduled every 60s")

    if TRANSPORT == "sse":
        import uvicorn
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            """Handle SSE (Server-Sent Events) transport connection.

            Creates an SSE stream for bidirectional communication with the
            MCP client. Returns an empty Response on disconnect.

            Args:
                request: Starlette HTTP request object.

            Returns:
                Response indicating disconnection.
            """
            # PHASE 32: Optional API key auth
            from kb_server.auth import is_auth_enabled, verify_request

            sse_subject: str | None = None
            if is_auth_enabled():
                auth_header = request.headers.get("Authorization")
                ok, err = verify_request(auth_header)
                if not ok:
                    return Response(
                        content=f'{{"error":"{err}"}}',
                        status_code=401,
                        media_type="application/json",
                    )
                # Derive subject from API key prefix
                sse_subject = _auth_header_to_subject_prefix(auth_header)

            # Fall back to client IP when no API key is present
            if sse_subject is None:
                forwarded = request.headers.get("X-Forwarded-For", "")
                sse_subject = (
                    forwarded.split(",")[0].strip()
                    or request.client.host
                    or "unknown"
                )

            # PHASE 33: Rate-limit the SSE connection itself
            if RATE_LIMIT_ENABLED and rate_limiter is not None:
                allowed, retry_after = await rate_limiter.check(
                    _hash_subject(sse_subject)
                )
                if not allowed:
                    record_rate_limit_rejected("sse")
                    log.warning(
                        "Rate-limit connection rejected for subject=%s "
                        "retry_after=%ds",
                        sse_subject,
                        retry_after,
                    )
                    return Response(
                        content='{"error":"Rate limit exceeded"}',
                        status_code=429,
                        media_type="application/json",
                        headers={"Retry-After": str(retry_after)},
                    )
                record_rate_limit_allowed("sse")

            # Set context for tool-level checks
            _current_subject.set(sse_subject)
            _current_transport.set("sse")

            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )
            return Response()

        async def handle_health(request):
            """Simple health check endpoint for Docker healthchecks."""
            return Response(
                content='{"status":"ok","service":"kb-rag"}',
                media_type="application/json",
            )

        starlette_app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/health", endpoint=handle_health),
                Mount("/messages/", app=sse.handle_post_message),
                Mount("/api/v1", app=_build_auth_app()),
            ]
        )

        log.info(f"Auth router mounted on SSE transport")
        log.info(f"SSE server at http://{SSE_HOST}:{SSE_PORT}/sse")
        config = uvicorn.Config(
            starlette_app, host=SSE_HOST, port=SSE_PORT, log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    elif TRANSPORT == "streamable-http":
        import uvicorn
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware
        from starlette.responses import Response
        from starlette.routing import Route
        from mcp.server.streamable_http_manager import (
            StreamableHTTPSessionManager,
            TransportSecuritySettings,
        )

        MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
        MCP_PORT = int(os.getenv("MCP_PORT", "8765"))
        MCP_ENDPOINT = os.getenv("MCP_ENDPOINT", "/mcp")
        MCP_JSON_RESPONSE = os.getenv(
            "MCP_JSON_RESPONSE", "false"
        ).lower() in (
            "true",
            "1",
        )
        MCP_STATELESS = os.getenv("MCP_STATELESS", "false").lower() in (
            "true",
            "1",
        )
        MCP_SESSION_TIMEOUT = float(os.getenv("MCP_SESSION_TIMEOUT", "300"))
        MCP_MAX_SESSIONS = int(os.getenv("MCP_MAX_SESSIONS", "50"))

        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[MCP_HOST] if MCP_HOST != "0.0.0.0" else [],
            allowed_origins=[],
        )

        async def handle_mcp(request):
            # ── Session limit enforcement ─────────────────────────
            mcp_session_id = request.headers.get("Mcp-Session-Id")
            if not mcp_session_id and not MCP_STATELESS:
                evicted_id = session_tracker.evict_if_needed()
                if evicted_id:
                    record_session_evicted("streamable-http")
                    log.info(
                        "Session limit reached: evicted %s",
                        evicted_id[:12],
                    )

            from kb_server.auth import is_auth_enabled, verify_request

            subject = "unknown"
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                key = auth_header[7:]
                prefix = key[:8] if len(key) >= 8 else key
                subject = f"key:{prefix}"
            else:
                forwarded = request.headers.get("X-Forwarded-For", "")
                subject = forwarded.split(",")[0].strip() or (
                    request.client.host if request.client else "unknown"
                )
            _current_subject.set(subject)
            _current_transport.set("streamable-http")

            if is_auth_enabled():
                ok, err = verify_request(auth_header)
                if not ok:
                    return Response(
                        content=f'{{"error":"{err}"}}',
                        status_code=401,
                        media_type="application/json",
                    )

            if RATE_LIMIT_ENABLED and rate_limiter is not None:
                allowed, retry_after = await rate_limiter.check(
                    _hash_subject(subject)
                )
                if not allowed:
                    record_rate_limit_rejected("streamable-http")
                    return Response(
                        content='{"error":"Rate limit exceeded"}',
                        status_code=429,
                        media_type="application/json",
                        headers={"Retry-After": str(retry_after)},
                    )
                record_rate_limit_allowed("streamable-http")

            # Track session activity for eviction ordering
            session_tracker.mark_active(mcp_session_id)

            await session_mgr.handle_request(
                request.scope, request.receive, request._send
            )

        starlette_app = Starlette(
            routes=[
                Route(
                    MCP_ENDPOINT,
                    endpoint=handle_mcp,
                    methods=["GET", "POST", "DELETE", "OPTIONS"],
                ),
                Route(
                    "/health",
                    endpoint=lambda r: Response(
                        content='{"status":"ok","service":"kb-rag"}',
                        media_type="application/json",
                    ),
                ),
                Mount("/api/v1", app=_build_auth_app()),
            ],
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                    allow_headers=[
                        "Content-Type",
                        "Accept",
                        "Authorization",
                        "Mcp-Session-Id",
                        "Last-Event-ID",
                        "MCP-Protocol-Version",
                    ],
                    expose_headers=["Mcp-Session-Id", "Content-Type"],
                ),
            ],
        )

        session_mgr = StreamableHTTPSessionManager(
            app=app,
            json_response=MCP_JSON_RESPONSE,
            stateless=MCP_STATELESS,
            security_settings=security,
            session_idle_timeout=MCP_SESSION_TIMEOUT,
        )

        session_tracker = _SessionTracker(session_mgr, MCP_MAX_SESSIONS)
        log.info(
            "Session limit: max_sessions=%d (tracking initialized)",
            MCP_MAX_SESSIONS,
        )

        async def _session_sweep() -> None:
            """Periodic session housekeeping every 60s (per D-04).

            Removes stale tracking entries from ``session_tracker``
            and records active session count as a Prometheus gauge.
            """
            while True:
                await asyncio.sleep(60)
                try:
                    stale = session_tracker.cleanup()
                    count = session_tracker.active_count
                    record_active_sessions(count, "streamable-http")
                    log.debug(
                        "Session sweep: %d active, %d stale cleaned",
                        count,
                        stale,
                    )
                except Exception:
                    log.exception("Session sweep error")

        asyncio.create_task(_session_sweep())
        log.info(
            "Session sweep scheduled every 60s (max_sessions=%d)",
            MCP_MAX_SESSIONS,
        )

        log.info(
            f"Streamable HTTP server at http://{MCP_HOST}:{MCP_PORT}{MCP_ENDPOINT} "
            f"(json_response={MCP_JSON_RESPONSE}, stateless={MCP_STATELESS})"
        )
        async with session_mgr.run():
            config = uvicorn.Config(
                starlette_app,
                host=MCP_HOST,
                port=MCP_PORT,
                log_level="info",
            )
            server = uvicorn.Server(config)
            await server.serve()
    else:
        log.info("stdio transport active")
        # Set context for tool-level rate-limit checks
        _current_subject.set("stdio")
        _current_transport.set("stdio")
        async with stdio_server() as (read, write):
            await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
