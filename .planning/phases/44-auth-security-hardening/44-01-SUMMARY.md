# Plan 44-01 SUMMARY: Auth Security Hardening

## Objective

Fix six auth infrastructure gaps: mount auth router on HTTP transports, split erasure approve/execute, enforce ownership checks, secure session cookies, batch verify_key writes, and hash rate-limit subjects.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_auth_api.py -v` | ✅ 37/37 PASS |
| `pytest tests/test_auth_registry.py -v` | ✅ 21/21 PASS |
| `pytest tests/test_ui_routes.py -v` | ✅ 20/20 PASS |
| `pytest tests/test_admin_ui.py -v` | ✅ 15/15 PASS |

## Tasks Executed

| # | Fix | Status |
|---|-----|--------|
| 1 | Mount auth router on SSE + Streamable HTTP transports | ✅ |
| 2 | Split erasure approve/execute into two endpoints | ✅ |
| 3 | Ownership checks on list_api_keys and export_user_data | ✅ |
| 4 | Gate session cookie secure flag on JWT_SECURE env var | ✅ |
| 5 | Remove last_used_at write from verify_key, add record_key_usage | ✅ |
| 6 | Hash rate-limit subjects with SHA-256 prefix | ✅ |

## Files Modified

- `kb_server/server.py` — Auth router mounted via FastAPI sub-app on both SSE and Streamable HTTP transports using `Mount("/api/v1", app=_build_auth_app())`, added `_hash_subject()` helper hashing all rate-limit subject identifiers
- `kb_server/auth/router.py` — Split erasure approve/execute into separate endpoints, ownership checks on `export_user_data` and `list_api_keys`, `JWT_SECURE` env var for cookie secure flag, `record_key_usage()` call on session creation
- `kb_server/auth/service.py` — Removed `last_used_at` write from `verify_key()`, added `record_key_usage()` method called explicitly from session endpoint only

## Implementation Notes

- Auth router mounted on both SSE transport (port 8765) and Streamable HTTP transport (port 8765) via Starlette `Mount` — no changes to stdio transport
- Erasure endpoints require admin role but are now separate calls enabling audit separation
- `list_api_keys` defaults to `current_user.id` when no `user_id` param provided; non-admin cross-user access returns 403
- `verify_key` no longer writes to DB — only `record_key_usage` (called from session creation) writes
- Rate-limit subjects hashed with SHA-256 truncated to 16 hex chars at all 3 check call sites
