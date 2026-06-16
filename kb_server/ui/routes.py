"""Web UI routes for document browsing and search testing."""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Form, Query, Request
from fastapi.responses import HTMLResponse

from kb_server.ui.app import app, templates
log = logging.getLogger("kb-mcp.ui")


def _parse_search_results(text: str) -> list[dict[str, Any]]:
    """Parse markdown search results into structured dicts."""
    import re

    results: list[dict[str, Any]] = []
    # Split on ### [N] heading
    sections = re.split(r'\n###\s*\[\d+\]\s+', text)
    for section in sections[1:]:  # Skip header
        lines = section.strip().split('\n')
        if not lines:
            continue
        # First line: source_file (relevance: XX.X%)
        header = lines[0]
        source_match = re.match(r'(.+?)\s+\(relevance:\s+([\d.]+)%\)', header)
        source_file = source_match.group(1) if source_match else header
        score = float(source_match.group(2)) / 100 if source_match else 0.0
        # Extract metadata from bold lines
        chunk_id = ''
        product = ''
        doc_type = ''
        page = ''
        for line in lines[1:]:
            if line.startswith('**ID:**'):
                id_match = re.search(r'`([^`]+)`', line)
                if id_match:
                    chunk_id = id_match.group(1)
            elif line.startswith('**Product:**'):
                product = line.replace('**Product:**', '').strip()
            elif line.startswith('**Type:**'):
                doc_type = line.replace('**Type:**', '').strip()
            elif line.startswith('**Page/section:**'):
                page = line.replace('**Page/section:**', '').strip()
        # Text is everything after the first --- or blank line
        text_content = '\n'.join(lines)
        # Find the chunk text (after metadata and before ---)
        text_parts = text_content.split('\n\n')
        chunk_text = ''
        if len(text_parts) > 1:
            chunk_text = text_parts[1]
        results.append({
            'source_file': source_file,
            'score': score,
            'chunk_id': chunk_id,
            'product': product,
            'doc_type': doc_type,
            'page': page,
            'text': chunk_text,
        })
    return results


# Database path configuration
DB_PATH = Path(os.getenv("KB_METADATA_DB", "data/kb_metadata.db"))


def _map_document(row: sqlite3.Row) -> Dict[str, Any]:
    """Map registry row to template-compatible dict."""
    doc = dict(row)
    # Registry schema uses rowid, path, chunks; templates expect id,
    # source_file, chunks_stored.
    doc["id"] = doc.get("rowid", 0)
    doc["source_file"] = doc.get("path", "").split("/")[-1] or doc.get(
        "path", ""
    )
    doc["chunks_stored"] = doc.get("chunks", 0)
    return doc


def get_documents(
    product: Optional[str] = None,
    doc_type: Optional[str] = None,
    version: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    file_type: Optional[str] = None,
    vendor: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "desc",
    limit: int = 25,
    offset: int = 0,
) -> tuple[List[Dict[str, Any]], int]:
    """
    Query documents from metadata database.

    Returns:
        Tuple of (documents list, total count)
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if product:
            where_clauses.append("product = ?")
            params.append(product)
        if doc_type:
            where_clauses.append("doc_type = ?")
            params.append(doc_type)
        if version:
            where_clauses.append("version = ?")
            params.append(version)
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        if date_from:
            where_clauses.append("indexed_at >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("indexed_at <= ?")
            params.append(date_to)
        if file_type:
            where_clauses.append("file_type = ?")
            params.append(file_type)
        if vendor:
            where_clauses.append("vendor = ?")
            params.append(vendor)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        count_query = f"SELECT COUNT(*) FROM files WHERE {where_sql}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        sort_columns = {
            "name": "source_file",
            "file_type": "doc_type",
            "vendor": "vendor",
            "product": "product",
            "date": "indexed_at",
            "status": "status",
        }
        order_clause = "ORDER BY indexed_at DESC"
        if sort_by and sort_by in sort_columns:
            col = sort_columns[sort_by]
            order = (
                "ASC" if sort_order and sort_order.upper() == "ASC" else "DESC"
            )
            order_clause = f"ORDER BY {col} {order}"

        query = f"""
            SELECT rowid, * FROM files
            WHERE {where_sql}
            {order_clause}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [limit, offset])
        rows = cursor.fetchall()

    documents = [_map_document(row) for row in rows]
    return documents, total


