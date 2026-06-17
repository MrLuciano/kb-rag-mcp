from datetime import datetime
import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response as FastAPIResponse

from kb_server.auth.deps import get_current_user, require_admin
from kb_server.auth.erasure import ErasureManager
from kb_server.auth.models import User
from kb_server.auth.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateUserRequest,
    ErasureRequestResponse,
    SessionResponse,
    UserResponse,
)
from kb_server.auth.service import AuthService

log = logging.getLogger("kb-mcp.auth.router")

_JWT_SECRET = os.getenv("JWT_SECRET", "")
_JWT_SECURE = os.getenv("JWT_SECURE", "false").lower() in (
    "true",
    "1",
)
_SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "1800"))

router = APIRouter(prefix="/api/v1", tags=["auth"])


def _get_service(request: Request) -> AuthService:
    svc = getattr(request.app.state, "auth_service", None)
    if svc is None:
        raise HTTPException(
            status_code=503, detail="Auth service not available"
        )
    return svc  # type: ignore[no-any-return]


def _get_erasure_manager(request: Request) -> ErasureManager:
    svc = _get_service(request)
    erasure = getattr(request.app.state, "erasure_manager", None)
    if erasure is None:
        erasure = ErasureManager(svc.session)
        request.app.state.erasure_manager = erasure
    return erasure


# ── Auth Session ────────────────────────────────────────────────


@router.post("/auth/session", response_model=SessionResponse)
async def create_session(
    request: Request,
    response: FastAPIResponse,
    current_user: User = Depends(get_current_user),
):
    """Exchange API key for an HttpOnly session cookie."""
    service = _get_service(request)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:].strip()
        if api_key:
            service.record_key_usage(api_key)

    expires_at = int(time.time()) + _SESSION_TIMEOUT
    raw = f"{current_user.id}:{expires_at}"
    secret = _JWT_SECRET or secrets.token_hex(32)
    signature = hmac.new(
        secret.encode(), raw.encode(), hashlib.sha256
    ).hexdigest()[:16]
    session_token = f"{raw}:{signature}"

    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=_SESSION_TIMEOUT,
        secure=_JWT_SECURE,
        path="/",
    )

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("User-Agent", "unknown")
    service.create_session_record(
        user_id=str(current_user.id),
        session_token=signature,
        ip_address=ip,
        user_agent=ua,
    )

    return SessionResponse(
        id=str(current_user.id),
        username=cast(str, current_user.username),
        role=cast(str, current_user.role),
        expires_in=_SESSION_TIMEOUT,
    )


@router.post("/auth/logout")
async def logout_session(response: FastAPIResponse):
    """Clear the session cookie."""
    response.delete_cookie(key="session", path="/")
    return {"status": "logged_out"}


# ── Session Management ──────────────────────────────────────────


@router.get("/auth/sessions")
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """List active sessions for the current user."""
    service = _get_service(request)
    sessions = service.list_user_sessions(current_user.id)
    return [
        {
            "id": s.id,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": str(s.created_at) if s.created_at else None,
            "last_used_at": str(s.last_used_at) if s.last_used_at else None,
            "is_revoked": s.is_revoked,
        }
        for s in sessions
    ]


@router.post("/auth/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
):
    """Revoke a session (admin only)."""
    service = _get_service(request)
    revoked = service.revoke_session(session_id, current_user.id)
    if not revoked:
        raise HTTPException(
            status_code=404, detail=f"Session not found: {session_id}"
        )
    return {"revoked": True, "session_id": session_id}


# ── User Endpoints ──────────────────────────────────────────────


@router.post("/users", response_model=UserResponse)
async def create_user(
    body: CreateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
):
    service = _get_service(request)
    try:
        user = service.create_user(username=body.username, role=body.role)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    request: Request,
    admin: User = Depends(require_admin),
):
    service = _get_service(request)
    users = service.list_users()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_endpoint(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    admin: User = Depends(require_admin),
):
    service = _get_service(request)
    deleted = service.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"User not found: {user_id}"
        )
    return {"deleted": True, "user_id": user_id}


# ── API Key Endpoints ───────────────────────────────────────────


@router.post("/api-keys", response_model=ApiKeyCreatedResponse)
async def create_api_key(
    body: CreateApiKeyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    service = _get_service(request)
    try:
        raw_key, api_key = service.create_api_key(
            user_id=body.user_id, description=body.description
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ApiKeyCreatedResponse(
        id=cast(str, api_key.id),
        prefix=cast(str, api_key.prefix),
        description=cast(str, api_key.description),
        is_revoked=cast(bool, api_key.is_revoked),
        created_at=cast(datetime, api_key.created_at),
        raw_key=raw_key,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    request: Request,
    current_user: User = Depends(get_current_user),
    user_id: Optional[str] = None,
):
    service = _get_service(request)
    target_id = user_id or cast(str, current_user.id)
    if target_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Cannot list another user's API keys",
        )
    keys = service.list_api_keys(target_id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    service = _get_service(request)
    revoked = service.revoke_api_key(key_id)
    if not revoked:
        raise HTTPException(
            status_code=404, detail=f"API key not found: {key_id}"
        )
    return {"revoked": True, "key_id": key_id}


# ── GDPR Erasure Endpoints ──────────────────────────────────────


@router.post("/users/{user_id}/erasure-request")
async def request_erasure(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    mgr = _get_erasure_manager(request)
    try:
        er = mgr.request_erasure(
            user_id=user_id,
            requested_by=cast(str, current_user.id),
            reason="User requested erasure",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ErasureRequestResponse.model_validate(er)


@router.post("/admin/erasure-requests/{request_id}/approve")
async def approve_erasure(
    request_id: str,
    request: Request,
    admin: User = Depends(require_admin),
):
    mgr = _get_erasure_manager(request)
    success = mgr.approve_erasure(request_id=request_id, approved_by=cast(str, admin.id))
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve — request not found or "
            "not in requested state",
        )
    return {
        "status": "approved",
        "request_id": request_id,
    }


@router.post("/admin/erasure-requests/{request_id}/execute")
async def execute_erasure(
    request_id: str,
    request: Request,
    admin: User = Depends(require_admin),
):
    mgr = _get_erasure_manager(request)
    executed = mgr.execute_erasure(request_id)
    if not executed:
        raise HTTPException(
            status_code=400,
            detail="Cannot execute — request not found or "
            "not in approved state",
        )
    return {
        "status": "completed",
        "request_id": request_id,
    }


@router.get("/users/{user_id}/export")
async def export_user_data(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Cannot export another user's data",
        )
    mgr = _get_erasure_manager(request)
    data = mgr.export_user_data(user_id)
    if data is None:
        raise HTTPException(
            status_code=404, detail=f"User not found: {user_id}"
        )
    return data
