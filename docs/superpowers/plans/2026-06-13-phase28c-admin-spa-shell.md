# Phase 28c: Admin SPA Shell

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admin SPA panel served at `/admin/` with Alpine.js login modal, sidebar navigation, role-based tab visibility, and HTMX-driven tab content loading.

**Architecture:** A new Jinja2 template `shell.html` with Alpine.js managing client-side state (auth, active tab). The FastAPI app in `kb_server/ui/` adds a `/admin/` route returning the shell. Tab content is loaded via HTMX `hx-get="/admin/tabs/{name}"`. Auth flow: API key in localStorage → Bearer header on all HTMX requests → 401 interception shows login modal. No build step — Alpine.js and HTMX loaded from CDN.

**Tech Stack:** FastAPI, Jinja2, Alpine.js (CDN), HTMX (CDN), Bootstrap 5.

---

### Task 1: Add Alpine.js CDN and admin nav link to base.html

**Files:**
- Modify: `kb_server/ui/templates/base.html`

- [ ] **Step 1: Add Alpine.js CDN script and admin link**

In `kb_server/ui/templates/base.html`:
- Add Alpine.js CDN script tag after HTMX in `<head>`
- Add "Admin Panel" nav link after "Search Tester" in the navbar

```html
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Alpine.js -->
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js" defer></script>
```

Nav link:
```html
                    <li class="nav-item">
                        <a class="nav-link" href="/admin/">
                            Admin Panel
                        </a>
                    </li>
```

- [ ] **Step 2: Commit**

```bash
git add kb_server/ui/templates/base.html
git commit -m "feat(28c): add Alpine.js CDN and admin nav link"
```

---

### Task 2: Create admin routes module

**Files:**
- Create: `kb_server/ui/routes_admin.py`
- Test: `tests/test_admin_ui.py`

- [ ] **Step 1: Write the failing test — /admin/ returns 200 with shell**

`tests/test_admin_ui.py`:
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

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::test_admin_shell_returns_200 -x -v 2>&1 | tail -10`
Expected: 404 or missing route

- [ ] **Step 3: Create routes_admin.py**

`kb_server/ui/routes_admin.py`:
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::test_admin_shell_returns_200 -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Create admin template directory and shell.html**

`mkdir -p kb_server/ui/templates/admin`

`kb_server/ui/templates/admin/shell.html`:
```html
{% extends "base.html" %}

{% block title %}Admin Panel - KB-RAG{% endblock %}

