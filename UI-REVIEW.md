# Phase 15 — UI Review

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured at `.planning/ui-reviews/20260616-015734/`
**Server:** Port 8002 (`python -m kb_server.ui.run_ui`)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Mostly clear labels; error page template variable mismatch causes empty "Error :" display |
| 2. Visuals | 3/4 | Clean Bootstrap 5 layout; admin panel shows generic error on 401 instead of login modal |
| 3. Color | 4/4 | Bootstrap semantic colors used consistently; no hardcoded colors; good 60/30/10 distribution |
| 4. Typography | 3/4 | Good heading hierarchy; search results use `<pre>` instead of styled `.search-result-text` class |
| 5. Spacing | 4/4 | Bootstrap spacing utilities used consistently; no arbitrary values; responsive breakpoints present |
| 6. Experience Design | 3/4 | Loading, error, empty states present; admin 401 flow broken; login form unreachable via GET |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Error page template variable mismatch** — `error.html` expects `code` and `title` but `routes.py` passes `error`. Users see blank "Error :" with no status code or message. — Fix: Pass `code` and `title` from the route, or update template to use `error`.
2. **Admin panel unauthenticated experience broken** — Initial HTMX tab load returns 401, which triggers base.html's generic "Failed to load content" alert instead of the login modal in `shell.html`. The login modal code exists but is never reached. — Fix: In the 401 handler, check if the target is `#tab-content` and show `#loginModal` instead of the generic alert.
3. **Search results render in monospace `<pre>`** — The `search_results.html` template uses `<pre>` for result text, which renders in monospace and looks like code rather than readable content. The `.search-result-text` CSS class exists with proper styling but is unused. — Fix: Replace `<pre>` with a `<div class="search-result-text">`.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- No generic labels like "Submit", "Click Here", or "OK" found.
- CTA labels are domain-specific: "Search", "Filter", "Clear", "Start Ingest", "Run Evaluation", "Generate New Key".
- Empty states are actionable: "No documents found matching the current filters. [Clear filters] or ingest documents." (`browse.html:125-128`).
- Error copy is human-friendly: "Failed to load content. Please try again later." (`base.html:94-95`).

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Error page renders blank "Error :" because template expects `code`/`title` but route passes `error` | `error.html` | 8 | **BLOCKER** |
| "Query *" label is terse; could be "Search query" | `search.html` | 15 | WARNING |
| Browse page shows "Page 1 of 0" when empty — confusing copy | `browse.html` | 71 | WARNING |

**Score rationale:** The template variable mismatch is a real user-facing defect. Otherwise copy is solid and domain-appropriate.

---

### Pillar 2: Visuals (3/4)

**Strengths**
- Clear visual hierarchy: dark navbar (focal point), white content area, cards for grouped content.
- Two-column search layout (form left, results right) is task-oriented.
- Status badges use consistent semantic colors (success/danger/warning).
- Admin sidebar + content area is a recognizable dashboard pattern.
- Mobile view stacks correctly to single column (`mobile-search.png`).
- Pagination with smart ellipsis (`browse.html:157-177`).
- Document chunks use accordion with "Show next 10" progressive disclosure.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin panel shows generic error alert on 401 instead of login modal | `shell.html` + `base.html` | 60, 91 | **WARNING** |
| Search results use raw `<pre>` — looks like code, not prose | `search_results.html` | 21 | WARNING |
| No favicon defined in `base.html` | `base.html` | — | WARNING |
| Navbar `aria-current` quotes are malformed: `active" aria-current="page{% endif %}` | `base.html` | 43, 49, 55 | WARNING |
| Login form at `login.html` is unreachable via GET (route returns 405) | `login.html` | — | WARNING |

**Score rationale:** The admin 401 flow is a notable UX gap. The search results `<pre>` styling degrades readability. Otherwise visual structure is solid.

---

### Pillar 3: Color (4/4)

**Strengths**
- Zero hardcoded hex or rgb colors in templates.
- CSS uses Bootstrap CSS variables exclusively: `var(--bs-success)`, `var(--bs-light)`, `var(--bs-border-color)`, etc. (`styles.css:59-77`).
- Semantic color usage is consistent:
  - `bg-success` / `text-success` for completed/ok states
  - `bg-danger` / `text-danger` for failed/error states
  - `bg-warning` / `text-warning` for pending states
  - `alert-info` for neutral empty states
  - `alert-success` for positive search results
- Approximate 60/30/10 distribution: white page (60), dark navbar/sidebar (30), blue primary accent (10).

**Issues**
- None found.

**Score rationale:** Color discipline is excellent. All colors derive from Bootstrap's semantic system.

---

### Pillar 4: Typography (3/4)

