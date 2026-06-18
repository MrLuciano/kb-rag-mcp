---
status: diagnosed
phase: 28c-fixes
source: 28c-fixes-01-SUMMARY.md
started: 2026-06-16T16:00:00Z
updated: 2026-06-17T16:30:00Z
---

## Current Test

[issue found — diagnosed, fix plan ready]

## Tests

### 1. Login Modal Appears on 401
expected: Any HTMX 401 → CustomEvent('show-login') → Alpine.js overlay visible
result: issue
reported: "I can't see anything happening internally from the web-ui — login overlay never appears"
severity: major
root_cause: "Auth router not mounted on UI app (planned for Plan 03)"

### 2. Login with API Key
expected: Enter key in Alpine modal → POST /api/v1/auth/session → session cookie set → modal closes
result: blocked
blocked_by: prior-phase
reason: "Auth router not mounted on UI app — curl POST /api/v1/auth/session returns 404. Fix scheduled in Plan 03 Task 2."

### 3. Logout Clears Session
expected: Click logout → POST /auth/logout → session cookie deleted → login overlay shown
result: blocked
blocked_by: prior-phase
reason: "Same root cause as Test 2 — auth router not on UI app. Scheduled for Plan 03."

### 4. Document Browse Checkbox Selection
expected: Table has checkbox column; select-all toggles all rows; bulk toolbar appears with selected count
result: issue
reported: "curl /admin/tabs/documents-content returns 'Unknown tab' — route ordering bug: /tabs/{tab_name} shadows /tabs/documents-content"
severity: major

### 5. Per-Document Actions Dropdown
expected: Each row has Actions dropdown; hx-confirm prompts before delete
result: pass

### 6. CSP Nonce + SRI Integrity
expected: tab_ragas.html inline script has nonce attr; login.html Bootstrap CSS link has integrity hash
result: pass

### 7. Login Modal on 401 (re-test of #1)
expected: HTMX 401 → CustomEvent('show-login') → Alpine.js overlay visible
result: issue
reported: "server running, nothing happens in this page"
severity: major

### 8. Login with API Key (re-test of #2)
expected: Enter key in Alpine modal → POST /api/v1/auth/session → session cookie set → modal closes
result: pending

### 9. Logout Clears Session (re-test of #3)
expected: Click logout → POST /auth/logout → session cookie deleted → login overlay shown
result: pending

### 10. Document Browse Checkbox Selection (re-test of #4)
expected: Table has checkbox column; select-all toggles all rows; bulk toolbar appears with selected count
result: pending

## Summary

total: 10
passed: 2
issues: 3
pending: 3
skipped: 0
blocked: 2

## Gaps

- truth: "Any HTMX 401 → CustomEvent('show-login') → Alpine.js overlay visible"
  status: failed
  reason: "User reported: I can't see anything happening internally from the web-ui — login overlay never appears"
  severity: major
  test: 1
  root_cause: "Auth router not mounted on UI app — the UI server runs on port 8001 and does not include kb_server/auth/router.py, so fetch('/api/v1/auth/session') goes to the UI server which has no auth endpoints"
  artifacts:
    - path: "kb_server/ui/app.py"
      issue: "Does not mount auth router"
    - path: "kb_server/ui/templates/admin/shell.html"
      issue: "Fetches /api/v1/auth/session from UI origin which lacks auth endpoints"
  missing:
    - "Mount auth router on UI app (include kb_server.auth.router on kb_server/ui/app.py)"
  debug_session: ""

- truth: "HTMX 401 → CustomEvent('show-login') → Alpine.js overlay visible"
  status: failed
  reason: "User reported: server running, nothing happens in this page"
  severity: major
  test: 7
  root_cause: "Alpine.js CSP build (@alpinejs/csp) does not support global function calls in x-data expressions. shell.html:6 uses x-data=\"adminApp()\" where adminApp() is a global function — CSP rejects it silently, the component never initializes, and the login overlay stays hidden by [x-cloak] CSS."
  artifacts:
    - path: "kb_server/ui/templates/admin/shell.html:6"
      issue: "x-data=\"adminApp()\" uses unsupported global function call in CSP build"
    - path: "kb_server/ui/templates/admin/shell.html:154-270"
      issue: "adminApp defined as global function instead of Alpine.data() registration"
    - path: "kb_server/ui/templates/base.html:22-25"
      issue: "Loads @alpinejs/csp which has this limitation"
  missing:
    - "Register adminApp via Alpine.data('adminApp', ...) inside alpine:init event listener"
    - "Change x-data=\"adminApp()\" to x-data=\"adminApp\" (name-only, no parens)"
  debug_session: ".planning/debug/admin-login-overlay-not-appearing.md"
- truth: "Table has checkbox column; select-all toggles all rows; bulk toolbar appears with selected count"
  status: failed
  reason: "User reported: curl /admin/tabs/documents-content returns 'Unknown tab' — route ordering bug: /tabs/{tab_name} shadows /tabs/documents-content"
  severity: major
  test: 4
  root_cause: "Route ordering bug in routes_admin.py — the generic @router.get('/tabs/{tab_name}') is registered before @router.get('/tabs/documents-content'), so FastAPI matches the generic route first and returns 404 (tab name not found in template_map)"
  artifacts:
    - path: "kb_server/ui/routes_admin.py"
      issue: "Generic /tabs/{tab_name} route (line 39) registered before specific routes like /tabs/documents-content (line 155)"
  missing:
    - "Reorder route registration: define specific routes before the generic /{tab_name} route, or import routes_admin after defining specific routes"
  debug_session: ""
