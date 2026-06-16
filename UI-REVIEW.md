# KB-RAG Web UI — 6-Pillar Visual Audit

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured at `.planning/ui-reviews/20260616-audit-010917/`
**Previous Audit:** 17/24 (20 issues)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Minor casing and pluralization inconsistencies remain |
| 2. Visuals | 2/4 | Search results render as a single card with raw markdown in `<pre>` — poor UX |
| 3. Color | 3/4 | Bootstrap semantic colors used well; hardcoded hex block remains in base.html |
| 4. Typography | 3/4 | Heading hierarchy substantially fixed; one minor visual skip in profile tab |
| 5. Spacing | 4/4 | All inline styles removed; Bootstrap spacing is consistent throughout |
| 6. Experience Design | 2/4 | Search results are broken due to data format mismatch; no HTMX timeout handling |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Search results render as a single card with raw markdown text in a `<pre>` block** — The `search_results.html` template iterates over `results` expecting individual chunk objects, but `_search_kb()` returns a `list[types.TextContent]` where `results[0].text` is a single markdown-formatted string containing ALL results. The template renders ONE card with the entire markdown inside `<pre>` tags. This is a **BLOCKER** for the primary search feature. Fix: either return raw chunk dicts from the route for HTML rendering, or parse the markdown into individual results in the template.

2. **No HTMX timeout handling — long requests will hang silently** — HTMX requests have no timeout configured. If the embedding backend or Qdrant is slow, the search button will show a spinner indefinitely with no feedback. Fix: add `hx-timeout="30000"` to the search form and configure `htmx:timeout` event handlers to show a user-friendly timeout message.

3. **Hardcoded hex colors in base.html `<style>` block** — The status and score color classes in `base.html:28-34` use raw hex values (`#198754`, `#dc3545`, `#ffc107`, `#fd7e14`, `#6c757d`) instead of Bootstrap CSS variables (`var(--bs-success)`, `var(--bs-danger)`, etc.) or utility classes. This prevents dark mode support and creates a maintenance burden. Fix: replace with Bootstrap CSS custom properties or utility classes.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths:**
- Empty states are informative and actionable:
  - `_documents_table.html:35`: "No documents found. Ingest documents to populate the knowledge base."
  - `tab_analytics.html:14`: "No query data available for the last 7 days. Query data appears after users search the knowledge base."
  - `document.html:103`: "Chunk data could not be loaded from the vector store."
- Form labels are descriptive and include placeholders with examples.
- Button labels are semantically clear ("Filter", "Clear", "Search", "View", "Back to Browse").
- HTMX confirm dialogs provide context: `tab_ragas.html:16` — "Run evaluation? This may take several minutes."
- `document_chunks.html:33`: "Show next 10 chunks (X remaining)" — clear pagination copy.

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Inconsistent casing: login button says "Log in" but logout says "Log out" | `admin/login.html:25` vs `admin/shell.html:41` | 25, 41 | WARNING |
| Status terminology mismatch: filter dropdown uses "failed" but database renders "error" | `browse.html:36-53` | 36-53 | WARNING |
| Parenthetical plural in "Found X result(s)" is awkward | `search_results.html:3` | 3 | WARNING |

**Score Rationale:** Copywriting is mostly clear and professional. The inconsistencies are minor but should be fixed for polish.

---

### Pillar 2: Visuals (2/4)

**Strengths:**
- Layout is clean and uses Bootstrap grid consistently (two-column search, card-based filters, sidebar admin shell).
- Admin shell uses a clear sidebar navigation with Alpine.js active tab states.
- Document detail page has a well-structured metadata card with `<dl>`/`<dt>`/`<dd>`.
- Pagination on browse page is implemented with smart truncation (ellipsis at page 4 and `total_pages - 3`).
- Navbar active state is implemented in `base.html:52` with conditional `active` class.
- No placeholder or stub visual content in admin tabs — all 7 tabs have real content.
- Status badges in admin tables use Bootstrap `bg-success`/`bg-warning` for clear visual distinction.

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results render as a single card with raw markdown text in `<pre>` — no scores, metadata, or individual result cards | `search_results.html:5-18` | 5-18 | BLOCKER |
| Status rendering is inconsistent: plain text in browse table, Bootstrap badges in admin table | `browse.html:102` vs `admin/_documents_table.html:22` | 102, 22 | WARNING |
| Search results page is bare — just a single alert + one card with pre block | `search_results.html` | 1-25 | WARNING |
| Navbar active state is visually subtle (Bootstrap dark navbar contrast) | `base.html:52` | 52 | WARNING |

