---
phase: 28c-fixes
plan: 03
type: execute
wave: 3
depends_on:
  - 28c-fixes-01
  - 28c-fixes-02
files_modified:
  - kb_server/ui/templates/base.html
  - kb_server/ui/app.py
  - kb_server/auth/deps.py
  - kb_server/auth/service.py
  - kb_server/auth/models.py
  - kb_server/ui/routes_admin.py
  - kb_server/server.py
autonomous: true
gap_closure: true
requirements:
  - SPA-01
  - SPA-02
  - SPA-12
must_haves:
  truths:
    - Admin panel login overlay appears on first visit (no server error)
    - User can log in with default admin API key and access all tabs
    - Tab content loads without "Failed to load content" error after auth
    - Server-side auth blocks unauthenticated tab content requests (401)
    - Auth endpoints (/api/v1/auth/session, /api/v1/users/me) work on UI port (8001)
    - Default admin user exists with auto-generated API key on first startup
  artifacts:
    - path: kb_server/ui/templates/base.html
      provides: Working Alpine.js CDN URL
      contains: "cdn.min.js"
    - path: kb_server/ui/app.py
      provides: Auth router mounted on UI app
      contains: "auth.router"
    - path: kb_server/auth/deps.py
      provides: Session cookie validation in get_current_user
      contains: "request.cookies.get"
    - path: kb_server/auth/service.py
      provides: Default admin account seeding method
      contains: "ensure_admin_account"
    - path: kb_server/ui/routes_admin.py
      provides: Auth-gated admin endpoints
      contains: "Depends(get_current_user)"
  key_links:
    - from: base.html Alpine.js script tag
      to: cdn.jsdelivr.net
      via: correct URL path
      pattern: "cdn.min.js"
    - from: app.py startup
      to: auth/service.py AuthService
      via: app.state.auth_service
      pattern: "auth_service"
    - from: routes_admin.py admin_tab_content
      to: auth/deps.py get_current_user
      via: Depends()
      pattern: "Depends(get_current_user)"
---

<objective>
Close the BLOCKER infrastructure gaps from Phase 28c UAT: fix Alpine.js CDN URL, mount auth router on UI app, add server-side auth gating to all admin routes, and seed default admin account. These fixes resolve the "Failed to load content" error and enable the auth flow to actually function.

Purpose: Without these fixes, the Admin SPA is completely broken — Alpine.js fails to load (all x-data/x-show silently fail), auth endpoints return 404 on the UI port, tab endpoints have zero server-side auth protection, and there is no default admin account to log in with.
Output: Working admin panel with functional auth flow on the UI server port.
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/admin/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/phases/28c-fixes/28c-fixes-CONTEXT.md
@.planning/phases/28c-admin-spa-panel/28c-UAT.md
@.planning/debug/admin-panel-auth-and-content-loading.md

# Source files modified by earlier plans (read current state after Plans 01-02 apply)
@kb_server/ui/templates/base.html
@kb_server/ui/app.py
@kb_server/auth/deps.py
@kb_server/auth/service.py
@kb_server/auth/models.py
@kb_server/ui/routes_admin.py

