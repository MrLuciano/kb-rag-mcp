"""
WR-08: Integration tests for the core _search_kb → VectorStore → TextContent path.

These tests mock Qdrant and embedding to verify that:
1. Results flow correctly from store.search() into TextContent output.
2. Zero-result case returns the expected "no results" TextContent.
3. Filters (product, doc_type, file_type) are passed through to store.search().
"""
import pytest
import sys
import os
import types
import asyncio

# ── Stub heavy dependencies before importing server ──────────────────────────

def _ensure_stubs():
    for mod_name in [
        "qdrant_client",
        "qdrant_client.async_qdrant_client",
        "qdrant_client.http",
        "qdrant_client.http.models",
        "qdrant_client.models",
        "mcp",
        "mcp.server",
        "mcp.server.fastmcp",
        "mcp.types",
        "fastembed",
        "sentence_transformers",
        "uvicorn",
        "starlette",
        "starlette.applications",
        "starlette.routing",
        "fastapi",
        # prometheus_client is a real installed package — do not stub it
    ]:
        sys.modules.setdefault(mod_name, types.ModuleType(mod_name))

    # mcp.server needs Server, SseServerTransport, stdio_server
    mcp_server = sys.modules["mcp.server"]
    if not hasattr(mcp_server, "Server"):
        class Server:
            def __init__(self, *a, **kw): pass
            def list_tools(self, *a, **kw):
                def d(fn): return fn
                return d
            def call_tool(self, *a, **kw):
                def d(fn): return fn
                return d
            async def run(self, *a, **kw): pass
        mcp_server.Server = Server

    # mcp.server.sse
    sse_mod = types.ModuleType("mcp.server.sse")
    class SseServerTransport:
        def __init__(self, *a, **kw): pass
        def handle_post_session(self, *a, **kw): pass
        def connect_sse(self, *a, **kw):
            import contextlib
            @contextlib.asynccontextmanager
            async def _(*a, **kw): yield (None, None)
            return _()
    sse_mod.SseServerTransport = SseServerTransport
    sys.modules["mcp.server.sse"] = sse_mod

    # mcp.server.stdio
    stdio_mod = types.ModuleType("mcp.server.stdio")
    import contextlib
    @contextlib.asynccontextmanager
    async def stdio_server(*a, **kw): yield (None, None)
    stdio_mod.stdio_server = stdio_server
    sys.modules["mcp.server.stdio"] = stdio_mod

    # mcp.types needs TextContent and Tool
    mt = sys.modules["mcp.types"]
    if not hasattr(mt, "TextContent"):
        class TextContent:
            def __init__(self, type, text):
                self.type = type
                self.text = text
        mt.TextContent = TextContent
    if not hasattr(mt, "Tool"):
        class Tool:
            def __init__(self, **kw): pass
        mt.Tool = Tool

    # mcp.server.fastmcp needs FastMCP
    mcp_fastmcp = sys.modules["mcp.server.fastmcp"]
    if not hasattr(mcp_fastmcp, "FastMCP"):
        class FastMCP:
            def __init__(self, *a, **kw): pass
            def tool(self, *a, **kw):
                def decorator(fn): return fn
                return decorator
        mcp_fastmcp.FastMCP = FastMCP

    # qdrant_client.http.models needs stub symbols
    models = sys.modules["qdrant_client.http.models"]
    for name in ["Distance", "VectorParams", "HnswConfigDiff", "PointStruct", "Filter",
                 "FieldCondition", "MatchValue", "PayloadSchemaType", "HasIdCondition"]:
        if not hasattr(models, name):
            # Create as a class (not instance) so it can be called and have class attrs
            stub_cls = type(name, (), {"COSINE": "Cosine", "__init__": lambda self, **kw: None})
            setattr(models, name, stub_cls)

    # Also mirror into qdrant_client.models
    qm = sys.modules["qdrant_client.models"]
    for name in ["Distance", "VectorParams", "HnswConfigDiff", "PointStruct", "Filter",
                 "FieldCondition", "MatchValue", "PayloadSchemaType", "HasIdCondition"]:
        if not hasattr(qm, name):
            setattr(qm, name, getattr(models, name))

    qc = sys.modules["qdrant_client"]
    if not hasattr(qc, "AsyncQdrantClient"):
        qc.AsyncQdrantClient = object

    # embed_client stub
    ec = types.ModuleType("embed_client")
    ec.get_embed_dim = lambda: 768
    ec.get_embedding = None
    ec.BACKEND = "fastembed"
    ec.MODEL = "test-model"
    sys.modules.setdefault("embed_client", ec)

    # server.cache.manager stub
    cm = types.ModuleType("kb_server.cache.manager")
    class FakeCM:
        pass
    cm.CacheManager = FakeCM
    sys.modules.setdefault("kb_server.cache.manager", cm)

    # server.retrieval stubs
    for mod in ["kb_server.retrieval", "kb_server.retrieval.hybrid_search",
                "kb_server.retrieval.reranker"]:
        sys.modules.setdefault(mod, types.ModuleType(mod))

    # server.telemetry stubs
    for mod in ["kb_server.telemetry", "kb_server.telemetry.query_logger"]:
        sys.modules.setdefault(mod, types.ModuleType(mod))
    ql_mod = sys.modules["kb_server.telemetry.query_logger"]
    if not hasattr(ql_mod, "QueryLogger"):
        class QueryLogger:
            def __init__(self, *a, **kw): pass
            def log_query(self, *a, **kw): pass
            def cleanup_old_queries(self, *a, **kw): return 0
        ql_mod.QueryLogger = QueryLogger

    # server.analytics / server.optimization stubs
    for mod in ["kb_server.analytics", "kb_server.analytics.query_analyzer",
                "kb_server.optimization", "kb_server.optimization.chunking_experiments",
                "kb_server.ui", "kb_server.ui.app"]:
        sys.modules.setdefault(mod, types.ModuleType(mod))


