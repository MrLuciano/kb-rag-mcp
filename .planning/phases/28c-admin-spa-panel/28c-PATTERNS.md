# Phase 28c: Admin SPA Panel — Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 23 total (4 modify, 19 create)
**Analogs found:** 22 / 23 (1 no-analog: monitor lights partial uses new pattern)

## File Classification

### Modified Files

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `kb_server/ui/app.py` | config (app bootstrap) | N/A | itself | exact (same file) |
| `kb_server/ui/templates/base.html` | template (layout) | N/A | itself | exact (same file) |
| `kb_server/auth/router.py` | controller (API) | request-response | itself | exact (same file) |
| `kb_server/ui/templates/browse.html` | template (view) | N/A | itself | exact (same file) |

### Created Files

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `kb_server/ui/routes_admin.py` | controller (routes) | request-response + CRUD | `kb_server/ui/routes.py` | exact (same role, same project) |
| `kb_server/ui/templates/admin/shell.html` | template (layout shell) | N/A | `kb_server/ui/templates/base.html` | role-match (Jinja2 layout) |
| `kb_server/ui/templates/admin/tab_documents.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 view partial) |
| `kb_server/ui/templates/admin/tab_monitoring.html` | template (partial) | N/A | `kb_server/ui/templates/search.html` | role-match (Jinja2 partial) |
| `kb_server/ui/templates/admin/tab_ingestion.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + form) |
| `kb_server/ui/templates/admin/tab_ragas.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + table) |
| `kb_server/ui/templates/admin/tab_admin.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + table) |
| `kb_server/ui/templates/admin/tab_profile.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + form) |
| `kb_server/ui/templates/admin/_config_table.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 partial) |
| `kb_server/ui/templates/admin/_monitor_lights.html` | template (partial) | N/A | none | no-analog (new health card pattern) |
| `kb_server/ui/templates/admin/_ingestion_manual.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + form) |
| `kb_server/ui/templates/admin/_ingestion_schedule.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + form + table) |
| `kb_server/ui/templates/admin/_ingestion_monitor.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + table) |
| `kb_server/ui/templates/admin/_ragas_editor.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + table) |
| `kb_server/ui/templates/admin/_ragas_results.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + table) |
| `kb_server/ui/templates/admin/_profile_content.html` | template (partial) | N/A | `kb_server/ui/templates/browse.html` | role-match (Jinja2 + form) |
| `tests/test_admin_ui.py` | test | N/A | `tests/test_ui_routes.py` | exact (same project, same test style) |

---

## Pattern Assignments

### `kb_server/ui/app.py` (config, N/A) — MODIFY

**Analog:** `kb_server/ui/app.py` (itself, extend existing pattern)

**Imports pattern** (lines 1-5):
```python
"""FastAPI application for KB-RAG Web UI."""
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
```

**Core app setup pattern** (lines 13-21):
```python
app = FastAPI(
    title="KB-RAG Web UI",
    description="Document browser and search tester for KB-RAG system",
    version=_version
)

# Template directory
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))
```

**Auth session endpoint addition pattern** — Add CSP middleware and mount admin router after `templates` initialization, using FastAPI middleware pattern and `app.mount()` or `app.include_router()`. CSP middleware injects `csp_nonce` into Jinja2 environment context per-request.

**Key additions needed:**
- Starlette Middleware for CSP nonce generation
- `app.include_router(admin_router)` import from `kb_server.ui.routes_admin`
- Jinja2 environment customization: `templates.env.globals["csp_nonce"] = ...`

---

### `kb_server/auth/router.py` (controller, request-response) — MODIFY

**Analog:** `kb_server/auth/router.py` (itself, add session endpoint)

**Existing imports pattern** (lines 1-16):
```python
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from kb_server.auth.deps import get_current_user, require_admin
from kb_server.auth.erasure import ErasureManager
from kb_server.auth.models import User
from kb_server.auth.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateUserRequest,
    ErasureRequestResponse,
    UserResponse,
)
from kb_server.auth.service import AuthService
```

**Router definition pattern** (line 20):
```python
router = APIRouter(prefix="/api/v1", tags=["auth"])
```

**Service retrieval pattern** (lines 23-29):
```python
def _get_service(request: Request) -> AuthService:
    svc = getattr(request.app.state, "auth_service", None)
    if svc is None:
        raise HTTPException(
            status_code=503, detail="Auth service not available"
        )
    return svc
