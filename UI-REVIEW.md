# UI Review — KB-RAG Web UI

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured to `.planning/ui-reviews/20260616-014950/` (desktop, mobile, tablet, search, browse, admin, login, document)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Clear labels and actionable empty states; some generic CTAs |
| 2. Visuals | 2/4 | Search results are unstyled plain text; no visual hierarchy in results |
| 3. Color | 2/4 | 13 hardcoded hex values in CSS; no CSS variables for theming |
| 4. Typography | 3/4 | Bootstrap heading system used well; minor CSS font-size fragmentation |
| 5. Spacing | 3/4 | Bootstrap utilities used consistently; arbitrary px values in CSS |
| 6. Experience Design | 4/4 | Excellent state coverage: loading, error, empty, auth, confirmation |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Search results lack styling** — `search_results.html` renders plain text in unstyled `<div>` elements with no cards, metadata, scores, or visual separation. This is the core user-facing feature of a RAG system and currently delivers a poor reading experience.
2. **Hardcoded colors in CSS** — `styles.css` contains 13 hex color values (e.g., `#198754`, `#dc3545`, `#f8f9fa`) instead of Bootstrap CSS variables (`var(--bs-success)`, `var(--bs-light)`). This blocks theming and makes maintenance brittle.
3. **No visual hierarchy in search results** — Results do not display relevance scores, source document metadata, or chunk index. Users cannot distinguish between high-confidence and low-confidence answers.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths:**
- Empty states are descriptive and actionable: "No documents found matching the current filters. Clear filters or ingest documents." (`browse.html:126`)
- Error messages are context-aware: "Failed to load content. Please try again later." (`base.html:94`), "Network error. Please check your connection." (`base.html:102-103`)
- Form labels are descriptive: "Number of Results", "Directory Path", "Query *"
- Status labels are human-readable: "Completed", "Pending", "Failed"
- Confirmation dialogs explain consequences: "Run evaluation? This may take several minutes." (`tab_ragas.html:16`)

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Generic button label "Filter" | `browse.html` | 56 | WARNING |
| Generic button label "View" | `browse.html` | 115 | WARNING |
| Generic button label "Edit" | `_config_table.html` | 22 | WARNING |
| "Please try again later" is boilerplate | `document.html` | 115 | WARNING |
| "Please try again later" is boilerplate | `base.html` | 95 | WARNING |

**Score Rationale:** Copywriting is functional and clear, but some CTA labels are generic. Error messages lean on boilerplate rather than specific recovery guidance. Empty states are a strong point.

---

### Pillar 2: Visuals (2/4)

**Strengths:**
- Bootstrap cards provide clear content containers (`search.html:10`, `document.html:13`)
- Status badges with semantic color coding create instant visual feedback (`browse.html:104-108`)
- Monitor light cards provide at-a-glance system health (`_monitor_lights.html`)
- Admin sidebar has clear tab navigation with active state indicators (`shell.html:11-38`)
- Loading spinners are paired with descriptive text ("Searching knowledge base...", "Loading documents...")

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results are unstyled plain text — no cards, borders, or visual separation | `search_results.html` | 6-10 | BLOCKER |
| No result metadata (score, source, chunk index) displayed in search results | `search_results.html` | 6-10 | BLOCKER |
| Login page is completely unstyled beyond `bg-light` — no branding, no visual interest | `login.html` | 9-31 | WARNING |
| Document chunk accordion lacks visual distinction between chunks | `document.html` | 72-97 | WARNING |
| No favicon declared in base template | `base.html` | 5-6 | WARNING |
| Navbar brand is plain text — no logo or icon | `base.html` | 34 | WARNING |
| `fs-6` on nav-links is redundant (Bootstrap nav-links already have correct sizing) | `base.html` | 43-57 | WARNING |

**Score Rationale:** The search results page is the primary user-facing output of a RAG system and is currently rendered as plain text blocks. This is a major visual failure. Other pages are functional but visually bland. The monitor lights and status badges are good visual elements.

---

### Pillar 3: Color (2/4)

