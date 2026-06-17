"""Admin SPA panel routes."""

import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote, urlencode

log = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from kb_server.auth.deps import get_current_user
from kb_server.auth.models import User

template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))
templates.env.globals["get_nonce"] = lambda request: getattr(
    request.state, "nonce", ""
)
templates.env.globals["quote_path"] = quote

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_shell(request: Request):
    """Render the admin SPA shell."""
    return templates.TemplateResponse(
        request,
        "admin/shell.html",
        {
            "request": request,
            "active_page": "admin",
        },
    )


# ── Specific tab routes (must be registered before generic /tabs/{tab_name}) ──


@router.get("/tabs/monitor-lights", response_class=HTMLResponse)
async def admin_monitor_lights(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return monitor lights partial with health data."""
    from kb_server.health import check_all_components

    components = await check_all_components()
    return templates.TemplateResponse(
        request,
        "admin/_monitor_lights.html",
        {"request": request, "components": components},
    )


@router.get("/tabs/config-table", response_class=HTMLResponse)
async def admin_config_table(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return config table partial."""
    return templates.TemplateResponse(
        request,
        "admin/_config_table.html",
        {"request": request},
    )


@router.get("/tabs/profile-content", response_class=HTMLResponse)
async def admin_profile_content(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return profile content partial."""
    return templates.TemplateResponse(
        request,
        "admin/_profile_content.html",
        {"request": request},
    )


@router.get("/tabs/documents-content", response_class=HTMLResponse)
async def admin_documents_content(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return documents table for admin panel."""
    import sqlite3

    db_path = Path(os.getenv("REGISTRY_DB_PATH", "data/registry.db"))
    documents = []
    total = 0

    if db_path.exists():
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM files WHERE status = 'completed'"
            )
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT rowid, * FROM files WHERE status = 'completed' "
                "ORDER BY rowid DESC LIMIT 20"
            )
            documents = [dict(row) for row in cursor.fetchall()]

    return templates.TemplateResponse(
        request,
        "admin/_documents_table.html",
        {
            "request": request,
            "documents": documents,
            "total": total,
        },
    )


