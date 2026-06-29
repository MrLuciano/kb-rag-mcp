import hashlib
import hmac
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger("kb-mcp.config.router")


def _verify_config_auth(request: Request):
    auth_header = request.headers.get("Authorization", "")
    api_key = None
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:].strip()
    if not api_key:
        api_key = request.headers.get("X-API-Key")
    if api_key:
        from pathlib import Path

        from kb_server.auth.service import AuthService

        try:
            svc = AuthService(
                db_path=Path(os.getenv("AUTH_DB_PATH", "data/auth.db"))
            )
            user = svc.verify_key(api_key)
            if user is not None:
                return
        except Exception:
            log.exception("AuthService verification in config router failed")

        from kb_server.auth_registry import get_registry

        registry = get_registry()
        if registry.verify_key(api_key):
            return

        raise HTTPException(
            status_code=401, detail="Invalid or revoked API key"
        )

    # No API key — try session cookie
    session_cookie = request.cookies.get("session")
    if session_cookie:
        parts = session_cookie.split(":")
        if len(parts) == 3:
            user_id, expires_at_str, signature = parts
            try:
                expires_at = int(expires_at_str)
                if expires_at >= int(time.time()):
                    secret = os.getenv("JWT_SECRET", "")
                    if not secret:
                        secret = "kb-rag-mcp-session-secret"
                    expected = hmac.new(
                        secret.encode(),
                        f"{user_id}:{expires_at}".encode(),
                        hashlib.sha256,
                    ).hexdigest()[:16]
                    if hmac.compare_digest(signature, expected):
                        from pathlib import Path

                        from kb_server.auth.service import AuthService

                        svc = AuthService(
                            db_path=Path(
                                os.getenv("AUTH_DB_PATH", "data/auth.db")
                            )
                        )
                        user = svc.get_user(user_id)
                        if user is not None and user.is_active:
                            return
            except (ValueError, IndexError):
                pass

    # Final fallback: allow if auth is disabled
    from kb_server.auth import is_auth_enabled

    if not is_auth_enabled():
        return

    raise HTTPException(status_code=401, detail="API key required")


router = APIRouter(
    prefix="/api/v1/config",
    tags=["config"],
    dependencies=[Depends(_verify_config_auth)],
)


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
