---
status: resolved
created: 2026-06-17T16:00:00Z
updated: 2026-06-29T18:05:00Z
---

# Debug Session: Admin Panel Auth & Content Loading

## Symptoms

- Page shows "Failed to load content. Please try again later."
- Logout button visible without login
- No login modal shown
- RAGAS tab missing from sidebar
- Tab navigation doesn't load content

## Root Causes Found

### 1. (PRIMARY) Alpine.js CDN URL Invalid (404)
`kb_server/ui/templates/base.html` line 22-25: URL `https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/csp.min.js` returns HTTP 404. Alpine.js 3.13.3 does NOT contain `dist/csp.min.js` — the CSP build is a separate package (`@alpinejs/csp`). All Alpine.js directives silently fail: `x-data`, `x-show`, `@click`, `:class`, `x-text`, `x-init`.

This explains:
- "Logout button visible" → `x-show="isAuthenticated"` never processed
- Login modal never shown → `init()` never runs
- All Alpine-dependent partials broken

### 2. No Auth Gating on Admin Endpoints
`kb_server/ui/routes_admin.py` — shell (`GET /admin`) and all tab content endpoints have zero authentication. No `Depends(get_current_user)`, no middleware, no API key check. The only auth enforcement was client-side via Alpine.js (which is broken).

### 3. Auth Endpoints on Different Server
`/api/v1/users/me` is mounted on MCP server's Starlette app (port 8765), not on UI app (port 8001). Shell's `authenticate()`/`init()` calls `fetch('/api/v1/users/me')` on port 8001 → 404. Fetch fails silently, `isAdmin` stays false, but user appears "authenticated".

### 4. "Failed to load content" Error
`base.html` `htmx:responseError` handler fires for tab content loading chain. Nested SQLite endpoint returns 500 on fresh system where `data/registry.db` doesn't exist or lacks expected schema.

## Files Involved

| File | Issue |
|------|-------|
| `kb_server/ui/templates/base.html:22-25` | Invalid Alpine.js CDN URL (404) |
| `kb_server/ui/routes_admin.py:24-35,38-118` | No auth gating on admin routes |
| `kb_server/ui/app.py:63-66` | UI app missing auth router mount |
| `kb_server/server.py:1508-1516,1673` | Auth only on MCP sub-app, not UI |
| `kb_server/ui/templates/admin/shell.html:113-129` | `init()` calls /api/v1/users/me → 404 |
| `kb_server/ui/templates/admin/shell.html:131-158` | `authenticate()` never POSTs JWT session |

## Resolution

All 7 items fixed in Phase 28c-fixes Plans 01-05:
1. Alpine.js CDN URL fixed — `@alpinejs/csp@3.13.3/dist/cdn.min.js` with SRI hash ✅
2. Server-side auth gating added — 13 endpoints use `Depends(get_current_user)` ✅
3. Auth router mounted on UI app — `app.py` includes auth_router ✅
4. JWT session cookie exchange — `POST /auth/session` → JWT cookie ✅
5. Default admin account seeded — `ensure_admin_account()` on startup ✅
6. Session timeout tracking — `_SESSION_TIMEOUT=1800`, `UserSession` table ✅
7. Error handling — status-code-specific error handler in base.html ✅

## Verified

Phase 28c-fixes UAT: 3/3 verification steps passed (password login, API key login, session validation).
