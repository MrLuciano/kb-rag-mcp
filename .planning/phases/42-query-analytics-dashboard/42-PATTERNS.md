# Phase 42: Query Logging Analytics Dashboard - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 5
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `kb_server/analytics/query_analyzer.py` | service | CRUD (SQLite query) | Same file — `get_most_common_queries()`, `get_zero_result_queries()` | exact (same file, same pattern) |
| `kb_server/ui/routes_admin.py` | controller | request-response (HTMX partial) | Same file — `admin_monitor_lights()` | role-match (data-fetching route handler) |
| `kb_server/ui/templates/admin/shell.html` | component | request-response (HTML sidebar) | Same file — existing `<li>` tab entries | exact (same file, same pattern) |
| `kb_server/ui/templates/admin/tab_analytics.html` | component | request-response (HTML fragment) | `admin/tab_monitoring.html` | role-match (multi-section data template) |
| `tests/test_admin_ui.py` | test | test | Same file — `TestAdminTemplates` class | exact (same file, same pattern) |

## Pattern Assignments

### `kb_server/analytics/query_analyzer.py` (service, CRUD)

**Action:** Add `get_latency_stats(time_range_days=7)` method.

**Analog:** Same file — `get_most_common_queries()` (lines 48–82)

**Imports pattern** (lines 1–5):
```python
"""Query pattern analyzer for RAG optimization."""
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
```

**Constructor pattern** (lines 21–24):
```python
def __init__(self, db_path: Path):
    """Initialize analyzer with database path."""
    self.db_path = db_path
    log.info("QueryAnalyzer initialized: db=%s", db_path)
```

**Core SQL query + return pattern** (lines 48–82 — use for `get_latency_stats`):
```python
def get_most_common_queries(
    self, limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get most frequently asked queries.
    
    Args:
        limit: Maximum number of queries to return
        
    Returns:
        List of {query_text, frequency} dicts
    """
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT query_text, COUNT(*) as frequency
        FROM query_log
        GROUP BY query_text
        HAVING frequency > 1
        ORDER BY frequency DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    log.debug(
        "Most common queries: %d results above threshold",
        len(rows),
    )
    return [
        {'query_text': row[0], 'frequency': row[1]}
        for row in rows
    ]
```

**Second analog — `get_zero_result_queries()`** (lines 112–137) — useful for the Content Gaps section query method that already exists:
```python
def get_zero_result_queries(self) -> List[Dict[str, Any]]:
    """
    Get queries that returned zero results (content gaps).
    
    Returns:
        List of query dictionaries with frequency counts
    """
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT query_text, COUNT(*) as frequency
        FROM query_log
        WHERE result_count = 0
        GROUP BY query_text
        ORDER BY frequency DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    log.debug("Zero-result queries: %d unique queries", len(rows))
    return [
        {'query_text': row[0], 'frequency': row[1]}
        for row in rows
    ]
```

**Expected approach for `get_latency_stats(time_range_days=7)`:**
- Follow the same `conn = sqlite3.connect()` / `cursor = conn.cursor()` / `cursor.execute()` / `rows = cursor.fetchall()` / `conn.close()` pattern
- Add a `WHERE timestamp >= ?` filter using the `time_range_days` parameter
- Use SQLite `PERCENTILE` or compute percentiles in Python from fetched latency values
- Return p50, p95, p99 per operation type OR overall (see Discretion in D-06)
- Log with `log.debug()` before returning

---

### `kb_server/ui/routes_admin.py` (controller, request-response)

**Action (1):** Add `"analytics": "admin/tab_analytics.html"` to `template_map`.

**Analog:** Same file — `template_map` dict (lines 34–41)

**Template map pattern** (lines 34–41):
```python
template_map = {
    "documents": "admin/tab_documents.html",
    "monitoring": "admin/tab_monitoring.html",
    "ingestion": "admin/tab_ingestion.html",
    "ragas": "admin/tab_ragas.html",
    "admin": "admin/tab_admin.html",
    "profile": "admin/tab_profile.html",
}
```
Changes: add `"analytics": "admin/tab_analytics.html"` entry.

**Action (2):** The `admin_tab_content` handler (lines 31–48) will automatically serve the analytics template once the template_map entry is added, because it dispatches by `tab_name`:
```python
@router.get("/tabs/{tab_name}", response_class=HTMLResponse)
async def admin_tab_content(request: Request, tab_name: str):
    """Render a tab content partial."""
    template_map = {
        ...
        "analytics": "admin/tab_analytics.html",
    }
    template = template_map.get(tab_name)
    if template is None:
        return HTMLResponse(
            "<div class='alert alert-danger'>Unknown tab</div>",
            status_code=404,
        )
    return templates.TemplateResponse(template, {"request": request})
```

**However**, the analytics tab needs data from `QueryAnalyzer`. The **best analog** for a route that fetches and passes data is `admin_monitor_lights()` (lines 51–60):

