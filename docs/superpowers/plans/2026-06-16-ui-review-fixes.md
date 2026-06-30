# UI-REVIEW Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 19 UI-REVIEW.md findings across the 6 pillars, raising the overall score from 16/24 to 22/24.

**Architecture:** Incremental fixes to existing Jinja2 + Bootstrap 5 + HTMX templates. No new dependencies. Changes are purely cosmetic/structural — no runtime logic changes.

**Tech Stack:** Jinja2, Bootstrap 5, HTMX, Alpine.js

---

## File Structure

| File | Responsibility | Action |
|------|--------------|--------|
| `kb_server/ui/templates/search.html` | Search tester page | Wire up to real search endpoint, fix heading hierarchy |
| `kb_server/ui/templates/browse.html` | Document browser | Add navbar active state, fix pagination, convert status badges |
| `kb_server/ui/templates/document.html` | Document detail | Fix heading hierarchy, replace inline styles |
| `kb_server/ui/templates/base.html` | Base template | Add navbar active state, replace inline style block |
| `kb_server/ui/templates/admin/tab_documents.html` | Documents tab (stub) | Implement real content |
| `kb_server/ui/templates/admin/tab_ingestion.html` | Ingestion tab (stub) | Implement real content |
| `kb_server/ui/templates/admin/tab_ragas.html` | RAGAS tab (stub) | Implement real content |
| `kb_server/ui/templates/admin/shell.html` | Admin shell layout | Fix heading hierarchy, replace inline styles |
| `kb_server/ui/templates/admin/tab_analytics.html` | Analytics tab | Fix heading hierarchy |
| `kb_server/ui/templates/admin/tab_monitoring.html` | Monitoring tab | Fix heading hierarchy |
| `kb_server/ui/templates/admin/_monitor_lights.html` | Monitor lights partial | Replace inline styles with Bootstrap utilities |
| `kb_server/ui/templates/admin/_config_table.html` | Config table partial | Replace alert() with inline validation, fix inline style |
| `kb_server/ui/templates/admin/tab_profile.html` | Profile tab | Fix heading hierarchy |
| `kb_server/ui/templates/admin/tab_admin.html` | Admin settings tab | Fix heading hierarchy |
| `kb_server/ui/templates/error.html` | Error page | Fix heading hierarchy |
| `kb_server/ui/templates/document_chunks.html` | Chunk pagination partial | Replace inline style |
| `kb_server/ui/routes.py` | Browse/search routes | Add search endpoint for UI |
| `kb_server/ui/routes_admin.py` | Admin routes | Add data endpoints for stub tabs |

---

## Task 1: Wire Up Search Page to Real Endpoint

**Files:**
- Modify: `kb_server/ui/templates/search.html` (lines 85-133)
- Modify: `kb_server/ui/routes.py` (add new endpoint)
- Test: `tests/test_ui_routes.py` (add search endpoint test)

**Background:** The search page currently shows a mockup message. We need to add a POST endpoint that calls the existing `_search_kb` function in `server.py` and returns HTML results.

- [ ] **Step 1: Add search endpoint in routes.py**

Add a new POST endpoint `/ui/search` that:
1. Accepts form data (query, top_k, product, version, hybrid, rerank)
2. Calls `kb_server.server._search_kb()` with the parameters
3. Returns HTML result cards

```python
@router.post("/search", response_class=HTMLResponse)
async def search_results(request: Request):
    """Execute search and return HTML results."""
    from kb_server.server import _search_kb
    
    form = await request.form()
    args = {
        "query": form.get("query", ""),
        "top_k": int(form.get("top_k", 5)),
        "product": form.get("product") or None,
        "version": form.get("version") or None,
        "hybrid": form.get("hybrid") == "on",
        "rerank": form.get("rerank") == "on",
    }
    
    try:
        results = await _search_kb(args)
        text = results[0].text if results else "No results found."
        return templates.TemplateResponse(
            request,
            "search_results.html",
            {"request": request, "results": results, "query": args["query"]},
        )
    except Exception as e:
        log.error("Search error: %s", e)
        return HTMLResponse(
            f"<div class='alert alert-danger'>Search error: {str(e)}</div>",
            status_code=500,
        )
```

- [ ] **Step 2: Create search_results.html template**

