"""Admin SPA panel routes."""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))
templates.env.globals["get_nonce"] = lambda request: getattr(
    request.state, "nonce", ""
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_shell(request: Request):
    """Render the admin SPA shell."""
    return templates.TemplateResponse(
        "admin/shell.html",
        {"request": request},
    )


@router.get("/tabs/{tab_name}", response_class=HTMLResponse)
async def admin_tab_content(request: Request, tab_name: str):
    """Render a tab content partial."""
    template_map = {
        "documents": "admin/tab_documents.html",
        "monitoring": "admin/tab_monitoring.html",
        "ingestion": "admin/tab_ingestion.html",
        "ragas": "admin/tab_ragas.html",
        "admin": "admin/tab_admin.html",
        "profile": "admin/tab_profile.html",
    }
    template = template_map.get(tab_name)
    if template is None:
        return HTMLResponse(
            "<div class='alert alert-danger'>Unknown tab</div>",
            status_code=404,
        )
    return templates.TemplateResponse(template, {"request": request})


@router.get("/tabs/monitor-lights", response_class=HTMLResponse)
async def admin_monitor_lights(request: Request):
    """Return monitor lights partial with health data."""
    from kb_server.health import check_all_components

    components = await check_all_components()
    return templates.TemplateResponse(
        "admin/_monitor_lights.html",
        {"request": request, "components": components},
    )


@router.get("/tabs/config-table", response_class=HTMLResponse)
async def admin_config_table(request: Request):
    """Return config table partial."""
    return templates.TemplateResponse(
        "admin/_config_table.html",
        {"request": request},
    )


@router.get("/tabs/profile-content", response_class=HTMLResponse)
async def admin_profile_content(request: Request):
    """Return profile content partial."""
    return templates.TemplateResponse(
        "admin/_profile_content.html",
        {"request": request},
    )


# ── Document Cleanup API ──────────────────────────────────────


api_router = APIRouter(prefix="/api/v1", tags=["api"])


@api_router.delete("/documents/{source_file:path}")
async def delete_document(source_file: str):
    """Delete a document from Qdrant and mark deleted in registry."""
    import sqlite3
    from pathlib import Path

    from kb_server.vector_store import VectorStore

    store = VectorStore()
    await store.connect()
    try:
        await store.delete_by_source(source_file)
    finally:
        await store.close()
    db_path = Path("data/kb_metadata.db")
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE files SET status = 'deleted' WHERE path = ?",
            (source_file,),
        )
        conn.commit()
        conn.close()
    return {"status": "deleted", "source_file": source_file}


@api_router.post("/documents/{source_file:path}/re-ingest")
async def reingest_document(source_file: str):
    """Re-ingest a document."""
    from ingest.ingest import process_file

    result = await process_file(source_file)
    return {
        "status": "re-ingested",
        "source_file": source_file,
        "result": str(result),
    }


@api_router.post("/documents/delete-failed")
async def delete_failed_documents():
    """Delete all documents with 'failed' status from registry."""
    import sqlite3
    from pathlib import Path

    db_path = Path("data/kb_metadata.db")
    if not db_path.exists():
        return {"status": "ok", "deleted": 0, "source_file": ""}
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute("DELETE FROM files WHERE status = 'failed'")
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return {"status": "ok", "deleted": deleted}


@api_router.get("/documents/export")
async def export_documents(
    format: str = Query("json", pattern="^(csv|json)$"),
    product: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """Export filtered documents as CSV or JSON."""
    from kb_server.ui.routes import get_documents

    docs, total = get_documents(
        product=product,
        doc_type=doc_type,
        vendor=vendor,
        status=status,
        file_type=file_type,
        limit=30000,
    )
    if format == "json":
        import json

        data = json.dumps(docs, indent=2, default=str)
        return Response(
            content=data,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=documents-export.json"
            },
        )
    else:
        import csv
        import io

        output = io.StringIO()
        if docs:
            writer = csv.DictWriter(output, fieldnames=docs[0].keys())
            writer.writeheader()
            writer.writerows(docs)
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=documents-export.csv"
            },
        )


# ── Grafana Embed Helpers ─────────────────────────────────────


def build_grafana_embed_url() -> str:
    """Build Grafana iframe URL from config."""
    grafana_url = os.getenv("GRAFANA_URL", "").rstrip("/")
    grafana_uid = os.getenv("GRAFANA_DASHBOARD_UID", "")
    if not grafana_url or not grafana_uid:
        return ""
    base = f"{grafana_url}/d-solo/{grafana_uid}"
    params = {"orgId": 1, "kiosk": "t", "theme": "light"}
    return f"{base}?{urlencode(params)}"


def build_grafana_embed_url_with_range(
    time_range: str = "6h",
) -> str:
    """Build Grafana iframe URL with time range."""
    grafana_url = os.getenv("GRAFANA_URL", "").rstrip("/")
    grafana_uid = os.getenv("GRAFANA_DASHBOARD_UID", "")
    if not grafana_url or not grafana_uid:
        return ""
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    range_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }
    delta = range_map.get(time_range, timedelta(hours=6))
    base = f"{grafana_url}/d-solo/{grafana_uid}"
    params = {
        "orgId": 1,
        "kiosk": "t",
        "theme": "light",
        "from": int((now - delta).timestamp() * 1000),
        "to": int(now.timestamp() * 1000),
    }
    return f"{base}?{urlencode(params)}"