_ensure_stubs()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_chunk(text="hello world", source="doc.md", score=0.9,
                product="acme", doc_type="guide", file_type="md"):
    return {
        "chunk_id": "abc-123",
        "text": text,
        "source_file": source,
        "score": score,
        "product": product,
        "doc_type": doc_type,
        "file_type": file_type,
        "chunk_index": 0,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_search_kb_returns_text_content_on_results(monkeypatch):
    """WR-08: _search_kb returns list[TextContent] containing result text."""
    import importlib
    srv = importlib.import_module("kb_server.server")

    fake_vector = [0.1] * 768

    async def fake_embed(query): return fake_vector
    monkeypatch.setattr(srv, "get_embedding", fake_embed)
    monkeypatch.setattr(srv, "query_logger", None)

    class FakeStore:
        async def search(self, vector, top_k, filter_type, product,
                         doc_type, version):
            return [_make_chunk()]
    monkeypatch.setattr(srv, "store", FakeStore())

    results = _run(srv._search_kb({"query": "test query", "hybrid": False}))

    assert results, "Expected at least one TextContent"
    assert all(r.type == "text" for r in results)
    combined = "\n".join(r.text for r in results)
    assert "hello world" in combined, "Result text should appear in output"


def test_search_kb_returns_no_results_message_when_store_empty(monkeypatch):
    """WR-08: _search_kb returns 'no results' TextContent when store returns []."""
    import importlib
    srv = importlib.import_module("kb_server.server")

    async def fake_embed(query): return [0.0] * 768
    monkeypatch.setattr(srv, "get_embedding", fake_embed)
    monkeypatch.setattr(srv, "query_logger", None)

    class FakeStore:
        async def search(self, **kw): return []
    monkeypatch.setattr(srv, "store", FakeStore())

    results = _run(srv._search_kb({"query": "nothing", "hybrid": False}))

    assert len(results) == 1
    assert "Nenhum resultado" in results[0].text


def test_search_kb_passes_filters_to_store(monkeypatch):
    """WR-08: filters (product, doc_type, filter_type) are forwarded to store.search()."""
    import importlib
    srv = importlib.import_module("kb_server.server")

    async def fake_embed(query): return [0.0] * 768
    monkeypatch.setattr(srv, "get_embedding", fake_embed)
    monkeypatch.setattr(srv, "query_logger", None)

    captured = {}

    class FakeStore:
        async def search(self, vector, top_k, filter_type, product,
                         doc_type, version):
            captured["filter_type"] = filter_type
            captured["product"] = product
            captured["doc_type"] = doc_type
            return []
    monkeypatch.setattr(srv, "store", FakeStore())

    _run(srv._search_kb({
        "query": "q",
        "hybrid": False,
        "product": "acme",
        "doc_type": "guide",
        "filter_type": "md",
    }))

    assert captured["product"] == "acme"
    assert captured["doc_type"] == "guide"
    assert captured["filter_type"] == "md"
