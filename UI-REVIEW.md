# UI Review — KB-RAG Web UI

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured at `.planning/ui-reviews/20260616-015206/`

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Clear labels overall; jargon persists ("RAGAS", "Chunks", "Top K") |
| 2. Visuals | 3/4 | Good hierarchy on browse/document; search results are raw text dumps |
| 3. Color | 3/4 | Bootstrap semantic colors used well; outline badges lack visibility |
| 4. Typography | 4/4 | Consistent heading scale, good use of `code`/`small`/`text-muted` |
| 5. Spacing | 4/4 | Bootstrap grid and utilities used consistently; no arbitrary values |
| 6. Experience Design | 3/4 | Loading/error/empty states covered; search results lack metadata and source links |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Search results are raw text dumps with no metadata** — Users cannot see which document a result came from, its relevance score, or navigate to the source. — Add document source, score, and a "View Document" link to each result in `search_results.html`.

2. **Admin documents table lacks pagination** — The admin panel's documents table only shows 20 records with no way to browse more. — Add pagination controls to `_documents_table.html` matching the browse page pattern.

3. **Profile/config badges are outline-only and hard to read** — `badge text-success border border-success` creates thin outline badges that are low-contrast. — Change to filled `badge bg-success`/`bg-danger` for better visibility.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- Form labels are descriptive: "Query *", "Number of Results", "Optional filter".
- Empty states are specific: "No documents found matching the current filters. Clear filters or ingest documents." (`browse.html:125-128`)
- Error messages provide actionable next steps: "Try searching or browse documents." (`error.html:12-13`)
- HTMX error handlers have distinct messages for 401 vs network errors (`base.html:94-104`)

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Technical jargon "RAGAS Evaluation" used as page title | `tab_ragas.html` | 1 | WARNING |
| Technical term "Chunks" exposed to end users throughout UI | `browse.html`, `document.html` | multiple | WARNING |
| Form label "Top K" is technical jargon; field label actually reads "Number of Results" which is fine, but internal naming leaks | `search.html` | 24 | MINOR |
| Generic "N/A" fallback for missing metadata fields | `document.html`, `browse.html` | multiple | MINOR |

**Score Rationale:** Copy is mostly clear and actionable, but technical jargon (RAGAS, chunks) and generic fallback text prevent a 4/4.

---

### Pillar 2: Visuals (3/4)

**Strengths**
- Clear visual hierarchy: `h1` page titles, `h2`/`h3` section headers, `h5` card titles.
- Status badges provide immediate color-coded status recognition (`badge bg-success`/`bg-danger`/`bg-warning`).
- Monitor light cards are compact, scannable health indicators (`_monitor_lights.html`).
- Loading spinners on buttons and content areas give clear feedback.
- Pagination uses ellipsis truncation for large page ranges (`browse.html:157-177`).

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results are raw text dumps with no visual hierarchy, metadata, or source links | `search_results.html` | 8-11 | **BLOCKER** |
| Admin documents table has no pagination — only 20 records shown | `_documents_table.html` | 40 | WARNING |
| Job status numbers are dumped in a loose flex container without grid alignment | `_job_status.html` | 4-17 | WARNING |
| Login page is extremely minimal with no branding or visual interest | `login.html` | 9-32 | MINOR |
| "Show less" button in chunk pagination reloads the entire page | `document_chunks.html` | 36-40 | WARNING |

**Score Rationale:** Browse and document pages have strong visual hierarchy, but the search results page — a primary user task — is a plain text dump. Admin table lacks pagination.

---

### Pillar 3: Color (3/4)

**Strengths**
- Zero hardcoded hex colors in templates.
- `styles.css` uses Bootstrap CSS variables exclusively: `var(--bs-success)`, `var(--bs-danger)`, `var(--bs-light)`, `var(--bs-border-color)`.
- Semantic color usage is consistent: `bg-success` for completed, `bg-danger` for failed, `bg-warning` for pending.
- `text-muted` is used appropriately for secondary text throughout.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Profile/config badges use outline-only styling (`text-success border border-success`) which is low-contrast | `tab_profile.html` | 9-27 | WARNING |
| Search results use `alert-success` for merely finding results — semantically odd | `search_results.html` | 3 | MINOR |
| Monitor light cards use `bg-secondary` for unconfigured state, which is acceptable but could be more neutral | `_monitor_lights.html` | 27 | MINOR |

**Score Rationale:** Color system is clean and Bootstrap-native, but outline badges on the profile page reduce readability. Alert-success for search results is slightly off-semantically.

---

### Pillar 4: Typography (4/4)

**Strengths**
- Consistent heading scale: `h1` for page titles, `h2` for sections, `h3` for card titles, `h5` for sub-cards, `h6` for config groups.
- `code` tags used for technical values (hash, query text, config keys).
- `small` and `text-muted` used for descriptive/hint text.
- `search-result-text` CSS class provides proper `font-family: inherit`, `font-size: 0.9rem`, and `line-height: 1.6`.
- Chunk preview uses `white-space: pre-wrap` with `word-break: break-word` for readability.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| `fs-6` on nav links is redundant (Bootstrap `nav-link` default is already appropriate) | `base.html` | 43, 49, 55 | MINOR |

**Score Rationale:** Typography is well-structured, readable, and consistently applied. One minor redundancy.

