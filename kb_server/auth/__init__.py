"""
Auth package — User management, API key CRUD, RBAC, GDPR erasure.

Backward-compatible re-exports from legacy kb_server/auth.py:
    is_auth_enabled, extract_bearer_token, verify_request
"""

from kb_server.auth.legacy import (
    extract_bearer_token,
    is_auth_enabled,
    verify_request,
)

__all__ = [
    "is_auth_enabled",
    "extract_bearer_token",
    "verify_request",
]