```python
@router.get("/tabs/monitor-lights", response_class=HTMLResponse)
async def admin_monitor_lights(request: Request):
    """Return monitor lights partial with health data."""
    from kb_server.health import check_all_components

    components = await check_all_components()
    return templates.TemplateResponse(
        "admin/_monitor_lights.html",
        {"request": request, "components": components},
    )
```

**Pattern to follow for analytics data passing:**
```python
# New endpoint OR modify admin_tab_content to pass data for 'analytics' tab
# Style: lazy import + construct + call + pass to template
from kb_server.analytics.query_analyzer import QueryAnalyzer
from pathlib import Path
import os

db_path = Path(os.getenv("QUERY_LOG_PATH", "data/kb_metadata.db"))
analyzer = QueryAnalyzer(db_path)
popular = analyzer.get_most_common_queries(limit=25)
gaps = analyzer.get_zero_result_queries()
latency = analyzer.get_latency_stats(time_range_days=7)
return templates.TemplateResponse(
    template,
    {"request": request, "popular_queries": popular, "content_gaps": gaps, "latency_stats": latency},
)
```

**Error handling pattern** from the same file (the template_map 404 case, lines 43–47):
```python
if template is None:
    return HTMLResponse(
        "<div class='alert alert-danger'>Unknown tab</div>",
        status_code=404,
    )
```
For analytics — wrap QueryAnalyzer calls in try/except, pass error context to template for graceful empty state.

---

### `kb_server/ui/templates/admin/shell.html` (component, request-response)

**Action:** Add Analytics tab `<li>` entry to the sidebar nav list.

**Analog:** Same file — existing `<li>` entries (lines 11–34)

**Sidebar nav list pattern** (lines 11–34):
```html
<ul class="nav nav-pills flex-column">
    <li class="nav-item">
        <a class="nav-link text-white" :class="{ 'active': activeTab === 'documents' }"
           href="#" @click.prevent="switchTab('documents')">📄 Documents</a>
    </li>
    <li class="nav-item">
        <a class="nav-link text-white" :class="{ 'active': activeTab === 'monitoring' }"
           href="#" @click.prevent="switchTab('monitoring')">📊 Monitoring</a>
    </li>
    <li class="nav-item">
        <a class="nav-link text-white" :class="{ 'active': activeTab === 'ingestion' }"
           href="#" @click.prevent="switchTab('ingestion')">📥 Ingestion</a>
    </li>
    <li class="nav-item">
        <a class="nav-link text-white" :class="{ 'active': activeTab === 'ragas' }"
           href="#" @click.prevent="switchTab('ragas')">🧪 RAGAS</a>
    </li>
    <li class="nav-item" x-show="isAdmin">
        <a class="nav-link text-white" :class="{ 'active': activeTab === 'admin' }"
           href="#" @click.prevent="switchTab('admin')">⚙ Admin</a>
    </li>
    <li class="nav-item">
        <a class="nav-link text-white" :class="{ 'active': activeTab === 'profile' }"
           href="#" @click.prevent="switchTab('profile')">👤 Profile</a>
    </li>
</ul>
```

**Insert new Analytics entry** — add after the "profile" entry (line 34) or before it:
```html
<li class="nav-item">
    <a class="nav-link text-white" :class="{ 'active': activeTab === 'analytics' }"
       href="#" @click.prevent="switchTab('analytics')">📈 Analytics</a>
</li>
```

**Note from CONTEXT.md (D-01):** Analytics is the 7th tab, placed in the sidebar. The location in the list is at the agent's discretion — recommend putting it between "Monitoring" and "Ingestion" or as the last tab.

---

### `kb_server/ui/templates/admin/tab_analytics.html` (component, request-response) — **NEW FILE**

**Analog:** `admin/tab_monitoring.html` (lines 1–40) — multi-section, server-rendered content with h3 headings

**Pattern to follow** (from `tab_monitoring.html`):
```html
<h3>Monitoring</h3>
<p class="text-muted">System health and Grafana dashboards.</p>

<!-- section content here, separated by <hr> -->
<hr>
<!-- next section -->
```

**Structure for the analytics template** (build from tab_monitoring.html and tab_admin.html patterns):

