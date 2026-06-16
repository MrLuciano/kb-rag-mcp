# KB-RAG Web UI — 6-Pillar Visual Audit (Post-Fix Verification)

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured from `http://localhost:8001`
**Screenshots Dir:** `.planning/ui-reviews/20260616-012528-kb-rag/`
**Note:** Running server is serving stale code (started at 00:58, before latest commits). This audit evaluates the **code on disk** (the actual implementation), with screenshots from the running instance noted where they diverge.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Labels are clear; jargon remains in "RAGAS Evaluation" and "Chunks" |
| 2. Visuals | 3/4 | Clean Bootstrap layout, navbar emoji fixed; search results still lack context |
| 3. Color | 3/4 | Inline hex colors removed to CSS; status badge logic bug remains |
| 4. Typography | 3/4 | Good hierarchy, semantic headings; magic numbers persist in CSS |
| 5. Spacing | 4/4 | All inline styles removed; Bootstrap utilities used consistently |
| 6. Experience Design | 3/4 | XSS fixed, login fixed, loading states added; search result context missing |

**Overall: 19/24**

**Not production-ready.** The score improved from 18/24 to 19/24 after fixes, but the UI still has notable gaps (search result metadata, empty states, status badge logic) that should be resolved before shipping.

---

## Top 3 Priority Fixes

1. **Add document metadata to search results** — The `search_results.html` template shows only raw `result.text` with no document title, source file, or relevance score. Users cannot see which document a result came from or how relevant it is. **Fix:** Extend the template to display `result.title`, `result.source_file`, and `result.score` (if available) above the text snippet.

2. **Fix status badge logic in admin documents table** — `_documents_table.html:22` uses `bg-warning` for any status that is not `completed`. This means "error" documents appear yellow (warning) instead of red (danger), which is misleading. **Fix:** Change the ternary to a proper mapping: `completed` → `bg-success`, `error`/`failed` → `bg-danger`, `pending` → `bg-warning`.

3. **Add empty state to browse table** — `browse.html` renders an empty table with headers when no documents match the filters. There is no alert or message explaining the empty state to the user. **Fix:** Add an `{% if not documents %}<div class="alert alert-info">...</div>{% endif %}` block before the table.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- No generic labels like "Submit" or "Click Here"
- Action verbs used: "Search", "Filter", "Clear", "Run Evaluation", "View", "Back to Browse"
- Placeholders are descriptive and contextual: "How to install...", "e.g., ArchiveCenter", "e.g., 23.4", "Optional filter"
- Error messages are helpful: "Failed to load content. Please try again later.", "Network error. Please check your connection."
- Empty states are informative: "No documents found. Ingest documents to populate the knowledge base.", "No query data available for the last 7 days."
- Login form action now matches the actual route (`/auth/login` → `app.py:119`)
- **FIXED:** Navbar emoji removed; brand is now text-only "KB-RAG Web UI"

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| "RAGAS Evaluation" uses internal jargon | `admin/tab_ragas.html` | 1 | WARNING |
| "Golden dataset" is technical jargon | `admin/tab_ragas.html` | 9 | Minor |
| "Chunks" is technical for end users | `document.html` | 59 | Minor |
| "GDPR Art. 20" is overly specific legal reference | `admin/_profile_content.html` | 32 | Minor |
| Login page placeholders are generic | `admin/login.html` | 19, 23 | Minor |

---

### Pillar 2: Visuals (3/4)

**Strengths**
- Clean Bootstrap 5 layout with cards, tables, and responsive grid
- Navbar with active state highlighting and mobile hamburger menu
- Table with `table-striped table-hover` for readability
- Pagination with ellipsis truncation for large datasets
- Document detail page has clear metadata card and conditional alerts
- Mobile responsive: filters stack vertically, tables scroll horizontally
- **FIXED:** Admin sidebar emojis removed; labels are now text-only
- **FIXED:** Navbar emoji gear icon removed
- **FIXED:** Browse filter button now has loading state with spinner

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results show only raw text — no document title, score, or source | `search_results.html` | 10 | **WARNING** |
| Browse table has no empty state when filters return zero results | `browse.html` | 76-118 | WARNING |
| Login page is basic and unstyled beyond Bootstrap defaults | `admin/login.html` | N/A | Minor |
| Hash field shows "N/A" in `<code>` pink monospace, which is odd for a missing value | `document.html` | 36 | Minor |
| Search results list lacks top margin after the alert | `search_results.html` | 6 | Minor |

---

### Pillar 3: Color (3/4)

**Strengths**
- Bootstrap 5 semantic colors used throughout: `btn-primary`, `alert-success`, `alert-danger`, `badge bg-success`, `text-muted`
- **FIXED:** Inline `<style>` block with hardcoded hex colors removed from `base.html`; colors now live in `styles.css`
- Status colors now cover both naming conventions: `.status-completed/.status-ok` (green), `.status-failed/.status-error` (red), `.status-pending` (yellow)
- Score colors defined: high (green), medium (orange), low (grey)
- Monitor lights use semantic colors

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin documents table badge maps all non-completed statuses to `bg-warning` | `_documents_table.html` | 22 | **WARNING** |
| Hardcoded hex colors in `styles.css` (Bootstrap defaults) | `styles.css` | 34-39 | Minor |
| `border-success`/`border-danger` outline badges have lower contrast than filled badges | `tab_admin.html`, `tab_profile.html` | 4, 9 | Minor |

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
- Accessible `visually-hidden` headings for "Filters", "Results", "Search Results", and "Document Chunks" sections
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

### Pillar 5: Spacing (4/4)