**Strengths:**
- Templates use Bootstrap semantic color classes exclusively (no hardcoded colors in templates)
- Status badges use consistent `bg-success`/`bg-danger`/`bg-warning` patterns across all pages
- Monitor lights use `bg-success`/`bg-danger`/`bg-secondary` for clear health indication
- Dark navbar (`bg-dark`) provides good contrast with white content area

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| 13 hardcoded hex color values in CSS | `styles.css` | 59-112 | BLOCKER |
| Status colors hardcoded (`#198754`, `#dc3545`, `#ffc107`) instead of Bootstrap variables | `styles.css` | 59-61 | WARNING |
| Search result background hardcoded (`#f8f9fa`) | `styles.css` | 73 | WARNING |
| Border colors hardcoded (`#dee2e6`, `#e9ecef`) | `styles.css` | 76, 97, 101 | WARNING |
| Text colors hardcoded (`#212529`, `#495057`, `#6c757d`) | `styles.css` | 84, 92, 112 | WARNING |
| No custom accent color or brand palette beyond Bootstrap defaults | — | — | WARNING |

**Score Rationale:** While templates use Bootstrap classes correctly, the CSS file hardcodes 13 hex values that mirror Bootstrap's own palette. This defeats the purpose of a CSS framework and makes theming impossible. Color usage is also monotonous — no accent color distinguishes the brand.

---

### Pillar 4: Typography (3/4)

**Strengths:**
- Bootstrap heading hierarchy is used consistently: `.h3` for tab titles, `.h5` for card titles, `.h6` for sub-sections
- `visually-hidden` headings provide screen-reader structure without visual clutter (`browse.html:8`, `search_results.html:2`)
- `text-muted` is used consistently for secondary/descriptive text
- Code content is wrapped in `<code>` tags for semantic distinction

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Custom font sizes in CSS fragment the scale (0.9rem, 1.25rem, 1rem, 0.85em) | `styles.css` | 71, 81, 88, 104 | WARNING |
| Mix of `rem` and `em` units in CSS without clear strategy | `styles.css` | 71, 104 | WARNING |
| `font-weight: bold` mixed with `font-weight: 600` | `styles.css` | 62, 82, 89, 108 | WARNING |
| Heading levels skip from `h1` to `.h5` on search page | `search.html` | 6, 12 | WARNING |

**Score Rationale:** Typography is mostly consistent thanks to Bootstrap's system. The CSS introduces minor fragmentation with custom sizes and mixed font-weight declarations. Not a critical issue but prevents a higher score.

---

### Pillar 5: Spacing (3/4)

**Strengths:**
- Bootstrap spacing utilities are used consistently: `mb-3`, `mb-4`, `mt-4`, `p-3`, `gap-2`, `gap-3`, `py-3`
- Mobile responsive breakpoints are present for admin shell (`styles.css:33-48`)
- Form spacing is consistent with `mb-3` between fields
- Card padding follows Bootstrap defaults

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Arbitrary pixel values: `max-width: 400px` | `styles.css` | 12 | WARNING |
| Arbitrary pixel values: `width: 220px` | `styles.css` | 22 | WARNING |
| Arbitrary pixel values: `height: 600px` | `styles.css` | 54 | WARNING |
| Arbitrary pixel values: `width: 160px` | `styles.css` | 117 | WARNING |
| Arbitrary pixel values: `max-width: 300px` | `styles.css` | 135 | WARNING |
| Arbitrary pixel values: `width: 12px`, `height: 12px` | `styles.css` | 122-123 | WARNING |
| Mix of Bootstrap utilities and CSS spacing without unified scale | — | — | WARNING |

**Score Rationale:** Bootstrap spacing utilities are well-applied. The CSS file contains multiple arbitrary pixel values for component sizing that do not follow a spacing scale. This is typical for component-specific sizing but prevents the UI from feeling fully systematic.

---

### Pillar 6: Experience Design (4/4)

**Strengths:**
- **Loading states:** Spinner borders with descriptive text on search (`search.html:73-80`), filter (`browse.html:58`), ingest (`tab_ingestion.html:20`), RAGAS (`tab_ragas.html:18`), and tab loading (`shell.html:52-55`)
- **Error states:** HTMX error handlers inject `alert-danger` for network failures (`base.html:91-106`), tab loading failures (`shell.html:60-103`), and config save errors (`_config_table.html:29-79`)
- **Empty states:** Well-handled for documents (`browse.html:124-129`, `_documents_table.html:41-45`), analytics (`tab_analytics.html:12-16`), config (`_config_table.html:28`), and search results (`search_results.html:11-14`)
- **Disabled states:** Buttons are disabled during form submission (`search.html:105`, `browse.html:211`, `tab_ingestion.html:44`)
- **Confirmation dialogs:** Destructive actions require confirmation — RAGAS evaluation (`tab_ragas.html:16`), data erasure (`_profile_content.html:93`), API key revocation (`_profile_content.html:75`)
- **Auth handling:** Login modal appears on 401 errors (`base.html:82-89`), API key stored in localStorage, role-based tab visibility (`shell.html:27`)
- **Pagination:** Full pagination with ellipsis support for large result sets (`browse.html:132-198`)
- **Progressive loading:** Document chunks load 10 at a time with HTMX (`document.html:98-105`, `document_chunks.html:28-34`)
- **Form validation:** Required attributes on inputs (`search.html:19`, `login.html:19`, `tab_ingestion.html:16`)