**Score Rationale:** The overall layout is clean and structured, but the search results presentation is a critical usability issue. The data format mismatch means the primary search feature renders a single card with all markdown text concatenated, making it essentially unusable for reviewing multiple results.

---

### Pillar 3: Color (3/4)

**Strengths:**
- Bootstrap semantic colors are used correctly throughout: `text-success`, `text-danger`, `text-warning`, `text-muted`, `bg-secondary`, `alert-danger`, `alert-success`, `alert-info`, `alert-warning`.
- Admin badges use `text-success border border-success` pattern which is accessible and clear.
- `styles.css` consolidates project-specific color-related styling.
- No custom color palette that conflicts with Bootstrap.
- Monitor lights now use Bootstrap `bg-success`/`bg-danger`/`bg-secondary` classes (fixed from previous audit).

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Hardcoded hex colors in `<style>` block in base.html | `base.html:28-34` | 28-34 | WARNING |
| No dark mode support (Grafana embed uses `theme=light` hardcoded) | `admin/tab_monitoring.html:15,31` | 15, 31 | WARNING |

**Score Rationale:** Colors are mostly semantic and accessible. The base.html `<style>` block uses hardcoded hex values instead of Bootstrap CSS variables, which prevents easy theming and dark mode. The Grafana embed hardcodes `theme=light`.

---

### Pillar 4: Typography (3/4)

**Strengths:**
- Heading hierarchy is substantially fixed from previous audit:
  - `login.html:15`: `<h1 class="card-title h5 mb-3">Login</h1>` — proper h1 element
  - `error.html:8`: `<h1 class="h4 alert-heading">Error {{ code }}: {{ title }}</h1>` — proper h1 element
  - `_profile_content.html:2,8,31`: `<h3 class="h5">Account/API Keys/GDPR</h3>` — proper h3 elements
  - `browse.html`: `h1` → `h2.visually-hidden` (filters) → `h2.visually-hidden` (results)
  - `search.html`: `h1` → `h2.h5` (card title)
  - `document.html`: `h1` → `h2.h5` (card header) → `h2.h4` (chunks)
  - Admin tabs: `h2.h3` (tab title) → `h3.h5` (subsections)
- Bootstrap heading utilities (`h1`, `h2`, `h3`, `h4`, `h5`, `h6`) are used consistently.
- Font size is readable; no tiny or oversized text.
- Code blocks and `<pre>` tags use `chunk-preview` class for wrapping.
- `search-result-excerpt` pre block uses `font-family: inherit` and `font-size: 0.9rem` for better readability.

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Profile Config subsection uses `<h3 class="h6">` — visual skip from h2 to h6 | `admin/tab_profile.html:5` | 5 | WARNING |
| `fs-6` on nav links is redundant (nav-link already sizes appropriately) | `base.html:52` | 52 | WARNING |

**Score Rationale:** Heading hierarchy is substantially improved from the previous audit. The login page and error page now have proper h1 elements. The profile sections use h3 elements. The only remaining issue is the `<h3 class="h6">` in `tab_profile.html` which creates a visual size skip.

---

### Pillar 5: Spacing (4/4)

**Strengths:**
- **Zero inline styles found** across all templates — a complete fix from the previous audit.
- Bootstrap spacing utilities are used consistently: `mb-3`, `mt-4`, `mb-4`, `py-3`, `px-3`, `p-3`, `p-4`, `gap-2`, `gap-3`, `ms-2`, `mt-2`.
- `styles.css` replaces all former inline styles with semantic classes:
  - `.chunk-preview` — white-space and word-break
  - `.chunk-title-truncate` — max-width
  - `.admin-shell` — min-height
  - `.admin-sidebar` — width and flex-shrink
  - `.monitoring-iframe` — width, height, border
  - `.monitor-card` — width
  - `.monitor-light` — width, height, border-radius
  - `.analytics-table` — width
  - `.config-search` — max-width
  - `.editable-field` — cursor
  - `.search-result-excerpt pre` — background, padding, border-radius
- `g-3` used in browse filter form for consistent gutter spacing.
- No arbitrary spacing values (e.g., `[10px]`, `[1.5rem]`) found in templates.
- Card-based layout provides consistent internal padding.

**Issues:**

None found.

**Score Rationale:** Spacing is entirely consistent. All inline styles have been removed and replaced with semantic CSS classes or Bootstrap utilities. This is a complete fix from the previous audit.

---

### Pillar 6: Experience Design (2/4)

**Strengths:**
- **Loading states present:**
  - Search page has `hx-indicator` spinner (`search.html:73`)
  - Admin shell has initial tab load spinner (`shell.html:52`)
  - Admin documents tab has spinner (`tab_documents.html:8`)
  - Admin job status has "Loading job status..." text (`tab_ingestion.html:30`)
