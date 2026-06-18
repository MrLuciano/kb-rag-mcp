---
phase: 28c-fixes
plan: 05
completed: 2026-06-17T17:00:00Z
task_count: 1
commits:
  - 1c36b27
---

## Summary

**Objective:** Fix admin login overlay not appearing — `@alpinejs/csp` silently rejected `x-data="adminApp()"` (global function calls unsupported in CSP build).

**Changes made to `kb_server/ui/templates/admin/shell.html`:**

- **Edit A (line 6):** `x-data="adminApp()"` → `x-data="adminApp"` — name-only reference, no parens
- **Edit B (lines 154-270):** `function adminApp() { return { ... }; }` → `document.addEventListener('alpine:init', () => { Alpine.data('adminApp', () => ({ ... })); });` — CSP-safe registration

**Preserved identically:**
- Component state/methods (init, switchTab, loginWithPassword, authenticate, logout)
- HTMX `responseError` and `beforeRequest` event listeners
- All other template content

## Verification

| Gate | Result |
|------|--------|
| `x-data="adminApp"` (no parens) | 1 match |
| `Alpine.data` present | 1 match |
| `alpine:init` present | 1 match |
| `function adminApp` absent | 0 matches |
| `htmx:responseError` preserved | 1 match |

## Test Results

1382 passed, 5 failed (pre-existing), 14 skipped — no regressions.
