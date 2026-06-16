# KB-RAG Web UI — 6-Pillar Visual Audit (Current State)

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured from `http://localhost:8001`
**Screenshots Dir:** `.planning/ui-reviews/20260616-012304/`
**Note:** Running server is serving stale code (started at 00:58, before latest commits at 01:21). This audit evaluates the code on disk, not the running instance.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Labels are clear, but navbar emoji and login form action mismatch remain |
| 2. Visuals | 3/4 | Clean Bootstrap layout, but navbar emoji and basic login page persist |
| 3. Color | 3/4 | Semantic Bootstrap colors used, hardcoded hex colors remain in inline style |
| 4. Typography | 3/4 | Good hierarchy, magic numbers in CSS persist |
| 5. Spacing | 3/4 | Bootstrap utilities used consistently, magic numbers in CSS remain |
| 6. Experience Design | 3/4 | XSS fixed, admin routes defined in code, but login form and status mismatch remain |

**Overall: 18/24**

**Not production-ready.** The browse, search, and document pages are functional and visually acceptable. The `| safe` XSS vulnerability has been fixed, and the admin sidebar emojis have been removed. However, the login form action is still mismatched, and the status terminology inconsistency persists across templates and filters.

---

## Top 3 Priority Fixes

1. **Fix login form action mismatch** — The `login.html` template POSTs to `/auth/login` but there is no route handler for this endpoint in the UI app. The `app.py` defines a `/login` GET route but no POST handler. The auth router (`kb_server.auth.router`) is not included in the UI FastAPI app. **Fix:** Either change the form action to `/login` and add a POST handler, or include the auth router in `app.py` and align the endpoint path.

2. **Normalize status terminology across templates and filters** — The CSS now covers both `.status-completed/.status-ok` and `.status-failed/.status-error`, but the browse filter (`browse.html:37-53`) only offers "completed/failed/pending" options. The document template (`document.html:41`) checks `status == 'failed'`. The admin documents table (`_documents_table.html:22`) only handles `completed` vs everything else. If the database uses "ok" or "error", these filters and conditional blocks will fail silently. **Fix:** Standardize on a single vocabulary throughout the UI and ensure all templates, filters, and CSS classes use the same status values.

3. **Remove hardcoded hex colors from inline `<style>` block** — `base.html:27-35` hardcodes Bootstrap hex colors (`#198754`, `#dc3545`, `#ffc107`, `#fd7e14`, `#6c757d`). These should use Bootstrap CSS variables (e.g., `var(--bs-success)`, `var(--bs-danger)`) or be moved to the external stylesheet. **Fix:** Replace inline hex colors with Bootstrap CSS variables or move the status color rules to `styles.css`.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- Clear form labels: "Query", "Number of Results", "Product", "Version", "Hybrid Search", "Rerank Results"
- Admin sidebar labels are clean and emoji-free: "Documents", "Monitoring", "Ingestion", "Evaluation", "Settings", "Analytics", "Profile"
- Informative empty states: "Enter a query and click Search to test the system", "No documents found. Ingest documents to populate the knowledge base."
- Error messages are actionable: "Failed to load content. Please try again later.", "Network error. Please check your connection."
- Buttons are semantically clear: "Search", "Filter", "Clear", "View", "Back to Browse"

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Navbar uses emoji gear icon (`⚙`) instead of text or icon font | `base.html` | 66 | WARNING |
| Login form action `/auth/login` does not match any registered route | `admin/login.html` | 16 | WARNING |
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
- Admin sidebar emojis removed in latest fix

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Navbar emoji gear icon is visually inconsistent | `base.html` | 66 | WARNING |
| Login page is basic and unstyled beyond Bootstrap defaults | `admin/login.html` | N/A | Minor |
| Hash field shows "N/A" in `<code>` pink monospace, which is odd for a missing value | `document.html` | 36 | WARNING |
| Search results have minimal spacing between the success alert and the result cards | `search_results.html` | 3-6 | Minor |

---

### Pillar 3: Color (3/4)

**Strengths**
- Bootstrap 5 semantic colors used throughout: `btn-primary`, `alert-success`, `alert-danger`, `badge bg-success`, `text-muted`
- Status colors now cover both naming conventions: `.status-completed/.status-ok` (green), `.status-failed/.status-error` (red), `.status-pending` (yellow)
- Score colors defined: high (green), medium (orange), low (grey)
- Monitor lights use semantic colors

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Inline `<style>` block hardcodes Bootstrap hex colors instead of using CSS variables | `base.html` | 27-35 | WARNING |
| Admin documents table badge only handles `completed` vs `warning` — "error" status gets `bg-warning` | `_documents_table.html` | 22 | WARNING |

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
- Accessible `visually-hidden` headings for "Filters", "Results", and "Search Results" sections
- `fs-6` for navbar links maintains readable size
- Code blocks use `<code>` and `<pre>` with proper styling
- Search result text uses `pre-wrap` with `font-family: inherit` and `line-height: 1.6`

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| "N/A" for missing hash rendered in `<code>` monospace instead of muted text | `document.html` | 36 | WARNING |
| `chunk-title-truncate` class has `max-width: 400px` which is a magic number | `styles.css` | 12 | Minor |

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
- Bootstrap spacing utilities used consistently throughout: `mt-4`, `mb-3`, `mb-4`, `p-3`, `py-3`, `gap-2`, `gap-3`, `ms-2`
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
| `.admin-sidebar` has fixed `width: 220px` — magic number | `styles.css` | 22 | Minor |
| `.monitoring-iframe` has fixed `height: 600px` — magic number | `styles.css` | 29 | Minor |