**Issues:**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| No skeleton screens — only spinners | — | — | WARNING |
| No toast/snackbar notifications — success/error only inline | — | — | WARNING |
| No global error boundary for uncaught JavaScript errors | — | — | WARNING |

**Score Rationale:** Experience Design is the strongest pillar. The UI handles loading, error, empty, and auth states comprehensively. Confirmation dialogs protect destructive actions. The only gaps are advanced UX patterns (skeletons, toasts) that are nice-to-have rather than blockers.

---

## Files Audited

| File | Lines | Notes |
|------|-------|-------|
| `kb_server/ui/templates/base.html` | 111 | Layout, navbar, HTMX error handlers |
| `kb_server/ui/templates/search.html` | 127 | Search form with loading states |
| `kb_server/ui/templates/browse.html` | 217 | Document table with filters and pagination |
| `kb_server/ui/templates/document.html` | 119 | Document detail, chunk accordion |
| `kb_server/ui/templates/error.html` | 17 | Error page with navigation links |
| `kb_server/ui/templates/search_results.html` | 15 | **Critical: unstyled results** |
| `kb_server/ui/templates/document_chunks.html` | 41 | HTMX chunk pagination |
| `kb_server/ui/templates/admin/shell.html` | 156 | Admin layout, Alpine.js tab switching |
| `kb_server/ui/templates/admin/login.html` | 33 | Standalone login page |
| `kb_server/ui/templates/admin/tab_documents.html` | 12 | Documents tab wrapper |
| `kb_server/ui/templates/admin/tab_ingestion.html` | 57 | Ingest trigger + job status |
| `kb_server/ui/templates/admin/tab_ragas.html` | 54 | Evaluation trigger |
| `kb_server/ui/templates/admin/tab_analytics.html` | 84 | Query analytics tables |
| `kb_server/ui/templates/admin/tab_monitoring.html` | 40 | Monitor lights + Grafana iframe |
| `kb_server/ui/templates/admin/tab_admin.html` | 9 | Settings tab wrapper |
| `kb_server/ui/templates/admin/tab_profile.html` | 37 | Profile config display |
| `kb_server/ui/templates/admin/_documents_table.html` | 45 | Reusable document table |
| `kb_server/ui/templates/admin/_job_status.html` | 19 | Job status counts |
| `kb_server/ui/templates/admin/_config_table.html` | 89 | Editable config table with search |
| `kb_server/ui/templates/admin/_monitor_lights.html` | 34 | System health indicators |
| `kb_server/ui/templates/admin/_profile_content.html` | 101 | API keys, GDPR actions |
| `kb_server/ui/static/styles.css` | 141 | Custom styles, hardcoded colors |

---

## Production-Readiness Assessment

**Score: 17/24 — Not production-ready.**

The UI is functional and handles all core interaction states well (loading, error, empty, auth). However, the **search results page is the primary user-facing feature and is currently unstyled plain text**, which is unacceptable for a production RAG system. Additionally, the CSS contains hardcoded color values that block theming and create maintenance risk.

### Must-Fix Before Production:
1. Style search results with cards, metadata, and relevance indicators
2. Replace hardcoded CSS colors with Bootstrap CSS variables
3. Add result scores and source attribution to search output

### Nice-to-Have:
- Add skeleton screens for tab loading
- Add toast notifications for success/error feedback
- Style the login page with brand elements
- Add a favicon

---

## Screenshot Evidence

Screenshots captured at `.planning/ui-reviews/20260616-014950/`:
- `desktop.png` — Homepage (1440x900)
- `mobile.png` — Homepage mobile (375x812)
- `tablet.png` — Homepage tablet (768x1024)
- `search.png` — Search page (1440x900)
- `browse.png` — Browse page (1440x900)
- `admin.png` — Admin panel (1440x900)
- `login.png` — Login page (1440x900)
- `document.png` — Document detail (1440x900)

---

*Audit completed by gsd-ui-auditor — adversarial stance enforced.*
