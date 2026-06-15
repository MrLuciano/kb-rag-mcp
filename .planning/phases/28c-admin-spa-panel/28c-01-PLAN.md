---
phase: 28c-admin-spa-panel
plan: "01"
type: execute
wave: 1
depends_on:
  - 28b-auth-api
files_modified:
  - kb_server/ui/templates/base.html
  - kb_server/ui/routes_admin.py
  - kb_server/ui/templates/admin/shell.html
  - kb_server/ui/templates/admin/tab_documents.html
  - kb_server/ui/templates/admin/tab_monitoring.html
  - kb_server/ui/templates/admin/tab_ingestion.html
  - kb_server/ui/templates/admin/tab_ragas.html
  - kb_server/ui/templates/admin/tab_admin.html
  - kb_server/ui/templates/admin/tab_profile.html
  - kb_server/ui/app.py
  - tests/test_admin_ui.py
autonomous: true
requirements:
  - R28C-01
must_haves:
  truths:
    - Admin SPA served at /admin/ with Alpine.js login modal
    - Sidebar navigation with role-based tab visibility
    - HTMX-driven partial loading for tab content
  artifacts:
    - path: "kb_server/ui/routes_admin.py"
      provides: "Admin SPA routes"
      contains: "admin_shell, admin_tab_content"
      min_lines: 50
    - path: "kb_server/ui/templates/admin/shell.html"
      provides: "Admin SPA shell template"
      contains: "x-data, adminApp"
      min_lines: 100
    - path: "tests/test_admin_ui.py"
      provides: "Admin UI test coverage"
      contains: "test_admin_shell, test_admin_tabs_list"
      min_lines: 30
---

<objective>
Admin SPA panel served at /admin/ with Alpine.js login modal, sidebar navigation, role-based tab visibility, and HTMX-driven partial loading for tab content.

Purpose: Phase 28c provides the admin user interface shell with API key-based auth flow (localStorage → Bearer header → 401 intercept), role-gated tab visibility, and HTMX-driven content loading from backend partials.

Architecture: A new Jinja2 template shell.html with Alpine.js managing client-side state (auth, active tab). The FastAPI app in kb_server/ui/ adds a /admin/ route returning the shell. Tab content is loaded via HTMX hx-get="/admin/tabs/{name}". Auth flow: API key in localStorage → Bearer header on all HTMX requests → 401 interception shows login modal. No build step — Alpine.js and HTMX loaded from CDN.

Output: Alpine.js CDN in base.html, admin nav link, routes_admin.py with shell + tab endpoints, shell.html with auth modal + sidebar + tab placeholders, 6 placeholder tab partials.
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@kb_server/ui/templates/base.html
@kb_server/ui/app.py
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → /admin/ | Untrusted browser requests reach admin SPA |
| HTMX → /admin/tabs/ | Tab partials loaded from backend |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-01 | Spoofing | unauthenticated /admin/ access | mitigate | API key in localStorage verified via /api/v1/session; 401 on HTMX triggers login modal |
| T-28c-02 | Information Disclosure | admin tab data leaked | mitigate | Server-side role gating on tab endpoints |
| T-28c-03 | Spoofing | CDN script injection | mitigate | Pinned CDN versions with SRI checks |
| T-28c-04 | Tampering | CSRF on HTMX actions | mitigate | Bearer token on all HTMX requests; CORS same-origin |
</threat_model>

<task type="auto">
  <name>Add Alpine.js CDN and admin nav link to base.html</name>
  <files>kb_server/ui/templates/base.html</files>
  <read_first>kb_server/ui/templates/base.html</read_first>
  <action>
    In kb_server/ui/templates/base.html:
    - Add Alpine.js CDN script tag after HTMX in head
    - Add "Admin Panel" nav link after "Search Tester" in the navbar

    Add Alpine.js CDN script:
    ```html
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <!-- Alpine.js -->
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js" defer></script>
    ```

    Add nav link:
    ```html
    <li class="nav-item">
      <a class="nav-link" href="/admin/">Admin Panel</a>
    </li>
    ```
  </action>
  <verify>
    <automated>python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - Alpine.js CDN script tag present in base.html head
    - Admin Panel nav link present in base.html navbar
    - Existing pages still render correctly
  </acceptance_criteria>
  <done>Alpine.js CDN script tag and Admin Panel nav link added to base.html</done>
</task>

