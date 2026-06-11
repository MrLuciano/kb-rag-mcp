"""
HTTP request auth guard helpers for MCP transport enforcement.

Provides middleware-compatible functions that extract and verify
``Authorization: Bearer <key>`` headers against the AuthRegistry.
"""

import logging
import os
from typing import Optional

from kb_server.auth_registry import get_registry

log = logging.getLogger("kb-mcp.auth")

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() in (
    "true", "1", "yes"
)


def is_auth_enabled() -> bool:
    """Check if API key authentication is globally enabled."""
    return AUTH_ENABLED


def extract_bearer_token(
    authorization: Optional[str],
) -> Optional[str]:
    """Extract a Bearer token from an Authorization header value.

    Args:
        authorization: The raw ``Authorization`` header value, or None.

    Returns:
        The token string if present and Bearer-format, else None.
    """
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token if token else None


def verify_request(
    authorization: Optional[str],
) -> tuple[bool, Optional[str]]:
    """Verify an HTTP request's Authorization header.

    Args:
        authorization: The raw Authorization header value, or None.

    Returns:
        Tuple of (is_authenticated, error_message). When auth is
        disabled, always returns (True, None). When auth is enabled
        and the key is valid, returns (True, None). Otherwise returns
        (False, error_message).
    """
    if not AUTH_ENABLED:
        return True, None

    token = extract_bearer_token(authorization)
    if not token:
        return False, "Missing or invalid Authorization header"

    registry = get_registry()
    if registry.verify_key(token):
        return True, None

    return False, "Invalid or revoked API key"