**Strengths**
- **FIXED:** All inline `style` attributes removed from templates
- Bootstrap spacing utilities used consistently throughout: `mt-4`, `mb-3`, `mb-4`, `p-3`, `py-3`, `gap-2`, `gap-3`, `ms-2`
- CSS file is well-organized with semantic class names: `.chunk-preview`, `.admin-shell`, `.monitor-card`, `.monitoring-iframe`
- Consistent spacing between cards and sections
- No arbitrary spacing values in templates

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
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
- Confirmation dialogs: RAGAS evaluation (`hx-confirm`), API key revocation (`confirm()`), GDPR erasure (`confirm()`)
- Form validation: `required` attribute on query input, `min="1" max="20"` on top_k
- Auto-refresh: job status polls every 10s, monitor lights every 30s
- Pagination with filter persistence across pages
- Mobile responsive design
- HTMX partial updates for chunks, job status, monitor lights, analytics
- **FIXED:** `| safe` XSS filter removed from search results; newlines handled via CSS `white-space: pre-wrap`
- **FIXED:** Login form action now matches the actual route (`/auth/login`)
- **FIXED:** Admin sidebar emojis removed; labels are now text-only
- **FIXED:** Admin tab error handling improved with `htmx:responseError` and `htmx:beforeRequest` listeners
- **FIXED:** Browse filter button now has loading state with spinner

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results show only raw text — no document title, score, or source | `search_results.html` | 10 | **WARNING** |
| Browse table has no empty state when filters return zero results | `browse.html` | 76-118 | WARNING |
| Status filter "failed" doesn't match if database uses "error" | `browse.html` | 37-53 | WARNING |
| Document template checks `status == 'failed'` but database may use "error" | `document.html` | 41 | WARNING |
| Search loading indicator is in the left card, not near the results area | `search.html` | 73-80 | Minor |
| Admin tab error handler (`#tab-error`) may not show on all error types | `admin/shell.html` | 60-62 | Minor |

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

---

## Production Readiness

**Score: 19/24 — Not production-ready.**

The browse, search, and document pages are functional and visually acceptable. The following fixes from the previous audit have been applied:

1. ✅ **Fixed login form action mismatch** — `login.html` POSTs to `/auth/login` and `app.py:119` now defines the handler.
2. ✅ **Removed inline `<style>` hex colors** — Status colors moved from `base.html` to `styles.css`.
3. ✅ **Removed navbar emoji** — `base.html` brand is now text-only.
4. ✅ **Removed admin sidebar emojis** — Labels are now text-only: "Documents", "Monitoring", "Ingestion", "Evaluation", "Settings", "Analytics", "Profile".
5. ✅ **Fixed `| safe` XSS vulnerability** — Search results now use Jinja2 auto-escaping with CSS `white-space: pre-wrap`.
6. ✅ **Added `.status-ok` and `.status-error` CSS classes** — Status colors now cover both naming conventions.
7. ✅ **Improved admin tab error handling** — `htmx:responseError` and `htmx:beforeRequest` listeners now show/hide the `#tab-error` alert.
8. ✅ **Added browse filter loading state** — Filter button now shows a spinner during submission.

The following blockers must still be resolved before shipping:

1. **Add document metadata to search results** — The search results page must show document title, source file, and score/relevance.
2. **Fix status badge logic in admin documents table** — Map "error" to `bg-danger`, not `bg-warning`.
3. **Add empty state to browse table** — Show an informative alert when no documents match the filters.
4. **Normalize status values** across the database, CSS, templates, and filters. Ensure `browse.html`, `document.html`, and `_documents_table.html` use the same status vocabulary.

After these fixes, the UI would score approximately **22/24** (production-ready).

---

## Screenshots Captured

| Screenshot | Resolution | Notes |
|------------|------------|-------|
| `desktop.png` | 1440x900 | Browse page (redirected from `/`) — **stale code** |
| `search.png` | 1440x900 | Search Tester page — **stale code** |
| `document.png` | 1440x900 | Document Details page — **stale code** |
| `admin.png` | 1440x900 | **404 JSON error** — server running stale code |
| `login.png` | 1440x900 | **404 JSON error** — server running stale code |
| `error.png` | 1440x900 | **404 JSON error** — server running stale code |
| `mobile-browse.png` | 375x812 | Mobile browse — responsive layout works |
| `mobile-admin.png` | 375x812 | **404 JSON error** — server running stale code |

**Note:** All screenshots reflect the running server which is serving stale code from before the latest commits. The actual code on disk includes the fixes described above. A server restart is required for the admin routes, login page, and exception handlers to be accessible.

---

## Change Log from Previous Audit

| Issue | Previous Audit | Current State | Status |
|-------|---------------|---------------|--------|
| `| safe` XSS in search results | WARNING | Fixed | ✅ |
| Missing `.status-ok` CSS class | WARNING | Fixed | ✅ |
| Admin sidebar emojis | WARNING | Fixed | ✅ |
| Navbar emoji in base.html | WARNING | Fixed | ✅ |
| Admin tab error handling | Minor | Improved | ✅ |
| Browse filter loading state | N/A | Added | ✅ |
| Login form action mismatch | WARNING | Fixed | ✅ |
| Hardcoded hex colors in inline style | WARNING | Fixed | ✅ |
| Status terminology mismatch | WARNING | Still present | ⚠️ |
| Magic numbers in CSS | Minor | Still present | ⚠️ |
| Search results lack metadata | WARNING | Still present | ⚠️ |
| Browse table empty state | N/A | Still missing | ⚠️ |
| Admin documents badge logic | WARNING | Still present | ⚠️ |
| Admin routes 404 at runtime | BLOCKER | Code fixed, server stale | ⚠️ |

**Score Change:** 18/24 → **19/24** (+1 point from spacing improvements and login fix).