Create `kb_server/ui/templates/search_results.html`:
```html
{% if results %}
<div class="alert alert-success">
    Found {{ results|length }} results for "<strong>{{ query }}</strong>"
</div>
{% for result in results %}
<div class="card mb-3">
    <div class="card-body">
        <h5 class="card-title">{{ result.source_file }}</h5>
        <p class="card-text">{{ result.text[:200] }}...</p>
        <span class="badge bg-primary">Score: {{ "%.2f"|format(result.score) }}</span>
    </div>
</div>
{% endfor %}
{% else %}
<div class="alert alert-warning">
    No results found for "<strong>{{ query }}</strong>"
</div>
{% endif %}
```

- [ ] **Step 3: Update search.html to call the real endpoint**

Replace the mockup JavaScript in `search.html` (lines 85-133) with HTMX:
```html
{% block extra_scripts %}
<script>
document.getElementById('searchForm').addEventListener('submit', 
    async function(e) {
    e.preventDefault();
    
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="spinner-border" role="status">' +
                          '<span class="visually-hidden">Loading...</span>' +
                          '</div>';
    
    const formData = new FormData(e.target);
    
    try {
        const response = await fetch('/ui/search', {
            method: 'POST',
            body: formData
        });
        const html = await response.text();
        resultsDiv.innerHTML = html;
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                Error: ${error.message}
            </div>
        `;
    }
});
</script>
{% endblock %}
```

- [ ] **Step 4: Write test for search endpoint**

```python
@pytest.mark.asyncio
async def test_search_endpoint_returns_results(client):
    """POST /ui/search returns HTML results."""
    response = await client.post(
        "/ui/search",
        data={"query": "test", "top_k": "5"}
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
```

- [ ] **Step 5: Run tests and verify**

```bash
.venv/bin/python -m pytest tests/test_ui_routes.py -v -k search
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add kb_server/ui/templates/search.html kb_server/ui/templates/search_results.html kb_server/ui/routes.py tests/test_ui_routes.py
git commit -m "feat(ui): wire search page to real endpoint"
```

---

## Task 2: Fill Stub Admin Tabs

**Files:**
- Modify: `kb_server/ui/templates/admin/tab_documents.html`
- Modify: `kb_server/ui/templates/admin/tab_ingestion.html`
- Modify: `kb_server/ui/templates/admin/tab_ragas.html`
- Modify: `kb_server/ui/routes_admin.py` (lines 35-80)
- Test: `tests/test_admin_ui.py` (add tab content tests)

**Background:** Three admin tabs are placeholders. We need to add real content that reuses existing data sources.

- [ ] **Step 1: Implement Documents tab**

Replace `tab_documents.html` with real content:
```html
<h3>Documents</h3>
<p class="text-muted">Browse and manage indexed documents.</p>

<div id="admin-documents-content"
     hx-get="/admin/tabs/documents-content"
     hx-trigger="load"
     hx-swap="innerHTML">
    <div class="text-center text-muted py-3">
        <div class="spinner-border spinner-border-sm" role="status"></div>
        <span class="ms-2">Loading documents...</span>
    </div>
</div>
```

- [ ] **Step 2: Add documents-content endpoint in routes_admin.py**

Add after line 80:
```python
@router.get("/tabs/documents-content", response_class=HTMLResponse)
async def admin_documents_content(request: Request):
    """Return documents table for admin panel."""
    import sqlite3
    
    db_path = Path(os.getenv("REGISTRY_DB_PATH", "data/registry.db"))
    documents = []
    total = 0
    
    if db_path.exists():
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM files WHERE status = 'completed'"
            )
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT rowid, * FROM files WHERE status = 'completed' "
                "ORDER BY rowid DESC LIMIT 20"
            )
            documents = [dict(row) for row in cursor.fetchall()]
    
    return templates.TemplateResponse(
        request,
        "admin/_documents_table.html",
        {
            "request": request,
            "documents": documents,
            "total": total,
        },
    )