- **Error handling:**
  - HTMX `responseError` handlers in `base.html:91-115` for 401, general errors, and network errors
  - FastAPI exception handlers in `app.py:129-174` for 404, 500, 403
  - `error.html` template renders user-friendly error pages
- **Empty states:**
  - `_documents_table.html:34`: "No documents found..."
  - `tab_analytics.html:13`: "No query data available..."
  - `document.html:102`: "Chunks Unavailable"
  - `search_results.html:22`: "No results found..."
  - `_config_table.html:28`: "No configuration entries found."
- **Confirmation dialogs:**
  - `tab_ragas.html:16`: `hx-confirm` for evaluation run
  - `_profile_content.html:75,93`: `confirm()` for revoke key and data erasure
- **Navigation:**
  - Responsive navbar with toggler
  - Pagination on browse page
  - Back button on document detail page
  - Admin tab switching via Alpine.js
  - Document chunk accordion with "Show next 10 chunks" / "Show less" pagination
- **Disabled states:**
  - Search button disables during request and shows spinner (`search.html:101-113`)
- **Keyboard accessibility:**
  - Login modal input handles `@keydown.enter` (`shell.html:75`)
  - Config editor handles `@keydown.enter` and `@keydown.escape` (`_config_table.html:16`)

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results are broken — single card with all markdown text in `<pre>` | `search_results.html` | 1-25 | BLOCKER |
| No HTMX timeout handling — long requests will hang silently | All templates | — | WARNING |
| Admin tab error target (`#tab-error`) exists but is never shown by HTMX error handlers | `shell.html:60` | 60 | WARNING |
| Search results page has no scores, source file links, or metadata per result | `search_results.html` | 5-18 | WARNING |
| No `aria-label` on icon-only navbar toggler | `base.html:44` | 44 | WARNING |
| `search.html` uses `document.querySelector('.btn-text')` which is fragile — if multiple `.btn-text` elements exist, it will break | `search.html:106,112` | 106, 112 | WARNING |

**Score Rationale:** Core state coverage is good (loading, error, empty states all present), but the search results are fundamentally broken due to a data format mismatch between the backend and the template. Missing timeout handling and the unused tab error target are notable gaps.

---

## Registry Safety

No `components.json` found. Project uses Bootstrap 5 CDN + HTMX + Alpine.js CSP build. No third-party registry audit required.

---

## Files Audited

### Templates
- `kb_server/ui/templates/base.html`
- `kb_server/ui/templates/search.html`
- `kb_server/ui/templates/browse.html`
- `kb_server/ui/templates/document.html`
- `kb_server/ui/templates/error.html`
- `kb_server/ui/templates/search_results.html`
- `kb_server/ui/templates/document_chunks.html`
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

### CSS
- `kb_server/ui/static/styles.css`

### Python Routes
- `kb_server/ui/app.py`
- `kb_server/ui/routes.py`
- `kb_server/ui/routes_admin.py`
- `kb_server/ui/run_ui.py`

### Server Backend
- `kb_server/server.py` (to verify `_search_kb` return format)

---

## Summary

**Score: 17/24** — Not production-ready.

**Fixes applied since previous audit:**
1. ✅ All inline styles removed from templates (replaced with CSS classes)
2. ✅ Monitor lights now use Bootstrap `bg-*` utilities instead of inline styles
3. ✅ Login page now has `<h1>` element (previously only `<h3>`)
4. ✅ Error page now has `<h1>` element
5. ✅ Profile sections now use `<h3>` elements (previously `<h5>`)
6. ✅ `styles.css` expanded with `.search-result-excerpt` styling

**Remaining issues (3 new, 4 carried forward):**
1. 🔴 **BLOCKER:** Search results are broken due to data format mismatch — `_search_kb` returns `list[TextContent]` but `search_results.html` expects individual chunk objects. The template renders a single card with all markdown text in a `<pre>` block.
2. 🔴 **WARNING:** No HTMX timeout handling — requests can hang indefinitely.
3. 🔴 **WARNING:** Hardcoded hex colors in `base.html` `<style>` block prevent theming.
4. 🔴 **WARNING:** Status terminology mismatch between filter dropdown and table rendering.
5. 🔴 **WARNING:** Admin tab error target (`#tab-error`) is never activated by error handlers.
6. 🔴 **WARNING:** Search results page has no scores, source file links, or metadata per result.
7. 🔴 **WARNING:** `document.querySelector('.btn-text')` in `search.html` is fragile.

The UI is substantially improved in spacing and typography but remains blocked from production readiness by the search results data format issue.