{% block extra_head %}
<style>
.sidebar { width: 240px; min-height: calc(100vh - 56px); background: #f8f9fa; border-right: 1px solid #dee2e6; }
.sidebar .nav-link { color: #495057; border-radius: 0; padding: 0.75rem 1rem; }
.sidebar .nav-link:hover { background: #e9ecef; }
.sidebar .nav-link.active { background: #0d6efd; color: white; }
.main-content { flex: 1; padding: 1.5rem; }
.login-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; }
.login-card { max-width: 400px; margin: 20vh auto; }
</style>
{% endblock %}

{% block content %}
<div x-data="adminApp()" x-init="init()">
    <!-- Login overlay -->
    <div x-show="!isAuthenticated" class="login-overlay" style="display: none;">
        <div class="login-card card shadow">
            <div class="card-body p-4">
                <h4 class="card-title mb-4">KB-RAG Admin Login</h4>
                <div x-show="loginError" class="alert alert-danger" x-text="loginError"></div>
                <form x-on:submit.prevent="login()">
                    <div class="mb-3">
                        <label for="apiKey" class="form-label">API Key</label>
                        <input type="password" class="form-control" id="apiKey" x-model="apiKeyInput" placeholder="Enter your API key" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100" x-text="loggingIn ? 'Verifying...' : 'Login'"></button>
                </form>
            </div>
        </div>
    </div>

    <!-- Admin panel -->
    <div x-show="isAuthenticated" class="d-flex">
        <!-- Sidebar -->
        <div class="sidebar flex-shrink-0">
            <div class="p-3 border-bottom">
                <strong>KB-RAG Admin</strong>
            </div>
            <ul class="nav flex-column">
                <template x-for="tab in tabs" :key="tab.id">
                    <li class="nav-item" x-show="!tab.admin_only || userRole === 'admin'">
                        <a class="nav-link" :class="{ active: activeTab === tab.id }" href="#"
                           x-on:click.prevent="activeTab = tab.id; loadTab(tab.id)"
                           x-text="tab.icon + ' ' + tab.label">
                        </a>
                    </li>
                </template>
            </ul>
            <div class="border-top p-3">
                <button class="btn btn-outline-danger btn-sm w-100" x-on:click="logout()">Logout</button>
            </div>
        </div>

        <!-- Main content -->
        <div class="main-content">
            <div x-show="activeTab === 'documents'">
                <div hx-get="/admin/tabs/documents" hx-trigger="load" hx-target="this"></div>
            </div>
            <div x-show="activeTab === 'monitoring'">
                <div hx-get="/admin/tabs/monitoring" hx-trigger="load" hx-target="this"></div>
            </div>
            <div x-show="activeTab === 'ingestion'">
                <div hx-get="/admin/tabs/ingestion" hx-trigger="load" hx-target="this"></div>
            </div>
            <div x-show="activeTab === 'ragas'">
                <div hx-get="/admin/tabs/ragas" hx-trigger="load" hx-target="this"></div>
            </div>
            <div x-show="activeTab === 'admin'">
                <div hx-get="/admin/tabs/admin" hx-trigger="load" hx-target="this"></div>
            </div>
            <div x-show="activeTab === 'profile'">
                <div hx-get="/admin/tabs/profile" hx-trigger="load" hx-target="this"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
function adminApp() {
    return {
        isAuthenticated: false,
        apiKeyInput: '',
        loggingIn: false,
        loginError: '',
        activeTab: 'documents',
        userRole: '',
        tabs: [
            { id: 'documents', label: 'Documents', icon: '📄' },
            { id: 'monitoring', label: 'Monitoring', icon: '📊' },
            { id: 'ingestion', label: 'Ingestion', icon: '⚡' },
            { id: 'ragas', label: 'RAGAS', icon: '🧪' },
            { id: 'admin', label: 'Admin', icon: '⚙️', adminOnly: true },
            { id: 'profile', label: 'Profile', icon: '👤' },
        ],

        init() {
            const savedKey = localStorage.getItem('kb_api_key');
            const savedRole = localStorage.getItem('kb_user_role');
            if (savedKey) {
                this.apiKeyInput = savedKey;
                this.userRole = savedRole || 'user';
                this.isAuthenticated = true;
            }
            document.body.addEventListener('htmx:beforeRequest', (evt) => {
                if (savedKey) {
                    evt.detail.requestConfig.headers['Authorization'] = 'Bearer ' + savedKey;
                }
            });
            document.body.addEventListener('htmx:responseError', (evt) => {
                if (evt.detail.xhr.status === 401) {
                    localStorage.removeItem('kb_api_key');
                    localStorage.removeItem('kb_user_role');
                    this.isAuthenticated = false;
                }
            });
        },

        login() {
            this.loggingIn = true;
            this.loginError = '';
            fetch('/api/v1/auth/session', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + this.apiKeyInput }
            })
            .then(r => {
                if (!r.ok) throw new Error('Invalid API key');
                return r.json();
            })
            .then(data => {
                this.userRole = data.role || 'user';
                localStorage.setItem('kb_api_key', this.apiKeyInput);
                localStorage.setItem('kb_user_role', this.userRole);
                this.isAuthenticated = true;
                this.loggingIn = false;
            })
            .catch(err => {
                this.loginError = err.message;
                this.loggingIn = false;
            });
        },

        logout() {
            localStorage.removeItem('kb_api_key');
            localStorage.removeItem('kb_user_role');
            this.isAuthenticated = false;
            this.apiKeyInput = '';
            this.userRole = '';
        },

        loadTab(tabId) {
            // HTMX handles the actual load via hx-trigger="load"
            // This function is for any additional init needed
        }
    };
}
</script>
{% endblock %}
```

- [ ] **Step 6: Create placeholder tab partials**

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
<div id="monitor-lights" hx-get="/admin/tabs/monitor-lights" hx-trigger="every 30s" hx-target="this"></div>
<hr>
<div id="grafana-embed">
    <p class="text-muted">Grafana dashboard will appear here after configuration.</p>
</div>
```

`kb_server/ui/templates/admin/tab_ingestion.html`:
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

`kb_server/ui/templates/admin/tab_ragas.html`:
```html
<h3>RAGAS Evaluation</h3>
<p class="text-muted">Manage golden datasets and run evaluations.</p>
<div hx-get="/admin/tabs/ragas-editor" hx-trigger="load" hx-target="this"></div>
```

`kb_server/ui/templates/admin/tab_admin.html`:
```html
<h3>Admin Settings</h3>
<p class="text-muted">System configuration and user management.</p>
<div hx-get="/api/v1/config" hx-trigger="load" hx-target="#config-table"></div>
<div id="config-table"></div>
```

`kb_server/ui/templates/admin/tab_profile.html`:
```html
<h3>Profile</h3>
<p class="text-muted">Your account settings and API keys.</p>
<div id="profile-content" hx-get="/admin/tabs/profile-content" hx-trigger="load" hx-target="this"></div>
```

- [ ] **Step 7: Update ui/app.py to import admin routes**

Add import to `kb_server/ui/app.py`:
```python
# Import routes
import kb_server.ui.routes  # noqa: F401
import kb_server.ui.routes_admin  # noqa: F401
```

Add to `kb_server/ui/__init__.py` if exists; otherwise ensure the import chain works.

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add kb_server/ui/routes_admin.py kb_server/ui/templates/admin/ kb_server/ui/app.py
git commit -m "feat(28c): add admin SPA shell with Alpine.js auth flow"
```