# Auth router (existing, provides POST /auth/session and GET /users/me)
@kb_server/auth/router.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix Alpine.js CDN URL and update error handling in base.html (D-08)</name>
  <files>
    kb_server/ui/templates/base.html
  </files>
  <behavior>
    - Test: base.html Alpine.js script src contains `cdn.min.js` instead of `csp.min.js`
    - Test: base.html Alpine.js script src does not contain a URL that returns 404
    - Test: base.html htmx:responseError handler shows distinct messages for 401 vs 404 vs 500
    - Test: base.html CSP middleware script-src directive allows the Alpine.js CDN URL
  </behavior>
  <action>
    1. In base.html line 22: Change Alpine.js script URL from `alpinejs@3.13.3/dist/csp.min.js` to `https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js` (standard Alpine.js build, not the CSP build — the CSP middleware already allows CDN script sources with nonce for inline scripts, and `cdp.min.js` is the correct non-CSP main build path for jsdelivr).
    2. Remove the `integrity` attribute from the Alpine.js script tag (the existing hash was computed for `csp.min.js` which returns 404; the executor should fetch the correct integrity hash for `cdn.min.js` from `https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js` via `openssl dgst -sha384 -binary | base64` and add it back if possible; if fetching fails, remove integrity entirely so Alpine.js loads).
    3. Update the `htmx:responseError` handler (second handler, line 91-98) that shows "Failed to load content" to provide status-code-specific messages:
       - `evt.detail.xhr.status === 401`: show "Session expired. Please log in again." (do NOT override the first 401 handler which triggers the login overlay)
       - `evt.detail.xhr.status === 404`: show "Page not found. The requested resource does not exist."
       - `evt.detail.xhr.status >= 500`: show "Server error. Please try again later."
       - Other errors: keep existing "Failed to load content. Please try again later."
  </action>
  <verify>
    <automated>grep -c 'cdn.min.js' kb_server/ui/templates/base.html</automated>
  </verify>
  <done>
    - Alpine.js loads from valid CDN URL (no 404)
    - Error messages distinguish 401 vs 404 vs 500 vs other
    - SRI integrity removed or updated to match cdn.min.js
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Mount auth router on UI app and seed default admin account (D-09)</name>
  <files>
    kb_server/ui/app.py
    kb_server/auth/service.py
    kb_server/auth/models.py
    kb_server/server.py
  </files>
  <behavior>
    - Test: app.py mounts auth_router at prefix /api/v1 (same as MCP server)
    - Test: app.py initializes AuthService during startup event and stores in app.state
    - Test: app.py startup seeds admin user ("admin" role="admin") + auto-generated API key if no users exist
    - Test: auth/service.py has `ensure_admin_account()` method that creates admin user + API key
    - Test: ensure_admin_account() returns the raw API key (for log display) or None if already exists
    - Test: ensure_admin_account() logs the API key to stdout with clear formatting
    - Test: app startup event calls ensure_admin_account()
    - Test: AuthService in app.py uses the same AUTH_DB_PATH as server.py (data/auth.db)
  </action>
    1. In kb_server/auth/service.py: Add `ensure_admin_account()` method:
       - Check if "admin" user exists via `self.get_user_by_username("admin")`
       - If exists, check if it has any non-revoked API keys
       - If no admin user: create one with `self.create_user(username="admin", role="admin")`
       - If no active API keys: generate one via `self.create_api_key(admin.id, description="Default admin key for UI login")`
       - Print the raw API key to stdout/logs with a clear banner:
         ```python
         log.info("=" * 60)
         log.info("DEFAULT ADMIN ACCOUNT READY")
         log.info(f"  Username: admin")
         log.info(f"  API Key: {raw_key}")
         log.info("=" * 60)
         ```
       - Return the raw_key string if created, or None if keys already exist
    2. In kb_server/auth/models.py: Add `UserSession` table with columns:
       - `id` (String 36, PK, UUID default)
       - `user_id` (String 36, FK to users.id, index)
       - `session_token` (String 255, unique, not null) — partial HMAC for lookup
       - `ip_address` (String 45, nullable) — client IP
       - `user_agent` (String 255, nullable)
       - `created_at` (DateTime, default=now)
       - `last_used_at` (DateTime, default=now)
       - `is_revoked` (Boolean, default=False)
       - This table is created by `Base.metadata.create_all(engine)` and will be used in Plan 04 for session management.
    3. In kb_server/ui/app.py: Add startup logic:
       - Import `kb_server.auth.router` as `auth_router`
       - Import `kb_server.auth.service.AuthService`
       - Import `Path` from pathlib
       - Add `@app.on_event("startup")` async function that:
         - Determines auth DB path: `Path(os.getenv("AUTH_DB_PATH", "data/auth.db"))`
         - Creates AuthService instance and assigns to `app.state.auth_service`
         - Calls `app.state.auth_service.ensure_admin_account()`
       - After the startup definition, mount the auth router:
         ```python
         app.include_router(auth_router)
         ```
       - Also add `from kb_server.auth.erasure import ErasureManager` and init erasure_manager on app.state so auth router dependencies work.
    4. In kb_server/server.py: The existing auth initialization creates `auth_service` inside `main()` for the SSE transport. No changes needed here since the UI app now handles its own auth initialization. However, ensure both use the same `AUTH_DB_PATH` env var (default `data/auth.db`), which they already do via `config.get("AUTH_DB_PATH", "data/auth.db")`.
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "auth"</automated>
  </verify>
  <done>
    - Auth router mounted on UI app at /api/v1
    - GET /api/v1/users/me works on UI port (8001) when authenticated
    - Default admin account created with API key logged to stdout on first startup
    - UserSession model defined in auth/models.py
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add server-side auth gating to admin routes and session cookie support in get_current_user (D-10)</name>
  <files>
    kb_server/auth/deps.py
    kb_server/ui/routes_admin.py
  </files>
  <behavior>
    - Test: get_current_user validates JWT session cookie (not just API key headers)
    - Test: Session cookie validation parses user_id:expires_at:signature and verifies HMAC
    - Test: Session cookie validation checks expiry (rejects expired tokens)
    - Test: admin_shell (GET /admin) does NOT require auth (returns HTML with Alpine.js login overlay)
    - Test: admin_tab_content (GET /tabs/{tab_name}) requires auth via Depends(get_current_user)
    - Test: admin_monitor_lights, admin_config_table, admin_profile_content require auth
    - Test: admin_documents_content, admin_ingest_trigger, admin_job_status, admin_ragas_run require auth
    - Test: Unauthenticated tab content requests return 401 with empty HTML fragment
    - Test: The `_verify_request_api_key` function on api_router routes is unchanged (still works)
  </behavior>
  <action>
    1. In kb_server/auth/deps.py:
       - Update `get_current_user()` function to also check the `session` cookie:
         - After checking API key headers and finding none, check `request.cookies.get("session")`
         - Parse the session cookie: `parts = session_cookie.split(":")` — expects 3 parts: `user_id:expires_at:signature`
         - Check `int(parts[1]) > time.time()` (not expired)
         - Compute expected HMAC: `hmac.new(secret.encode(), f"{parts[0]}:{parts[1]}".encode(), hashlib.sha256).hexdigest()[:16]`
         - Compare with `hmac.compare_digest(parts[2], expected)`
         - If valid, look up user via `service.get_user(parts[0])`
         - Return user if found and active
       - Import `hashlib`, `hmac`, `time`, `os` at the top of the file (if not already)
       - Read `_JWT_SECRET` from env at module level (same pattern as auth/router.py)
       - Keep the existing API-key-header check as primary auth mechanism (session cookie is fallback)
       - Log a debug message when session cookie is used for auth: `log.debug("Authenticated via session cookie: user=%s", user.id)`

    2. In kb_server/ui/routes_admin.py:
       - Add import: `from kb_server.auth.deps import get_current_user`
       - Add `Depends(get_current_user)` to all tab content and action endpoints **except** the shell endpoint:
         - `admin_tab_content` (line 38): add `_auth: User = Depends(get_current_user)` parameter
         - `admin_monitor_lights` (line 121): add auth dependency
         - `admin_config_table` (line 134): add auth dependency
         - `admin_profile_content` (line 144): add auth dependency
         - `admin_documents_content` (line 154): add auth dependency
         - `admin_ingest_trigger` (line 188): add auth dependency
         - `admin_job_status` (line 206): add auth dependency
         - `admin_ragas_run` (line 230): add auth dependency
       - Do NOT add auth to `admin_shell` (line 24) — the shell endpoint returns HTML that contains the Alpine.js login overlay, which handles the unauthenticated state via `x-show="!isAuthenticated"`
       - The existing `api_router` endpoints already use `Depends(_verify_request_api_key)` — leave them unchanged
       - When tab content endpoints receive an unauthenticated request, `get_current_user` raises `HTTPException(401)`. FastAPI converts this to a 401 JSON response. Since HTMX expects HTML, the executor should ensure that the 401 response for HTMX requests returns an HTML fragment (or rely on the HTMX error handler in base.html to catch it). Actually, FastAPI's default 401 handler returns JSON. To make HTMX work properly with 401 responses:
         - Add a custom exception handler in routes_admin.py for 401 that returns an HTML error fragment when the request has `HX-Request: true` header:
         ```python
         @router.exception_handler(HTTPException)
         async def admin_auth_exception_handler(request: Request, exc: HTTPException):
             if exc.status_code == 401 and request.headers.get("HX-Request") == "true":
                 return HTMLResponse(
                     content="",
                     status_code=401,
                     headers={"HX-Redirect": "/admin"} if ... else {},
                 )
             raise exc
         ```
         - The simplest approach: the base.html `htmx:responseError` handler already catches 401 and shows the login overlay. As long as the tab-content target div is not overwritten with an error message, the flow works. The current base.html handler (Task 1 of this plan updated) checks for 401 first and returns early (letting the existing handler logic run). So no custom exception handler is needed — the HTMX 401 response will trigger the base.html handler which shows the login modal.
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "auth"</automated>
  </verify>
  <done>
    - get_current_user validates both API key headers AND session cookies
    - All tab content endpoints return 401 when unauthenticated (except shell)
    - Shell endpoint serves HTML without auth (login overlay handles unauthenticated state)
    - Existing api_router auth (via _verify_request_api_key) unchanged
    - 401 responses from HTMX tab requests correctly trigger login overlay
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client→UI app | Unauthenticated users access /admin shell; tab content endpoints require auth |
| UI app→auth DB | AuthService reads/writes auth.db for user and API key data |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-09 | Spoofing | get_current_user session cookie | mitigate | Session cookie HMAC-signed with JWT_SECRET; cookie validated on every request (including expiry check) |
| T-28c-10 | Tampering | base.html Alpine.js CDN URL | mitigate | Remove SRI integrity if hash cannot be verified (allowing load); CDN is trusted (jsdelivr) |
| T-28c-11 | Elevation of Privilege | admin routes without auth | mitigate | Per D-10: all tab content endpoints require Depends(get_current_user) |
| T-28c-12 | Information Disclosure | Default admin API key in logs | accept | Logged at startup only; key displayed once; admin expected to generate new key immediately |
</threat_model>