<task type="auto">
  <name>Create admin routes module with TDD</name>
  <files>tests/test_admin_ui.py, kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/shell.html, kb_server/ui/templates/admin/tab_*.html, kb_server/ui/app.py</files>
  <read_first>kb_server/ui/app.py, kb_server/ui/templates/base.html</read_first>
  <action>
    Step 1: Write failing tests in tests/test_admin_ui.py:
    - test_admin_shell_returns_200: GET /admin/ returns 200, text/html, contains alpinejs/x-data
    - test_admin_tabs_list: GET /admin/tabs/documents returns 200, GET /admin/tabs/nonexistent returns 404

    ```python
    import pytest
    from httpx import AsyncClient, ASGITransport
    from kb_server.ui.app import app


    @pytest.mark.asyncio
    async def test_admin_shell_returns_200():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "x-alpine" in resp.text or "alpinejs" in resp.text or "x-data" in resp.text


    @pytest.mark.asyncio
    async def test_admin_tabs_list():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/tabs/documents")
        assert resp.status_code == 200
        from fastapi import HTTPException
        resp2 = await ac.get("/admin/tabs/nonexistent")
        assert resp2.status_code == 404
    ```

    Step 2: Run tests to verify failure (expected: 404 or missing route):
    cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::test_admin_shell_returns_200 -x -v 2>&1 | tail -10

    Step 3: Create kb_server/ui/routes_admin.py:
    ```python
    """Admin SPA routes — shell, tab partials, and auth flow."""
    from fastapi import APIRouter, Request, HTTPException
    from fastapi.responses import HTMLResponse
    from kb_server.ui.app import app, templates

    router = APIRouter()


    @app.get("/admin/", response_class=HTMLResponse, include_in_schema=False)
    async def admin_shell(request: Request):
        """Admin SPA shell with sidebar, tabs, and auth modal."""
        return templates.TemplateResponse(
            request,
            "admin/shell.html",
            {
                "request": request,
                "tabs": [
                    {"id": "documents", "label": "Documents", "icon": "📄"},
                    {"id": "monitoring", "label": "Monitoring", "icon": "📊"},
                    {"id": "ingestion", "label": "Ingestion", "icon": "⚡"},
                    {"id": "ragas", "label": "RAGAS", "icon": "🧪"},
                    {"id": "admin", "label": "Admin", "icon": "⚙️", "admin_only": True},
                    {"id": "profile", "label": "Profile", "icon": "👤"},
                ],
            },
        )


    @app.get("/admin/tabs/{tab_name}", response_class=HTMLResponse, include_in_schema=False)
    async def admin_tab_content(tab_name: str, request: Request):
        """Return partial HTML for a tab."""
        tab_templates = {
            "documents": "admin/tab_documents.html",
            "monitoring": "admin/tab_monitoring.html",
            "ingestion": "admin/tab_ingestion.html",
            "ragas": "admin/tab_ragas.html",
            "admin": "admin/tab_admin.html",
            "profile": "admin/tab_profile.html",
        }
        template = tab_templates.get(tab_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"Tab '{tab_name}' not found")
        return templates.TemplateResponse(
            request,
            template,
            {"request": request},
        )
    ```

    Step 4: Run tests to verify they pass:
    cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::test_admin_shell_returns_200 -x -v 2>&1 | tail -10

    Step 5: Create admin template directory and shell.html:
    mkdir -p kb_server/ui/templates/admin

    kb_server/ui/templates/admin/shell.html — contains:
    - Extends base.html
    - Alpine.js app with adminApp() data in x-data directive
    - Login overlay modal with API key input, form submission via x-on:submit.prevent
    - Sidebar with role-based visibility (x-show="!tab.admin_only || userRole === 'admin'")
    - Active tab tracking with Alpine.activeTab, click handlers switching tabs
    - HTMX-driven tab content loading for all 6 tabs (documents, monitoring, ingestion, ragas, admin, profile)
    - adminApp() Alpine component with: isAuthenticated, apiKeyInput, loggingIn, loginError, activeTab, userRole state
    - init() loading saved API key and role from localStorage, intercepting HTMX requests to add Authorization header
    - login() calling POST /api/v1/auth/session with Bearer token, storing key/role on success
    - logout() clearing localStorage and resetting state
    - loadTab() placeholder for additional tab init

    Step 6: Create placeholder tab partials:

    kb_server/ui/templates/admin/tab_documents.html:
    ```html
    <h3>Documents</h3>
    <p class="text-muted">Browse and manage indexed documents.</p>
    <div hx-get="/ui/browse" hx-trigger="load" hx-target="this"></div>
    ```

    kb_server/ui/templates/admin/tab_monitoring.html:
    ```html
    <h3>Monitoring</h3>
    <p class="text-muted">System health and Grafana dashboards.</p>
    <div id="monitor-lights" hx-get="/admin/tabs/monitor-lights" hx-trigger="every 30s" hx-target="this"></div>
    <hr>
    <div id="grafana-embed">
      <p class="text-muted">Grafana dashboard will appear here after configuration.</p>
    </div>
    ```

    kb_server/ui/templates/admin/tab_ingestion.html:
    ```html
    <h3>Ingestion</h3>
    <div id="ingestion-app">
      <ul class="nav nav-tabs mb-3">
        <li class="nav-item">
          <a class="nav-link active" href="#" hx-get="/admin/tabs/ingestion-manual" hx-target="#ingestion-content" hx-swap="innerHTML">Manual</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#" hx-get="/admin/tabs/ingestion-schedule" hx-target="#ingestion-content" hx-swap="innerHTML">Schedule</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#" hx-get="/admin/tabs/ingestion-monitor" hx-target="#ingestion-content" hx-swap="innerHTML">Monitor</a>
        </li>
      </ul>
      <div id="ingestion-content">
        <div hx-get="/admin/tabs/ingestion-manual" hx-trigger="load" hx-target="this"></div>
      </div>
    </div>
    ```

    kb_server/ui/templates/admin/tab_ragas.html:
    ```html
    <h3>RAGAS Evaluation</h3>
    <p class="text-muted">Manage golden datasets and run evaluations.</p>
    <div hx-get="/admin/tabs/ragas-editor" hx-trigger="load" hx-target="this"></div>
    ```

    kb_server/ui/templates/admin/tab_admin.html:
    ```html
    <h3>Admin Settings</h3>
    <p class="text-muted">System configuration and user management.</p>
    <div hx-get="/api/v1/config" hx-trigger="load" hx-target="#config-table"></div>
    <div id="config-table"></div>
    ```

    kb_server/ui/templates/admin/tab_profile.html:
    ```html
    <h3>Profile</h3>
    <p class="text-muted">Your account settings and API keys.</p>
    <div id="profile-content" hx-get="/admin/tabs/profile-content" hx-trigger="load" hx-target="this"></div>
    ```

    Step 7: Update kb_server/ui/app.py to import admin routes:
    ```python
    import kb_server.ui.routes  # noqa: F401
    import kb_server.ui.routes_admin  # noqa: F401
    ```

    Step 8: Run all tests:
    cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -10
    Expected: PASS
  </action>
  <verify>
    <automated>python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - tests/test_admin_ui.py exists with test_admin_shell_returns_200 and test_admin_tabs_list
    - Tests pass (admin shell returns 200 with HTML content containing Alpine.js markers)
    - Tab partials return 200 for valid tab names, 404 for invalid
    - /admin/ route renders shell.html template with tabs context
    - Admin template directory contains shell.html and all 6 tab partials
    - routes_admin.py module is imported from app.py
  </acceptance_criteria>
  <done>Admin SPA shell with Alpine.js auth flow, sidebar navigation, and HTMX-driven tab content created and tested</done>
