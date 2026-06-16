import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from kb_server.auth.models import User
from kb_server.auth.service import AuthService

log = logging.getLogger("kb-mcp.auth.deps")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    user = service.verify_key(api_key)
    if user is None:
        raise HTTPException(
            status_code=401, detail="Invalid or revoked API key"
        )
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
