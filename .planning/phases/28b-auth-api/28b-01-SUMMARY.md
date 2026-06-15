# Plan 28b-01 SUMMARY: Auth & User Management API

## Objective

Full REST API for user management, API key CRUD, SHA-256 hash storage, role-based access control (admin/user), and GDPR erasure workflow — exposed via `/api/v1/users` and `/api/v1/api-keys` REST endpoints.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_auth_api.py -x -v` | ✅ 37/37 PASS |
| `pytest tests/test_auth_registry.py -x -v` | ✅ 21/21 PASS (backward compat) |
| `flake8 kb_server/auth/ tests/test_auth_api.py tests/test_auth_registry.py` | ✅ Clean |
| `black --check kb_server/auth/ tests/test_auth_api.py tests/test_auth_registry.py` | ✅ Clean |
| `isort --check-only kb_server/auth/ tests/test_auth_api.py tests/test_auth_registry.py` | ✅ Clean |

## Tasks Executed

| # | Task | Status |
|---|------|--------|
| 1 | SQLAlchemy models (User, ApiKey, AuditLog, ErasureRequest) + `create_tables()` | ✅ |
| 2 | AuthService CRUD (create/list/get users, create/list/revoke API keys, verify_key, delete_user) | ✅ |
| 3 | FastAPI dependency guards (`get_current_user`, `require_admin`, `require_auth`) | ✅ |
| 4 | REST API router (`/api/v1/users`, `/api/v1/api-keys`) + Pydantic schemas | ✅ |
| 5 | GDPR erasure workflow (ErasureManager: request → approve → execute state machine) | ✅ |
| 6 | Audit log auto-prune (`prune_audit_logs(days=90)`) + DATA_INVENTORY.md | ✅ |

## Key Files Created

- `kb_server/auth/__init__.py` — Package init, backward-compat re-exports from legacy auth.py
- `kb_server/auth/models.py` — SQLAlchemy models: User, ApiKey, AuditLog, ErasureRequest; `create_session()`
- `kb_server/auth/service.py` — AuthService: user CRUD, API key lifecycle, verify_key, prune_audit_logs
- `kb_server/auth/deps.py` — FastAPI deps: `get_current_user`, `require_admin`, `require_auth`
- `kb_server/auth/schemas.py` — Pydantic request/response models
- `kb_server/auth/router.py` — FastAPI router: user management, API keys, erasure, export endpoints
- `kb_server/auth/erasure.py` — ErasureManager: state machine (requested→approved→completed)
- `kb_server/auth/legacy.py` — Legacy `auth.py` moved into package for backward compatibility
- `tests/test_auth_api.py` — 37 tests covering models, service, deps, API, erasure, audit pruning
- `docs/DATA_INVENTORY.md` — GDPR data inventory cataloging all stores with PII classification

## Implementation Notes

- All timestamps are timezone-naive UTC for SQLite/SQLAlchemy compatibility
- API key raw value returned only on creation (`ApiKeyCreatedResponse`); `key_hash` never exposed (T-28b-01)
- Erasure state machine enforced: `requested → approved → completed`; invalid transitions return False (T-28b-03)
- Erased users blocked from `verify_key` via `erasure_status` check (T-28b-05)
- Audit log auto-prune with `prune_audit_logs(days=90)` (T-28b-04)
- Legacy `kb_server/auth.py` moved into `kb_server/auth/legacy.py`; `__init__.py` re-exports for backward compat
- Old `test_auth_registry.py` tests (21) pass unchanged after updating patch targets
