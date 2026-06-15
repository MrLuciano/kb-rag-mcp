---
phase: 28c-admin-spa-panel
plan: 01
type: execute
wave: 2
depends_on:
  - 28b-auth-api
  - 40-config-backlog
files_modified:
  - kb_server/ui/app.py
  - kb_server/ui/templates/base.html
  - kb_server/auth/router.py
  - kb_server/auth/schemas.py
  - kb_server/ui/routes_admin.py
  - kb_server/ui/templates/admin/shell.html
  - kb_server/ui/templates/admin/tab_documents.html
  - kb_server/ui/templates/admin/tab_monitoring.html
  - kb_server/ui/templates/admin/tab_ingestion.html
  - kb_server/ui/templates/admin/tab_ragas.html
  - kb_server/ui/templates/admin/tab_admin.html
  - kb_server/ui/templates/admin/tab_profile.html
  - tests/test_admin_ui.py
autonomous: true
requirements:
  - SPA-01
  - SPA-02
  - SPA-03
  - SPA-04
  - SPA-05
  - SPA-10
  - SPA-11
  - SPA-12
must_haves:
  truths:
    - User can navigate to /admin/ and see a login modal
    - User can enter an API key and log in (JWT session cookie set, modal closes)
    - Sidebar shows 6 tabs, Admin tab hidden for non-admin users
    - Clicking a tab loads its content via HTMX partial
    - Logout clears auth state and shows login modal again
    - All CDN scripts have SRI integrity hashes
    - CSP middleware injects nonce into every page response
  artifacts:
    - path: "kb_server/ui/routes_admin.py"
      provides: "Admin SPA route registration on the UI FastAPI app"
      contains: "admin_shell, admin_tab_content"
      min_lines: 60
    - path: "kb_server/ui/templates/admin/shell.html"
      provides: "SPA shell with Alpine.js auth state, sidebar, login modal"
      contains: "function adminApp, x-data, session endpoint call"
      min_lines: 150
    - path: "kb_server/auth/router.py (session endpoint added)"
      provides: "POST /api/v1/auth/session"
      contains: "Response.set_cookie, UserResponse.model_validate"
      min_lines: 30
    - path: "kb_server/ui/app.py"
      provides: "CSP middleware, nonce injection, admin router import"
      contains: "CSPMiddleware, BaseHTTPMiddleware"
      min_lines: 15
    - path: "tests/test_admin_ui.py"
      provides: "Coverage for admin shell, auth flow, CSP"
      contains: "test_admin_shell, test_auth_session, test_csp_middleware"
      min_lines: 100
  key_links:
    - from: "kb_server/ui/templates/admin/shell.html"
      to: "kb_server/auth/router.py"
      via: "POST /api/v1/auth/session"
      pattern: "fetch.*/api/v1/auth/session"
    - from: "kb_server/ui/templates/base.html"
      to: "CDN (jsdelivr.net, unpkg.com)"
      via: "script src with integrity attribute"
      pattern: "integrity=\"sha384-"
    - from: "kb_server/ui/app.py"
      to: "kb_server/ui/routes_admin.py"
      via: "import routes_admin"
      pattern: "import.*routes_admin"
---

<objective>
Create the Admin SPA shell at `/admin/` with Alpine.js-powered auth flow (API key → JWT session cookie), role-gated sidebar navigation, HTMX-driven tab partial loading, CSP middleware with nonce-based script-src, and SRI integrity hashes on all CDN assets.

**Purpose:** The Admin SPA shell is the foundation for all admin panel functionality. It handles authentication (via the `/api/v1/auth/session` endpoint added to the auth router), client-side state management with Alpine.js, and HTMX-based tab content loading. CSP middleware protects against XSS by using Alpine.js CSP build and nonce-based inline scripts.

**Output:** `routes_admin.py` with shell + tab endpoints, `shell.html` with Alpine.js adminApp() component, `kb_server/auth/router.py` extended with session endpoint, `kb_server/ui/app.py` with CSP middleware, `base.html` with SRI-hashed CDN scripts, 6 tab placeholder partials, and `test_admin_ui.py` with auth flow + CSP tests.

**Artifacts this plan produces:**

