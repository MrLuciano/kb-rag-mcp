---
phase: 28c-fixes
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kb_server/ui/templates/admin/shell.html
  - kb_server/ui/templates/base.html
  - kb_server/ui/templates/admin/_documents_table.html
  - kb_server/ui/templates/admin/tab_ragas.html
  - kb_server/ui/templates/admin/login.html
  - kb_server/auth/router.py
  - kb_server/ui/routes_admin.py
  - tests/test_admin_ui.py
autonomous: true
gap_closure: true
requirements:
  - SPA-02
  - SPA-03
  - SPA-09
  - SPA-12
must_haves:
  truths:
    - User enters API key and frontend POSTs to /api/v1/auth/session to receive HttpOnly JWT cookie
    - Login modal visibility is controlled by Alpine.js x-show, not Bootstrap JS API
    - Document table has checkbox column, bulk toolbar, and per-document Actions dropdown
    - tab_ragas.html inline script has CSP nonce; login.html Bootstrap CSS has SRI integrity
  artifacts:
    - path: kb_server/ui/templates/admin/shell.html
      provides: Alpine.js auth flow with JWT cookie exchange
      contains: "x-show=\"!isAuthenticated\""
    - path: kb_server/ui/templates/admin/_documents_table.html
      provides: Document browse with selection and bulk actions
      contains: "type=\"checkbox\""
    - path: kb_server/auth/router.py
      provides: Logout endpoint
      exports: ["logout"]
  key_links:
    - from: shell.html authenticate()
      to: /api/v1/auth/session
      via: POST with Bearer token
      pattern: "auth/session"
    - from: base.html htmx:responseError
      to: Alpine.js auth state
      via: event listener
      pattern: "isAuthenticated"
---

<objective>
Close the BLOCKER auth flow gap and HIGH-priority document browse / CSP / SRI gaps so the Admin SPA matches the 28c-UI-SPEC.md security and feature contracts.

Purpose: Without these fixes, the Admin SPA uses an insecure auth model (raw API key in localStorage instead of JWT cookie) and lacks critical document management features. CSP/SRI gaps cause browser blocking.
Output: Updated shell, document table, auth router, and base template with passing tests.
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/admin/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/phases/28c-fixes/28c-fixes-CONTEXT.md
@.planning/phases/28c-admin-spa-panel/28c-UAT.md
@.planning/phases/28c-admin-spa-panel/28c-UI-REVIEW.md
@.planning/phases/28c-admin-spa-panel/28c-UI-SPEC.md
@.planning/phases/28c-admin-spa-panel/28c-01-SUMMARY.md

