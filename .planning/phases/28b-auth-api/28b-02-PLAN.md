---
phase: 28b-auth-api
plan: 02
type: execute
wave: 2
depends_on:
  - 28b-01
files_modified:
  - kb_server/ui/static/styles.css
  - kb_server/ui/templates/admin/shell.html
  - kb_server/ui/templates/admin/tab_users.html
autonomous: true
requirements:
  - AUTH-01
  - AUTH-04
  - AUTH-07
gap_closure: true
must_haves:
  truths:
    - Admin Users tab shows "Create User" button with visible text
    - Clicking "Create User" reveals the user creation form
    - Admin can submit form to create a user with username, email, role
    - Created user has an API key shown exactly once
    - User table lists users with their username, role, status
  artifacts:
    - path: "kb_server/ui/static/styles.css"
      provides: "[x-cloak] CSS rule for Alpine CSP flicker prevention"
      contains: "\\[x-cloak\\]"
    - path: "kb_server/ui/templates/admin/shell.html"
      provides: "htmx:afterSettle handler for Alpine.initTree(); session-cookie-based auth in userManager/profilePage"
      contains: "Alpine.initTree"
  key_links:
    - from: "kb_server/ui/templates/base.html"
      to: "kb_server/ui/templates/admin/shell.html"
      via: "htmx:afterSettle event dispatches after HTMX swap; shell.html handler calls Alpine.initTree on the swapped target"
---

<objective>
Fix three compounding issues preventing the Admin UI Users tab from working: (1) Alpine CSP build not processing HTMX-swapped content — x-text/x-show never evaluate, (2) Password login stores no API key in localStorage but userManager.createUser() reads Bearer null → 401, (3) Alpine CSP build cannot evaluate inline expression `showCreateForm = !showCreateForm` in x-on:click.

Purpose: Unblock UAT Test #1 (Create a user through the Admin UI) by making the "Create User" button, form, and submission work end-to-end.

