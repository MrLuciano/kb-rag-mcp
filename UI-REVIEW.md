# KB-RAG Web UI — 6-Pillar Visual Audit

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured at `.planning/ui-reviews/20260616-005608/`
**Previous Audit:** 16/24 (19 issues)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Labels are clear, but "Log in" vs "Log out" and status terminology inconsistencies remain |
| 2. Visuals | 3/4 | Layout is clean, but search results display in a single `<pre>` tag — poor UX |
| 3. Color | 3/4 | Bootstrap semantic colors used well, but 3 inline styles remain in monitor lights |
| 4. Typography | 2/4 | Heading hierarchy has skips in login.html and profile sections |
| 5. Spacing | 3/4 | Bootstrap spacing consistent, but 3 inline styles remain |
| 6. Experience Design | 3/4 | Good state coverage, but no HTMX timeout handling and search results UX is poor |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Search results render in a single `<pre>` tag** — The primary search feature returns all results concatenated into one `<pre>` block with no scores, metadata, or individual result cards. This is a **BLOCKER** for usability. Fix: render each result as a card with score, source file, and highlighted excerpt.
2. **3 inline `style` attributes remain in `_monitor_lights.html`** — Previous audit identified this; fix was incomplete. The monitor light colors should use CSS classes or Bootstrap `bg-*` utilities instead of `style="background:#..."`. Fix: add `.monitor-light-healthy`, `.monitor-light-unhealthy`, `.monitor-light-unknown` classes to `styles.css`.
3. **Heading hierarchy skips in `login.html` and `_profile_content.html`** — `login.html` has no `<h1>` or `<h2>` on the page (only `<h3 class="h5">`). `_profile_content.html` uses `<h5>` for Account/API Keys/GDPR sections without `<h3>` or `<h4>` parents. Fix: use `<h1>` for login page title, `<h3>` for profile sections.

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

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Inconsistent casing: login button says "Log in" but logout says "Log out" | `admin/login.html:25` vs `admin/shell.html:41` | 25, 41 | WARNING |
| Status terminology mismatch: filter dropdown uses "failed" but database renders "error" | `browse.html:36-53` | 36-53 | WARNING |
| Parenthetical plural in "Found X result(s)" is awkward | `search_results.html:3` | 3 | WARNING |

**Score Rationale:** Copywriting is mostly clear and professional. The inconsistencies are minor but should be fixed for polish.

---

### Pillar 2: Visuals (3/4)

**Strengths:**
- Layout is clean and uses Bootstrap grid consistently (two-column search, card-based filters, sidebar admin shell).
- Admin shell uses a clear sidebar navigation with Alpine.js active tab states.
- Document detail page has a well-structured metadata card with `<dl>`/`<dt>`/`<dd>`.
- Pagination on browse page is implemented with smart truncation (ellipsis at page 4 and total_pages-3).
- Navbar active state is implemented in `base.html:52` with conditional `active` class.
- No placeholder or stub visual content in admin tabs — all 7 tabs have real content.

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results render in a single `<pre>` tag — no individual cards, scores, or metadata | `search_results.html:7` | 7 | BLOCKER |
| Status rendering is inconsistent: plain text in browse table, Bootstrap badges in admin table | `browse.html:102` vs `admin/_documents_table.html:22` | 102, 22 | WARNING |
| Search results page is bare — just a single alert + pre block | `search_results.html` | 1-14 | WARNING |
| Navbar active state is implemented but visually subtle (Bootstrap dark navbar contrast) | `base.html:52` | 52 | WARNING |

**Score Rationale:** The overall layout is clean and structured, but the search results presentation is a significant usability issue. Status inconsistency between browse and admin tables degrades visual coherence.

---

### Pillar 3: Color (3/4)

**Strengths:**
- Bootstrap semantic colors are used correctly throughout: `text-success`, `text-danger`, `text-warning`, `text-muted`, `bg-secondary`, `alert-danger`, `alert-success`, `alert-info`, `alert-warning`.
- Admin badges use `text-success border border-success` pattern which is accessible and clear.
- `styles.css` consolidates project-specific color-related styling.
- No custom color palette that conflicts with Bootstrap.

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| 3 inline `style` attributes with hardcoded hex colors in monitor lights | `admin/_monitor_lights.html:19,23,27` | 19, 23, 27 | WARNING |
| Hardcoded hex colors in `<style>` block in base.html | `base.html:28-33` | 28-33 | WARNING |
| No dark mode support (Grafana embed uses `theme=light` hardcoded) | `admin/tab_monitoring.html:15,31` | 15, 31 | WARNING |

