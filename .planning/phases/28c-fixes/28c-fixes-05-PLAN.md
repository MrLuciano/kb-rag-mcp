---
phase: 28c-fixes
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - kb_server/ui/templates/admin/shell.html
autonomous: true
requirements: SPA-01
must_haves:
  truths:
    - "Login overlay appears when visiting /admin/ without authentication"
    - "Alpine.js adminApp component initializes correctly with @alpinejs/csp"
    - "x-data expression evaluates without silent rejection from CSP build"
  artifacts:
    - path: "kb_server/ui/templates/admin/shell.html"
      provides: "Fully working admin SPA with CSP-compatible Alpine component registration"
      contains: "Alpine.data"
  key_links:
    - from: "kb_server/ui/templates/admin/shell.html:6"
      to: "kb_server/ui/templates/admin/shell.html:extra_scripts"
      via: "x-data references Alpine.data-registered component name"
      pattern: 'x-data="adminApp"'
    - from: "kb_server/ui/templates/base.html:22-25"
      to: "kb_server/ui/templates/admin/shell.html:extra_scripts"
      via: "@alpinejs/csp loaded with defer, then alpine:init registers adminApp"
      pattern: "alpine:init"
---

<objective>
Fix the admin login overlay never appearing by making the adminApp Alpine component compatible with the CSP build of Alpine.js (which silently rejects global function calls in x-data expressions).

**Purpose:** The @alpinejs/csp build prohibits `x-data="adminApp()"` because it evaluates arbitrary JavaScript expressions. The component silently fails to initialize, so `[x-cloak]` keeps the login overlay permanently hidden.

**Output:** Working admin login overlay that appears on first visit and on HTMX 401 responses.
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/admin/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/28c-fixes/28c-fixes-UAT.md

The root cause is documented in the UAT gap for test 7:
"Alpine.js CSP build (@alpinejs/csp) does not support global function calls in x-data expressions. shell.html:6 uses x-data=\"adminApp()\" where adminApp() is a global function — CSP rejects it silently, the component never initializes, and the login overlay stays hidden by [x-cloak] CSS."
</context>

<source_audit>
All items covered:

- **GAP (UAT test 7):** "Alpine.js CSP build does not support global function calls in x-data expressions" → Task 1
- **Requirement SPA-01:** "User can log in at /admin/ with API key via login modal" — login overlay must be visible for this to work → Task 1
</source_audit>

<tasks>

<task type="auto">
  <name>Task 1: Make adminApp CSP-compatible — register via Alpine.data() and switch x-data to name-only reference</name>
  <files>kb_server/ui/templates/admin/shell.html</files>
  <action>
    Make two specific edits to `kb_server/ui/templates/admin/shell.html` to comply with the @alpinejs/csp security model:

    **Edit A — x-data attribute (line 6):** Change `x-data="adminApp()"` to `x-data="adminApp"`. The CSP build does not evaluate global function calls; it only looks up component names registered via `Alpine.data()`. This change references the registered component by name without invoking it as a function expression.

    **Edit B — Component definition (lines 154-270):** Replace the global `function adminApp() { return { ... }; }` definition with an Alpine.data() registration inside an `alpine:init` event listener. The function body (the return object with all methods: init, switchTab, loginWithPassword, authenticate, logout) must remain identical — only the registration mechanism changes.

    The replacement structure inside the `{% block extra_scripts %}` `<script>` element should be:

    ```
    document.addEventListener('alpine:init', () => {
        Alpine.data('adminApp', () => ({
            // ... identical object content as current function body ...
        }));
    });
    ```

    Specifically:
    1. Remove the `function adminApp() { return {` wrapper (line 154) and its closing `}; }` (line 269-270)
    2. Wrap the component object with `document.addEventListener('alpine:init', () => { Alpine.data('adminApp', () => ({` ... `})); });`
    3. The entire existing `extra_scripts` block (HTMX error handlers + adminApp definition) must remain in a single `<script nonce="{{ get_nonce(request) }}">` element

    **Important:** Keep ALL existing code in the `{% block extra_scripts %}` block intact — the HTMX event listeners (lines 134-152) must NOT be modified or removed. Only the `adminApp` registration mechanism changes. The HTMX handlers and the component body remain exactly as-is.

    **Do NOT change:**
    - The component's internal logic, method names, or behavior
    - The HTMX responseError/beforeRequest event listeners (lines 134-152)
    - Any other file or template
  </action>
  <verify>
    <automated>grep -c 'x-data="adminApp"' kb_server/ui/templates/admin/shell.html | grep -q 1 && grep -c 'Alpine.data' kb_server/ui/templates/admin/shell.html | grep -q 1 && grep -c 'alpine:init' kb_server/ui/templates/admin/shell.html | grep -q 1 && grep -c 'function adminApp' kb_server/ui/templates/admin/shell.html | grep -q 0</automated>
  </verify>
  <done>
    Line 6 has `x-data="adminApp"` (no parentheses). The extra_scripts block registers adminApp via `Alpine.data('adminApp', () => ({...}))` inside `document.addEventListener('alpine:init', ...)`. No remaining `function adminApp()` global. All existing HTMX event listeners preserved. The login overlay appears when visiting /admin/ unauthenticated.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CSP build → DOM | Alpine.js CSP build evaluates only registered component data, not arbitrary JS expressions |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-05-01 | Tampering | shell.html inline script | mitigate | Script uses `nonce="{{ get_nonce(request) }}"` per existing CSP policy |
| T-28c-05-02 | Information Disclosure | Alpine.data registered component | accept | Component data (auth state, tab state) is client-side only; all server endpoints are gated per D-10 |
</threat_model>

<verification>
1. `grep -c 'x-data="adminApp"' kb_server/ui/templates/admin/shell.html` returns 1 (no parens)
2. `grep -c 'Alpine.data' kb_server/ui/templates/admin/shell.html` returns 1 (CSP-safe registration)
3. `grep -c 'alpine:init' kb_server/ui/templates/admin/shell.html` returns 1 (event-based init)
4. `grep -c 'function adminApp' kb_server/ui/templates/admin/shell.html` returns 0 (no global function)
5. HTMX responseError listener (401 handler) preserved — `grep -c 'htmx:responseError' kb_server/ui/templates/admin/shell.html` returns 1
</verification>

<success_criteria>
- `x-data="adminApp"` (no parens) on the shell div
- `Alpine.data('adminApp', () => ({...}))` inside `alpine:init` listener replaces the global function
- All existing component behavior preserved identically
- Login overlay visible when visiting /admin/ without session cookie
</success_criteria>

<output>
Create `.planning/phases/28c-fixes/28c-fixes-05-SUMMARY.md` when done
</output>