```

**POST endpoint pattern** (lines 44-55) — Create a `POST /auth/session` endpoint following this pattern:
```python
@router.post("/users", response_model=UserResponse)
async def create_user(
    body: CreateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
):
    service = _get_service(request)
    try:
        user = service.create_user(username=body.username, role=body.role)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return UserResponse.model_validate(user)
```

**Auth dependency pattern** (lines 24-43 from `kb_server/auth/deps.py`):
```python
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
) -> User:
    service = _get_service(request)
    if not api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:].strip()
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    user = service.verify_key(api_key)
    if user is None:
        raise HTTPException(
            status_code=401, detail="Invalid or revoked API key"
        )
    return user
```

**Session endpoint pattern (to add):**
- Receives Bearer token from Authorization header
- Calls `service.verify_key()` to validate
- On success, sets HttpOnly session cookie via `Response.set_cookie()` with `httponly=True, samesite="lax", max_age=28800` (8h)
- Returns user info as response
- Does NOT require a separate schema — reuses `UserResponse`

---

### `kb_server/ui/routes_admin.py` (controller, request-response + CRUD) — CREATE

**Analog:** `kb_server/ui/routes.py` (lines 1-163)

**Imports pattern** (lines 1-8 of routes.py):
```python
"""Web UI routes for document browsing and search testing."""
import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import Request, Query
from fastapi.responses import HTMLResponse
from kb_server.ui.app import app, templates
```

**Admin routes will use a sub-router instead of `@app.get`** — but same import style with `APIRouter`:
```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from kb_server.ui.app import templates

router = APIRouter(prefix="/admin", tags=["admin"])
```

**TemplateResponse pattern** (lines 107-123 of routes.py) — All tab endpoints follow this:
```python
@app.get("/ui/browse", response_class=HTMLResponse)
async def browse_documents(
    request: Request,
    product: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    version: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1)
):
    """Browse documents page with filters and pagination."""
    limit = 20
    offset = (page - 1) * limit
    documents, total = get_documents(
        product=product, doc_type=doc_type,
        version=version, status=status,
        limit=limit, offset=offset
    )
    total_pages = (total + limit - 1) // limit
    return templates.TemplateResponse(
        request,
        "browse.html",
        {
            "request": request,
            "documents": documents,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "filters": {
                "product": product,
                "doc_type": doc_type,
                "version": version,
                "status": status
            }
        }
    )
```

**Tab endpoint pattern** — Each tab returns an HTML partial:
```python
@router.get("/tabs/{name}", response_class=HTMLResponse)
async def admin_tab(request: Request, name: str):
    """Render admin tab partial by name."""
    template_map = {
        "documents": "admin/tab_documents.html",
        "monitoring": "admin/tab_monitoring.html",
        "ingestion": "admin/tab_ingestion.html",
        "ragas": "admin/tab_ragas.html",
        "admin": "admin/tab_admin.html",
        "profile": "admin/tab_profile.html",
    }
    template = template_map.get(name)
    if not template:
        return HTMLResponse("Tab not found", status_code=404)
    return templates.TemplateResponse(
        request, template,
        {"request": request, ...}
    )
