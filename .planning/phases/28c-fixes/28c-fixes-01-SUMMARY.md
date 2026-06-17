# Plan 28c-fixes-01 SUMMARY

## Goal
Fix Admin SPA UAT failures for auth flow, document browse, and CSP/SRI compliance.

## Tasks Completed

### Task 1: Auth flow rewrite
- **shell.html**: Rewrote with Alpine.js `x-show` login overlay. `authenticate()` POSTs to `/api/v1/auth/session`, `logout()` calls POST `/auth/logout`, `init()` silently re-auths on load, `@show-login.window` listener for global events.
- **base.html**: 401 handler dispatches `CustomEvent('show-login')` instead of Bootstrap Modal API.
- **auth/router.py**: Added POST `/auth/logout` endpoint with `delete_cookie` on session cookie.

### Task 2: Document browse selection + bulk actions
- **_documents_table.html**: Rewritten with Alpine.js `docBrowser()` scope. Checkbox column with `select-all` via `selectAll()` / per-row via `toggleDoc()`. Bulk toolbar shows Delete, Re-ingest, Delete Failed buttons when `selectedCount > 0`. Per-document Actions dropdown with `hx-confirm` for delete.
- **routes_admin.py**: `quote_path()` registered as Jinja2 global for URL-safe document paths.

### Task 3: CSP/SRI fixes
- **tab_ragas.html**: Added `nonce` attribute to inline script; updated empty state text.
- **login.html**: Added `integrity="sha384-..."` to Bootstrap CSS link.

## Verification
- `pytest tests/test_admin_ui.py -v` — 35 passed, 0 failed
- 8 files changed, 324 insertions, 127 deletions
- Commit: `bd44ef7`

## Deviations
- None. Followed PLAN.md exactly.

## Dependencies for Next Plans
- Plan 02 depends on this plan (uses shell.html auth flow, document browse selection)
- Plan 03 depends on this plan (builds on auth router and 401 handler)