Output: Working Users tab in the Admin UI where admin can create users and see them listed.
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/admin/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/28b-auth-api/28b-UAT.md
@.planning/phases/28b-auth-api/28b-01-SUMMARY.md
@kb_server/ui/templates/admin/shell.html
@kb_server/ui/templates/admin/tab_users.html
@kb_server/ui/static/styles.css
@kb_server/ui/templates/base.html
@kb_server/auth/deps.py
@kb_server/auth/router.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add [x-cloak] CSS rule and htmx:afterSettle handler for Alpine CSP + HTMX integration</name>
  <files>
    kb_server/ui/static/styles.css,
    kb_server/ui/templates/admin/shell.html
  </files>
  <action>
    **Part A — Add `[x-cloak]` CSS rule to styles.css**

    Append this rule at the end of `kb_server/ui/static/styles.css` (after line 179, the last `.editable-field` rule):

    ```css
    /* Prevent Alpine.js flicker — hide elements until CSP build initializes */
    [x-cloak] {
        display: none !important;
    }
    ```

    Place it after the `.editable-field` block. The CSS file is already loaded by `base.html` line 14 via `<link rel="stylesheet" href="/static/styles.css">`, so no additional loading needed.

    **Part B — Add htmx:afterSettle → Alpine.initTree() event listener in shell.html**

    In `kb_server/ui/templates/admin/shell.html`, within the existing `<script nonce="{{ get_nonce(request) }}">` block at lines 129-728, and within the `document.addEventListener('alpine:init', ...)` block (lines 150-726), add the `htmx:afterSettle` handler.

    The event listener must be added OUTSIDE the `alpine:init` handler but within the same `<script>` block, at the top level of the script (never inside `Alpine.data(...)` definitions). It should call `Alpine.initTree(evt.detail.target)` on every HTMX afterSettle event so that Alpine CSP's mutation observer processes all x- directives in HTMX-swapped partials.

    Insert AFTER the existing `htmx:sendError` listener at line 107 of `base.html`, OR more practically, add it at the top level of the shell.html `<script>` block (lines 129-728), before the `document.addEventListener('alpine:init', ...)` block. It must NOT be nested inside `Alpine.data(...)`.

    The code to add (at the top level of the script, after the existing `htmx:beforeRequest` handler at lines 141-148 in shell.html, before line 150's `document.addEventListener('alpine:init', ...)`):

    ```javascript
    // Initialize Alpine components in HTMX-swapped content
    document.addEventListener('htmx:afterSettle', function(evt) {
        Alpine.initTree(evt.detail.target);
    });
    ```

    This ensures that when partials like `tab_users.html` are loaded via `htmx.ajax()` (triggered from `_switchTab()` at shell.html line 635), Alpine processes the `x-data`, `x-text`, `x-show`, `x-on:click`, etc. directives in the swapped DOM.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && grep -c '\[x-cloak\]' kb_server/ui/static/styles.css && grep -c 'Alpine.initTree' kb_server/ui/templates/admin/shell.html</automated>
  </verify>
  <done>
    - `styles.css` contains `[x-cloak] { display: none !important; }`
    - `shell.html` contains `Alpine.initTree(evt.detail.target)` in the htmx:afterSettle handler
    - No errors in script syntax (no parse errors when template renders)
  </done>
</task>

<task type="auto">
  <name>Task 2: Remove Bearer Authorization headers from userManager/profilePage fetch() calls and add toggleCreateForm() CSP-compatible method</name>
  <files>
    kb_server/ui/templates/admin/shell.html,
    kb_server/ui/templates/admin/tab_users.html
  </files>
  <action>
    **Context:** `kb_server/auth/deps.py` `get_current_user()` (lines 31-94) has a three-way fallback chain: (1) X-API-Key header, (2) Authorization Bearer token, (3) session cookie (HMAC-validated). After any successful login (password or API key), an HttpOnly session cookie is set. The current `userManager` and `profilePage` methods use direct `fetch()` with `Authorization: Bearer ' + localStorage.getItem('kb_api_key')` — but after password login, no API key is stored in localStorage, so this sends "Bearer null" → 401. The fix is to remove the Bearer header from all direct `fetch()` calls; the session cookie will authenticate them automatically.

    **Part A — Remove `Authorization: Bearer` headers from userManager methods in shell.html**

    In `kb_server/ui/templates/admin/shell.html`, remove the `Authorization` header from every `fetch()` call in all `userManager` component methods. The affected methods and their line-local variable declarations are:

    1. `loadUsers()`: lines 326-327 — remove the `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };` line; rewrite `fetch('/api/v1/users', { headers: headers })` to `fetch('/api/v1/users')`.
    2. `createUser()`: lines 350-351 — change `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key'), 'Content-Type': 'application/json' };` to `var headers = { 'Content-Type': 'application/json' };`. Then in the subsequent fetch calls at lines 353 and 363, they use `headers` directly (which still has Content-Type set).
    3. `deleteUser()`: lines 386-387 — remove `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };`; change line 388 `fetch('/api/v1/users/' + user.id, { method: 'DELETE', headers: headers })` to `fetch('/api/v1/users/' + user.id, { method: 'DELETE' })`.
    4. `showApiKeys()`: lines 395-396 — remove `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };`; change line 397 `fetch('/api/v1/api-keys?user_id=' + user.id, { headers: headers })` to `fetch('/api/v1/api-keys?user_id=' + user.id)`.
    5. `generateKeyForUser()`: lines 404-405 — change `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key'), 'Content-Type': 'application/json' };` to `var headers = { 'Content-Type': 'application/json' };`.
    6. `revokeKey()`: lines 422-423 — remove `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };`; change line 424 `fetch('/api/v1/api-keys/' + key.id, { method: 'DELETE', headers: headers })` to `fetch('/api/v1/api-keys/' + key.id, { method: 'DELETE' })`.

    **Part B — Remove `Authorization: Bearer` headers from profilePage methods in shell.html**

    7. `profilePage.init()`: line 444 — remove the `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };` line; change line 445 `fetch('/api/v1/users/me', { headers: headers })` to `fetch('/api/v1/users/me')`.
    8. `profilePage.loadKeys()`: lines 451-452 — remove the `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };` line; change line 452 `fetch('/api/v1/api-keys?user_id=' + this.user.id, { headers: headers })` to `fetch('/api/v1/api-keys?user_id=' + this.user.id)`.
    9. `profilePage.generateKey()`: lines 458-459 — change `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key'), 'Content-Type': 'application/json' };` to `var headers = { 'Content-Type': 'application/json' };`.
    10. `profilePage.revokeKey()`: lines 472-473 — remove `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };`; change line 473 `fetch('/api/v1/api-keys/' + keyId, { method: 'DELETE', headers: headers })` to `fetch('/api/v1/api-keys/' + keyId, { method: 'DELETE' })`.
    11. `profilePage.exportData()`: lines 477-478 — remove `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };`; change line 478 `fetch('/api/v1/users/' + this.user.id + '/export', { headers: headers })` to `fetch('/api/v1/users/' + this.user.id + '/export')`.
    12. `profilePage.requestErasure()`: lines 490-491 — change `var headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key'), 'Content-Type': 'application/json' };` to `var headers = { 'Content-Type': 'application/json' };`.

    **Part C — Add `toggleCreateForm()` method to userManager for CSP compatibility**

    The Alpine CSP build (`@alpinejs/csp@3.13.3/dist/cdn.min.js`) uses a safe evaluator that evaluates method calls but NOT arbitrary JavaScript expressions in `x-on:click`. The inline expression `showCreateForm = !showCreateForm` may not evaluate. Convert it to a component method.

    In the `userManager` Alpine data component definition in shell.html (lines 312-436), add a new method after the `createUser()` method (after line 382's closing brace), before `deleteUser()` at line 384:

    ```javascript
    toggleCreateForm() {
        this.showCreateForm = !this.showCreateForm;
    },
    ```

    **Part D — Update tab_users.html x-on:click to use the component method**

    In `kb_server/ui/templates/admin/tab_users.html`, line 8, change:
    ```
    x-on:click="showCreateForm = !showCreateForm"
    ```
    to:
    ```
    x-on:click="toggleCreateForm()"
    ```

    **Rationale for each change per D-03 (from 28b-CONTEXT.md):**
    - Removing Bearer headers relies on the session cookie fallback in `get_current_user()` (deps.py lines 50-93). The session cookie is set by both `_loginWithPassword()` (router.py line 83-91) and `_doAuth()` (shell.html line 698-716). This mirrors how the HTMX `base.html` handler (lines 76-81) already works — it only adds Bearer if the key exists, otherwise falls back to the cookie.
    - The `Content-Type: 'application/json'` header IS still needed for POST/PUT requests that send a JSON body, so it is kept where the request sends a body.
    - The `toggleCreateForm()` method approach follows the same pattern as every other method in userManager. It avoids direct expression evaluation by the CSP safe evaluator.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && grep -c "toggleCreateForm" kb_server/ui/templates/admin/shell.html && grep -c "toggleCreateForm()" kb_server/ui/templates/admin/tab_users.html</automated>
  </verify>
  <done>
    - All userManager and profilePage fetch() calls use session cookie auth (no Bearer null headers)
    - `kb_server/ui/templates/admin/tab_users.html` line 8 uses `toggleCreateForm()` not `showCreateForm = !showCreateForm`
    - `userManager` component has `toggleCreateForm()` method defined
    - Admin UI Users tab: clicking "Create User" button shows the form, submit creates user with API key shown once
    - Existing tests still pass
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → API | Direct fetch() and HTMX requests from admin UI to REST API; session cookie (HttpOnly, SameSite=Lax) authenticates requests |
| HTMX-loaded partial → Alpine CSP | HTMX swaps HTML partials containing Alpine directives; Alpine.initTree() processes them |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28b-02 | Spoofing | userManager fetch() calls removing Bearer header | mitigate | Session cookie fallback in `get_current_user()` (deps.py line 50-93) validates HMAC signature + expiry + DB session record. Attacker without the cookie cannot authenticate. |
| T-28b-SC | Tampering | npm/pip installs | accept | No new packages; only CSS/JS changes to existing templates |
</threat_model>

<verification>
### Per-Task Verification

Each task has inline `<verify>` checks (see above).

### Functional Verification (manual on running server)
```bash
# Start server with: cd /home/admin/kb-rag-mcp && python -m kb_server.server --port 8001
# Open http://localhost:8001/admin
# Login with password or API key
# Click Users tab
# Expected: "Create User" button visible with text, clicking reveals form
# Fill form, submit → user created with API key shown once
```

### Regression Check
```bash
cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -20
```
Expected: All admin UI tests pass (43 tests).

```bash
cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py -x -v 2>&1 | tail -20
```
Expected: All 37 auth API tests pass.

```bash
cd /home/admin/kb-rag-mcp && python -m pytest -x --timeout=60 2>&1 | tail -20
```
Expected: No regressions in existing tests.
</verification>

<success_criteria>
- `[x-cloak]` CSS rule prevents Alpine CSP flicker on HTMX-loaded partials
- `htmx:afterSettle` handler calls `Alpine.initTree()` on swapped targets — x-text, x-show, x-on:click render in tab_users.html
- `userManager.createUser()` and `loadUsers()` authenticate via session cookie (not Bearer null) — no more 401
- `profilePage.init()`, `loadKeys()`, `generateKey()`, `revokeKey()`, `exportData()`, `requestErasure()` authenticate via session cookie
- `toggleCreateForm()` method replaces inline `showCreateForm = !showCreateForm` for CSP compatibility
- Admin UI Users tab: Create User button visible, form toggle works, submit creates user with API key shown
- All existing tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/28b-auth-api/28b-02-SUMMARY.md`
</output>
