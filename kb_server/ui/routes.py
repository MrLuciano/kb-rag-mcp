"""Web UI routes for document browsing and search testing."""

import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import Request, Query
from fastapi.responses import HTMLResponse
from kb_server.ui.app import app, templates

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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Build query with filters
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

    # Get total count
    count_query = f"SELECT COUNT(*) FROM files WHERE {where_sql}"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # Sortable columns mapping (D-08)
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
        order = "ASC" if sort_order and sort_order.upper() == "ASC" else "DESC"
        order_clause = f"ORDER BY {col} {order}"

    # Get paginated results
    query = f"""
        SELECT rowid, * FROM files
        WHERE {where_sql}
        {order_clause}
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [limit, offset])
    rows = cursor.fetchall()
    conn.close()

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
        },
    )


@app.get("/ui/search", response_class=HTMLResponse)
async def search_tester(request: Request):
    """Search testing page."""
    return templates.TemplateResponse(
        request, "search.html", {"request": request}
    )


@app.get("/ui/document/{doc_id}", response_class=HTMLResponse)
async def document_detail(request: Request, doc_id: int):
    """Document detail page showing metadata and chunks."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get document metadata
    cursor.execute("SELECT rowid, * FROM files WHERE rowid = ?", (doc_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "error": "Document not found"},
            status_code=404,
        )

    document = _map_document(row)
    conn.close()

    return templates.TemplateResponse(
        request, "document.html", {"request": request, "document": document}
    )
