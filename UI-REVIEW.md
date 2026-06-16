# Phase 15 — UI Review

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md)
**Screenshots:** Captured from http://localhost:8002
**Screen:** Desktop (1440×900), Mobile (375×812)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Actionable labels and empty states are solid; jargon-heavy admin labels and inconsistent tab naming drag it down. |
| 2. Visuals | 3/4 | Clean card-based layout, but login page is isolated from the brand shell and search results lack focal hierarchy. |
| 3. Color | 3/4 | Bootstrap semantic palette used correctly, but zero brand identity; everything is default blue/gray/white. |
| 4. Typography | 2/4 | Heading hierarchy is broken on multiple pages (h1.h5, h2.h5 vs h2.h4, h3.h6) — screen-reader hostile. |
| 5. Spacing | 3/4 | Bootstrap scale is respected, no arbitrary values. Minor double-container padding bug on error page. |
| 6. Experience Design | 3/4 | Good loading/error/empty state coverage. Admin auth flow requires an unnecessary 401 round-trip. |

**Overall: 17/24**

**Production-ready:** Yes, with minor fixes. Not 22+/24.

---

## Top 3 Priority Fixes

1. **Admin shell defers login modal until a 401 error occurs** — Unauthenticated users visiting `/admin` see the full sidebar and can click tabs. Only after a failed HTMX request does the modal appear. This creates a confusing "why is nothing loading?" moment. The modal should be shown immediately on `init()` if `kb_api_key` is missing.

2. **Heading hierarchy is contradictory across pages** — `login.html` uses `h1.h5` (semantic page title visually smaller than a section). `document.html` has two `h2` elements with different visual classes (`h5` and `h4`). `tab_profile.html` uses `h3.h6` for subsections. This breaks the document outline for screen readers and degrades visual hierarchy.

3. **Search results lack query-term highlighting and the score badge is low-contrast** — `search_results.html` truncates raw text at 500 chars with no `highlight_term()` call (unlike `document.html`). The match score uses `badge bg-secondary` which is low-contrast gray. Users cannot see *why* a result matched.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- Empty states are helpful and actionable: *"No documents found matching the current filters. Clear filters or ingest documents."* (`browse.html:126`)
- Error page includes useful next-step links: *"Try searching or browse documents."* (`error.html:12`)
- GDPR labels in profile are precise: *"Export My Data (GDPR Art. 20)"* (`admin/_profile_content.html:32`)
- Confirmation dialogs for destructive actions: *"Run evaluation? This may take several minutes."* (`admin/tab_ragas.html:16`)

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| "RAGAS Evaluation" is jargon-heavy; sidebar calls the same tab "Evaluation" | `admin/tab_ragas.html` | 1 | WARNING |
| Technical abbreviations in profile config: "K", "BM25", "Rerank" | `admin/tab_profile.html` | 7, 15, 23 | WARNING |
| "Search Tester" is an odd product-facing name for the primary search interface | `search.html` | 6 | WARNING |
| "Chunk Loading Failed" is overly technical for an end-user message | `document.html` | 114 | WARNING |
| "Login" heading is generic; no brand context or "Sign in to KB-RAG" | `admin/login.html` | 15 | MINOR |

---

### Pillar 2: Visuals (3/4)

**Strengths**
- Card-based layouts provide clear visual grouping on search, browse, and admin pages.
- Status badges use semantic color (green/red/yellow) for immediate status recognition.
- Monitor light cards give an at-a-glance system health view.
- Accordion chunks conserve vertical space on the document page.
- Responsive tables use `table-responsive` for horizontal scroll on mobile.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Login page is isolated — no navbar, no logo, no way back to the main site | `admin/login.html` | 1 | WARNING |
| Admin sidebar on mobile becomes a tall full-width bar that pushes content far down | `admin/shell.html` + `styles.css` | 8, 34 | WARNING |
| Search results have no focal point; score badge is low-contrast secondary gray | `search_results.html` | 12 | WARNING |
| Matching query terms are not highlighted in search results (unlike document chunks) | `search_results.html` | 21 | WARNING |
| Job status counters in admin are left-aligned in a wide card; no centering or distribution | `admin/_job_status.html` | 4 | MINOR |

---

### Pillar 3: Color (3/4)

**Strengths**
- Zero hardcoded hex or RGB values in templates.
- `styles.css` uses Bootstrap CSS variables (`var(--bs-success)`, `var(--bs-danger)`, etc.) for all status colors.
- Semantic color usage is consistent: `bg-success` for completed, `bg-danger` for failed, `bg-warning` for pending.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Entirely Bootstrap default palette — no brand identity or custom accent | All | — | WARNING |
| Admin sidebar is flat dark gray with no visual texture or depth | `admin/shell.html` | 8 | MINOR |
| Login page is completely devoid of brand color (white card on gray) | `admin/login.html` | 9 | MINOR |

