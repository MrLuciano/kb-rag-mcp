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

## Suggested Fix Direction

1. Fix Alpine.js CDN URL — use `dist/cdn.min.js` from a trusted CDN or install `@alpinejs/csp`
2. Add server-side auth gating to ALL admin routes using `Depends(get_current_user)`
3. Mount auth router on UI app so `/api/v1/users/me` and `/api/v1/auth/session` available
4. Implement JWT session cookie exchange in `authenticate()`
5. Seed default admin account (admin/admin) on first startup
6. Add session timeout tracking
7. Add proper error handling (distinguish 404 vs 401 vs 500)
