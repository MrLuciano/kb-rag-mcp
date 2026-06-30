# Phase 43: Chunk Preview in Document Detail — Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 4 (2 modified, 1 new template partial, 1 test extension)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `kb_server/ui/routes.py` (modify) | controller/route | request-response | `kb_server/ui/routes_admin.py:135-162` — delete_document (VectorStore in route) | role-match |
| `kb_server/ui/templates/document.html` (modify) | template/component | request-response | `kb_server/ui/templates/admin/tab_analytics.html` — HTMX refresh partial | role-match |
| `kb_server/ui/templates/document_chunks.html` (new) | template/partial | request-response | `kb_server/ui/templates/admin/_config_table.html` — Admin HTMX partial | role-match |
| `tests/test_ui_routes.py` (modify) | test | request-response | `tests/test_ui_routes.py` — existing UI test patterns | exact |

## Pattern Assignments

### `kb_server/ui/routes.py` — Extend `document_detail` handler (controller, request-response)

**Analog:** `kb_server/ui/routes_admin.py:135-162` — delete_document handler  
**Also analog:** `kb_server/vector_store.py:607-670` — `get_chunk_with_context` for scroll-by-source_file pattern

**Imports pattern** (routes_admin.py:145), lazy import inside handler:
```python
from kb_server.vector_store import VectorStore

store = VectorStore()
await store.connect()
try:
    await store.delete_document(source_file)
finally:
    await store.close()
```

**Scroll-by-source_file pattern** (vector_store.py:645-657), to fetch all chunks:
```python
neighbors, _ = await self.client.scroll(
    collection_name=self.collection,
    scroll_filter=Filter(
        must=[
            FieldCondition(
                key="source_file", match=MatchValue(value=source_file)
            )
        ]
    ),
    limit=context_window * 2 + 10,
    with_payload=True,
    with_vectors=False,
)
```

**Chunk payload extraction pattern** (vector_store.py:659-668):
```python
chunks = [
    {
        "chunk_id": str(n.id),
        "text": n.payload.get("text", ""),
        "source_file": n.payload.get("source_file", ""),
        "chunk_index": int(n.payload.get("chunk_index", 0)),
    }
    for n in neighbors
]
```

**Existing document_detail handler pattern** (routes.py:187-212) — template context pattern:
```python
@app.get("/ui/document/{doc_id}", response_class=HTMLResponse)
async def document_detail(request: Request, doc_id: int):
    """Document detail page showing metadata and chunks."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, * FROM files WHERE rowid = ?", (doc_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return templates.TemplateResponse(
            request, "error.html",
            {"request": request, "error": "Document not found"},
            status_code=404,
        )
    document = _map_document(row)
    conn.close()
    return templates.TemplateResponse(
        request, "document.html",
        {"request": request, "document": document}
    )
```

**Search query param pattern** — add `q` query parameter (routes.py:187-212 style):
```python
from fastapi import Request, Query

async def document_detail(
    request: Request,
    doc_id: int,
    q: Optional[str] = Query(None),  # search term highlighting
):
```

**Error handling pattern for Qdrant** — graceful degradation (routes_admin.py:71-75):
```python
except Exception as e:
    log.error("Failed to load analytics data: %s", e)
    context["popular_queries"] = []
    context["content_gaps"] = []
    context["latency_stats"] = []
```

---

### `kb_server/ui/templates/document.html` — Add chunk accordion (template, request-response)

**Analog:** `kb_server/ui/templates/admin/tab_analytics.html` — HTMX partial loading pattern  
**Also analog:** `kb_server/ui/templates/browse.html` — page structure, conditionals, `{% %}` control flow

**Block structure pattern** (all templates extend `base.html`):
```html
{% extends "base.html" %}
{% block title %}...{% endblock %}
{% block content %}
...page content...
{% endblock %}
{% block extra_scripts %}
...page-specific JS...
{% endblock %}
```

**Bootstrap 5 accordion markup** — existing bootstrap pattern in project (base.html includes bootstrap 5 JS/CSS):
```html
<div class="accordion" id="chunksAccordion">
  {% for chunk in chunks %}
  <div class="accordion-item">
    <h2 class="accordion-header" id="heading-{{ loop.index }}">
      <button class="accordion-button {% if loop.index > 10 %}collapsed{% endif %}"
              type="button" data-bs-toggle="collapse"
              data-bs-target="#collapse-{{ loop.index }}"
              aria-expanded="{% if loop.index <= 10 %}true{% else %}false{% endif %}">
        Chunk {{ chunk.chunk_index }}
      </button>
    </h2>
    <div id="collapse-{{ loop.index }}"
         class="accordion-collapse collapse {% if loop.index <= 10 %}show{% endif %}"
         aria-labelledby="heading-{{ loop.index }}"
         data-bs-parent="#chunksAccordion">
      <div class="accordion-body">
        <pre class="mb-0" style="white-space: pre-wrap;">{{ chunk.text }}</pre>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
```

