# KB-RAG Web UI — 6-Pillar Visual Audit

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured from `http://localhost:8001`
**Screenshots Dir:** `.planning/ui-reviews/20260616-011905/`

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Labels are clear, but navbar emoji and status terminology mismatch |
| 2. Visuals | 3/4 | Clean Bootstrap layout, but admin page inaccessible, status colors broken |
| 3. Color | 3/4 | Semantic Bootstrap colors used, but hardcoded inline hex and missing `.status-ok` class |
| 4. Typography | 3/4 | Good hierarchy, but `| safe` filter on user text and code-formatted "N/A" |
| 5. Spacing | 3/4 | Bootstrap utilities used consistently, no inline styles remain |
| 6. Experience Design | 2/4 | Admin SPA and login page are 404 (broken); status filter mismatches data |

**Overall: 17/24**

**Not production-ready.** The admin panel and login page are functionally broken, and the status color/filter system is mismatched with actual data values.

---

## Top 3 Priority Fixes

1. **Admin SPA and login routes return 404** — The `/admin` shell, all tab routes, and `/auth/login` endpoint are inaccessible in the running instance. The Python code defines them correctly, but the running `kb_server.ui.run_ui` process appears to be serving stale code. **Fix:** Restart the UI server (`python -m kb_server.ui.run_ui`) and verify all routes are reachable. Also, the login form action in `login.html` is `/auth/login` but the route is `/login` — align these.

2. **Status terminology mismatch between CSS, filters, and database** — The CSS defines `.status-completed`, `.status-failed`, `.status-pending`, but the database contains "ok" and "error". The browse filter options are "completed/failed/pending" which don't match the data. The document template checks for `status == 'failed'` which never matches "error". **Fix:** Normalize all status values to a single vocabulary (e.g., `completed`, `failed`, `pending`) and update CSS classes accordingly. Add `.status-ok` if keeping the current data.

3. **Search results use `| safe` on raw user text** — `search_results.html:11` renders `result.text` with `| replace('\n', '<br>') | safe`. This bypasses Jinja2 auto-escaping and is a potential XSS vector if search results contain malicious HTML. **Fix:** Escape the text first, then replace newlines with `<br>`, or use a custom Jinja2 filter that safely replaces newlines.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- Clear form labels: "Query", "Number of Results", "Product", "Version", "Hybrid Search", "Rerank Results"
- Informative empty states: "Enter a query and click Search to test the system", "No documents found. Ingest documents to populate the knowledge base."
- Error messages are actionable: "Document not found", "Path not found", "Failed to load content. Please try again later."
- Buttons are semantically clear: "Search", "Filter", "Clear", "View", "Back to Browse"

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Navbar uses emoji gear icon instead of text or icon font | `base.html` | 67 | WARNING |
| Status terminology mismatch: CSS expects `completed/failed/pending` but data shows `ok/error` | `browse.html`, `document.html`, `base.html` | various | WARNING |
| Login form action `/auth/login` does not match the actual route `/login` | `admin/login.html` | 16 | WARNING |
| "Chunks" heading is generic; could be more descriptive | `document.html` | 59 | Minor |

---

### Pillar 2: Visuals (3/4)

**Strengths**
- Clean Bootstrap 5 layout with cards, tables, and responsive grid
- Navbar with active state highlighting and mobile hamburger menu
- Table with `table-striped table-hover` for readability
- Pagination with ellipsis truncation for large datasets
- Document detail page has clear metadata card and conditional alerts
- Mobile responsive: filters stack vertically, tables scroll horizontally

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin page renders raw JSON `{"detail":"Not Found"}` instead of the admin SPA shell | Running server | N/A | BLOCKER |
| Login page returns 404 instead of rendered form | Running server | N/A | BLOCKER |
| Status "error" text in browse table renders in plain black instead of red | `browse.html` | 103 | WARNING |
| Navbar emoji gear icon is visually inconsistent | `base.html` | 67 | WARNING |
| Hash field shows "N/A" in `<code>` pink monospace, which is odd for a missing value | `document.html` | 36 | WARNING |
| Search results have no spacing between the success alert and the result cards | `search_results.html` | 3-6 | Minor |