**Strengths**
- Heading hierarchy is clear and consistent:
  - `h1` for page titles (Search Tester, Browse Documents)
  - `h2` for major sections (with `h3`/`h4`/`h5` utility classes for sizing)
  - `h5` for card titles (Search Parameters, Quick Ingest, Evaluation Dataset)
  - `h6` for sub-headings (Config in Profile)
- `text-muted` used consistently for secondary/meta text.
- `small` class used for metadata lines (chunk IDs, product, type, page).
- `<code>` used appropriately for IDs, hashes, and query text.
- No custom font families or arbitrary font sizes.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search result text rendered in `<pre>` (monospace) instead of `.search-result-text` | `search_results.html` | 21 | WARNING |
| `font-size: 0.85rem` and `font-size: 0.9rem` in CSS are slightly off the Bootstrap scale but acceptable | `styles.css` | 71, 120 | MINOR |

**Score rationale:** The `<pre>` issue is the only notable gap. Otherwise typography is clean and hierarchical.

---

### Pillar 5: Spacing (4/4)

**Strengths**
- Bootstrap spacing utilities used consistently: `mb-3`, `mb-4`, `mt-4`, `mt-2`, `mb-2`, `mb-0`, `py-3`, `p-3`, `p-4`, `gap-2`, `gap-3`.
- Zero inline `style="..."` attributes found in templates.
- Zero arbitrary Tailwind-like bracket values (`[10px]`) found.
- CSS spacing is systematic: `1rem` padding for result blocks, `0.75rem` for excerpts, `0.375rem` border radius.
- Responsive breakpoints in CSS for admin sidebar (`@media (max-width: 768px)` at `styles.css:33`).
- Monitor cards have fixed width (`160px`) for consistent grid layout.

**Issues**
- None found.

**Score rationale:** Spacing is disciplined and consistent throughout.

---

### Pillar 6: Experience Design (3/4)

**Strengths**
- **Loading states:** Spinners in search button, filter button, ingest button, RAGAS button, admin tab loader, and inline `#search-loading` div.
- **Error states:** HTMX responseError handlers for 401 (modal), generic errors, and network errors. Tab-specific error div in `shell.html`. Config save error in `_config_table.html`. Document chunk loading failures handled with `alert-warning`.
- **Empty states:** Browse, search results, analytics, documents table, and config table all have contextual empty messages with next steps.
- **Disabled states:** Search, filter, ingest, and RAGAS buttons disable during submission.
- **Confirmations:** RAGAS evaluation has `hx-confirm`. Profile key revocation and data erasure use `confirm()` dialogs.
- **Partial updates:** HTMX used for search results, tab content, chunk pagination, job status, monitor lights, and analytics refresh.
- **Pagination:** Browse has numbered pagination with ellipsis. Document chunks have "Show next 10" / "Show less".
- **Accessibility:** `visually-hidden` headings for screen readers (Search Results, Filters, Results, Document Chunks). `aria-label` on pagination nav.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin 401 flow: base.html generic alert overrides shell.html login modal | `base.html` | 91-98 | **WARNING** |
| Login page template exists but route only accepts POST (405 on GET) | `login.html` | — | WARNING |
| Search results show 500-character raw `<pre>` excerpt; no "Read more" or link to full document | `search_results.html` | 21 | WARNING |
| No skeleton/shimmer loaders — only spinners | — | — | MINOR |
| No error boundary for unhandled JS exceptions in Alpine.js components | — | — | MINOR |

**Score rationale:** Most states are covered, but the broken 401 flow and unreachable login page are notable gaps. The search result truncation is also a mild UX issue.

---

## Registry Safety

No `components.json` found. Project uses Bootstrap 5 CDN, HTMX CDN, and Alpine.js CDN — no shadcn or third-party registry blocks. Registry audit skipped.

---

## Files Audited

### Templates
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

### Styles & Routes
- `kb_server/ui/static/styles.css`
- `kb_server/ui/routes.py`
- `kb_server/ui/run_ui.py`

### Screenshots
- `.planning/ui-reviews/20260616-015734/desktop-search.png`
- `.planning/ui-reviews/20260616-015734/desktop-browse.png`
- `.planning/ui-reviews/20260616-015734/desktop-admin.png`
- `.planning/ui-reviews/20260616-015734/mobile-search.png`
- `.planning/ui-reviews/20260616-015734/error-404.png`
- `.planning/ui-reviews/20260616-015734/admin-analytics.png`
- `.planning/ui-reviews/20260616-015734/admin-monitoring.png`
- `.planning/ui-reviews/20260616-015734/search-results-query.png`

---

## Production Readiness

**Score: 20/24 — Not production-ready.**

The UI is structurally sound and visually clean, but the **error page template bug** (BLOCKER) and the **broken admin unauthenticated flow** (WARNING) must be fixed before shipping. The search results `<pre>` rendering should also be addressed. With these three fixes, the UI would score 22+/24 and be production-ready.
