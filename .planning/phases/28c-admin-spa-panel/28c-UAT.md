---
status: diagnosed
phase: 28c-admin-spa-panel
source: 28c-01-SUMMARY.md, 28c-02-SUMMARY.md, 28c-03-SUMMARY.md, 28c-04-SUMMARY.md
started: 2026-06-16T17:10:00Z
updated: 2026-06-16T17:25:00Z
---

## Current Test

[testing paused — 8 items outstanding]

## Tests

### 1. Login with API Key
expected: |
  Opening the admin panel shows a login modal. Entering a valid API key establishes a session (JWT cookie set). The modal closes and the admin shell with sidebar appears.
result: issue
reported: "Page shows 'Failed to load content. Please try again later.' Logout button visible but no login was required. Need: default admin account (admin/admin), login page on first open, password change page under settings, configurable session timeout (30 min default), user session management."
severity: blocker

### 2. Tab Navigation via Sidebar
expected: |
  Clicking sidebar tabs (Documents, Monitoring, Ingestion, RAGAS, Admin, Profile) loads content via HTMX without full page reload. Active tab has visual indicator.
result: issue
reported: "Nothing loads, error message: 'Failed to load content. Please try again later.' RAGAS tab is not present in the sidebar."
severity: blocker

### 3. Role Gating
expected: |
  An admin user sees all sidebar tabs. A non-admin user sees a restricted set of tabs. Unauthorized tab access returns 403.
result: [pending]

### 4. Monitor Lights - Health Indicators
expected: |
  The Monitoring tab shows health status indicators for 7 components (Qdrant, Embedding, LLM, Cache, Database, Filesystem, Grafana). Indicators show green/red/yellow status. View auto-refreshes every 30 seconds.
result: [pending]

### 5. Config Inline Editing
expected: |
  The Admin tab shows a config table with search filter. Double-clicking a value opens inline edit mode. Pressing Enter saves, Escape cancels. Changes persist after page reload.
result: [pending]

### 6. Profile - API Key CRUD
expected: |
  The Profile tab shows account info and an API keys table. "Generate New Key" creates a key with prefix/created/status. The raw key is shown once with a Copy button. Keys can be revoked.
result: [pending]

### 7. Profile - GDPR Export & Erasure
expected: |
  "Export My Data" button downloads a JSON file with personal data. "Request Erasure" triggers a confirmation dialog; after confirmation, erasure is requested.
result: [pending]

### 8. Document Actions - Delete & Re-ingest
expected: |
  The Documents tab shows a sortable table (click column headers to sort). Each document has action buttons (Delete, Re-ingest). Delete shows confirmation. Deleted documents disappear from list.
result: [pending]

### 9. Advanced Filters
expected: |
  The Documents tab has filter controls: date range (from/to), file type multi-select, vendor/product dropdowns. Applying filters updates the document list. URL reflects active filter params. "Clear All Filters" resets everything.
result: [pending]

### 10. Document Export (CSV/JSON)
expected: |
  An Export button on the Documents tab allows downloading as CSV or JSON. The export respects all active filters. Downloads have proper filenames and Content-Disposition headers.
result: [pending]

## Summary

total: 10
passed: 0
issues: 2
pending: 8
skipped: 0
blocked: 0

## Gaps

- truth: "Opening the admin panel shows a login modal. Entering a valid API key establishes a session. The modal closes and the admin shell with sidebar appears."
  status: failed
  reason: "User reported: Page shows 'Failed to load content. Please try again later.' Logout button visible but no login was required. Need: default admin account (admin/admin), login page on first open, password change page under settings, configurable session timeout (30 min default), user session management."
  severity: blocker
  test: 1
  root_cause: "Three interconnected root causes: (1) Alpine.js CDN URL invalid (404) — alpinejs@3.13.3/dist/csp.min.js doesn't exist, all x-data/x-show silently fail; (2) No server-side auth gating on admin endpoints in routes_admin.py; (3) Auth endpoints mounted on MCP server (port 8765) not UI app (port 8001)"
  artifacts:
    - path: "kb_server/ui/templates/base.html:22-25"
      issue: "Invalid Alpine.js CDN URL — alpinejs@3.13.3 has no dist/csp.min.js"
    - path: "kb_server/ui/routes_admin.py:24-35,38-118"
      issue: "No server-side auth gating on admin shell or tab endpoints"
    - path: "kb_server/ui/app.py:63-66"
      issue: "Auth router not mounted on UI app, only on MCP server sub-app"
    - path: "kb_server/server.py:1508-1516,1673"
      issue: "Auth routes only on MCP sub-app (port 8765), not UI app (port 8001)"
    - path: "kb_server/ui/templates/admin/shell.html:113-129"
      issue: "init() calls /api/v1/users/me on UI app → 404"
    - path: "kb_server/ui/templates/admin/shell.html:131-158"
      issue: "authenticate() never POSTs to /api/v1/auth/session"
  missing:
    - "Fix Alpine.js CDN URL to valid path (dist/cdn.min.js or @alpinejs/csp)"
    - "Add server-side Depends(get_current_user) to all admin routes"
    - "Mount auth router on UI FastAPI app"
    - "Implement JWT session cookie exchange in authenticate()"
    - "Seed default admin account (admin/admin) on first startup"
    - "Add configurable session timeout (30 min default)"
    - "Add proper error handling (distinguish 404 vs 401 vs 500)"
    - "Add RAGAS tab to sidebar"
    - "Add password change page under settings"
  debug_session: ".planning/debug/admin-panel-auth-and-content-loading.md"

- truth: "Clicking sidebar tabs (Documents, Monitoring, Ingestion, RAGAS, Admin, Profile) loads content via HTMX without full page reload. Active tab has visual indicator."
  status: failed
  reason: "User reported: Nothing loads, error message: 'Failed to load content. Please try again later.' RAGAS tab is not present in the sidebar."
  severity: blocker
  test: 2
  root_cause: "Cascading consequence of root causes from Test 1: Alpine.js broken means tab switching x-show directives don't work; no auth on tab endpoints means they fail; missing RAGAS tab in sidebar config"
  artifacts:
    - path: "kb_server/ui/templates/admin/shell.html"
      issue: "RAGAS tab missing from sidebar nav items"
  missing:
    - "Add RAGAS tab to sidebar navigation"
    - "Fix content loading chain (depends on auth fix from gap 1)"
  debug_session: ".planning/debug/admin-panel-auth-and-content-loading.md"
