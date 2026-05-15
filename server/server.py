"""
KB RAG MCP Server
Expõe tools de busca semântica na knowledge base via protocolo MCP.
Compatível com Claude Code, OpenCode e qualquer cliente MCP.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# ── Carrega .env antes de qualquer leitura de os.getenv ──────────────────────
try:
    from dotenv import load_dotenv
    _env = Path(__file__).parent.parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
except ImportError:
    pass

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport

from embed_client import get_embedding
from vector_store import VectorStore

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(os.getenv("LOG_PATH", "/tmp/kb-mcp.log")),
    ],
)
log = logging.getLogger("kb-mcp")

# ── Config ───────────────────────────────────────────────────────────────────
TRANSPORT   = os.getenv("MCP_TRANSPORT", "stdio")   # stdio | sse
SSE_HOST    = os.getenv("SSE_HOST", "0.0.0.0")
SSE_PORT    = int(os.getenv("SSE_PORT", "8765"))
TOP_K       = int(os.getenv("DEFAULT_TOP_K", "5"))

# ── Inicialização ─────────────────────────────────────────────────────────────
app   = Server("kb-rag")
store = VectorStore()


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    doc_type_enum = [
        "admin_guide", "install_guide", "upgrade_guide", "config_guide",
        "user_guide", "api_guide", "release_notes", "howto",
        "training", "overview", "reference", "standard",
        "meeting", "release_artifact", "document",
    ]
    return [
        types.Tool(
            name="search_kb",
            description=(
                "Busca semântica na knowledge base local de documentação de produtos OpenText e padrões técnicos. "
                "Retorna os chunks mais relevantes com score, fonte e metadados. "
                "Filtre por product (ex: 'ArchiveCenter', 'xECM', 'OTDS') e/ou doc_type "
                "(ex: 'install_guide', 'release_notes', 'standard', 'training') para resultados mais precisos. "
                "Use sempre que precisar de informações sobre instalação, configuração, APIs, "
                "upgrades, normas ISO ou exemplos de código."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Pergunta ou termo a buscar na KB",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Número de resultados (padrão: 5, máx: 20)",
                        "default": TOP_K,
                        "minimum": 1,
                        "maximum": 20,
                    },
                    "product": {
                        "type": "string",
                        "description": (
                            "Filtrar por produto. Exemplos: ArchiveCenter, ContentServer, "
                            "xECM, OTDS, WEM, AppWorks, ProcessSuite, Adobe, SAP, ISO, geral"
                        ),
                    },
                    "doc_type": {
                        "type": "string",
                        "description": (
                            "Filtrar por tipo de conteúdo. "
                            "admin_guide=administração, install_guide=instalação, "
                            "upgrade_guide=upgrade/migração, config_guide=configuração, "
                            "release_notes=notas de release, api_guide=API/SDK, "
                            "howto=tutoriais/case studies, training=treinamentos, "
                            "overview=visão geral, standard=normas ISO/regulamentos, "
                            "reference=referência técnica"
                        ),
                        "enum": doc_type_enum,
                    },
                    "filter_type": {
                        "type": "string",
                        "description": "Filtrar por formato do arquivo: pdf, docx, xlsx, pptx, txt, code",
                        "enum": ["pdf", "docx", "xlsx", "pptx", "txt", "code"],
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="list_documents",
            description=(
                "Lista documentos indexados na knowledge base. "
                "Útil para descobrir quais documentos estão disponíveis antes de buscar. "
                "Filtre por product e/ou doc_type para navegar por categoria."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "product": {
                        "type": "string",
                        "description": "Filtrar por produto (ex: ArchiveCenter, xECM, OTDS)",
                    },
                    "doc_type": {
                        "type": "string",
                        "description": "Filtrar por tipo de conteúdo",
                        "enum": doc_type_enum,
                    },
                    "filter_type": {
                        "type": "string",
                        "description": "Filtrar por formato: pdf, docx, xlsx, pptx, txt, code",
                        "enum": ["pdf", "docx", "xlsx", "pptx", "txt", "code"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Máximo de documentos a retornar (padrão: 50)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_chunk",
            description=(
                "Retorna o conteúdo completo de um chunk específico com contexto expandido. "
                "Use após search_kb quando precisar do texto completo de um resultado."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "string",
                        "description": "ID do chunk (retornado pelo search_kb)",
                    },
                    "context_window": {
                        "type": "integer",
                        "description": "Chunks vizinhos a incluir para contexto (0-3, padrão: 1)",
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
            description="Estatísticas da KB: total de documentos, chunks, breakdown por produto e tipo de conteúdo.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        if name == "search_kb":
            return await _search_kb(arguments)
        elif name == "list_documents":
            return await _list_documents(arguments)
        elif name == "get_chunk":
            return await _get_chunk(arguments)
        elif name == "kb_stats":
            return await _kb_stats()
        else:
            return [types.TextContent(type="text", text=f"Tool desconhecida: {name}")]
    except Exception as e:
        log.error(f"Erro em {name}: {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Erro ao executar {name}: {str(e)}")]


# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

async def _search_kb(args: dict) -> list[types.TextContent]:
    query       = args["query"]
    top_k       = args.get("top_k", TOP_K)
    filter_type = args.get("filter_type")
    product     = args.get("product")
    doc_type    = args.get("doc_type")

    log.info(f"search_kb: '{query}' top_k={top_k} product={product} doc_type={doc_type} file_type={filter_type}")

    vector  = await get_embedding(query)
    results = await store.search(
        vector=vector, top_k=top_k,
        filter_type=filter_type, product=product, doc_type=doc_type,
    )

    if not results:
        return [types.TextContent(
            type="text",
            text="Nenhum resultado encontrado na knowledge base para essa query."
        )]

    lines = [f"## Resultados para: \"{query}\"\n"]
    for i, r in enumerate(results, 1):
        score_pct = f"{r['score'] * 100:.1f}%"
        lines.append(f"### [{i}] {r['source_file']}  (relevância: {score_pct})")
        lines.append(
            f"**ID:** `{r['chunk_id']}`  |  "
            f"**Produto:** {r.get('product','n/a')}  |  "
            f"**Tipo:** {r.get('doc_type','n/a')}  |  "
            f"**Formato:** {r['file_type']}"
        )
        if r.get("page"):
            lines.append(f"**Página/seção:** {r['page']}")
        lines.append("")
        lines.append(r["text"])
        lines.append("\n---")

    lines.append("\n*Use `get_chunk` com o ID para obter contexto expandido.*")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _list_documents(args: dict) -> list[types.TextContent]:
    docs = await store.list_documents(
        filter_type=args.get("filter_type"),
        product=args.get("product"),
        doc_type=args.get("doc_type"),
        limit=args.get("limit", 50),
    )

    if not docs:
        return [types.TextContent(type="text", text="Nenhum documento indexado na KB.")]

    lines = [f"## Documentos na Knowledge Base ({len(docs)} encontrados)\n"]
    by_dt: dict[str, list] = {}
    for d in docs:
        by_dt.setdefault(d.get("doc_type", "document"), []).append(d)

    for dt, items in sorted(by_dt.items()):
        lines.append(f"### {dt}  ({len(items)} documentos)")
        for d in items:
            lines.append(
                f"- `{d['source_file']}` — {d['chunk_count']} chunks"
                f" | produto: {d.get('product','n/a')}"
                f" | formato: {d['file_type']}"
            )
        lines.append("")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _get_chunk(args: dict) -> list[types.TextContent]:
    chunk_id = args["chunk_id"]
    context  = args.get("context_window", 1)

    chunks = await store.get_chunk_with_context(chunk_id, context)
    if not chunks:
        return [types.TextContent(type="text", text=f"Chunk `{chunk_id}` não encontrado.")]

    lines = [f"## Chunk `{chunk_id}` com contexto\n"]
    for c in chunks:
        marker = "→ **[chunk solicitado]**" if c["chunk_id"] == chunk_id else ""
        lines.append(f"### {c['source_file']} — chunk {c['chunk_index']} {marker}")
        lines.append(c["text"])
        lines.append("")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _kb_stats() -> list[types.TextContent]:
    stats = await store.get_stats()
    lines = [
        "## Knowledge Base — Estatísticas\n",
        f"- **Total de documentos:** {stats['total_documents']}",
        f"- **Total de chunks:** {stats['total_chunks']}",
        f"- **Tamanho do índice:** {stats['index_size_mb']:.1f} MB",
        f"- **Modelo de embedding:** {stats['embed_model']}",
        f"- **Dimensões do vetor:** {stats['embed_dim']}",
        "\n**Por tipo de conteúdo (doc_type):**",
    ]
    for dt, count in sorted(stats["by_doc_type"].items(), key=lambda x: -x[1]):
        lines.append(f"  - {dt}: {count} documentos")

    lines.append("\n**Por formato de arquivo:**")
    for ft, count in sorted(stats["by_file_type"].items(), key=lambda x: -x[1]):
        lines.append(f"  - {ft}: {count} documentos")

    return [types.TextContent(type="text", text="\n".join(lines))]


# ─────────────────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    log.info(f"KB RAG MCP Server iniciando (transport={TRANSPORT})")
    await store.connect()

    if TRANSPORT == "sse":
        import uvicorn
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount

        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options())

        starlette_app = Starlette(routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages", app=sse.handle_post_message),
        ])

        log.info(f"SSE server em http://{SSE_HOST}:{SSE_PORT}/sse")
        config = uvicorn.Config(starlette_app, host=SSE_HOST, port=SSE_PORT, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        log.info("stdio transport ativo")
        async with stdio_server() as (read, write):
            await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