@app.get("/ui/browse", response_class=HTMLResponse)
async def browse_documents(
    request: Request,
    product: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    version: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
):
    """Browse documents page with filters and pagination."""
    limit = 25  # per D-09
    offset = (page - 1) * limit

    documents, total = get_documents(
        product=product,
        doc_type=doc_type,
        version=version,
        status=status,
        date_from=date_from,
        date_to=date_to,
        file_type=file_type,
        vendor=vendor,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    total_pages = (total + limit - 1) // limit

    return templates.TemplateResponse(
        request,
        "browse.html",
        {
            "request": request,
            "documents": documents,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "sort_by": sort_by or "",
            "sort_order": sort_order,
            "filters": {
                "product": product,
                "doc_type": doc_type,
                "version": version,
                "status": status,
                "date_from": date_from,
                "date_to": date_to,
                "file_type": file_type,
                "vendor": vendor,
            },
            "active_page": "browse",
        },
    )


@app.get("/ui/search", response_class=HTMLResponse)
async def search_tester(request: Request):
    """Search testing page."""
    return templates.TemplateResponse(
        request, "search.html", {"request": request, "active_page": "search"}
    )


@app.post("/ui/search", response_class=HTMLResponse)
async def search_kb(
    request: Request,
    query: str = Form(...),
    top_k: int = Form(5),
    product: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    hybrid: bool = Form(False),
    rerank: bool = Form(False),
):
    """Execute search and return HTML results."""
    from kb_server.server import _search_kb

    args = {
        "query": query,
        "top_k": top_k,
        "product": product,
        "version": version,
        "hybrid": hybrid,
        "rerank": rerank,
    }
    results = await _search_kb(args)
    result_text = results[0].text if results else "No results found."
    parsed_results = _parse_search_results(result_text) if results else []

    return templates.TemplateResponse(
        request,
        "search_results.html",
        {
            "request": request,
            "query": query,
            "results": results,
            "result_text": result_text,
            "parsed_results": parsed_results,
        },
    )


@app.get("/ui/document/{doc_id}", response_class=HTMLResponse)
async def document_detail(
    request: Request,
    doc_id: int,
    q: Optional[str] = Query(None),
):
    """Document detail page showing metadata and chunks."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT rowid, * FROM files WHERE rowid = ?", (doc_id,))
        row = cursor.fetchone()

        if not row:
            return templates.TemplateResponse(
                request,
                "error.html",
                {
                    "request": request,
                    "code": 404,
                    "title": "Not Found",
                    "detail": "Document not found",
                },
                status_code=404,
            )

        document = _map_document(row)

    # Query Qdrant for chunks
    chunks: list[dict] = []
    if (
        document.get("chunks_stored", 0) > 0
        and document.get("status") != "failed"
    ):
        try:
            from qdrant_client.models import (
                FieldCondition,
                Filter,
                MatchValue,
            )

            from kb_server.vector_store import VectorStore

            store = VectorStore()
            await store.connect()
            try:
                source_file = row["path"]
                client = store.client
                assert client is not None
                results, _ = await client.scroll(
                    collection_name=store.collection,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="source_file",
                                match=MatchValue(value=source_file),
                            )
                        ]
                    ),
                    limit=500,
                    with_payload=True,
                    with_vectors=False,
                )
                chunks = []
                for r in results:
                    assert r.payload is not None
                    chunks.append({
                        "chunk_id": str(r.id),
                        "text": r.payload.get("text", ""),
                        "chunk_index": int(r.payload.get("chunk_index", 0)),
                    })
                chunks.sort(key=lambda c: c["chunk_index"])
            except Exception as e:
                log.error("Failed to load chunks for doc %s: %s", doc_id, e)
            finally:
                await store.close()
        except Exception as e:
            log.error("VectorStore error for doc %s: %s", doc_id, e)

    return templates.TemplateResponse(
        request,
        "document.html",
        {
            "request": request,
            "document": document,
            "chunks": chunks,
            "search_query": q,
            "active_page": "browse",
        },
    )


@app.get("/ui/document/{doc_id}/chunks", response_class=HTMLResponse)
async def document_chunks(
    request: Request,
    doc_id: int,
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
):
    """HTMX partial — returns next page of chunks starting at offset."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT rowid, * FROM files WHERE rowid = ?", (doc_id,))
        row = cursor.fetchone()
    if not row:
        return HTMLResponse("")

    page: list[dict] = []
    total = 0
    try:
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
        )

        from kb_server.vector_store import VectorStore

        store = VectorStore()
        await store.connect()
        try:
            source_file = row["path"]
            client = store.client
            assert client is not None
            results, _ = await client.scroll(
                collection_name=store.collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_file",
                            match=MatchValue(value=source_file),
                        )
                    ]
                ),
                limit=500,
                with_payload=True,
                with_vectors=False,
            )
            chunks = []
            for r in results:
                assert r.payload is not None
                chunks.append({
                    "chunk_id": str(r.id),
                    "text": r.payload.get("text", ""),
                    "chunk_index": int(r.payload.get("chunk_index", 0)),
                })
            chunks.sort(key=lambda c: c["chunk_index"])
            page = chunks[offset : offset + 50]
            total = len(chunks)
        except Exception as e:
            log.error("Failed to load chunks for doc %s: %s", doc_id, e)
        finally:
            await store.close()
    except Exception as e:
        log.error("VectorStore error for doc %s: %s", doc_id, e)

    return templates.TemplateResponse(
        request,
        "document_chunks.html",
        {
            "request": request,
            "chunks": page,
            "search_query": q,
            "offset": offset,
            "total": total,
            "doc_id": doc_id,
        },
    )
