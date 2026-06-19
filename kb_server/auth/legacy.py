"""
Legacy HTTP auth guard helpers — backward-compatible re-export.

Moved from kb_server/auth.py when auth became a package (Phase 28b).

Now also checks the SQLAlchemy-backed AuthService as a fallback so that
keys created via ``kb-rag auth create`` (which writes to the ``api_keys``
table) continue to work with MCP transport authentication.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from kb_server.auth_registry import get_registry

log = logging.getLogger("kb-mcp.auth")

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() in (
    "true",
    "1",
    "yes",
)

_AUTH_SERVICE = None


def _get_auth_service():
    """Lazily initialised AuthService singleton for fallback verification."""
    global _AUTH_SERVICE
    if _AUTH_SERVICE is None:
        from kb_server.auth.service import AuthService

        db_path = Path(os.getenv("AUTH_DB_PATH", "data/auth.db"))
        _AUTH_SERVICE = AuthService(db_path=db_path)
    return _AUTH_SERVICE


def is_auth_enabled() -> bool:
    """Check if API key authentication is globally enabled."""
    return AUTH_ENABLED


def extract_bearer_token(
    authorization: Optional[str],
) -> Optional[str]:
    """Extract a Bearer token from an Authorization header value."""
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token if token else None


def verify_request(
    authorization: Optional[str],
) -> tuple[bool, Optional[str]]:
    """Verify an HTTP request's Authorization header."""
    if not AUTH_ENABLED:
        return True, None

    token = extract_bearer_token(authorization)
    if not token:
        return False, "Missing or invalid Authorization header"

    # Check legacy auth_api_keys table
    registry = get_registry()
    if registry.verify_key(token):
        return True, None

    # Fallback: check AuthService (api_keys table via SQLAlchemy)
    try:
        svc = _get_auth_service()
        user = svc.verify_key(token)
        if user is not None:
            return True, None
    except Exception:
        log.exception("AuthService fallback verification failed")

    return False, "Invalid or revoked API key"