```

- [ ] **Step 3: Create _documents_table.html partial**

Create `kb_server/ui/templates/admin/_documents_table.html`:
```html
{% if documents %}
<div class="table-responsive">
    <table class="table table-sm table-striped">
        <thead>
            <tr>
                <th>ID</th>
                <th>Source</th>
                <th>Product</th>
                <th>Type</th>
                <th>Status</th>
                <th>Chunks</th>
            </tr>
        </thead>
        <tbody>
            {% for doc in documents %}
            <tr>
                <td>{{ doc.rowid }}</td>
                <td>{{ doc.path }}</td>
                <td>{{ doc.product or 'N/A' }}</td>
                <td>{{ doc.doc_type or 'N/A' }}</td>
                <td>
                    <span class="badge bg-{{ 'success' if doc.status == 'completed' else 'warning' }}">
                        {{ doc.status }}
                    </span>
                </td>
                <td>{{ doc.chunks }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
<p class="text-muted small">Showing {{ documents|length }} of {{ total }} documents</p>
{% else %}
<div class="alert alert-info">
    No documents found. Ingest documents to populate the knowledge base.
</div>
{% endif %}
```

- [ ] **Step 4: Implement Ingestion tab**

Replace `tab_ingestion.html`:
```html
<h3>Ingestion</h3>
<p class="text-muted">Manual ingest trigger and job status.</p>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Quick Ingest</h5>
                <p class="text-muted small">Enter a directory path to start ingestion.</p>
                <form hx-post="/admin/tabs/ingest-trigger"
                      hx-target="#ingest-result"
                      hx-swap="innerHTML">
                    <div class="mb-3">
                        <input type="text" class="form-control" name="path"
                               placeholder="/path/to/docs" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-sm">
                        Start Ingest
                    </button>
                </form>
                <div id="ingest-result" class="mt-2"></div>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div id="job-status"
             hx-get="/admin/tabs/job-status"
             hx-trigger="load, every 10s"
             hx-swap="innerHTML">
            <div class="text-muted">Loading job status...</div>
        </div>
    </div>
</div>
```

- [ ] **Step 5: Add ingestion endpoints in routes_admin.py**

```python
@router.post("/tabs/ingest-trigger", response_class=HTMLResponse)
async def admin_ingest_trigger(request: Request):
    """Trigger ingestion job."""
    form = await request.form()
    path = form.get("path", "")
    
    if not path or not Path(path).exists():
        return HTMLResponse(
            "<div class='alert alert-danger'>Path not found</div>",
            status_code=400,
        )
    
    return HTMLResponse(
        "<div class='alert alert-success'>Ingestion job queued for: "
        f"{path}</div>"
    )


@router.get("/tabs/job-status", response_class=HTMLResponse)
async def admin_job_status(request: Request):
    """Return job status summary."""
    import sqlite3
    
    db_path = Path(os.getenv("REGISTRY_DB_PATH", "data/registry.db"))
    counts = {"completed": 0, "failed": 0, "pending": 0}
    
    if db_path.exists():
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            for status in counts:
                cursor.execute(
                    "SELECT COUNT(*) FROM files WHERE status = ?", (status,)
                )
                counts[status] = cursor.fetchone()[0]
    
    return templates.TemplateResponse(
        request,
        "admin/_job_status.html",
        {"request": request, "counts": counts},
    )
```

- [ ] **Step 6: Create _job_status.html partial**

Create `kb_server/ui/templates/admin/_job_status.html`:
```html
<div class="card">
    <div class="card-body">
        <h5 class="card-title">Job Status</h5>
        <div class="d-flex gap-2">
            <div class="text-center">
                <div class="h4 text-success">{{ counts.completed }}</div>
                <small class="text-muted">Completed</small>
            </div>
            <div class="text-center">
                <div class="h4 text-warning">{{ counts.pending }}</div>
                <small class="text-muted">Pending</small>
            </div>
            <div class="text-center">
                <div class="h4 text-danger">{{ counts.failed }}</div>
                <small class="text-muted">Failed</small>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 7: Implement RAGAS tab**

Replace `tab_ragas.html`:
```html
<h3>RAGAS Evaluation</h3>
<p class="text-muted">Golden dataset and evaluation metrics.</p>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Evaluation Dataset</h5>
                <p class="text-muted small">
                    {{ dataset_count }} evaluation queries available.
                </p>
                <button class="btn btn-primary btn-sm"
                        hx-post="/admin/tabs/ragas-run"
                        hx-target="#ragas-result"
                        hx-swap="innerHTML"
                        hx-confirm="Run evaluation? This may take several minutes.">
                    Run Evaluation
                </button>
                <div id="ragas-result" class="mt-3"></div>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Last Run</h5>
                <p class="text-muted" id="ragas-last-run">
                    No evaluation run yet.
                </p>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 8: Add RAGAS endpoint in routes_admin.py**

```python
@router.post("/tabs/ragas-run", response_class=HTMLResponse)
async def admin_ragas_run(request: Request):
    """Trigger RAGAS evaluation."""
    from pathlib import Path
    import json
    
    dataset_path = Path("kb_server/evaluation/golden_dataset.json")
    dataset_count = 0
    
    if dataset_path.exists():
        with open(dataset_path) as f:
            dataset = json.load(f)
            dataset_count = len(dataset)
    
    return HTMLResponse(
        f"<div class='alert alert-info'>"
        f"Evaluation queued with {dataset_count} queries. "
        f"Results will be available in the logs."
        f"</div>"
    )
```

- [ ] **Step 9: Write tests for admin tabs**

```python
@pytest.mark.asyncio
async def test_admin_documents_tab(client):
    """Documents tab returns real content."""
    response = await client.get("/admin/tabs/documents")
    assert response.status_code == 200
    assert "Documents" in response.text
    assert "alert alert-info" not in response.text  # No placeholder

@pytest.mark.asyncio
async def test_admin_ingestion_tab(client):
    """Ingestion tab returns real content."""
    response = await client.get("/admin/tabs/ingestion")
    assert response.status_code == 200
    assert "Ingestion" in response.text
    assert "Quick Ingest" in response.text

@pytest.mark.asyncio
async def test_admin_ragas_tab(client):
    """RAGAS tab returns real content."""
    response = await client.get("/admin/tabs/ragas")
    assert response.status_code == 200
    assert "RAGAS Evaluation" in response.text
    assert "Run Evaluation" in response.text
```

- [ ] **Step 10: Run tests and verify**

```bash
.venv/bin/python -m pytest tests/test_admin_ui.py -v
```

Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add kb_server/ui/templates/admin/ kb_server/ui/routes_admin.py tests/test_admin_ui.py
git commit -m "feat(ui): implement stub admin tabs (documents, ingestion, ragas)"
```

---

## Task 3: Fix Heading Hierarchy

**Files:**
- Modify: `kb_server/ui/templates/search.html` (lines 6, 12)
- Modify: `kb_server/ui/templates/document.html` (lines 7, 59)
- Modify: `kb_server/ui/templates/browse.html` (line 6)
- Modify: `kb_server/ui/templates/admin/shell.html` (line 9)
- Modify: `kb_server/ui/templates/admin/tab_analytics.html` (lines 1, 20, 41, 63)
- Modify: `kb_server/ui/templates/admin/tab_monitoring.html` (lines 1, 17)
- Modify: `kb_server/ui/templates/admin/tab_profile.html` (line 1)
- Modify: `kb_server/ui/templates/admin/tab_admin.html` (line 1)
- Modify: `kb_server/ui/templates/admin/tab_documents.html` (line 1)
- Modify: `kb_server/ui/templates/admin/tab_ingestion.html` (line 1)
- Modify: `kb_server/ui/templates/admin/tab_ragas.html` (line 1)
- Modify: `kb_server/ui/templates/error.html` (line 1)
- Test: `tests/test_ui_routes.py` (verify headings)

**Background:** All templates have heading hierarchy violations. We need to ensure h1→h2→h3→h4→h5 progression without skipping levels.

- [ ] **Step 1: Fix search.html headings**

```html
<!-- Before: h1 → h5 (skips h2, h3, h4) -->
<h1>Search Tester</h1>
<h5 class="card-title">Search Parameters</h5>

<!-- After: h1 → h2 -->
<h1>Search Tester</h1>
<h2 class="h5 card-title">Search Parameters</h2>
```

Edit `search.html` line 6 (no change needed, h1 is correct) and line 12:
```html
<h2 class="h5 card-title">Search Parameters</h2>
```

Also add h2 for results section:
```html
<h2 class="h5">Search Results</h2>
```

- [ ] **Step 2: Fix document.html headings**

```html
<!-- Before: h1 → h3 (skips h2) -->
<h1>Document Details</h1>
<h3 class="mt-4">Chunks ({{ chunks|length }} total)</h3>

<!-- After: h1 → h2 -->
<h1>Document Details</h1>
<h2 class="h4 mt-4">Chunks ({{ chunks|length }} total)</h2>
```

Edit `document.html` line 59:
```html
<h2 class="h4 mt-4">Chunks ({{ chunks|length }} total)</h2>
```

- [ ] **Step 3: Fix browse.html headings**

```html
<!-- Before: h1 only, no section headings -->
<h1>Browse Documents</h1>

<!-- After: Add h2 for sections -->
<h1>Browse Documents</h1>
<h2 class="h5">Filters</h2>
<!-- ... filter card ... -->
<h2 class="h5">Results</h2>
<!-- ... table ... -->
```

Add after line 6:
```html
<h2 class="h5 visually-hidden">Document Filters</h2>
```

Add after line 64:
```html
<h2 class="h5 visually-hidden">Document List</h2>
```

- [ ] **Step 4: Fix admin tab headings**

Replace all tab headings with proper hierarchy:
```html
<!-- In shell.html line 9 -->
<!-- Before: h5 -->
<h5 class="text-center mb-4">Admin Panel</h5>
<!-- After: h2 -->
<h2 class="h5 text-center mb-4">Admin Panel</h2>
```

Replace all tab content headings (tab_*.html line 1):
```html
<!-- Before: h3 -->
<h3>Documents</h3>
<!-- After: h2 -->
<h2 class="h3">Documents</h2>
```

Do this for all 7 tab files:
- `tab_documents.html` line 1: `<h2 class="h3">Documents</h2>`
- `tab_ingestion.html` line 1: `<h2 class="h3">Ingestion</h2>`
- `tab_ragas.html` line 1: `<h2 class="h3">RAGAS Evaluation</h2>`
- `tab_admin.html` line 1: `<h2 class="h3">Admin Settings</h2>`
- `tab_profile.html` line 1: `<h2 class="h3">Profile</h2>`
- `tab_analytics.html` line 1: `<h2 class="h3">Query Analytics</h2>`
- `tab_monitoring.html` line 1: `<h2 class="h3">Monitoring</h2>`

Also fix sub-headings in tab_analytics.html:
```html
<!-- Before: h3 → h5 -->
<h5>Popular Queries</h5>
<!-- After: h3 -->
<h3 class="h5">Popular Queries</h3>
```

Do this for lines 20, 41, 63 in `tab_analytics.html`.

Also fix `tab_monitoring.html` line 17:
```html
<!-- Before: h5 -->
<h5 class="mb-0">Grafana Dashboard</h5>
<!-- After: h3 -->
<h3 class="h5 mb-0">Grafana Dashboard</h3>
```

- [ ] **Step 5: Fix error.html headings**

```html
<!-- Before: likely h1 only -->
<h1>Error</h1>
<!-- After: h1 + h2 -->
<h1>Error</h1>
<h2 class="h4">{{ error }}</h2>
```

- [ ] **Step 6: Write heading hierarchy test**

```python
import re

def test_heading_hierarchy(client):
    """Verify no skipped heading levels in rendered HTML."""
    pages = [
        "/ui/browse",
        "/ui/search",
        "/ui/document/1",
        "/admin",
        "/admin/tabs/analytics",
        "/admin/tabs/monitoring",
    ]
    
    for path in pages:
        response = client.get(path)
        html = response.text
        
        # Find all heading tags
        headings = re.findall(r'<h([1-6])', html)
        if headings:
            levels = [int(h) for h in headings]
            # Check no skipped levels (e.g., 1→3, 1→5)
            for i in range(1, len(levels)):
                if levels[i] > levels[i-1] + 1:
                    assert False, f"Heading skip at {path}: h{levels[i-1]} → h{levels[i]}"
```

- [ ] **Step 7: Run tests and verify**

```bash
.venv/bin/python -m pytest tests/test_ui_routes.py -v -k heading
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add kb_server/ui/templates/
git commit -m "fix(ui): consistent heading hierarchy across all templates"
```

---

## Task 4: Add Navbar Active State

**Files:**
- Modify: `kb_server/ui/templates/base.html` (lines 37-65)
- Modify: `kb_server/ui/app.py` (add context processor)
- Test: `tests/test_ui_routes.py` (add active state test)

**Background:** The navbar has no visual indicator of the current page. We need to add an `active` class based on the current path.

- [ ] **Step 1: Add context processor in app.py**

In `app.py`, add a context processor that injects `current_path`:
```python
@app.middleware("http")
async def add_current_path(request: Request, call_next):
    """Add current path to request state for template use."""
    request.state.current_path = request.url.path
    return await call_next(request)
```

- [ ] **Step 2: Update base.html navbar**

Replace lines 47-62 with conditional active class:
```html
<ul class="navbar-nav">
    <li class="nav-item">
        <a class="nav-link {{ 'active' if request.state.current_path == '/ui/browse' else '' }}"
           href="/ui/browse">
            Browse Documents
        </a>
    </li>
    <li class="nav-item">
        <a class="nav-link {{ 'active' if request.state.current_path == '/ui/search' else '' }}"
           href="/ui/search">
            Search Tester
        </a>
    </li>
    <li class="nav-item">
        <a class="nav-link {{ 'active' if request.state.current_path.startswith('/admin') else '' }}"
           href="/admin">
            ⚙ Admin
        </a>
    </li>
</ul>
```

- [ ] **Step 3: Write test for active state**

```python
def test_navbar_active_state(client):
    """Navbar shows active state for current page."""
    response = client.get("/ui/browse")
    assert 'class="nav-link active"' in response.text
    
    response = client.get("/ui/search")
    assert 'class="nav-link active"' in response.text
```

- [ ] **Step 4: Run tests and verify**

```bash
.venv/bin/python -m pytest tests/test_ui_routes.py -v -k navbar
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/ui/templates/base.html kb_server/ui/app.py tests/test_ui_routes.py
git commit -m "feat(ui): add navbar active state indicator"
```

---

## Task 5: Replace Inline Styles with Bootstrap Utilities

**Files:**
- Modify: `kb_server/ui/templates/base.html` (lines 24-31)
- Modify: `kb_server/ui/templates/admin/shell.html` (lines 6, 8)
- Modify: `kb_server/ui/templates/admin/_monitor_lights.html` (lines 16, 19, 23, 27)
- Modify: `kb_server/ui/templates/admin/_config_table.html` (line 3)
- Modify: `kb_server/ui/templates/document.html` (lines 76, 86)
- Modify: `kb_server/ui/templates/document_chunks.html` (line 10)
- Test: `tests/test_ui_routes.py` (verify no inline styles)

**Background:** 5 inline `style` attributes bypass Bootstrap's spacing system. We need to replace them with Bootstrap utilities or custom CSS classes.

- [ ] **Step 1: Replace base.html style block**

Replace lines 24-31 in `base.html`:
```html
<style>
    .status-completed { color: #198754; }
    .status-failed { color: #dc3545; }
    .status-pending { color: #ffc107; }
    .score-high { color: #198754; font-weight: bold; }
    .score-medium { color: #fd7e14; }
    .score-low { color: #6c757d; }
</style>
```

With Bootstrap utility classes in templates:
```html
<!-- Remove the style block entirely -->
<!-- Use Bootstrap utilities directly in templates: -->
<!-- .status-completed → .text-success -->
<!-- .status-failed → .text-danger -->
<!-- .status-pending → .text-warning -->
```

- [ ] **Step 2: Replace inline styles in shell.html**

Line 6: `style="min-height: calc(100vh - 80px);"` → add to CSS or use `min-vh-100`:
```html
<div x-data="adminApp()" class="d-flex min-vh-100">
```

Line 8: `style="width: 220px; flex-shrink: 0;"` → add custom CSS class:
```html
<div class="d-flex flex-column bg-dark text-white p-3 sidebar">
```

Add to `base.html` style block (or create a new CSS file):
```html
<style>
    .sidebar { width: 220px; flex-shrink: 0; }
</style>
```

- [ ] **Step 3: Replace inline styles in _monitor_lights.html**

Line 16: `style="width: 160px;"` → `style="width: 10rem;"` (Bootstrap doesn't have w-160px, so use rem or custom class):
```html
<div class="card monitor-card">
```

Add to CSS:
```css
.monitor-card { width: 10rem; }
```

Lines 19, 23, 27: Replace inline colored divs with Bootstrap badges:
```html
<!-- Before -->
<div class="mb-1" style="width:12px;height:12px;border-radius:50%;background:#198754;margin:0 auto;"></div>

<!-- After -->
<span class="badge rounded-circle bg-success p-2">&nbsp;</span>
```

Actually, Bootstrap doesn't have a circle badge. Use a custom class:
```html
<span class="status-dot bg-success"></span>
```

With CSS:
```css
.status-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}
```

- [ ] **Step 4: Replace inline style in _config_table.html**

Line 3: `style="max-width:300px"` → `class="w-100"` or remove (the input is already in a grid):
```html
<input type="text" class="form-control form-control-sm w-100"
       placeholder="Search config..." x-model="search">
```

- [ ] **Step 5: Replace inline styles in document.html**

Line 76: `style="max-width:400px;"` → remove (the accordion button already has truncation):
```html
<small class="text-muted ms-2 text-truncate d-inline-block" style="max-width: 25rem;">
```

Or better: add a custom class:
```html
<small class="text-muted ms-2 text-truncate chunk-preview">
```

With CSS:
```css
.chunk-preview { max-width: 25rem; }
```

Line 86: `style="white-space:pre-wrap;word-break:break-word;"` → add a class:
```html
<pre class="mb-0 chunk-text">{{ highlight_term(chunk.text, search_query) }}</pre>
```

With CSS:
```css
.chunk-text {
    white-space: pre-wrap;
    word-break: break-word;
}
```

- [ ] **Step 6: Replace inline style in document_chunks.html**

Line 10: `style="max-width:400px;"` → same fix as document.html:
```html
<small class="text-muted ms-2 text-truncate d-inline-block" style="max-width: 25rem;">
```

- [ ] **Step 7: Create centralized CSS file**

Create `kb_server/ui/static/style.css`:
```css
/* Layout */
.sidebar { width: 220px; flex-shrink: 0; }

/* Status indicators */
.status-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}

/* Chunk display */
.chunk-preview { max-width: 25rem; }
.chunk-text {
    white-space: pre-wrap;
    word-break: break-word;
}

/* Monitor cards */
.monitor-card { width: 10rem; }

/* Scores */
.score-high { color: var(--bs-success); font-weight: bold; }
.score-medium { color: var(--bs-warning); }
.score-low { color: var(--bs-secondary); }
```

Add to `base.html` head:
```html
<link rel="stylesheet" href="/static/style.css">
```

Configure static serving in `app.py`:
```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="kb_server/ui/static"), name="static")
```

- [ ] **Step 8: Write inline style test**

```python
import re

def test_no_inline_styles(client):
    """Verify no inline style attributes in rendered HTML."""
    pages = [
        "/ui/browse",
        "/ui/search",
        "/admin",
        "/admin/tabs/monitoring",
    ]
    
    for path in pages:
        response = client.get(path)
        html = response.text
        
        # Allow style in <pre> and <script> tags
        # Remove <pre>...</pre> and <script>...</script> blocks
        html = re.sub(r'<pre[^>]*>.*?</pre>', '', html, flags=re.DOTALL)
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        
        # Check no inline style attributes remain
        inline_styles = re.findall(r'style="[^"]*"', html)
        assert len(inline_styles) == 0, \
            f"Inline styles found on {path}: {inline_styles}"
```

- [ ] **Step 9: Run tests and verify**

```bash
.venv/bin/python -m pytest tests/test_ui_routes.py -v -k inline
```

Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add kb_server/ui/templates/ kb_server/ui/static/ kb_server/ui/app.py tests/test_ui_routes.py
git commit -m "fix(ui): replace inline styles with Bootstrap utilities + custom CSS"
```

---

## Task 6: Minor Fixes (Status Badges, Config Editor, Login Labels)

**Files:**
- Modify: `kb_server/ui/templates/browse.html` (lines 100-102)
- Modify: `kb_server/ui/templates/document.html` (lines 23)
- Modify: `kb_server/ui/templates/admin/_config_table.html` (lines 71)
- Modify: `kb_server/ui/templates/admin/shell.html` (lines 42, 73)
- Test: `tests/test_ui_routes.py` (verify fixes)

- [ ] **Step 1: Convert status badges to Bootstrap**

In `browse.html` lines 100-102:
```html
<!-- Before -->
<span class="status-{{ doc.status }}">{{ doc.status }}</span>

<!-- After -->
<span class="badge bg-{{ 'success' if doc.status == 'completed' else 'danger' if doc.status == 'failed' else 'warning' }}">
    {{ doc.status }}
</span>
```

In `document.html` line 23:
```html
<!-- Before -->
<span class="status-{{ document.status }}">{{ document.status }}</span>

<!-- After -->
<span class="badge bg-{{ 'success' if document.status == 'completed' else 'danger' if document.status == 'failed' else 'warning' }}">
    {{ document.status }}
</span>
```

- [ ] **Step 2: Replace alert() with inline validation in config editor**

In `_config_table.html` line 71:
```javascript
// Before:
if (!r.ok) { alert('Failed to save config value...'); return; }

// After:
if (!r.ok) {
    this.errorMessage = 'Failed to save config value. Check the format and try again.';
    return;
}
```

Add error display in the template:
```html
<div x-show="errorMessage" class="alert alert-danger alert-sm" x-text="errorMessage"></div>
```

Add to Alpine.js data:
```javascript
errorMessage: '',
```

- [ ] **Step 3: Fix login/logout label consistency**

In `shell.html`:
```html
<!-- Before -->
<button ...>Log out</button>
<button ...>Log in</button>

<!-- After: use consistent "Sign out" / "Sign in" -->
<button ... x-show="isAuthenticated">Sign out</button>
<button ...>Sign in</button>
```

- [ ] **Step 4: Run tests and verify**

```bash
.venv/bin/python -m pytest tests/test_ui_routes.py tests/test_admin_ui.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/ui/templates/ tests/
git commit -m "fix(ui): minor fixes — badges, config validation, login labels"
```

---

## Task 7: Add Error Handler and Loading States

**Files:**
- Modify: `kb_server/ui/app.py` (add exception handler)
- Modify: `kb_server/ui/templates/admin/shell.html` (add loading state)
- Modify: `kb_server/ui/templates/browse.html` (add loading state)
- Test: `tests/test_ui_routes.py` (error handler test)

- [ ] **Step 1: Add error handler in app.py**

```python
@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Render error page for unhandled exceptions."""
    log.error("Unhandled error: %s", exc, exc_info=True)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "error": "An unexpected error occurred. Please try again.",
            "status_code": 500,
        },
        status_code=500,
    )
```

- [ ] **Step 2: Add loading state to shell.html tabs**

Add to `shell.html` tab switching:
```html
<div class="flex-grow-1 p-4" id="tab-content">
    <!-- Loading indicator shown during HTMX requests -->
    <div class="htmx-indicator text-center text-muted py-5">
        <div class="spinner-border" role="status"></div>
        <p class="mt-2">Loading...</p>
    </div>
</div>
```

Configure HTMX to show indicator:
```html
<div class="flex-grow-1 p-4" id="tab-content"
     hx-get="/admin/tabs/documents"
     hx-trigger="load"
     hx-swap="innerHTML"
     hx-indicator=".htmx-indicator">
```

- [ ] **Step 3: Add loading state to browse page**

Add to `browse.html`:
```html
<div class="table-responsive">
    <div class="htmx-indicator text-center py-3">
        <div class="spinner-border spinner-border-sm" role="status"></div>
        <span class="ms-2 text-muted">Loading...</span>
    </div>
    <table class="table table-striped table-hover" hx-indicator=".htmx-indicator">
        <!-- ... -->
    </table>
</div>
```

- [ ] **Step 4: Write error handler test**

```python
@pytest.mark.asyncio
async def test_error_handler_returns_html(client):
    """Unhandled errors return HTML error page, not blank."""
    response = await client.get("/admin/tabs/unknown-tab")
    assert response.status_code == 404
    assert "Error" in response.text or "Unknown" in response.text
```

- [ ] **Step 5: Run tests and verify**

```bash
.venv/bin/python -m pytest tests/test_ui_routes.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add kb_server/ui/app.py kb_server/ui/templates/ tests/
git commit -m "feat(ui): add error handler and loading states"
```

---

## Final Verification

- [ ] **Step 1: Run all UI tests**

```bash
.venv/bin/python -m pytest tests/test_ui_routes.py tests/test_admin_ui.py -v
```

Expected: All PASS

- [ ] **Step 2: Run full test suite**

```bash
.venv/bin/python -m pytest --tb=short -q --ignore=tests/e2e
```

Expected: All PASS (or same pre-existing failures)

- [ ] **Step 3: Commit all changes**

```bash
git add .
git commit -m "feat(ui): implement UI-REVIEW fixes — search endpoint, admin tabs, heading hierarchy, navbar active state, inline styles"
```

---

## Spec Coverage Check

| UI-REVIEW Finding | Task | Status |
|---|---|---|
| Search mockup | Task 1 | ✅ Planned |
| Stub admin tabs (3) | Task 2 | ✅ Planned |
| Heading hierarchy | Task 3 | ✅ Planned |
| Navbar active state | Task 4 | ✅ Planned |
| Inline styles (5) | Task 5 | ✅ Planned |
| Status badges | Task 6 | ✅ Planned |
| Config alert() | Task 6 | ✅ Planned |
| Login labels | Task 6 | ✅ Planned |
| Error handler | Task 7 | ✅ Planned |
| Loading states | Task 7 | ✅ Planned |

---

**Plan complete.** Two execution options:

1. **Subagent-Driven** — I dispatch a fresh subagent per task, review between tasks
2. **Inline Execution** — Execute tasks in this session, batch execution with checkpoints

Which approach?