---

### Pillar 3: Color (3/4)

**Strengths**
- Bootstrap 5 semantic colors used throughout: `btn-primary`, `alert-success`, `alert-danger`, `badge bg-success`, `text-muted`
- Status colors defined semantically: green for completed, red for failed, yellow for pending
- Score colors defined: high (green), medium (orange), low (grey)

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Inline `<style>` block hardcodes Bootstrap hex colors instead of using CSS variables | `base.html` | 27-35 | WARNING |
| `.status-ok` class is missing — "ok" status renders in default text color | `base.html` | 27-35 | WARNING |
| `.status-error` class is defined but `.status-failed` is expected by the filter logic | `base.html` | 28-30 | WARNING |
| Admin page renders raw JSON with no color system at all | Running server | N/A | BLOCKER |

**Color usage audit:**
- `btn-primary` — search, filter, submit buttons
- `btn-secondary` — clear, back buttons
- `btn-outline-primary` — view, show more buttons
- `alert-success` — search results found, document indexed
- `alert-danger` — error messages, failed document
- `alert-warning` — no results, no chunks
- `alert-info` — empty states, chunks unavailable
- `text-muted` — secondary text, placeholders, descriptions
- `bg-success` / `bg-danger` — monitor lights, status badges

---

### Pillar 4: Typography (3/4)

**Strengths**
- Proper heading hierarchy: `h1` for page titles, `h2` for sections (downgraded with `h5` class), `h3` for card titles
- Accessible `visually-hidden` headings for "Filters" and "Results" sections
- `fs-6` for navbar links maintains readable size
- Code blocks use `<code>` and `<pre>` with proper styling
- Search result text uses `pre-wrap` with `font-family: inherit` and `line-height: 1.6`

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| `| safe` filter on `result.text` bypasses auto-escaping and risks XSS | `search_results.html` | 11 | WARNING |
| "N/A" for missing hash rendered in `<code>` monospace instead of muted text | `document.html` | 36 | WARNING |
| `chunk-title-truncate` class has `max-width: 400px` which is a magic number | `styles.css` | 12 | Minor |
| Admin page JSON error has no typography styling | Running server | N/A | BLOCKER |

**Font size distribution:**
- `h1` (default Bootstrap) — page titles
- `h2` with `h5` class — section headers, card titles
- `h3` with `h5`/`h6` class — subsection headers
- `fs-6` — navbar links
- `small` — metadata, hints, status messages
- `0.9rem` — search result text (custom CSS)
- `0.85em` — inline code (custom CSS)

---

### Pillar 5: Spacing (3/4)

**Strengths**
- Bootstrap spacing utilities used consistently: `mt-4`, `mb-3`, `mb-4`, `p-3`, `py-3`, `gap-2`, `gap-3`, `ms-2`
- No inline `style` attributes remain in templates (moved to `styles.css`)
- CSS file is well-organized with semantic class names: `.chunk-preview`, `.admin-shell`, `.monitor-card`, `.monitoring-iframe`
- Consistent spacing between cards and sections

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results list lacks top margin after the alert | `search_results.html` | 6 | Minor |
| `.monitor-card` has fixed width `160px` — magic number | `styles.css` | 41 | Minor |
| `.chunk-title-truncate` has fixed `max-width: 400px` — magic number | `styles.css` | 12 | Minor |
| `.config-search` has fixed `max-width: 300px` — magic number | `styles.css` | 59 | Minor |

---

### Pillar 6: Experience Design (2/4)