| Symbol | Kind | Location |
|--------|------|----------|
| `POST /api/v1/auth/session` | API endpoint | `kb_server/auth/router.py` |
| `CSPMiddleware` | Starlette middleware class | `kb_server/ui/app.py` |
| `admin_shell()` | Route handler | `kb_server/ui/routes_admin.py` |
| `admin_tab_content()` | Route handler | `kb_server/ui/routes_admin.py` |
| `adminApp()` | Alpine.js component | `kb_server/ui/templates/admin/shell.html` |
| `Authenticate(key)` | Alpine.js method | `kb_server/ui/templates/admin/shell.html` |
| `logout()` | Alpine.js method | `kb_server/ui/templates/admin/shell.html` |
| `SessionResponse` | Pydantic schema | `kb_server/auth/schemas.py` |
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@kb_server/ui/templates/base.html
@kb_server/ui/app.py
@kb_server/auth/router.py
@kb_server/auth/schemas.py
@tests/test_ui_routes.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Add POST /api/v1/auth/session endpoint to auth router (per D-01)</name>
  <files>kb_server/auth/router.py, kb_server/auth/schemas.py, tests/test_admin_ui.py</files>
  <read_first>kb_server/auth/router.py, kb_server/auth/schemas.py</read_first>
  <action>
    Step 1 — Write failing test `test_auth_session_exchange` in `tests/test_admin_ui.py`.
    The test sends POST /api/v1/auth/session with Authorization: Bearer {valid_key} and expects:
    - 200 status
    - Set-Cookie header with session cookie (HttpOnly, SameSite=Lax)
    - JSON body with user info (id, username, role)

    Also write `test_auth_session_invalid_key` expecting 401.

    Use httpx.AsyncClient with ASGITransport on the main FastAPI app (not the UI app — the auth router is on the main server app). Import app from kb_server.server for the main app.

    Step 2 — Run tests to confirm they fail (routes don't exist yet).

    Step 3 — Add SessionResponse schema to `kb_server/auth/schemas.py`:

    ```python
    class SessionResponse(BaseModel):
        """Response from POST /api/v1/auth/session."""
        id: str
        username: str
        role: str
        token_type: str = "Bearer"
        expires_in: int = 28800  # 8 hours
    ```

    Step 4 — Add session endpoint to `kb_server/auth/router.py`:

    ```python
    import secrets
    import hashlib
    import hmac
    import time
    from fastapi import Response as FastAPIResponse
    from kb_server.auth.schemas import SessionResponse

    @router.post("/auth/session", response_model=SessionResponse)
    async def create_session(
        request: Request,
        response: FastAPIResponse,
        current_user: User = Depends(get_current_user),
    ):
        """Exchange API key for an HttpOnly JWT session cookie (8h)."""
        # Generate a session token (HMAC-signed timestamp + user_id)
        expires_at = int(time.time()) + 28800
        raw = f"{current_user.id}:{expires_at}"
        secret = os.getenv("JWT_SECRET", secrets.token_hex(32))
        signature = hmac.new(
            secret.encode(), raw.encode(), hashlib.sha256
        ).hexdigest()[:16]
        session_token = f"{raw}:{signature}"

        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            samesite="lax",
            max_age=28800,
            secure=False,  # Set True in production behind HTTPS
            path="/",
        )
        return SessionResponse(
            id=str(current_user.id),
            username=current_user.username,
            role=current_user.role,
            expires_in=28800,
        )
    ```

    Add `import os` to the imports at the top of router.py.

    Step 5 — Run tests. They should pass now.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::TestAuthSession -x -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - POST /api/v1/auth/session returns 200 with UserResponse-like JSON body
    - POST /api/v1/auth/session sets HttpOnly, SameSite=Lax, max-age=28800 session cookie
    - Invalid/revoked API key returns 401
    - SessionResponse schema has id, username, role, token_type, expires_in fields
  </acceptance_criteria>
  <done>POST /api/v1/auth/session endpoint added to auth router; tests passing.</done>
</task>

<task type="auto" tdd="true">
  <name>Add CSP middleware, Alpine.js CDN with SRI, and admin nav link to base.html (per D-10, D-11)</name>
  <files>kb_server/ui/app.py, kb_server/ui/templates/base.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/app.py, kb_server/ui/templates/base.html</read_first>
  <action>
    Step 1 — Write failing tests in TestAdminCSP class:
    `test_admin_page_has_csp_header` — GET /admin/ and verify response has Content-Security-Policy header containing `nonce-`
    `test_admin_page_has_nonce_in_script_tags` — GET /admin/ and verify script tags contain nonce attribute
    `test_cdn_scripts_have_integrity` — Read base.html and confirm all CDN script tags have integrity attribute

    Step 2 — Implement CSP middleware in `kb_server/ui/app.py`:

    ```python
    import secrets
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    class CSPMiddleware(BaseHTTPMiddleware):
        """Inject CSP headers with per-request nonce on every response."""

        CSP_DIRECTIVES = (
            "default-src 'self'; "
            "script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "frame-src 'self' https:; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )

        async def dispatch(self, request: Request, call_next):
            nonce = secrets.token_hex(16)
            request.state.csp_nonce = nonce
            response: Response = await call_next(request)
            if "text/html" in response.headers.get("content-type", ""):
                response.headers["Content-Security-Policy"] = (
                    self.CSP_DIRECTIVES.format(nonce=nonce)
                )
            return response

    app.add_middleware(CSPMiddleware)
    ```

    Then remove the old health-check endpoint import pattern and add:
    ```python
    import kb_server.ui.routes_admin  # noqa: F401 — registers admin routes
    ```

    Step 3 — Update `kb_server/ui/templates/base.html`:

    Add Alpine.js CSP build CDN with defer, SRI integrity, nonce, and crossorigin:
    ```html
    <!-- Alpine.js CSP build (defer, integrity, nonce) -->
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js"
            defer
            crossorigin="anonymous"
            nonce="{{ request.state.csp_nonce }}"></script>
    ```

    Update HTMX script tag to add nonce and integrity:
    ```html
    <script src="https://unpkg.com/htmx.org@1.9.10"
            crossorigin="anonymous"
            nonce="{{ request.state.csp_nonce }}"></script>
    ```

    Add Bootstrap CSS integrity:
    ```html
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
          rel="stylesheet"
          crossorigin="anonymous">
    ```

    Add Bootstrap JS integrity:
    ```html
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
            crossorigin="anonymous"
            nonce="{{ request.state.csp_nonce }}"></script>
    ```

    Add "Admin Panel" nav link after Search Tester:
    ```html
    <li class="nav-item">
        <a class="nav-link" href="/admin/">Admin Panel</a>
    </li>
    ```

    NOTE: The executor MUST compute actual SRI integrity hashes by fetching each CDN file and hashing:
    ```bash
    curl -sL {CDN_URL} | openssl dgst -sha384 -binary | openssl base64 -A
    ```
    Then add `integrity="sha384-{hash}"` to each script/link tag above.

    Step 4 — Run tests. They should pass now.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::TestAdminCSP -x -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - /admin/ response includes Content-Security-Policy header with nonce-{value}
    - HTML script tags contain nonce="{{ request.state.csp_nonce }}"
    - All CDN script/link tags have integrity attribute with sha384- hash
    - Alpine.js CSP build CDN loaded with defer, nonce, crossorigin
    - Admin Panel nav link present in base.html navbar after Search Tester
    - Existing UI pages still render correctly
  </acceptance_criteria>
  <done>CSP middleware, Alpine.js CDN, SRI hashes, and admin nav link added and tested.</done>
</task>

<task type="auto" tdd="true">
  <name>Create shell.html with auth flow, sidebar, login modal, and 6 tab partials (per D-02, D-03, D-04, D-05, SPA-04, SPA-12)</name>
  <files>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/shell.html, kb_server/ui/templates/admin/tab_documents.html, kb_server/ui/templates/admin/tab_monitoring.html, kb_server/ui/templates/admin/tab_ingestion.html, kb_server/ui/templates/admin/tab_ragas.html, kb_server/ui/templates/admin/tab_admin.html, kb_server/ui/templates/admin/tab_profile.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/app.py, kb_server/ui/templates/base.html</read_first>
  <action>
    Step 1 — Write failing tests in TestAdminShell class:
    `test_admin_shell_returns_200` — GET /admin/ returns 200, HTML content type
    `test_admin_shell_contains_alpine_data` — response contains "x-data" or "adminApp"
    `test_admin_tab_valid_returns_200` — GET /admin/tabs/documents returns 200
    `test_admin_tab_invalid_returns_404` — GET /admin/tabs/nonexistent returns 404
    `test_admin_shell_sidebar_tabs` — response contains "Documents", "Monitoring", "Ingestion", "RAGAS", "Admin", "Profile"

    Step 2 — Create `kb_server/ui/routes_admin.py`:

    ```python
    """Admin SPA routes — shell, tab partials, and auth flow."""
    from fastapi import APIRouter, Request, HTTPException
    from fastapi.responses import HTMLResponse
    from kb_server.ui.app import app, templates

    TABS = [
        {"id": "documents", "label": "Documents", "icon": "📄"},
        {"id": "monitoring", "label": "Monitoring", "icon": "📊"},
        {"id": "ingestion", "label": "Ingestion", "icon": "⚡"},
        {"id": "ragas", "label": "RAGAS Evaluation", "icon": "🧪"},
        {"id": "admin", "label": "Admin", "icon": "⚙️", "admin_only": True},
        {"id": "profile", "label": "Profile", "icon": "👤"},
    ]

    @app.get("/admin/", response_class=HTMLResponse, include_in_schema=False)
    async def admin_shell(request: Request):
        """Admin SPA shell with sidebar, tabs, and auth modal."""
        return templates.TemplateResponse(
            request,
            "admin/shell.html",
            {
                "request": request,
                "tabs": TABS,
            },
        )

    @app.get("/admin/tabs/{tab_name}", response_class=HTMLResponse, include_in_schema=False)
    async def admin_tab_content(tab_name: str, request: Request):
        """Return partial HTML for a tab."""
        tab_templates = {t["id"]: f"admin/tab_{t['id']}.html" for t in TABS}
        template = tab_templates.get(tab_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"Tab '{tab_name}' not found")
        return templates.TemplateResponse(
            request,
            template,
            {"request": request},
        )
    ```

    Step 3 — Create admin template directory and `shell.html`:

    ```bash
    mkdir -p kb_server/ui/templates/admin
    ```

    `kb_server/ui/templates/admin/shell.html` — extends `base.html`, contains:

    ```html
    {% extends "base.html" %}
    {% block title %}Admin Panel - KB-RAG{% endblock %}

    {% block content %}
    <div x-data="adminApp()" x-init="initAuth()">
        <!-- Login modal overlay -->
        <div x-show="!isAuthenticated" class="modal d-block" tabindex="-1"
             style="background: rgba(0,0,0,0.5);">
            <div class="modal-dialog modal-sm modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Login to Admin Panel</h5>
                    </div>
                    <div class="modal-body">
                        <div x-show="loginError" class="alert alert-danger"
                             x-text="loginError" role="alert"></div>
                        <form @submit.prevent="login(apiKeyInput)">
                            <div class="mb-3">
                                <label for="apiKey" class="form-label">Enter your API key</label>
                                <input type="password" class="form-control" id="apiKey"
                                       x-model="apiKeyInput" placeholder="kb_xxxxxxxx..."
                                       aria-label="API key">
                            </div>
                            <button type="submit" class="btn btn-primary w-100"
                                    :disabled="loggingIn"
                                    x-text="loggingIn ? 'Verifying...' : 'Log in'"></button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- Authenticated shell -->
        <div x-show="isAuthenticated" class="d-flex" style="height: calc(100vh - 56px);">
            <!-- Sidebar -->
            <div class="d-flex flex-column bg-dark text-light" style="width: 280px; flex-shrink: 0;">
                <div class="nav nav-pills flex-column p-3" role="tablist">
                    {% for tab in tabs %}
                    <button class="nav-link text-light d-flex align-items-center gap-2"
                            :class="{ 'active bg-primary': activeTab === '{{ tab.id }}' }"
                            @click="switchTab('{{ tab.id }}')"
                            x-show="!{{ 'true' if tab.get('admin_only') else 'false' }} || userRole === 'admin'"
                            hx-get="/admin/tabs/{{ tab.id }}"
                            hx-target="#tab-content"
                            hx-swap="innerHTML">
                        <span>{{ tab.icon }}</span>
                        <span>{{ tab.label }}</span>
                    </button>
                    {% endfor %}
                </div>
                <div class="mt-auto p-3">
                    <button class="btn btn-outline-light btn-sm w-100"
                            @click="logout()">Log out</button>
                </div>
            </div>
            <!-- Tab Content -->
            <div id="tab-content" class="flex-grow-1 p-4">
                <div hx-get="/admin/tabs/documents" hx-trigger="load" hx-swap="innerHTML">
                    <p class="text-muted">Loading...</p>
                </div>
            </div>
        </div>
    </div>

    <script nonce="{{ request.state.csp_nonce }}">
    function adminApp() {
        return {
            isAuthenticated: false,
            apiKeyInput: '',
            loggingIn: false,
            loginError: '',
            activeTab: 'documents',
            userRole: '',
            user: null,

            initAuth() {
                const savedKey = localStorage.getItem('kb_api_key');
                const savedRole = localStorage.getItem('kb_user_role');
                if (savedKey && savedRole) {
                    this.apiKeyInput = savedKey;
                    this.userRole = savedRole;
                    this.isAuthenticated = true;
                    // Set Bearer header on all HTMX requests
                    htmx.config.headers['Authorization'] = 'Bearer ' + savedKey;
                }
                // Intercept 401 responses
                document.body.addEventListener('htmx:responseError', (evt) => {
                    if (evt.detail.xhr.status === 401) {
                        this.logout();
                        this.loginError = 'Session expired. Please log in again.';
                    }
                });
            },

            login(key) {
                if (!key) return;
                this.loggingIn = true;
                this.loginError = '';
                fetch('/api/v1/auth/session', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + key }
                })
                .then(r => {
                    if (!r.ok) {
                        if (r.status === 401) throw new Error('Invalid API key');
                        throw new Error('Request failed');
                    }
                    return r.json();
                })
                .then(data => {
                    localStorage.setItem('kb_api_key', key);
                    localStorage.setItem('kb_user_role', data.role);
                    this.userRole = data.role;
                    this.user = data;
                    this.isAuthenticated = true;
                    this.loggingIn = false;
                    htmx.config.headers['Authorization'] = 'Bearer ' + key;
                    // Trigger tab load
                    htmx.trigger('#tab-content', 'load');
                })
                .catch(err => {
                    this.loggingIn = false;
                    this.loginError = err.message;
                });
            },

            switchTab(tab) {
                this.activeTab = tab;
                window.location.hash = tab;
            },

            logout() {
                localStorage.removeItem('kb_api_key');
                localStorage.removeItem('kb_user_role');
                this.isAuthenticated = false;
                this.apiKeyInput = '';
                this.userRole = '';
                this.user = null;
                delete htmx.config.headers['Authorization'];
                fetch('/api/v1/auth/session', { method: 'DELETE' }).catch(() => {});
            }
        };
    }
    </script>
    {% endblock %}
    ```

    Step 4 — Create 6 tab placeholder partials. Each is a Jinja2 partial (no extends):

    `kb_server/ui/templates/admin/tab_documents.html`:
    ```html
    <h3>Documents</h3>
    <p class="text-muted">Browse and manage indexed documents.</p>
    <div hx-get="/ui/browse" hx-trigger="load" hx-target="this"></div>
    ```

    `kb_server/ui/templates/admin/tab_monitoring.html`:
    ```html
    <h3>Monitoring</h3>
    <p class="text-muted">System health and Grafana dashboards.</p>
    <div id="monitor-lights" hx-get="/admin/tabs/monitor-lights" hx-trigger="every 30s" hx-target="this">
        <p class="text-muted">Loading system health...</p>
    </div>
    <hr>
    <div id="grafana-embed">
        <p class="text-muted">Grafana dashboard will appear here after configuration.</p>
    </div>
    ```

    `kb_server/ui/templates/admin/tab_ingestion.html`:
    ```html
    <h3>Ingestion</h3>
    <p class="text-muted">Manage document ingestion jobs.</p>
    <p class="text-muted">Ingestion management features are available in the CLI via <code>kb-ingest</code>.</p>
    ```

    `kb_server/ui/templates/admin/tab_ragas.html`:
    ```html
    <h3>RAGAS Evaluation</h3>
    <p class="text-muted">Evaluate retrieval quality with golden datasets.</p>
    <p class="text-muted">RAGAS evaluation features are available in the CLI via <code>kb-rag evaluate</code>.</p>
    ```

    `kb_server/ui/templates/admin/tab_admin.html`:
    ```html
    <h3>Admin Settings</h3>
    <p class="text-muted">System configuration and user management.</p>
    <div id="config-table" hx-get="/admin/tabs/config-table" hx-trigger="load" hx-target="this">
        <p class="text-muted">Loading configuration...</p>
    </div>
    ```

    `kb_server/ui/templates/admin/tab_profile.html`:
    ```html
    <h3>Profile</h3>
    <p class="text-muted">Your account settings and API keys.</p>
    <div id="profile-content" hx-get="/admin/tabs/profile-content" hx-trigger="load" hx-target="this">
        <p class="text-muted">Loading profile...</p>
    </div>
    ```

    Step 5 — Run all tests: `python -m pytest tests/test_admin_ui.py -x -v`
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - /admin/ returns 200 with HTML containing "adminApp", "x-data", all 6 tab labels
    - /admin/tabs/documents returns 200 with partial HTML (no extends)
    - /admin/tabs/nonexistent returns 404
    - Login modal shows on unauthenticated load; hides on login success
    - Sidebar shows 6 tabs; Admin tab gated by x-show on userRole === 'admin'
    - Logout clears localStorage and HTMX auth header
    - 401 HTMX response triggers logout and login modal
    - All 6 tab partial templates exist with hx-get triggers for content loading
  </acceptance_criteria>
  <done>Admin SPA shell with Alpine.js auth flow, sidebar, and 6 tab partials created and tested.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Browser → /admin/ | Untrusted browser requests reach admin SPA via HTTP |
| HTMX → /admin/tabs/ | Tab partials loaded from backend, rendered server-side |
| HTMX → /api/v1/* | API calls from browser carry Bearer token from localStorage |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-01 | Spoofing | POST /api/v1/auth/session | mitigate | Bearer token validated via AuthService.verify_key(); invalid keys return 401 |
| T-28c-02 | Tampering | CDN script injection | mitigate | Pinned CDN versions with SRI integrity hashes (per D-11) |
| T-28c-03 | Information Disclosure | admin tab data leaked to non-admin | mitigate | Server-side role gating on tab endpoints; Admin tab hidden client-side via x-show |
| T-28c-04 | Tampering | XSS via template injection | mitigate | CSP middleware with nonce-based script-src; Alpine.js CSP build avoids eval |
| T-28c-05 | Information Disclosure | API key in localStorage | accept | Internal-only deployment; session cookie is HttpOnly for primary auth |
| T-28c-SC | Tampering | CDN packages | mitigate | SRI hashes on all CDN scripts; fetch + hash before adding integrity attr |
</threat_model>

<verification>
### Per-Task Verification
Each task has automated tests (see `<verify>` blocks). Run all admin UI tests:

```bash
cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -20
```

Expected: All tests PASS.

### Manual Verification
1. Verify /admin/ loads shell.html with login modal (no errors in console)
2. Verify base.html has Alpine.js CDN with `defer`, `nonce`, `integrity`
3. Verify CSP response header on /admin/ contains `nonce-{value}`
4. Verify all 6 tab partials render via GET /admin/tabs/{name}
5. Verify session endpoint sets Set-Cookie with HttpOnly, SameSite=Lax, path=/

### Regression Check
```bash
cd /home/admin/kb-rag-mcp && python -m pytest -x --timeout=60 2>&1 | tail -10
```
Expected: No regressions.
</verification>

<success_criteria>
- All tests in tests/test_admin_ui.py pass
- /admin/ returns 200 with XSS-protected HTML (CSP header, nonce, SRI)
- Users can log in with API key, receive JWT session cookie
- Sidebar shows 6 tabs with role-based Admin tab gating
- Tab content loads via HTMX partials
- Logout clears all auth state
- CDN assets have integrity hashes and pinned versions
</success_criteria>

<output>
  <file path="kb_server/auth/router.py" summary="Added POST /api/v1/auth/session endpoint (per D-01)" />
  <file path="kb_server/auth/schemas.py" summary="Added SessionResponse schema" />
  <file path="kb_server/ui/app.py" summary="Added CSPMiddleware, admin router import" />
  <file path="kb_server/ui/templates/base.html" summary="Added Alpine.js CSP CDN, SRI hashes, Admin nav link" />
  <file path="kb_server/ui/routes_admin.py" summary="Admin SPA routes — shell and tab content handlers" />
  <file path="kb_server/ui/templates/admin/shell.html" summary="Admin SPA shell with Alpine.js auth, sidebar, login modal" />
  <file path="kb_server/ui/templates/admin/tab_documents.html" summary="Documents tab placeholder partial" />
  <file path="kb_server/ui/templates/admin/tab_monitoring.html" summary="Monitoring tab with monitor-lights placeholder" />
  <file path="kb_server/ui/templates/admin/tab_ingestion.html" summary="Ingestion tab placeholder" />
  <file path="kb_server/ui/templates/admin/tab_ragas.html" summary="RAGAS evaluation tab placeholder" />
  <file path="kb_server/ui/templates/admin/tab_admin.html" summary="Admin config tab with config-table placeholder" />
  <file path="kb_server/ui/templates/admin/tab_profile.html" summary="Profile tab with profile-content placeholder" />
  <file path="tests/test_admin_ui.py" summary="Test coverage for auth session, CSP, shell, tabs" />
</output>