```html
<h3>Analytics</h3>
<p class="text-muted">Query usage patterns and performance over the last 7 days.</p>

<!-- Empty state (when no data) -->
{% if not popular_queries and not content_gaps and not latency_stats %}
<div class="alert alert-info">
    <p>No query data available for the last 7 days. Query data appears after users search the knowledge base.</p>
</div>
{% else %}

<!-- Popular Queries -->
<h4 class="mt-4">Popular Queries</h4>
<p class="text-muted small">Top 25 most frequent queries in the last 7 days.</p>
<div class="table-responsive">
    <table class="table table-striped table-sm">
        <thead>
            <tr><th>#</th><th>Query</th><th>Frequency</th></tr>
        </thead>
        <tbody>
            {% for q in popular_queries %}
            <tr><td>{{ loop.index }}</td><td>{{ q.query_text }}</td><td>{{ q.frequency }}</td></tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<hr>

<!-- Content Gaps -->
<h4 class="mt-4">Content Gaps</h4>
<p class="text-muted small">Zero-result queries — documentation may be missing.</p>
<div class="table-responsive">
    <table class="table table-striped table-sm">
        <thead>
            <tr><th>Query</th><th>Frequency</th><th>Action</th></tr>
        </thead>
        <tbody>
            {% for g in content_gaps %}
            <tr>
                <td>{{ g.query_text }}</td>
                <td>{{ g.frequency }}</td>
                <td><a href="/ui/search?q={{ g.query_text | urlencode }}" class="btn btn-sm btn-outline-secondary">Search</a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<hr>

<!-- Latency Statistics -->
<h4 class="mt-4">Latency Statistics</h4>
<p class="text-muted small">Query latency distribution (p50, p95, p99) in milliseconds.</p>
<div class="table-responsive">
    <table class="table table-striped table-sm">
        <thead>
            <tr><th>Metric</th><th>Count</th><th>p50</th><th>p95</th><th>p99</th></tr>
        </thead>
        <tbody>
            {% for stat in latency_stats %}
            <tr>
                <td>{{ stat.operation }}</td>
                <td>{{ stat.count }}</td>
                <td>{{ "%.1f"|format(stat.p50_ms) }}</td>
                <td>{{ "%.1f"|format(stat.p95_ms) }}</td>
                <td>{{ "%.1f"|format(stat.p99_ms) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

{% endif %}

<!-- Refresh button -->
<div class="mt-3">
    <button class="btn btn-outline-primary btn-sm"
            hx-get="/admin/tabs/analytics"
            hx-target="#tab-content"
            hx-swap="innerHTML">↻ Refresh</button>
</div>
```

**Key patterns from existing tabs:**
- `tab_monitoring.html` — uses `h3` heading + `p.text-muted` description pattern (lines 1–2)
- `tab_admin.html` — uses HTMX `hx-get` + `hx-trigger="load"` for data loading (lines 1–8)
- `tab_profile.html` — same HTMX data loading pattern (lines 1–8)
- Bootstrap `table table-striped table-sm` classes for table formatting (common across the UI)

---

### `tests/test_admin_ui.py` (test, test)

**Action:** Add analytics tab existence test + route test.

**Analog:** Same file — `TestAdminTemplates` class (lines 60–75)

**Existing test pattern** (lines 60–75):
```python
class TestAdminTemplates:
    def test_all_tab_templates_exist(self):
        tabs = [
            "documents",
            "monitoring",
            "ingestion",
            "ragas",
            "admin",
            "profile",
        ]
        for tab in tabs:
            path = f"kb_server/ui/templates/admin/tab_{tab}.html"
            assert os.path.exists(path), f"Missing template: {path}"

    def test_shell_template_exists(self):
        assert os.path.exists("kb_server/ui/templates/admin/shell.html")
```

**Test fixture pattern** (same file, lines 10–12):
```python
@pytest.fixture
def client():
    return TestClient(app)
```

**Test pattern for testing route response** (from same file, `TestCSP` pattern lines 27–35):
```python
def test_analytics_tab_returns_html(self, client):
    resp = client.get("/admin/tabs/analytics")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
```

**Additional test approaches** (from `test_query_analyzer.py` pattern):
- Test that `get_latency_stats()` returns expected structure
- Test empty database case
- Test with sample data in temp database

---

## Shared Patterns

### Tab Loading via HTMX
**Source:** `kb_server/ui/templates/admin/shell.html` (lines 89–92) — `switchTab()` JavaScript
```javascript
switchTab(tab) {
    this.activeTab = tab;
    var target = '/admin/tabs/' + tab;
    htmx.ajax('GET', target, { target: '#tab-content', swap: 'innerHTML' });
}
```
**Apply to:** Analytics tab is loaded identically — no changes needed to `switchTab()`, just add the sidebar entry with the correct tab name.

### Template Dispatcher
**Source:** `kb_server/ui/routes_admin.py` lines 31–48
**Pattern:** The existing `admin_tab_content` handler dispatches by `tab_name` via `template_map`. Adding the analytics entry to `template_map` is the primary integration point. **If the analytics tab needs computed data**, either:
1. Modify `admin_tab_content` to detect `tab_name == "analytics"` and inject extra context, OR
2. Add a dedicated `/admin/tabs/analytics` endpoint (like `admin_monitor_lights`) that calls `QueryAnalyzer` methods

### QueryAnalyzer Data Pattern
**Source:** `kb_server/analytics/query_analyzer.py`
**Pattern:** All methods follow the same pattern: open connection → execute SQL → fetch rows → close connection → return list of dicts.
- DB path resolved via env var: `QUERY_LOG_PATH` with default `data/kb_metadata.db`
- Error handling: bare `sqlite3.connect()` will raise on missing file — wrap in try/except in the route handler

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | | | All files have exact or role-match analogs in the codebase |

## Metadata

**Analog search scope:** `kb_server/analytics/`, `kb_server/ui/`, `kb_server/ui/templates/admin/`, `tests/`
**Files scanned:** 12
**Pattern extraction date:** 2026-06-15
