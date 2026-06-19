# Quick Task: Unify Auth Systems

**Date:** 2026-06-19

**Goal:** Remove the duplicate auth system. `kb-rag auth create` keys (previously stored in
`auth_api_keys` table via `AuthRegistry`) must write to `api_keys` table (SQLAlchemy via
`AuthService`) so there's a single point of authorization for all subsystems.

## What Changed

| File | Change |
|------|--------|
| `kb_server/auth/service.py` | Added `list_all_api_keys()`, `find_key_by_prefix()`, `revoke_key_by_prefix()` for CLI-facing cross-user operations |
| `ingest/cli/auth.py` | Rewired `create`, `list`, `revoke` from `AuthRegistry` → `AuthService`. Auto-creates admin user if missing. |
| `kb_server/auth/legacy.py` | `verify_request()` now falls back to `AuthService.verify_key()` if `AuthRegistry` fails |
| `kb_server/config/router.py` | `_verify_config_auth()` checks `AuthService` first, falls back to `AuthRegistry` |
| `kb_server/ui/routes_admin.py` | `_verify_request_api_key()` checks `AuthService` first, falls back to `AuthRegistry` |

## Verification

- 108 tests pass, 1 pre-existing failure (MockRequest missing cookies attribute)
- `AuthRegistry` class left intact for backward compatibility
- All auth verification paths check both tables (new first, legacy fallback)