---

### Pillar 6: Experience Design (3/4)

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
- **FIXED:** `| safe` XSS filter removed from search results; newlines handled via CSS `white-space: pre-wrap`
- **FIXED:** Admin sidebar emojis removed; labels are now text-only
- **FIXED:** Admin shell tab error handler improved with `htmx:responseError` and `htmx:beforeRequest` listeners
- **FIXED:** Browse filter button now has loading state with spinner

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Login form POSTs to `/auth/login` which has no route handler in the UI app | `admin/login.html` | 16 | **WARNING** |
| Auth router (`kb_server.auth.router`) is not included in `app.py` | `app.py` | N/A | **WARNING** |
| Status filter "failed" doesn't match if database uses "error" documents | `browse.html` | 37-53 | **WARNING** |
| Document template checks `status == 'failed'` but database may use "error" | `document.html` | 41 | WARNING |
| Search loading indicator is in the left card, not near the results area | `search.html` | 73-80 | Minor |
| Admin tab error handler (`#tab-error`) may not show on all error types | `admin/shell.html` | 60-62 | Minor |

**Note on admin routes:** The Python code in `routes_admin.py` and `app.py` correctly defines all admin routes (`/admin`, `/admin/tabs/*`, `/api/v1/*`). The `app` object includes both `routes_admin.router` and `routes_admin.api_router`. However, the running `kb_server.ui.run_ui` process (started at 00:58) is serving stale code from before the latest commits (01:21). A server restart is required for the routes to be accessible.

**Note on login form:** The `login.html` template has `action="/auth/login"` but there is no POST handler for this path in the UI app. The `app.py` defines a GET `/login` route that renders the page, but the form submission will 404. The auth router (`kb_server.auth.router`) is not included in the UI FastAPI app.

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

### Routes (4 files)
- `kb_server/ui/routes.py`
- `kb_server/ui/routes_admin.py`
- `kb_server/ui/app.py`
- `kb_server/ui/run_ui.py`

### Auth (1 file)
- `kb_server/auth/router.py`

---

## Production Readiness

**Score: 18/24 — Not production-ready.**

The browse, search, and document pages are functional and visually acceptable. The following fixes from the previous audit have been applied:

1. ✅ **Removed `| safe` XSS filter** — Search results now use Jinja2 auto-escaping with CSS `white-space: pre-wrap` for newline handling.
2. ✅ **Added `.status-ok` and `.status-error` CSS classes** — Status colors now cover both naming conventions.
3. ✅ **Removed admin sidebar emojis** — Labels are now text-only: "Documents", "Monitoring", "Ingestion", "Evaluation", "Settings", "Analytics", "Profile".
4. ✅ **Improved admin tab error handling** — `htmx:responseError` and `htmx:beforeRequest` listeners now show/hide the `#tab-error` alert.
5. ✅ **Added browse filter loading state** — Filter button now shows a spinner during submission.

The following blockers must still be resolved before shipping:

1. **Fix the login form action** — The form submits to `/auth/login` but no handler exists. Either align the action with the actual route or add a POST handler.
2. **Normalize status values** across the database, CSS, templates, and filters. Ensure `browse.html`, `document.html`, and `_documents_table.html` use the same status vocabulary as the CSS and the database.
3. **Move hardcoded hex colors** from the inline `<style>` block in `base.html` to the external stylesheet or use Bootstrap CSS variables.

After these fixes, the UI would score approximately **21/24** (production-ready).

---

## Screenshots Captured

| Screenshot | Resolution | Notes |
|------------|------------|-------|
| `desktop.png` | 1440x900 | Browse page (redirected from `/`) — **stale code** |
| `search.png` | 1440x900 | Search Tester page — **stale code** |
| `browse.png` | 1440x900 | Browse Documents page — **stale code** |
| `admin.png` | 1440x900 | **404 JSON error** — server running stale code |
| `login.png` | 1440x900 | Login page — **stale code** |

**Note:** All screenshots reflect the running server which is serving stale code from before the latest commits. The actual code on disk includes the fixes described above.

---

## Change Log from Previous Audit

| Issue | Previous Audit | Current State | Status |
|-------|---------------|---------------|--------|
| `| safe` XSS in search results | WARNING | Fixed | ✅ |
| Missing `.status-ok` CSS class | WARNING | Fixed | ✅ |
| Admin sidebar emojis | WARNING | Fixed | ✅ |
| Admin tab error handling | Minor | Improved | ✅ |
| Browse filter loading state | N/A | Added | ✅ |
| Navbar emoji in base.html | WARNING | Still present | ⚠️ |
| Login form action mismatch | WARNING | Still present | ⚠️ |
| Hardcoded hex colors | WARNING | Still present | ⚠️ |
| Status terminology mismatch | WARNING | Still present | ⚠️ |
| Magic numbers in CSS | Minor | Still present | ⚠️ |
| Admin routes 404 at runtime | BLOCKER | Code fixed, server stale | ⚠️ |
