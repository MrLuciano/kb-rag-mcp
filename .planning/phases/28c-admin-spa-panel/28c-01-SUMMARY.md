# Plan 28c-01 SUMMARY: Admin SPA Shell + Auth + CSP

## Objective

Create the Admin SPA shell with Alpine.js auth flow (API key → JWT session cookie), role-gated sidebar, HTMX tab loading, CSP middleware, and SRI integrity hashes on CDN assets.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_admin_ui.py -v` | ✅ 6/6 PASS |
| `pytest tests/test_ui_routes.py -v` | ✅ 14/14 PASS (no regressions) |
| `pytest tests/test_auth_api.py -v` | ✅ 37/37 PASS (no regressions) |
| Full suite (147 tests) | ✅ All pass |

## Key Files Created/Modified

### Auth
- `kb_server/auth/router.py` — Added `POST /api/v1/auth/session` (HMAC-signed, HttpOnly cookie, 8h)
- `kb_server/auth/schemas.py` — Added `SessionResponse` Pydantic model

### Admin UI Shell
- `kb_server/ui/routes_admin.py` — Admin shell + tab content endpoints + monitor-lights/config-table/profile-content endpoints
- `kb_server/ui/templates/admin/shell.html` — Alpine.js SPA with sidebar, login modal, 401 handling, role-gating
- `kb_server/ui/templates/admin/tab_*.html` — 6 tab placeholder partials (documents, monitoring, ingestion, ragas, admin, profile)

### CSP & Base Template
- `kb_server/ui/app.py` — CSPMiddleware (nonce-based, frame-src https:, script-src with CDN whitelist)
- `kb_server/ui/templates/base.html` — Alpine.js CSP build, HTMX, Bootstrap 5 with SRI integrity hashes, 401 interceptor, admin nav link

## Implementation Notes

- Auth: HMAC-signed session token (SHA-256, 16-char signature), configurable JWT_SECRET env var
- CSP: Nonce-based script-src using Starlette BaseHTTPMiddleware, nonce injected into Jinja2 globals
- SRI: All CDN scripts pinned with integrity hashes (Alpine.js 3.13.3, HTMX 1.9.10, Bootstrap 5.3.0)
- 401 handling: HTMX responseError listener shows Bootstrap login modal, API key stored in localStorage
