"""FastAPI router for ingestion schedule CRUD."""

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ingest.core.metadata import MetadataStore
from ingest.core.cron import validate_cron
from kb_server.auth.deps import require_admin

log = logging.getLogger("kb-mcp.schedules.router")


def _get_store(request: Request) -> MetadataStore:
    store = getattr(request.app.state, "metadata_store", None)
    if store is None:
        db_path = Path("data/kb_metadata.db")
        store = MetadataStore(db_path)
        store.connect()
        request.app.state.metadata_store = store
    return store


router = APIRouter(
    prefix="/api/v1/schedules",
    tags=["schedules"],
)


class CreateScheduleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    cron_expr: str = Field(..., min_length=1, max_length=64)
    docs_path: str = Field(..., min_length=1)
    product: Optional[str] = None
    workers: int = Field(default=2, ge=1, le=8)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    clean: bool = False
    force: bool = False


class UpdateScheduleRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    cron_expr: Optional[str] = Field(None, min_length=1, max_length=64)
    docs_path: Optional[str] = None
    product: Optional[str] = None
    workers: Optional[int] = Field(None, ge=1, le=8)
    priority: Optional[str] = Field(None, pattern="^(low|normal|high)$")
    clean: Optional[bool] = None
    force: Optional[bool] = None
    enabled: Optional[bool] = None


@router.get("")
async def list_schedules(
    request: Request,
    _user=Depends(require_admin),
):
    store = _get_store(request)
    return store.list_schedules()


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    request: Request,
    _user=Depends(require_admin),
):
    store = _get_store(request)
    sched = store.get_schedule(schedule_id)
    if sched is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
    return sched


@router.post("", status_code=201)
async def create_schedule(
    body: CreateScheduleRequest,
    request: Request,
    _user=Depends(require_admin),
):
    try:
        validate_cron(body.cron_expr)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    store = _get_store(request)
    schedule_id = str(uuid.uuid4())
    sched = store.add_schedule(
        schedule_id=schedule_id,
        name=body.name,
        cron_expr=body.cron_expr,
        docs_path=body.docs_path,
        product=body.product,
        workers=body.workers,
        priority=body.priority,
        clean=body.clean,
        force=body.force,
    )
    return sched


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    body: UpdateScheduleRequest,
    request: Request,
    _user=Depends(require_admin),
):
    if body.cron_expr is not None:
        try:
            validate_cron(body.cron_expr)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    store = _get_store(request)
    sched = store.update_schedule(
        schedule_id=schedule_id,
        name=body.name,
        cron_expr=body.cron_expr,
        docs_path=body.docs_path,
        product=body.product,
        workers=body.workers,
        priority=body.priority,
        clean=body.clean,
        force=body.force,
        enabled=body.enabled,
    )
    if sched is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
    return sched


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    request: Request,
    _user=Depends(require_admin),
):
    store = _get_store(request)
    deleted = store.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
    return {"deleted": True, "schedule_id": schedule_id}