</task>

<verification>
  <step>
    Run pytest on the admin UI tests:
    cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -10
  </step>
  <step>
    Verify shell.html contains x-data directive and adminApp() function:
    grep -c 'x-data="adminApp()"' kb_server/ui/templates/admin/shell.html
    grep -c 'function adminApp' kb_server/ui/templates/admin/shell.html
  </step>
  <step>
    Verify routes_admin.py contains /admin/ and /admin/tabs/{tab_name} routes:
    grep -c '@app.get("/admin/")' kb_server/ui/routes_admin.py
    grep -c '@app.get("/admin/tabs/{tab_name}")' kb_server/ui/routes_admin.py
  </step>
</verification>

<success_criteria>
  - All tests in tests/test_admin_ui.py pass
  - /admin/ returns 200 with HTML containing Alpine.js components
  - /admin/tabs/{valid_name} returns 200 with partial HTML
  - /admin/tabs/invalid returns 404
  - base.html includes Alpine.js CDN script and Admin Panel nav link
  - All 6 tab partial templates exist in kb_server/ui/templates/admin/
</success_criteria>

<output>
  <file path="kb_server/ui/templates/base.html" summary="Added Alpine.js CDN script and Admin Panel nav link" />
  <file path="tests/test_admin_ui.py" summary="Test coverage for admin shell and tab routes" />
  <file path="kb_server/ui/routes_admin.py" summary="Admin SPA routes — shell and tab content handlers" />
  <file path="kb_server/ui/templates/admin/shell.html" summary="Admin SPA shell with Alpine.js auth, sidebar, and HTMX tab loading" />
  <file path="kb_server/ui/templates/admin/tab_documents.html" summary="Documents tab placeholder partial" />
  <file path="kb_server/ui/templates/admin/tab_monitoring.html" summary="Monitoring tab placeholder partial" />
  <file path="kb_server/ui/templates/admin/tab_ingestion.html" summary="Ingestion tab placeholder partial with sub-tabs" />
  <file path="kb_server/ui/templates/admin/tab_ragas.html" summary="RAGAS evaluation tab placeholder partial" />
  <file path="kb_server/ui/templates/admin/tab_admin.html" summary="Admin settings tab placeholder partial" />
  <file path="kb_server/ui/templates/admin/tab_profile.html" summary="Profile tab placeholder partial" />
  <file path="kb_server/ui/app.py" summary="Added import for routes_admin module" />
</output>
