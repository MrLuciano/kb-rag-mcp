import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger("kb-mcp.config.router")

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigUpdate(BaseModel):
    value: str
    type: str = "string"
    group_name: Optional[str] = None
    description: Optional[str] = None


class ConfigResponse(BaseModel):
    key: str
    value: str
    type: str
    group_name: str
    description: str
    updated_at: float
    updated_by: str


def _get_loader(request: Request):
    loader = getattr(request.app.state, "config_loader", None)
    if loader is None:
        raise HTTPException(
            status_code=503, detail="Config loader not available"
        )
    return loader


@router.get("")
async def list_config(request: Request, group: Optional[str] = None):
    loader = _get_loader(request)
    entries = await loader.get_all(group_name=group)
    return entries


@router.get("/{key}")
async def get_config(request: Request, key: str):
    loader = _get_loader(request)
    entry = await loader.get_item(key)
    if entry is None:
        raise HTTPException(
            status_code=404, detail=f"Config key not found: {key}"
        )
    return entry


@router.put("/{key}")
async def set_config(request: Request, key: str, body: ConfigUpdate):
    loader = _get_loader(request)
    try:
        result = await loader.set(
            key=key,
            value=body.value,
            type_name=body.type,
            group_name=body.group_name or "general",
            description=body.description or "",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation failed",
                "field": "value",
                "type": body.type,
                "reason": str(e),
            },
        )
    return result


@router.delete("/{key}")
async def delete_config(request: Request, key: str):
    loader = _get_loader(request)
    deleted = await loader.delete(key)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Config key not found: {key}"
        )
    return {"deleted": True, "key": key}


@router.post("/reset")
async def reset_config(request: Request):
    loader = _get_loader(request)
    deleted = await loader.reset_all()
    return {"reset": True, "entries_deleted": deleted}
