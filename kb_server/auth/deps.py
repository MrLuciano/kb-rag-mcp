import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from kb_server.auth.models import User
from kb_server.auth.service import AuthService

log = logging.getLogger("kb-mcp.auth.deps")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_JWT_SECRET = os.getenv("JWT_SECRET", "")


def _get_service(request: Request) -> AuthService:
    svc = getattr(request.app.state, "auth_service", None)
    if svc is None:
        raise HTTPException(
            status_code=503, detail="Auth service not available"
        )
    return svc  # type: ignore[no-any-return]


async def get_current_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
) -> User:
    service = _get_service(request)

    if not api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:].strip()

    if api_key:
        user = service.verify_key(api_key)
        if user is None:
            raise HTTPException(
                status_code=401, detail="Invalid or revoked API key"
            )
        return user

    # Fallback: session cookie
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Missing API key")

    parts = session_cookie.split(":")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid session cookie")

    user_id, expires_at, signature = parts
    now = int(time.time())

    try:
        if int(expires_at) < now:
            raise HTTPException(status_code=401, detail="Session expired")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session cookie")

    secret = _JWT_SECRET or "kb-rag-mcp-session-secret"
    expected = hmac.new(
        secret.encode(),
        f"{user_id}:{expires_at}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid session cookie")

    user = service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    # Check session validity in DB
    session = service.get_user_session(user.id, signature)
    if session is None:
        raise HTTPException(
            status_code=401, detail="Session has been revoked"
        )
    session.last_used_at = datetime.now(timezone.utc).replace(tzinfo=None)
    service.session.commit()

    log.debug("Authenticated via session cookie: user=%s", user.id)
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_auth(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    return current_user