---

### Pillar 4: Typography (2/4)

**Strengths**
- `visually-hidden` headings provide screen-reader context for filter and result sections (`browse.html:8,68`).
- `aria-label` on pagination nav (`browse.html:133`).
- `small` and `text-muted` utilities are used consistently for metadata.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| `h1` styled as `h5` — semantic page title is visually smaller than a section heading | `admin/login.html` | 15 | WARNING |
| Two `h2` elements on the same page with different visual sizes (`h5` vs `h4`) | `document.html` | 15, 65 | WARNING |
| `h3.h6` used for a subsection under an `h2` — should be `h3` or `h4` without size override | `admin/tab_profile.html` | 5 | WARNING |
| `h3.h5` used for data section titles under `h2.h3` — creates a skipped/confused outline | `admin/tab_analytics.html` | 20, 41, 63 | WARNING |
| `h2.h5` used for card header inside the document detail card | `document.html` | 15 | WARNING |

**Rationale:** The project consistently uses Bootstrap heading utility classes (`.h1`–`.h6`) to override visual size while preserving semantic `h1`–`h6` tags. This is an acceptable pattern when applied consistently, but the same page often contains multiple headings at the same semantic level with *different* visual classes, which breaks the expected outline for screen-reader users and creates a confusing visual hierarchy.

---

### Pillar 5: Spacing (3/4)

**Strengths**
- Bootstrap spacing utilities are used consistently (`mt-4`, `mb-3`, `p-4`, `gap-2`, `py-3`).
- No arbitrary Tailwind-style values (e.g., no `[10px]`, `[2rem]`).
- Grid system (`col-md-4`, `col-md-8`, etc.) provides a responsive layout.
- CSS custom values are reasonable: `220px` sidebar, `160px` monitor cards, `600px` iframe height.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| `error.html` nests `<div class="container">` inside base's `container`, creating double horizontal padding | `error.html` | 6 | WARNING |
| Pagination `href` attributes contain whitespace and newlines from Jinja2 formatting | `browse.html` | 138–146 | MINOR |
| Mobile search page stacks the alert flush against the card bottom (no `mt-3` on results area) | `search.html` | 86 | MINOR |

---

### Pillar 6: Experience Design (3/4)

**Strengths**
- Loading states on almost every async action: spinner in search button, filter button, ingest button, RAGAS button, tab content, admin documents.
- Empty states are informative: search, browse, analytics, documents table, RAGAS.
- Error states are covered: network errors, 401 auth, tab load failures, chunk load failures, config save failures.
- Confirmation dialogs for destructive actions: RAGAS run, API key revoke, GDPR erasure.
- HTMX global error handlers in `base.html` catch 401, generic errors, and network failures.
- Accordion chunks are paginated ("Show next 10 chunks") to avoid overwhelming the user.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin login modal is not shown on initial load; user must trigger a 401 first | `admin/shell.html` | 113–126 | **BLOCKER** |
| Search results do not highlight matching terms; users can't see *why* a result matched | `search_results.html` | 21 | WARNING |
| No dismissible alerts anywhere — users can't close info/warning banners | Multiple | — | WARNING |
| Config table edit interaction is undiscoverable (double-click is not hinted) | `admin/_config_table.html` | 14 | WARNING |
| RAGAS evaluation shows no progress indication beyond the button spinner | `admin/tab_ragas.html` | 12–19 | WARNING |
| No pagination on search results; large result sets will scroll indefinitely | `search_results.html` | 6–26 | WARNING |

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

### Styles
- `kb_server/ui/static/styles.css`

### Screenshots
- `.planning/ui-reviews/phase-20260616-020015/search.png`
- `.planning/ui-reviews/phase-20260616-020015/search-mobile.png`
- `.planning/ui-reviews/phase-20260616-020015/browse.png`
- `.planning/ui-reviews/phase-20260616-020015/browse-mobile.png`
- `.planning/ui-reviews/phase-20260616-020015/admin.png`
- `.planning/ui-reviews/phase-20260616-020015/admin-mobile.png`
- `.planning/ui-reviews/phase-20260616-020015/document.png`
- `.planning/ui-reviews/phase-20260616-020015/error-page.png`
- `.planning/ui-reviews/phase-20260616-020015/login.png`