@router.get("/tabs/ingestion-manual", response_class=HTMLResponse)
async def admin_ingestion_manual(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return manual ingestion form partial."""
    return templates.TemplateResponse(
        request,
        "admin/_ingestion_manual.html",
        {"request": request},
    )


@router.get("/tabs/ingestion-schedule", response_class=HTMLResponse)
async def admin_ingestion_schedule(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return ingestion schedule partial."""
    return templates.TemplateResponse(
        request,
        "admin/_ingestion_schedule.html",
        {"request": request},
    )


@router.get("/tabs/ingestion-monitor", response_class=HTMLResponse)
async def admin_ingestion_monitor(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return ingestion monitor partial."""
    return templates.TemplateResponse(
        request,
        "admin/_ingestion_monitor.html",
        {"request": request},
    )


@router.get("/tabs/ragas-editor", response_class=HTMLResponse)
async def admin_ragas_editor(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return RAGAS editor partial."""
    dataset_path = Path("kb_server/evaluation/golden_dataset.json")
    dataset_count = 0
    if dataset_path.exists():
        import json
        with open(dataset_path) as f:
            dataset = json.load(f)
            dataset_count = len(dataset)
    return templates.TemplateResponse(
        request,
        "admin/_ragas_editor.html",
        {"request": request, "dataset_count": dataset_count},
    )


@router.get("/tabs/ragas-results", response_class=HTMLResponse)
async def admin_ragas_results(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return RAGAS results partial."""
    return templates.TemplateResponse(
        request,
        "admin/_ragas_results.html",
        {"request": request},
    )


@router.post("/tabs/ingest-trigger", response_class=HTMLResponse)
async def admin_ingest_trigger(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Trigger ingestion job."""
    form = await request.form()
    path = form.get("path", "")

    if not path or not Path(path).exists():
        return HTMLResponse(
            "<div class='alert alert-danger'>Path not found</div>",
            status_code=400,
        )

    return HTMLResponse(
        "<div class='alert alert-success'>Ingestion job queued for: "
        f"{path}</div>"
    )


@router.get("/tabs/job-status", response_class=HTMLResponse)
async def admin_job_status(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return job status summary."""
    import sqlite3

    db_path = Path(os.getenv("REGISTRY_DB_PATH", "data/registry.db"))
    counts = {"completed": 0, "failed": 0, "pending": 0}

    if db_path.exists():
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            for status in counts:
                cursor.execute(
                    "SELECT COUNT(*) FROM files WHERE status = ?", (status,)
                )
                counts[status] = cursor.fetchone()[0]

    return templates.TemplateResponse(
        request,
        "admin/_job_status.html",
        {"request": request, "counts": counts},
    )


@router.post("/tabs/ragas-run", response_class=HTMLResponse)
async def admin_ragas_run(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Trigger RAGAS evaluation."""
    from pathlib import Path
    import json

    dataset_path = Path("kb_server/evaluation/golden_dataset.json")
    dataset_count = 0

    if dataset_path.exists():
        with open(dataset_path) as f:
            dataset = json.load(f)
            dataset_count = len(dataset)

    return HTMLResponse(
        f"<div class='alert alert-info'>"
        f"Evaluation queued with {dataset_count} queries. "
        f"Results will be available in the logs."
        f"</div>"
    )


@router.get("/tabs/sessions-content", response_class=HTMLResponse)
async def admin_sessions_content(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return session management partial."""
    return templates.TemplateResponse(
        request,
        "admin/_sessions_table.html",
        {"request": request},
    )


@router.get("/tabs/credentials-content", response_class=HTMLResponse)
async def admin_credentials_content(
    request: Request,
    _auth: User = Depends(get_current_user),
):
    """Return credentials/API key management partial."""
    return templates.TemplateResponse(
        request,
        "admin/_credentials_section.html",
        {"request": request},
    )


# ── Generic tab content route (registered after specific routes) ──


@router.get("/tabs/{tab_name}", response_class=HTMLResponse)
async def admin_tab_content(
    request: Request,
    tab_name: str,
    _auth: User = Depends(get_current_user),
):
    """Render a tab content partial."""
    template_map = {
        "documents": "admin/tab_documents.html",
        "monitoring": "admin/tab_monitoring.html",
        "ingestion": "admin/tab_ingestion.html",
        "ragas": "admin/tab_ragas.html",
        "admin": "admin/tab_admin.html",
        "profile": "admin/tab_profile.html",
        "analytics": "admin/tab_analytics.html",
    }
    template = template_map.get(tab_name)
    if template is None:
        return HTMLResponse(
            "<div class='alert alert-danger'>Unknown tab</div>",
            status_code=404,
        )
    context: dict[str, Any] = {
        "request": request,
        "active_page": "admin",
    }

    if tab_name == "analytics":
        try:
            from kb_server.analytics.query_analyzer import (
                QueryAnalyzer,
            )

            db_path = Path(os.getenv("QUERY_LOG_PATH", "data/kb_metadata.db"))
            analyzer = QueryAnalyzer(db_path)
            context["popular_queries"] = analyzer.get_most_common_queries(
                limit=25, time_range_days=7
            )
            context["content_gaps"] = analyzer.get_zero_result_queries(
                time_range_days=7
            )
            context["latency_stats"] = analyzer.get_latency_stats(
                time_range_days=7
            )
        except Exception as e:
            log.error("Failed to load analytics data: %s", e)
            context["popular_queries"] = []
            context["content_gaps"] = []
            context["latency_stats"] = []

    if tab_name == "ragas":
        dataset_path = Path("kb_server/evaluation/golden_dataset.json")
        dataset_count = 0
        if dataset_path.exists():
            import json

            with open(dataset_path) as f:
                dataset = json.load(f)
                dataset_count = len(dataset)
        context["dataset_count"] = dataset_count

    if tab_name == "profile":
        qdrant_k = int(os.getenv("DEFAULT_TOP_K", "5"))
        bm25_enabled = os.getenv("HYBRID_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        reranker_enabled = os.getenv("RERANK_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        context["qdrant_k"] = qdrant_k
        context["bm25_enabled"] = bm25_enabled
        context["reranker_enabled"] = reranker_enabled
        context["config_validation"] = {
            "qdrant_k": 1 <= qdrant_k <= 100,
            "bm25_enabled": isinstance(bm25_enabled, bool),
            "reranker_enabled": isinstance(reranker_enabled, bool),
        }

    return templates.TemplateResponse(
        request, template, context
    )


# ── Document Cleanup API ──────────────────────────────────────


async def _verify_request_api_key(request: Request):
    """Verify API key from Authorization header or X-API-Key header."""
    auth_header = request.headers.get("Authorization", "")
    api_key = None
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:].strip()
    if not api_key:
        api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    from kb_server.auth_registry import get_registry

    registry = get_registry()
    if not registry.verify_key(api_key):
        raise HTTPException(
            status_code=401, detail="Invalid or revoked API key"
        )


api_router = APIRouter(prefix="/api/v1", tags=["api"], dependencies=[])


@api_router.delete("/documents/{source_file:path}")
async def delete_document(
    source_file: str,
    request: Request,
    _auth=Depends(_verify_request_api_key),
):
    """Delete a document from Qdrant and mark deleted in registry."""
    import sqlite3
    from pathlib import Path

    from kb_server.vector_store import VectorStore

    store = VectorStore()
    await store.connect()
    try:
        await store.delete_document(source_file)
    finally:
        await store.close()
    db_path = Path("data/kb_metadata.db")
    if db_path.exists():
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "UPDATE files SET status = 'deleted' WHERE path = ?",
                (source_file,),
            )
            conn.commit()
    return {"status": "deleted", "source_file": source_file}


@api_router.post("/documents/{source_file:path}/re-ingest")
async def reingest_document(
    source_file: str,
    _auth=Depends(_verify_request_api_key),
):
    """Re-ingest a document."""
    from ingest.ingest import process_file

    result = await process_file(source_file)  # type: ignore[call-arg, arg-type]
    return {
        "status": "re-ingested",
        "source_file": source_file,
        "result": str(result),
    }


@api_router.post("/documents/delete-failed")
async def delete_failed_documents(
    request: Request,
    _auth=Depends(_verify_request_api_key),
):
    """Delete all documents with 'failed' status from registry."""
    import sqlite3
    from pathlib import Path

    db_path = Path("data/kb_metadata.db")
    if not db_path.exists():
        return {"status": "ok", "deleted": 0}
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute("DELETE FROM files WHERE status = 'failed'")
        deleted = cur.rowcount
        conn.commit()
    return {"status": "ok", "deleted": deleted}


@api_router.get("/documents/export")
async def export_documents(
    request: Request,
    _auth=Depends(_verify_request_api_key),
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
                "Content-Disposition": "attachment; "
                "filename=documents-export.json"
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
                "Content-Disposition": "attachment; "
                "filename=documents-export.csv"
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
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
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