**Conditional alert pattern** (document.html:52-73):
```html
{% elif document.chunks_stored == 0 %}
<div class="alert alert-warning">
    <strong>No Chunks Stored</strong>
    <p class="mb-0">This document has no searchable chunks yet.</p>
</div>
```

**`<mark>` tag highlighting** — server-side search term wrapping (Jinja2 filter or template function). Pattern for registering a template function (app.py:50-52):
```python
templates.env.globals["get_nonce"] = lambda request: getattr(
    request.state, "nonce", ""
)
```
The `highlight_term` function should follow same `env.globals` registration in `app.py`.

---

### `kb_server/ui/templates/document_chunks.html` (new) — HTMX partial for progressive chunk reveal

**Analog:** `kb_server/ui/templates/admin/_config_table.html` — HTMX partial loaded on demand  
**Also analog:** `kb_server/ui/templates/admin/tab_analytics.html` — HTMX refresh button pattern

**HTMX partial pattern** — standalone fragment (no `{% extends %}`), just HTML:
```html
<!-- tab_analytics.html is a full template, but HTMX partials like _config_table.html are fragments -->
<h3>Query Analytics</h3>
<p class="text-muted">Query log analysis for the last 7 days.</p>
...
```

**HTMX "Show More" button pattern** (analytics tab:4-9):
```html
<button class="btn btn-sm btn-outline-secondary mb-3"
        hx-get="/ui/document/{{ doc_id }}/chunks?offset={{ offset }}"
        hx-target="#chunks-container"
        hx-swap="beforeend">
    Show next 10 chunks
</button>
```

---

### `tests/test_ui_routes.py` — Chunk preview tests (test, request-response)

**Analog:** `tests/test_ui_routes.py:207-228` — Existing `test_document_detail_*` tests

**Mock pattern for document detail** (test_ui_routes.py:207-228):
```python
def test_document_detail_found_returns_200(self):
    fake = _fake_row(doc_id=42)
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fake
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("sqlite3.connect", return_value=mock_conn), \
            _mock_template_response():
        resp = client.get("/ui/document/42")
    assert resp.status_code == 200
```

**Mock pattern for TemplateResponse** (test_ui_routes.py:148-155):
```python
def _mock_template_response():
    return patch(
        "kb_server.ui.routes.templates.TemplateResponse",
        side_effect=lambda request, name, ctx, status_code=200, **kw: _html_response(
            f"<html>{name}</html>", status_code=status_code
        ),
    )
```

**Pattern for mocking VectorStore** — use same lazy import + mock approach (adapt from test patterns in test_vector_store_unit.py style):
```python
with patch("kb_server.vector_store.VectorStore") as mock_vs_class:
    mock_store = MagicMock()
    mock_vs_class.return_value = mock_store
    # mock_store.scroll.return_value = ...
```

---

## Shared Patterns

### Qdrant Scroll for Chunks by Source File
**Source:** `kb_server/vector_store.py:607-670` — `get_chunk_with_context`  
**Also source:** `kb_server/vector_store.py:500-603` — `list_documents`  
**Apply to:** `kb_server/ui/routes.py` — document_detail handler
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

chunks = []
offset = None
while True:
    results, offset = await store.client.scroll(
        collection_name=store.collection,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="source_file", match=MatchValue(value=source_file)
                )
            ]
        ),
        limit=500,
        offset=offset,
        with_payload=True,
        with_vectors=False,
    )
    for r in results:
        chunks.append({
            "chunk_id": str(r.id),
            "text": r.payload.get("text", ""),
            "chunk_index": int(r.payload.get("chunk_index", 0)),
        })
    if offset is None:
        break
chunks.sort(key=lambda c: c["chunk_index"])
```

### Google-style Docstrings
**Source:** project conventions  
**Apply to:** All Python code
```python
def my_function(param1: str, param2: Optional[int] = None) -> dict:
    """Short description.

    Longer description of what this does.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        SomeException: When something goes wrong.
    """
```

### Lazy VectorStore Import + Connect Pattern
**Source:** `kb_server/ui/routes_admin.py:135-162` — delete_document  
**Apply to:** `kb_server/ui/routes.py` — document_detail handler
```python
from kb_server.vector_store import VectorStore

store = VectorStore()
await store.connect()
try:
    # ... use store ...
finally:
    await store.close()
```

### Jinja2 Template Function Registration
**Source:** `kb_server/ui/app.py:50-52`  
**Apply to:** Register `highlight_term` as a template global
```python
templates.env.globals["highlight_term"] = lambda text, query: (
    re.sub(f'({re.escape(query)})', r'<mark>\1</mark>', text, flags=re.IGNORECASE)
    if query else text
)
```

### Logging Pattern
**Source:** CONVENTIONS.md  
**Apply to:** All Python modules
```python
import logging
log = logging.getLogger(__name__)
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All files have close analogs |

## Metadata

**Analog search scope:** `kb_server/ui/`, `kb_server/`, `tests/`, `kb_server/ui/templates/`
**Files scanned:** 10+
**Pattern extraction date:** 2026-06-15