```

**Document export endpoint pattern** — Synchronous CSV/JSON download following FastAPI `StreamingResponse` or direct `Response`:
```python
@app.get("/admin/export", response_class=Response)
async def export_documents(
    format: str = Query("csv"),
    ...
):
    """Export documents as CSV or JSON."""
    if format == "csv":
        # Return CSV content
        return Response(content=csv_data, media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=documents.csv"})
    # Return JSON
    return Response(content=json_data, media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=documents.json"})
```

---

### `kb_server/ui/templates/base.html` (template layout) — MODIFY

**Analog:** `kb_server/ui/templates/base.html` (itself, extend)

**Existing head pattern** (lines 1-12):
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}KB-RAG Web UI{% endblock %}</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
```

**Additions to head:**
1. Alpine.js CSP build CDN (`https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js`) with `defer` + `integrity` hash + `nonce="{{ csp_nonce }}"`
2. HTMX script updated to include `nonce="{{ csp_nonce }}"` + SRI integrity hash
3. Bootstrap CSS updated with SRI integrity attribute

**Existing navbar pattern** (lines 27-50):
```html
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
        <a class="navbar-brand" href="/">KB-RAG Web UI</a>
        <button class="navbar-toggler" type="button" 
                data-bs-toggle="collapse" 
                data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav">
                <li class="nav-item">
                    <a class="nav-link" href="/ui/browse">Browse Documents</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/ui/search">Search Tester</a>
                </li>
            </ul>
        </div>
    </div>
</nav>
```

**Additions to navbar:** Add "Admin Panel" nav link pointing to `/admin`.

**Existing body container pattern** (lines 53-55):
```html
<div class="container mt-4">
    {% block content %}{% endblock %}
</div>
```

**Existing extra_scripts block** (line 60):
```html
{% block extra_scripts %}{% endblock %}
```

---

### `kb_server/ui/templates/admin/shell.html` (template layout shell) — CREATE

**Analog:** `kb_server/ui/templates/base.html`

**Inherit from base.html:**
```html
{% extends "base.html" %}
{% block title %}Admin Panel - KB-RAG{% endblock %}
```

**Alpine.js state initialization** — `x-data` on the body/container for auth state:
```html
<div x-data="adminPanel()" x-init="init()">
```

**Alpine.js component pattern:**
```javascript
function adminPanel() {
    return {
        isAuthenticated: false,
        apiKeyInput: '',
        loggingIn: false,
        loginError: '',
        activeTab: 'documents',
        userRole: '',
        init() {
            const savedKey = localStorage.getItem('kb_api_key');
            if (savedKey) {
                this.apiKeyInput = savedKey;
                this.authenticate(savedKey);
            }
        },
        authenticate(key) { ... },
        logout() {
            localStorage.removeItem('kb_api_key');
            this.isAuthenticated = false;
            this.apiKeyInput = '';
        }
    }
}
```

**Login modal pattern** (Bootstrap `modal-dialog modal-sm` with `x-show`):
```html
<div x-show="!isAuthenticated" class="modal d-block" tabindex="-1">
    <div class="modal-dialog modal-sm modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Login to Admin Panel</h5>
            </div>
            <div class="modal-body">
                <div x-show="loginError" class="alert alert-danger" role="alert" x-text="loginError"></div>
                <form @submit.prevent="authenticate(apiKeyInput)">
                    <div class="mb-3">
                        <label for="apiKey" class="form-label">Enter your API key</label>
                        <input type="password" class="form-control" id="apiKey"
                               x-model="apiKeyInput" placeholder="kb_xxxxxxxx..."
                               aria-label="API key">
                    </div>
                    <button type="submit" class="btn btn-primary w-100"
                            :disabled="loggingIn" x-text="loggingIn ? 'Verifying...' : 'Log in'">
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
```

**Sidebar pattern** (280px fixed, bg-dark):
```html
<div class="d-flex" style="height: calc(100vh - 56px);">
    <!-- Sidebar -->
    <div class="d-flex flex-column bg-dark text-light" style="width: 280px; flex-shrink: 0;">
        <div class="nav nav-pills flex-column p-3" role="tablist">
            <button class="nav-link text-light d-flex align-items-center gap-2"
                    :class="{ 'active bg-primary': activeTab === 'documents' }"
                    @click="activeTab = 'documents'"
                    hx-get="/admin/tabs/documents" hx-target="#tab-content">
                📄 Documents
            </button>
            <!-- repeat for: Monitoring 📊, Ingestion ⚡, RAGAS 🧪, Admin ⚙️, Profile 👤 -->
        </div>
        <div class="mt-auto p-3">
            <button class="btn btn-outline-light btn-sm w-100" @click="logout()">Log out</button>
        </div>
    </div>
    <!-- Tab Content -->
    <div id="tab-content" class="flex-grow-1 p-4">
        <!-- HTMX loads tab partials here -->
    </div>
</div>
```

---

### `kb_server/ui/templates/admin/tab_*.html` (template partials) — CREATE (6 files)

**Analog:** `kb_server/ui/templates/browse.html` — For all tab partials, strip the `{% extends "base.html" %}` since they're loaded via HTMX into the shell content area.

**HTMX partial pattern (no extends, no full HTML structure):**
```html
<!-- Tab title -->
<h3>Tab Name</h3>
<p class="text-muted">Tab description...</p>

<!-- Content -->
<div>
    <!-- Tab-specific content (table, form, etc.) -->
</div>
```

**Table pattern** (from browse.html lines 72-115):
```html
<div class="table-responsive">
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th>Column1</th>
                <th>Column2</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ item.field }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

**Form pattern** (from browse.html lines 9-63):
```html
<div class="card mb-4">
    <div class="card-body">
        <form method="get" action="/some/path" class="row g-3">
            <div class="col-md-3">
                <label for="field" class="form-label">Label</label>
                <input type="text" class="form-control" id="field" name="field">
            </div>
            <div class="col-12">
                <button type="submit" class="btn btn-primary">Submit</button>
            </div>
        </form>
    </div>
</div>
```

---

### `kb_server/ui/templates/admin/_config_table.html` (template partial) — CREATE

**Analog:** `kb_server/ui/templates/browse.html` (table pattern)

**Alpine.js inline editing pattern** — Each config row:
```html
<tr x-data="{ editing: false, originalValue: '{{ entry.value }}' }">
    <td><span class="badge bg-info">{{ entry.group_name }}</span></td>
    <td><code>{{ entry.key }}</code></td>
    <td>
        <div x-show="!editing">
            <span x-text="originalValue" @dblclick="editing = true"></span>
        </div>
        <div x-show="editing">
            <input type="text" x-model="originalValue" class="form-control form-control-sm"
                   @keydown.escape="editing = false; originalValue = '{{ entry.value }}'"
                   @keydown.enter="editing = false; $event.target.form.requestSubmit()"
                   @click.outside="editing = false; originalValue = '{{ entry.value }}'">
        </div>
    </td>
    <td><small class="text-muted">{{ entry.type }}</small></td>
    <td>
        <button class="btn btn-sm btn-outline-danger"
                hx-delete="/api/v1/config/{{ entry.key }}"
                hx-confirm="Reset this config value?"
                hx-target="closest tr" hx-swap="outerHTML">Reset</button>
    </td>
</tr>
```

**Search filter pattern** (Alpine.js):
```html
<input type="text" class="form-control mb-3" placeholder="Search config keys..."
       x-model="searchQuery" aria-label="Search config keys">
<!-- Row visibility controlled via x-show -->
<tr x-data="{ editing: false, originalValue: '{{ entry.value }}' }"
    x-show="searchQuery === '' || '{{ entry.key }}'.includes(searchQuery) 
            || '{{ entry.group_name }}'.includes(searchQuery)">
```

---

### `kb_server/ui/templates/admin/_monitor_lights.html` (template partial) — CREATE

**No close analog in codebase** — This is a new pattern. Use the UI-SPEC interaction contract directly.

**Health card pattern:**
```html
<div class="d-flex gap-3 flex-wrap">
    {% for name, status in components.items() %}
    <div class="card" style="width: 160px;" x-data="{ expanded: false }">
        <div class="card-body text-center p-2">
            <!-- Colored dot -->
            <span class="badge d-inline-block rounded-circle p-0
                         {% if status.healthy %}bg-success
                         {% elif status.healthy is none %}bg-secondary
                         {% else %}bg-danger{% endif %}"
                  style="width: 12px; height: 12px;"
                  aria-label="{{ name }} status: {% if status.healthy %}healthy{% else %}unhealthy{% endif %}">
            </span>
            <!-- Component name -->
            <small class="d-block mt-1 fw-semibold">{{ name }}</small>
            <!-- Latency -->
            {% if status.latency_ms %}
            <small class="text-muted">{{ status.latency_ms }}ms</small>
            {% endif %}
            <!-- Expand details -->
            <button class="btn btn-sm btn-link p-0" @click="expanded = !expanded">details</button>
            <div x-show="expanded" class="mt-1 text-start small">
                <pre>{{ status.details | tojson }}</pre>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
```

---

### `tests/test_admin_ui.py` (test) — CREATE

**Analog:** `tests/test_ui_routes.py` (lines 1-244)

**Test imports pattern** (lines 1-16):
```python
"""Smoke tests for kb_server/ui/ — routes_admin.py and admin templates.

Uses FastAPI TestClient with mocked dependencies to avoid live infrastructure.
"""
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

import kb_server.ui.routes_admin  # noqa: F401 — registers admin routes
from kb_server.ui.app import app

client = TestClient(app, raise_server_exceptions=False)
```

**Template response mocking pattern** (lines 148-155):
```python
def _mock_template_response():
    """Patch templates.TemplateResponse to avoid Jinja2 rendering."""
    return patch(
        "kb_server.ui.routes.templates.TemplateResponse",
        side_effect=lambda request, name, ctx, status_code=200, **kw: _html_response(
            f"<html>{name}</html>", status_code=status_code
        ),
    )
```

**Test class structure pattern** (lines 40-57):
```python
class TestAdminShell:
    def test_shell_returns_200(self):
        with _mock_template_response():
            resp = client.get("/admin")
        assert resp.status_code == 200

    def test_tab_documents_returns_200(self):
        with _mock_template_response():
            resp = client.get("/admin/tabs/documents")
        assert resp.status_code == 200

    def test_tab_invalid_returns_404(self):
        resp = client.get("/admin/tabs/invalid_tab")
        assert resp.status_code == 404
```

---

## Shared Patterns

### Authentication (Session + API Key)
**Sources:** `kb_server/auth/deps.py` (lines 24-43), `kb_server/auth/router.py` (lines 93-113)

**Apply to:** `kb_server/auth/router.py` (add session endpoint)

The session endpoint exchanges Bearer API key for an HttpOnly JWT cookie. Key pattern:
```python
@router.post("/auth/session")
async def create_session(
    request: Request,
    response: Response,
    api_key: Optional[str] = Depends(api_key_header),
):
    service = _get_service(request)
    
    # Extract Bearer token if not via header
    if not api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:].strip()
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    user = service.verify_key(api_key)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Set HttpOnly session cookie
    # (JWT token generation via python-jose or similar)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=28800,  # 8 hours
        secure=False,   # Set True in production
    )
    
    return UserResponse.model_validate(user)