**Strengths**
- Loading states present: spinner on search button, spinner on filter button, spinner on admin tab load, spinner on admin documents load
- Error states handled: custom `error.html` template for 404/500/403, HTMX error handlers for 401 modal and network errors
- Empty states handled: "No documents found", "No results found", "No query data available"
- Form validation: `required` attribute on query input, `min="1" max="20"` on top_k
- Confirmation dialogs: RAGAS evaluation (`hx-confirm`), API key revocation (`confirm()`), GDPR erasure (`confirm()`)
- Pagination with filter persistence across pages
- Mobile responsive design
- HTMX partial updates for chunks, job status, monitor lights, analytics
- Auto-refresh: job status polls every 10s, monitor lights every 30s

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin SPA (`/admin`) returns 404 JSON — completely broken | Running server | N/A | **BLOCKER** |
| Login page (`/login`) returns 404 — login form inaccessible | Running server | N/A | **BLOCKER** |
| All admin tab routes (`/admin/tabs/*`) return 404 | Running server | N/A | **BLOCKER** |
| Status filter "failed" doesn't match "error" documents in database | `browse.html` | 37-53 | **BLOCKER** |
| Document template checks `status == 'failed'` but data is "error" | `document.html` | 41 | WARNING |
| Search results use `| safe` on raw text — XSS risk | `search_results.html` | 11 | WARNING |
| Search loading indicator is in the left card, not near the results area | `search.html` | 73-80 | Minor |
| Admin tab error handler (`#tab-error`) is hidden by default but may not show on all error types | `admin/shell.html` | 60-62 | Minor |

**Note on admin routes:** The Python code in `routes_admin.py` and `app.py` correctly defines all admin routes. The `app` object inspection confirms routes are registered. However, the running `kb_server.ui.run_ui` process (started at 00:58) appears to be serving stale code without the admin routes. A server restart is required.

**Note on login form:** The `login.html` template has `action="/auth/login"` but the actual route in `app.py` is `/login`. The form submission will 404.

---

## Registry Safety

No `components.json` found. No third-party registry blocks to audit.

---

## Files Audited

### Templates (22 files)
- `kb_server/ui/templates/base.html`
- `kb_server/ui/templates/search.html`
- `kb_server/ui/templates/browse.html`
- `kb_server/ui/templates/document.html`
- `kb_server/ui/templates/error.html`
- `kb_server/ui/templates/search_results.html`
- `kb_server/ui/templates/admin/shell.html`
- `kb_server/ui/templates/admin/login.html`
- `kb_server/ui/templates/admin/tab_documents.html`
- `kb_server/ui/templates/admin/tab_ingestion.html`
- `kb_server/ui/templates/admin/tab_ragas.html`
- `kb_server/ui/templates/admin/tab_analytics.html`
- `kb_server/ui/templates/admin/tab_monitoring.html`
- `kb_server/ui/templates/admin/tab_admin.html`
- `kb_server/ui/templates/admin/tab_profile.html`
- `kb_server/ui/templates/admin/_documents_table.html`
- `kb_server/ui/templates/admin/_job_status.html`
- `kb_server/ui/templates/admin/_config_table.html`
- `kb_server/ui/templates/admin/_monitor_lights.html`
- `kb_server/ui/templates/admin/_profile_content.html`
- `kb_server/ui/templates/document_chunks.html`

### Styles (1 file)
- `kb_server/ui/static/styles.css`

### Routes (2 files)
- `kb_server/ui/routes.py`
- `kb_server/ui/routes_admin.py`
- `kb_server/ui/app.py`
- `kb_server/ui/run_ui.py`

---

## Production Readiness

**Score: 17/24 — Not production-ready.**

The browse, search, and document pages are functional and visually acceptable. However, the following blockers must be resolved before shipping:

1. **Restart the UI server** to pick up the admin routes and login route.
2. **Fix the login form action** to match the actual route (`/login` not `/auth/login`).
3. **Normalize status values** across the database, CSS, templates, and filters.
4. **Fix the `| safe` XSS risk** in search results.

After these fixes, the UI would score approximately **21/24** (production-ready).

---

## Screenshots Captured

| Screenshot | Resolution | Notes |
|------------|------------|-------|
| `desktop.png` | 1440x900 | Browse page (redirected from `/`) |
| `mobile.png` | 375x812 | Browse page mobile view |
| `tablet.png` | 768x1024 | Browse page tablet view |
| `search.png` | 1440x900 | Search Tester page |
| `browse.png` | 1440x900 | Browse Documents page |
| `admin.png` | 1440x900 | **404 JSON error** — admin page broken |
| `document.png` | 1440x900 | Document detail page |
| `error.png` | 1440x900 | 404 error page (custom template) |