---

### Pillar 5: Spacing (4/4)

**Strengths**
- Bootstrap grid used consistently: `row`, `col-md-4`, `col-md-8`, `col-md-3`, `col-md-6`.
- Spacing utilities applied uniformly: `mb-3` for form groups, `mb-4` for sections, `mt-2` for stacked elements, `gap-2`/`gap-3` for flex children.
- No arbitrary Tailwind-style bracket values (`[24px]`) found.
- Admin shell uses custom CSS for sidebar width (`220px`) and min-height (`calc(100vh - 80px)`) which is documented and justified.
- Mobile responsive admin shell uses media queries (`@media (max-width: 768px)`).

**Issues**
- None found.

**Score Rationale:** Spacing is consistent, grid-based, and responsive. No arbitrary or non-standard spacing values.

---

### Pillar 6: Experience Design (3/4)

**Strengths**
- **Loading states:** Spinner borders on buttons (`search.html:68`, `browse.html:58`, `tab_ingestion.html:20`), loading indicators in content areas (`tab_documents.html:8-11`), and HTMX `hx-indicator` integration.
- **Error states:** Global HTMX error handlers for 401, network errors, and generic failures (`base.html:82-106`). Config save error div (`_config_table.html:29-31`). Tab load error div (`shell.html:60-62`).
- **Empty states:** No documents (`browse.html:125-128`, `_documents_table.html:42-44`), no query data (`tab_analytics.html:13-16`), no config entries (`_config_table.html:28`), no chunks (`document.html:108-111`), chunk load failure (`document.html:113-116`).
- **Disabled states:** Buttons disabled during submission (`search.html:105`, `browse.html:211`, `tab_ingestion.html:44`).
- **Confirmation dialogs:** `hx-confirm` on RAGAS run (`tab_ragas.html:16`), `confirm()` on API key revocation and erasure (`_profile_content.html:75`, `93`).
- **Auto-refresh:** Job status poll every 10s (`tab_ingestion.html:30`), monitor lights every 30s (`tab_monitoring.html:7`).
- **Pagination:** Full pagination with Previous/Next and ellipsis truncation (`browse.html:132-198`).
- **HTMX partial updates:** Chunk pagination (`document_chunks.html:29-34`), tab content (`shell.html:47-51`), config table (`tab_admin.html:4-9`), profile content (`tab_profile.html:32-37`).
- **Authentication:** Login modal with `data-bs-backdrop="static"` (`shell.html:65`), API key stored in localStorage, bearer token injected into HTMX requests (`base.html:76-80`).

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results lack document source, score, and navigation — users cannot act on results | `search_results.html` | 8-11 | **BLOCKER** |
| Admin documents table has no pagination — limited to 20 records | `_documents_table.html` | 40 | WARNING |
| "Show less" button reloads the entire page body instead of collapsing accordion | `document_chunks.html` | 36-40 | WARNING |
| No error handling for RAGAS evaluation button — no user feedback on failure | `tab_ragas.html` | 12-19 | WARNING |
| No empty state for job status when all counts are zero — card shows zeros with no context | `_job_status.html` | 4-17 | MINOR |
| Ingest result div starts empty with no placeholder — user doesn't know what to expect | `tab_ingestion.html` | 23 | MINOR |
| Login modal has no close button (intentional but rigid) | `shell.html` | 65 | MINOR |

**Score Rationale:** State coverage is comprehensive for loading, error, and empty states. The primary blocker is that search results — the core user task — are raw text dumps with no actionable metadata. Admin table pagination is also missing.

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

### Routes
- `kb_server/ui/app.py`
- `kb_server/ui/routes.py`
- `kb_server/ui/routes_admin.py`

---

## Screenshots Captured

| Screenshot | File |
|------------|------|
| Desktop Search | `.planning/ui-reviews/20260616-015206/desktop-search.png` |
| Desktop Browse | `.planning/ui-reviews/20260616-015206/desktop-browse.png` |
| Desktop Document | `.planning/ui-reviews/20260616-015206/desktop-document.png` |
| Desktop Login | `.planning/ui-reviews/20260616-015206/desktop-login.png` |
| Mobile Search | `.planning/ui-reviews/20260616-015206/mobile-search.png` |
| Tablet Search | `.planning/ui-reviews/20260616-015206/tablet-search.png` |

---

## Production Readiness

**Score: 20/24 — Not production-ready.**

The UI is solid for browsing and document inspection, but the **search results page is a critical blocker**. Users performing the primary task (searching the knowledge base) receive raw text with no document source, no relevance score, and no way to navigate to the original document. This breaks the core user journey.

The remaining issues (admin pagination, profile badge visibility) are warnings that should be addressed before a wider rollout but do not block basic task completion.

---

## Additional Notes

- **Discrepancy between repo and running server:** The running server on `localhost:8001` rendered HTML with inline `<style>` blocks containing hardcoded hex colors and a different search form implementation than the files in the repo. The repo files are the canonical source for this audit; the server may be running stale cached code.
- **No UI-SPEC.md exists:** This audit was conducted against abstract 6-pillar standards rather than a specific design contract.
- **Bootstrap 5 + HTMX + Alpine.js:** The stack is well-chosen and consistently applied. The admin shell's Alpine.js tab switching is clean, and HTMX partial updates work across the app.