```

### CSP Middleware (Nonce Generation)
**Source:** UI-SPEC CSP contract (section 13)

**Apply to:** `kb_server/ui/app.py` (add CSP middleware)

```python
from starlette.middleware.base import BaseHTTPMiddleware
import secrets

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Generate per-request nonce
        nonce = secrets.token_hex(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        return response

# Register middleware
app.add_middleware(CSPMiddleware)

# Make nonce available in Jinja2 context
templates.env.globals["csp_nonce"] = lambda: request.state.csp_nonce
```

### HTMX Configuration (401 Interceptor + Auth Header)
**Apply to:** All admin templates

**HTMX 401 interceptor + Bearer header** in shell.html:
```html
<script nonce="{{ csp_nonce }}">
    document.addEventListener('DOMContentLoaded', function() {
        const savedKey = localStorage.getItem('kb_api_key');
        if (savedKey) {
            htmx.config.headers['Authorization'] = 'Bearer ' + savedKey;
        }
        
        document.body.addEventListener('htmx:responseError', function(evt) {
            if (evt.detail.xhr.status === 401) {
                // Show login modal
                Alpine.store('auth').showLogin();
            }
        });
    });
</script>
```

### Jinja2 Template Conventions
**Source:** `kb_server/ui/templates/base.html` and `browse.html`

**Apply to:** All created template files

| Convention | Pattern |
|-----------|---------|
| Block inheritance | `{% extends "base.html" %}` for full pages, no extends for HTMX partials |
| Template variables | `{{ variable }}` for display, `{% if condition %}` for conditional rendering |
| HTMX attributes | `hx-get`, `hx-target`, `hx-swap`, `hx-trigger`, `hx-indicator` |
| Alpine.js bindings | `x-data`, `x-model`, `x-show`, `x-text`, `x-init`, `@click`, `:class` |
| CDN script loading | Pinned version URLs with `integrity` hash and `crossorigin="anonymous"` |

### Bootstrap 5 Visual Patterns
**Apply to:** All admin templates

- Sidebar: `d-flex flex-column bg-dark text-light`, 280px width
- Cards: `card mb-4` with `card-body p-3`
- Tables: `table table-striped table-hover` in `table-responsive` wrapper
- Buttons: Primary = `btn btn-primary`, Danger = `btn btn-outline-danger`, Secondary = `btn btn-secondary`
- Forms: `row g-3` with `col-md-*` for grid layout, `form-label` + `form-control`/`form-select`
- Pagination: `nav` > `ul.pagination` with `page-item`/`page-link`
- Modals: `modal-dialog modal-sm modal-dialog-centered`

### Error Handling
**Source:** `kb_server/auth/router.py` (lines 50-55, 100-105, 134-138)

**Apply to:** `kb_server/ui/routes_admin.py`, `kb_server/auth/router.py` (new endpoint)

```python
try:
    result = service.some_operation()
except ValueError as e:
    raise HTTPException(status_code=409, detail=str(e))
except SomeSpecificError as e:
    raise HTTPException(status_code=422, detail={"error": str(e), ...})
```

### Document Export Pattern
**Source:** CONTEXT.md D-12

**Apply to:** `kb_server/ui/routes_admin.py`

Synchronous CSV/JSON download:
```python
import csv
import io
from fastapi.responses import Response

@router.get("/export")
async def export_documents(
    format: str = Query("csv"),
    # ... filter params ...
):
    documents, _ = get_documents(limit=10000, ...)
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[...])
        writer.writeheader()
        writer.writerows(documents)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=documents.csv"}
        )
    
    # JSON format
    return Response(
        content=json.dumps(documents, default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=documents.json"}
    )
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `kb_server/ui/templates/admin/_monitor_lights.html` | template (partial) | N/A | No existing health card / status light pattern in the codebase. Health is currently consumed as JSON only (via `/health/detailed`). This partial introduces a new visual pattern for server status indication. The planner should use UI-SPEC section "Monitor Lights Bar" interaction contract and `HealthStatus.to_dict()` (lines 57-67 of `kb_server/health.py`) as the data source contract. |

---

## Metadata

**Analog search scope:** `kb_server/ui/`, `kb_server/auth/`, `kb_server/health*.py`, `kb_server/config/`, `tests/`
**Files scanned:** 18
**Pattern extraction date:** 2026-06-15
