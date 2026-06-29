---
status: resolved
trigger: "Admin panel login overlay doesn't appear for user visiting admin page without valid session"
created: 2026-06-17T18:00:00Z
updated: 2026-06-17T18:00:00Z
---

## Current Focus

hypothesis: "[pending]"
test: "[pending]"
expecting: "[pending]"
next_action: "gather symptoms from code analysis"

## Symptoms

expected: |
  1. User visits /admin/ without session cookie
  2. HTMX request returns 401
  3. 401 triggers CustomEvent('show-login')
  4. Alpine.js overlay listens and shows login form
actual: "Page loads but no login overlay appears"
errors: "none reported"
reproduction: "Visit /admin/ from a fresh browser (no session cookie, no API key in localStorage)"
started: "unknown — likely since UI was deployed"

## Eliminated

- hypothesis: "Invalid Alpine.js CDN URL"
  evidence: "URL https://cdn.jsdelivr.net/npm/@alpinejs/csp@3.13.3/dist/cdn.min.js returns HTTP 200 with valid JS content (44337 bytes). Integrity hash matches."
  timestamp: 2026-06-17T18:00:00Z

- hypothesis: "CSP blocks Alpine.js script"
  evidence: "CSP header allows cdn.jsdelivr.net. Alpine CSP build does not require unsafe-eval. Inline scripts have valid nonces matching the CSP nonce."
  timestamp: 2026-06-17T18:00:00Z

- hypothesis: "isAuthenticated starts as true"
  evidence: "Data model explicitly sets isAuthenticated: false in adminApp() return object (shell.html line 158)"
  timestamp: 2026-06-17T18:00:00Z

- hypothesis: "x-show expression !isAuthenticated not supported by CSP build"
  evidence: "Official CSP docs show '!loading && count > 0' as supported basic operation. The ! operator is supported."
  timestamp: 2026-06-17T18:00:00Z

- hypothesis: "Missing [x-cloak] CSS rule causes flash of overlay"
  evidence: "Alpine CSP build injects [x-cloak] { display: none !important; } CSS automatically on startup (confirmed in CDN source)."
  timestamp: 2026-06-17T18:00:00Z

- hypothesis: "Server-side 401 not returned"
  evidence: "TestClient confirms /admin/tabs/documents returns 401 without auth. /admin/ shell route returns 200."
  timestamp: 2026-06-17T18:00:00Z

- hypothesis: "Auth endpoints not mounted on UI app"
  evidence: "app.py includes auth_router at line 79. POST /api/v1/auth/login returns 200 with session cookie. POST /api/v1/auth/session returns 401 with bad key."
  timestamp: 2026-06-17T18:00:00Z

- hypothesis: "HTMX htmx:responseError handler not dispatching show-login"
  evidence: "base.html lines 82-86: handler dispatches window.dispatchEvent(new CustomEvent('show-login')) when evt.detail.xhr.status === 401. Code is syntactically correct."
  timestamp: 2026-06-17T18:00:00Z

## Evidence

- timestamp: 2026-06-17T18:00:00Z
  checked: "kb_server/ui/templates/admin/shell.html"
  found: "Component defined as global function adminApp() used with x-data='adminApp()'"
  implication: "Uses global function call pattern for Alpine component"

- timestamp: 2026-06-17T18:00:00Z
  checked: "kb_server/ui/templates/base.html"
  found: "Alpine CSP build loaded: @alpinejs/csp@3.13.3/dist/cdn.min.js with defer"
  implication: "Alpine CSP build is being used, NOT standard Alpine"

- timestamp: 2026-06-17T18:00:00Z
  checked: "Official Alpine CSP documentation (alpinejs.dev/advanced/csp)"
  found: "Global variables and functions are NOT supported in CSP build expressions. This includes: console.log(), document.title, Math.max(), parseInt(), JSON.stringify(), and any other global function calls."
  implication: "x-data='adminApp()' calls a global function adminApp() — NOT supported by CSP build"

- timestamp: 2026-06-17T18:00:00Z
  checked: "Official Alpine CSP documentation — 'When to Extract Logic'"
  found: "CSP build supports Alpine.data() for reusable components. Uses x-data='componentName' (without parentheses) for registered components."
  implication: "Fix is to register adminApp via Alpine.data('adminApp', () => ({...})) and use x-data='adminApp'"

## Resolution

root_cause: "adminApp() is defined as a global function and invoked via x-data='adminApp()' in shell.html. The Alpine CSP build (@alpinejs/csp) does NOT support calling global functions in expressions per its documented limitations. The component never initializes — Alpine injects [x-cloak] CSS (hiding the overlay), but never processes the component (so x-cloak is never removed, x-show is never evaluated, and the overlay stays hidden)."
fix: "Registered adminApp via Alpine.data('adminApp', () => ({...})) and changed x-data='adminApp()' to x-data='adminApp' in shell.html (Phase 28c-fixes Plan 05)"
verification: "Login overlay appears on 401; JWT session cookie exchange works end-to-end (verified in 28c-fixes UAT)"
files_changed: ["kb_server/ui/templates/admin/shell.html"]