<verification>
- Run admin UI tests: `pytest tests/test_admin_ui.py -v -k "auth"`
- Check Alpine.js loads: `python -c "import requests; r=requests.get('https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js'); print(f'Status: {r.status_code}, Size: {len(r.content)}')"` (should return 200)
- Verify auth router mounted: `grep -c 'include_router.*auth_router' kb_server/ui/app.py` (should be >= 1)
- Verify auth gating: `grep -c 'Depends(get_current_user)' kb_server/ui/routes_admin.py` (should be >= 8)
- Run full test suite: `pytest tests/ -x --timeout=60 -q | tail -5`
- Run linting: `flake8 kb_server/ui/routes_admin.py kb_server/ui/app.py kb_server/auth/deps.py kb_server/auth/service.py`
</verification>

<success_criteria>
- [ ] Alpine.js loads from valid CDN URL (no 404)
- [ ] Auth router mounted on UI app — /api/v1/auth/session reachable on port 8001
- [ ] Default admin account seeded on first startup with API key logged to stdout
- [ ] All admin tab content endpoints require auth (8 endpoints gated)
- [ ] get_current_user validates session cookies in addition to API key headers
- [ ] Shell endpoint serves HTML without auth (login overlay handles unauthenticated state)
- [ ] "Failed to load content" error replaced with status-code-specific messages
- [ ] All new tests pass; no regressions in existing test suite
- [ ] Flake8 clean on all modified files
</success_criteria>

<output>
Create `.planning/phases/28c-fixes/28c-fixes-03-SUMMARY.md` when done
</output>