**Score Rationale:** Colors are mostly semantic and accessible. The 3 inline styles in monitor lights are a regression from the previous audit fix attempt. The base.html style block is less severe than inline styles but still hardcoded.

---

### Pillar 4: Typography (2/4)

**Strengths:**
- Most pages use proper heading hierarchy:
  - `browse.html`: h1 → h2.visually-hidden (filters) → h2.visually-hidden (results)
  - `search.html`: h1 → h2.h5 (card title)
  - `document.html`: h1 → h2.h5 (card header) → h2.h4 (chunks)
  - Admin tabs: h2.h3 (tab title) → h3.h5 (subsections)
- Bootstrap heading utilities (`h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `h5`) are used consistently.
- Font size is readable; no tiny or oversized text.
- Code blocks and `<pre>` tags use `chunk-preview` class for wrapping.

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Login page has no `<h1>` or `<h2>` — only `<h3 class="h5">` | `admin/login.html:15` | 15 | WARNING |
| Profile sections use `<h5>` without `<h3>` or `<h4>` parents (tab title is `<h2>`) | `admin/_profile_content.html:2,8,31` | 2, 8, 31 | WARNING |
| Profile Config subsection uses `<h5 class="h6">` — skips 3 levels | `admin/tab_profile.html:5` | 5 | WARNING |
| Error page has `<h2>` but no `<h1>` | `error.html:8` | 8 | WARNING |
| `fs-6` on nav links is redundant (nav-link already sizes appropriately) | `base.html:52` | 52 | WARNING |

**Score Rationale:** Heading hierarchy is the weakest pillar. The login page and profile sections have notable skips. The error page missing h1 is acceptable but the others should be fixed.

---

### Pillar 5: Spacing (3/4)

**Strengths:**
- Bootstrap spacing utilities are used consistently: `mb-3`, `mt-4`, `mb-4`, `py-3`, `px-3`, `p-3`, `p-4`, `gap-2`, `gap-3`.
- `styles.css` replaces all but 3 inline styles with semantic classes.
- `g-3` used in browse filter form for consistent gutter spacing.
- No arbitrary spacing values (e.g., `[10px]`, `[1.5rem]`) found in templates.
- Card-based layout provides consistent internal padding.

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| 3 inline `style` attributes remain in monitor lights | `admin/_monitor_lights.html:19,23,27` | 19, 23, 27 | WARNING |

**Score Rationale:** Spacing is almost entirely consistent. The 3 inline styles in monitor lights are the only deviation from the Bootstrap spacing system.

---

### Pillar 6: Experience Design (3/4)

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
  - `search_results.html:11`: "No results found..."
- **Confirmation dialogs:**
  - `tab_ragas.html:16`: `hx-confirm` for evaluation run
  - `_profile_content.html:75,93`: `confirm()` for revoke key and data erasure
- **Navigation:**
  - Responsive navbar with toggler
  - Pagination on browse page
  - Back button on document detail page
  - Admin tab switching via Alpine.js

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results UX is poor — single `<pre>` block, no scores, no individual result cards | `search_results.html` | 1-14 | BLOCKER |
| No HTMX timeout handling — long requests will hang silently | All templates | — | WARNING |
| Search button does not show disabled state during request; button spinner is hidden | `search.html:68` | 68 | WARNING |
| Admin tab error target (`#tab-error`) exists but is never shown by HTMX error handlers | `shell.html:60` | 60 | WARNING |
| No `aria-label` on icon-only navbar toggler (Bootstrap handles this by default, but good to verify) | `base.html:44` | 44 | WARNING |

**Score Rationale:** Core state coverage is good, but the search results presentation is a significant usability blocker. Missing timeout handling and disabled button states are notable gaps.

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

---

## Summary

**Score: 17/24** — Not production-ready. The previous audit found 19 issues; several have been fixed (admin tabs are no longer stubs, search is functional, error boundaries exist, loading states added). However, **3 inline styles remain** in monitor lights, **search results UX is still poor**, and **heading hierarchy skips** in login/profile pages are unaddressed. The UI is substantially improved from the previous 16/24 but needs the Top 3 fixes before it can be considered production-ready.