# Source files (current state before fixes)
@kb_server/ui/templates/admin/shell.html
@kb_server/ui/templates/base.html
@kb_server/ui/templates/admin/_documents_table.html
@kb_server/ui/templates/admin/tab_ragas.html
@kb_server/ui/templates/admin/login.html
@kb_server/auth/router.py
@kb_server/ui/routes_admin.py
@tests/test_admin_ui.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Rewrite auth flow to use JWT session cookie (D-01)</name>
  <files>
    kb_server/ui/templates/admin/shell.html
    kb_server/ui/templates/base.html
    kb_server/auth/router.py
  </files>
  <behavior>
    - Test: test_shell_html_uses_alpine_xshow — shell.html contains `x-show="!isAuthenticated"` on login overlay (not Bootstrap modal API)
    - Test: test_authenticate_posts_to_auth_session — `authenticate()` sends POST to `/api/v1/auth/session` with Bearer header
    - Test: test_logout_calls_auth_logout — `logout()` calls POST `/api/v1/auth/logout` to clear cookie
    - Test: test_base_html_401_sets_alpine_state — base.html 401 handler sets Alpine.js `isAuthenticated = false` instead of calling Bootstrap modal
    - Test: test_auth_router_has_logout — Auth router has `POST /api/v1/auth/logout` that clears `session` cookie
    - Test: test_login_modal_heading — Login modal heading is "Login to Admin Panel" (not "Authentication Required")
    - Test: test_api_key_placeholder — API key placeholder is "kb_xxxxxxxx..."
    - Test: test_sidebar_tab_labels — Sidebar tab labels are "RAGAS Evaluation" and "Admin"
  </behavior>
  <action>
    1. In shell.html: Replace the Bootstrap modal markup (`<div class="modal fade" id="loginModal" ...>`) with an Alpine.js-controlled overlay div using `x-show="!isAuthenticated"` and `x-transition`. Use a centered card layout inside a full-viewport backdrop (`position: fixed; inset: 0; background: rgba(0,0,0,0.5)`).
    2. In shell.html: Change modal title to `<h3 class="h3">Login to Admin Panel</h3>`. Change input placeholder to `kb_xxxxxxxx...`. Add `aria-label="API key"` to the input. Add `aria-labelledby` on the overlay container.
    3. In shell.html: Rewrite `authenticate(key)` to:
       - POST `/api/v1/auth/session` with header `Authorization: Bearer {key}`.
       - On 200: store key in localStorage, set `isAuthenticated = true`, set `loginError = ''`, then fetch `/api/v1/users/me` to set `isAdmin`.
       - On 401/403: set `loginError = 'Invalid API key. Please check your key and try again. If the problem persists, generate a new key.'`, clear localStorage, keep `isAuthenticated = false`.
    4. In shell.html: Rewrite `init()` to:
       - Read key from localStorage.
       - If present, attempt silent auth via POST `/api/v1/auth/session` (same flow as authenticate).
       - If no key or auth fails, `isAuthenticated = false` (overlay shows automatically via `x-show`).
    5. In shell.html: Rewrite `logout()` to:
       - Call POST `/api/v1/auth/logout`.
       - Clear localStorage `kb_api_key`.
       - Set `isAuthenticated = false`, `isAdmin = false`.
       - The overlay shows automatically via `x-show`.
    6. In shell.html: Add Alpine.js data properties: `loggingIn`, `loginError`.
    7. In shell.html: Change sidebar tab labels: "Evaluation" → "RAGAS Evaluation", "Settings" → "Admin".
    8. In base.html: Replace the Bootstrap-modal-based 401 handler with one that dispatches a custom event or directly manipulates the Alpine.js store. Since shell.html uses Alpine.js `x-data="adminApp()"`, the 401 handler can call `document.querySelector('[x-data="adminApp()"]').__x.$data.isAuthenticated = false` or emit a custom event that adminApp listens for. Prefer a custom event `show-login` that `adminApp` listens to with `@show-login.window="isAuthenticated = false"`.
    9. In kb_server/auth/router.py: Add `POST /auth/logout` endpoint that returns a `FastAPIResponse` with `response.delete_cookie(key="session", path="/")`.
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "auth or login or logout or modal or session"</automated>
  </verify>
  <done>
    - shell.html uses Alpine.js `x-show` for login overlay (no Bootstrap modal API)
    - authenticate() POSTs to /api/v1/auth/session and handles 200/401/403
    - logout() calls logout endpoint and clears localStorage
    - base.html 401 handler triggers Alpine.js auth state reset
    - Auth router has working POST /api/v1/auth/logout
    - Copy matches spec: "Login to Admin Panel", "kb_xxxxxxxx...", "RAGAS Evaluation", "Admin"
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add document browse selection and bulk actions (D-02)</name>
  <files>
    kb_server/ui/templates/admin/_documents_table.html
    kb_server/ui/routes_admin.py
  </files>
  <behavior>
    - Test: test_doc_table_select_all_checkbox — _documents_table.html has checkbox `<input type="checkbox">` in header for "select all"
    - Test: test_doc_table_per_row_checkbox — Each data row has a checkbox for individual selection
    - Test: test_doc_table_bulk_toolbar — Bulk toolbar present with "Delete", "Re-ingest", "Delete Failed" buttons
    - Test: test_doc_table_per_row_actions — Per-document Actions dropdown contains "View", "Delete", "Re-ingest"
    - Test: test_destructive_actions_have_confirm — Delete actions have `hx-confirm` attribute
    - Test: test_doc_table_empty_state — Empty state reads "No documents match your search filters. Try adjusting your filter criteria or clear all filters."
  </behavior>
  <action>
    1. In _documents_table.html: Add a `<th>` checkbox column as the first column. In the header, use `<input type="checkbox" @click="toggleSelectAll()">`. In each row, use `<input type="checkbox" x-model="selected" :value="{{ doc.rowid }}">`.
    2. Wrap the table in an Alpine.js `x-data="docBrowser()"` scope. Add `selected: []` array, `toggleSelectAll()`, and bulk action methods.
    3. Add a bulk toolbar div above the table that shows only when `selected.length > 0` (`x-show`). Toolbar buttons:
       - "Delete" — calls `bulkDelete()` which sends DELETE requests to `/api/v1/documents/{path}` for each selected doc, then refreshes table via `htmx.ajax('GET', '/admin/tabs/documents-content', {target: '#tab-content', swap: 'innerHTML'})`.
       - "Re-ingest" — calls `bulkReingest()` similarly via POST `/api/v1/documents/{path}/re-ingest`.
       - "Delete Failed" — calls `deleteFailed()` via POST `/api/v1/documents/delete-failed`.
    4. Add `hx-confirm` attributes on destructive buttons with spec text: "Delete document: Are you sure you want to delete this document? This action cannot be undone."
    5. Replace the single "View" button with a Bootstrap dropdown "Actions" per row containing: View (link to `/ui/document/{{ doc.rowid }}`), Delete, Re-ingest. Use `hx-confirm` on Delete.
    6. Fix empty state text: "No documents found. No documents match your search filters. Try adjusting your filter criteria or clear all filters."
    7. In routes_admin.py: Ensure the existing document API endpoints (`delete_document`, `reingest_document`, `delete_failed_documents`) are wired and functional. No new endpoints needed for the bulk actions if using client-side fetch loops; however, if HTMX is preferred for individual actions, add HTMX wrapper endpoints under `/admin/api/documents/{id}/delete` that proxy to the existing JSON endpoints and return HTML fragments. For gap closure, client-side fetch + HTMX refresh is acceptable and minimizes route changes.
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "doc_table or doc_bulk or destructive"</automated>
  </verify>
  <done>
    - Document table has checkbox column with select-all
    - Bulk toolbar appears when >=1 row selected with Delete, Re-ingest, Delete Failed
    - Per-document Actions dropdown has View, Delete (with hx-confirm), Re-ingest
    - Empty state copy matches spec
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Fix CSP nonce and SRI integrity (D-03)</name>
  <files>
    kb_server/ui/templates/admin/tab_ragas.html
    kb_server/ui/templates/admin/login.html
  </files>
  <behavior>
    - Test: test_tab_ragas_has_csp_nonce — tab_ragas.html inline `<script>` tag includes `nonce="{{ get_nonce(request) }}"`
    - Test: test_login_html_has_sri_integrity — login.html Bootstrap CSS link includes `integrity="sha384-..."`
    - Test: test_ragas_empty_state_text — tab_ragas.html empty state reads "No evaluation results yet. Run an evaluation to see results here."
  </behavior>
  <action>
    1. In tab_ragas.html: Add `nonce="{{ get_nonce(request) }}"` to the `<script>` tag at line 36.
    2. In tab_ragas.html: Change empty state text from "No evaluation run yet." to "No evaluation results yet. Run an evaluation to see results here."
    3. In login.html: Add `integrity="sha384-9ndCyUaIbzAi2FUVXJi0CjmCapSmO7SnpJef0486qhLnuZ2cdeRhO02iuK6FUUVM"` and `crossorigin="anonymous"` to the Bootstrap CSS `<link>` on line 7.
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "csp or sri or nonce or integrity or ragas"</automated>
  </verify>
  <done>
    - tab_ragas.html script has CSP nonce
    - login.html Bootstrap CSS has SRI integrity hash
    - tab_ragas.html empty state matches spec
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client→API | API key crosses from browser localStorage to server via Bearer header (temporary exchange for JWT cookie) |
| CDN→browser | External scripts/styles loaded from CDN must have integrity verification |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-01 | Spoofing / Information Disclosure | shell.html auth flow | mitigate | Per D-01: exchange API key for HttpOnly JWT cookie via POST /api/v1/auth/session; do not send raw key on every request |
| T-28c-02 | Tampering | tab_ragas.html inline script | mitigate | Per D-03: add CSP nonce so strict script-src allows execution |
| T-28c-03 | Tampering | login.html Bootstrap CSS | mitigate | Per D-03: add SRI integrity hash; browser rejects modified CDN content |
| T-28c-04 | Repudiation / Elevation of Privilege | Document delete actions | mitigate | Per D-02: hx-confirm on all destructive actions; user must confirm before delete/re-ingest |
</threat_model>

<verification>
- Run full test suite: `pytest tests/test_admin_ui.py -v`
- Run UI regression tests: `pytest tests/test_ui_routes.py -v`
- Verify no new flake8/mypy errors: `flake8 kb_server/ui/ kb_server/auth/router.py && mypy kb_server/ui/ kb_server/auth/router.py`
- Manual spot-check: open shell.html and confirm no `bootstrap.Modal` references remain
</verification>

<success_criteria>
- [ ] Auth flow exchanges API key for JWT cookie; login overlay uses Alpine.js x-show
- [ ] Document table has checkboxes, bulk toolbar, and per-document Actions dropdown
- [ ] tab_ragas.html script has CSP nonce; login.html has SRI integrity
- [ ] All new tests pass; no regressions in existing 666 tests
- [ ] Code review passed (black, flake8, mypy clean)
</success_criteria>

<output>
Create `.planning/phases/28c-fixes/28c-fixes-01-SUMMARY.md` when done
</output>
