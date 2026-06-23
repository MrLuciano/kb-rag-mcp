---
phase: 28b-auth-api
plan: 02
subsystem: auth
tags: [alpinejs, htmx, csp, session-cookie, admin-ui]

# Dependency graph
requires:
  - phase: 28b-01
    provides: Auth & User Management API (deps.py, service.py, router.py)
provides:
  - Alpine CSP + HTMX integration via [x-cloak] CSS rule and htmx:afterSettle → Alpine.initTree handler
  - Session-cookie-based auth for all userManager/profilePage fetch() calls
  - CSP-compatible toggleCreateForm() method replacing inline expression
affects:
  - 28b-03

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Alpine CSP component methods (not inline expressions) for x-on:click handlers
    - Session cookie fallback over Bearer token for fetch() calls from admin UI

key-files:
  created: []
  modified:
    - kb_server/ui/static/styles.css
    - kb_server/ui/templates/admin/shell.html
    - kb_server/ui/templates/admin/tab_users.html

key-decisions:
  - "Remove Bearer Authorization headers from all direct fetch() calls — rely on HttpOnly session cookie set by login, which get_current_user() validates via HMAC signature + DB session record (deps.py line 50-93)"
  - "Keep Content-Type: application/json headers on POST/PUT requests that send a JSON body"
  - "Convert inline x-on:click expression to toggleCreateForm() method for Alpine CSP build compatibility"

patterns-established:
  - "Auth pattern for admin UI fetch(): omit Authorization header; session cookie is automatically sent by browser for same-origin requests"

requirements-completed:
  - AUTH-01
  - AUTH-04
  - AUTH-07

# Metrics
duration: 8min
completed: 2026-06-23
status: complete
---

# Phase 28b Plan 02: Admin UI Users Tab Gap Closure

**[x-cloak] CSS rule, htmx:afterSettle Alpine.initTree handler, session-cookie auth refactor, and CSP-compatible toggle method to unblock Admin UI user creation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-23T21:00:26Z
- **Completed:** 2026-06-23T21:08:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `[x-cloak] { display: none !important; }` CSS rule to prevent Alpine CSP flicker on HTMX-loaded partials
- Added `htmx:afterSettle` → `Alpine.initTree()` listener so Alpine processes `x-data`, `x-text`, `x-show`, `x-on:click` directives in HTMX-swapped tab content
- Removed `Authorization: Bearer` headers from all 12 `fetch()` calls in `userManager` and `profilePage` — session cookie fallback authenticates automatically
- Added `toggleCreateForm()` method to `userManager` for Alpine CSP compatibility, replacing inline `showCreateForm = !showCreateForm`
- All existing tests pass: 68 admin UI, 41 auth API, 1458 total with 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Add [x-cloak] CSS rule and htmx:afterSettle handler** — `36f2ff9` (fix)
2. **Task 2: Remove Bearer headers and add toggleCreateForm method** — `d075fde` (fix)

## Files Created/Modified

- `kb_server/ui/static/styles.css` — Added `[x-cloak]` CSS rule after `.editable-field` block
- `kb_server/ui/templates/admin/shell.html` — Added `htmx:afterSettle → Alpine.initTree()` handler; removed Bearer auth headers from 12 fetch() calls in userManager and profilePage; added `toggleCreateForm()` method
- `kb_server/ui/templates/admin/tab_users.html` — Changed `x-on:click` from inline expression `showCreateForm = !showCreateForm` to `toggleCreateForm()`

## Decisions Made

- **Session cookie over Bearer token:** All direct `fetch()` calls in the admin UI now authenticate via the HttpOnly session cookie set at login, rather than `Authorization: Bearer` header from localStorage. `get_current_user()` (deps.py) has a three-way fallback chain (X-API-Key → Bearer → session cookie) — removing the Bearer header means the session cookie fallback activates automatically.
- **Content-Type preserved for POST/PUT:** Methods sending a JSON body retain `Content-Type: application/json` in their headers; only the Authorization line was removed.
- **Alpine CSP method pattern:** Instead of evaluating arbitrary JavaScript in `x-on:click`, the `toggleCreateForm()` component method follows the same pattern as all other `userManager` methods, working correctly with the CSP safe evaluator.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both tasks completed without issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Admin UI Users tab now has all three fixes applied: HTMX-swapped Alpine directives render correctly, session cookie auth works for user CRUD, and CSP-compatible toggle shows the create form
- All 1458 tests pass with no regressions
- Ready for functional verification (UAT Test #1) and subsequent gap closure plans

---

*Phase: 28b-auth-api*
*Completed: 2026-06-23*
