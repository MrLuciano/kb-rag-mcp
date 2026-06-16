# Phase UI — UI Review

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Captured at `.planning/ui-reviews/20260616-013431/`

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Clear labels and helpful placeholders; minor branding inconsistency |
| 2. Visuals | 2/4 | Search results are plain text dumps; malformed HTML in ingestion form |
| 3. Color | 3/4 | Bootstrap semantic colors used well; hardcoded hex values in CSS |
| 4. Typography | 3/4 | Bootstrap scale mostly followed; custom sizes in CSS |
| 5. Spacing | 3/4 | Bootstrap utilities used well; arbitrary CSS values present |
| 6. Experience Design | 2/4 | Search results lack critical metadata; config save uses `alert()` |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Search results lack source metadata, scores, and chunk index** — Users cannot see which document a result came from, its relevance score, or the chunk index. This is a critical RAG UI failure. — Add document source link, score badge, and chunk index to `search_results.html`.
2. **Malformed HTML and missing label in tab ingestion form** — The `<script>` tag in `tab_ingestion.html` is placed inside the `<form>` after a `</div>` and before the `<button>`, which is invalid structure. The path input also has no `<label>`. — Move the script to `extra_scripts` block and add a proper `<label for="path">`.
3. **Config save uses browser `alert()`** — `_config_table.html` uses `alert('Failed to save config value...')` which interrupts the user flow. — Replace with a Bootstrap inline alert or toast notification.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- All form labels are descriptive and contextual: "Query", "Number of Results", "Product", "Version"
- Placeholders are helpful: `placeholder="How to install..."`, `placeholder="e.g., ArchiveCenter"`
- Empty states are actionable: "No documents found matching the current filters. Clear filters or ingest documents."
- Error messages are descriptive: "Chunk data could not be loaded from the vector store. Please try again later."
- No generic "Submit" or "Click Here" buttons found.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Branding inconsistency: error page title says "Knowledge Base" while rest of app says "KB-RAG" | `error.html` | 3 | WARNING |
| Config save error uses generic browser `alert()` | `admin/_config_table.html` | 71 | WARNING |

**Score Rationale:** Copywriting is generally strong with contextual labels and helpful empty states. Minor branding inconsistency and one generic `alert()` prevent a 4.

---

### Pillar 2: Visuals (2/4)

**Strengths**
- Clear visual hierarchy with h1/h2/h3 and Bootstrap cards
- Status badges use semantic colors (success/danger/warning) consistently across `browse.html`, `document.html`, `admin/_documents_table.html`
- Loading spinners on buttons (search, filter, ingest, ragas) with `btn-text` / spinner swap pattern
- Monitor lights in `_monitor_lights.html` provide clear color-coded status indicators
- Accordion for chunk display with smart collapse/expand (first 10 open, rest closed)
- Pagination with smart ellipsis logic (`browse.html` lines 132-198)
- Responsive tables with `table-responsive` wrapper

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results are plain text dumps with no cards, metadata, scores, or source links | `search_results.html` | 6-10 | BLOCKER |
| Malformed HTML: `<script>` tag is inside `<form>` but after `</div>` and before `<button>` | `admin/tab_ingestion.html` | 17-43 | BLOCKER |
| Path input has no `<label>` — only a placeholder | `admin/tab_ingestion.html` | 14-15 | BLOCKER |
| Leftover badge examples with no context in admin settings | `admin/tab_admin.html` | 4-7 | WARNING |
| `admin/login.html` heading is `h1 class="h5"` — semantic/visual mismatch | `admin/login.html` | 15 | WARNING |

**Score Rationale:** The search results presentation is a critical visual failure — users are dumped raw text without any context. The malformed HTML in the ingestion form and missing label are also serious. These structural issues outweigh the otherwise good hierarchy.

---

### Pillar 3: Color (3/4)

**Strengths**
- Bootstrap semantic colors (`bg-success`, `bg-danger`, `bg-warning`, `text-primary`, etc.) used consistently
- Monitor lights use semantic colors for health status
- Admin sidebar uses `bg-dark` with `text-white` for good contrast
- Status badges are color-coded correctly across all tables

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Hardcoded hex colors in CSS that map to Bootstrap but bypass the token system | `styles.css` | 34-39, 54, 59, 63 | WARNING |
| No dark mode support | — | — | WARNING |

**Score Rationale:** Color usage is mostly correct and semantic. Hardcoded hex values in CSS (e.g., `#198754`, `#dc3545`) are Bootstrap color mappings but bypass the Bootstrap token system. No dark mode support is a minor gap.

---

### Pillar 4: Typography (3/4)

**Strengths**
- Bootstrap heading classes (`h1` through `h6`) used consistently
- `font-family: inherit` on `.search-result-text` prevents monospace intrusion — good choice
- `line-height: 1.6` on search results improves readability
- `fs-6` used for nav links in `base.html`
- `visually-hidden` used for accessible headings (e.g., "Filters", "Results", "Search Results")

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Custom font sizes in CSS (`0.9rem`, `1.1rem`, `0.85em`) outside Bootstrap type scale | `styles.css` | 46, 51, 66 | WARNING |
| Inconsistent heading levels for card titles: `h2 class="h5"` vs `h3 class="h5"` | `search.html`, `tab_ingestion.html` | 12, 8 | WARNING |

**Score Rationale:** Typography is mostly consistent with Bootstrap's scale. Custom font sizes in CSS and minor heading-level inconsistency prevent a 4.

---

### Pillar 5: Spacing (3/4)

**Strengths**
- Bootstrap spacing utilities (`p-3`, `p-4`, `mb-3`, `mt-2`, `gap-2`, `gap-3`) used consistently
- `flex-grow-1` and `flex-column` used correctly in admin shell layout
- Cards and tables have adequate internal padding

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Arbitrary width values in CSS (`220px`, `160px`, `400px`, `300px`) | `styles.css` | 12, 22, 75, 93 | WARNING |
| `min-height: calc(100vh - 80px)` is fragile if navbar height changes | `styles.css` | 17 | WARNING |
| `monitoring-iframe` has fixed height `600px` | `styles.css` | 29 | WARNING |

**Score Rationale:** Spacing is well-structured with Bootstrap utilities. Some arbitrary CSS values for layout dimensions are documented but not part of the Bootstrap spacing system.

---

### Pillar 6: Experience Design (2/4)

**Strengths**
- **Loading states:** Button spinners on search, filter, ingest, ragas; HTMX loading indicators in admin tabs
- **Empty states:** Handled in browse, documents table, analytics, config table, search results
- **Error states:** HTMX `responseError` and `sendError` handlers with fallback messages; error page with recovery links
- **Confirmations:** Config save, API key revocation, data erasure, and RAGAS run all use confirmation dialogs
- **Disabled states:** Buttons disabled during async operations
- **Pagination:** Smart ellipsis with filter preservation
- **Chunk lazy loading:** HTMX-powered "Show next 10 chunks" with "Show less" fallback
- **Auth flow:** Login modal with localStorage API key, auto-prompt on 401
- **Accessibility:** `aria-hidden` on decorative spinners, `visually-hidden` on screen-reader text, `aria-expanded` on accordions, `role="alert"` on alerts

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Search results lack source document, score, and chunk index — users cannot trace results | `search_results.html` | 6-10 | BLOCKER |
| Malformed HTML in ingestion form may cause JS errors | `admin/tab_ingestion.html` | 17-43 | BLOCKER |
| Config save error uses browser `alert()` — interrupts flow | `admin/_config_table.html` | 71 | WARNING |
| Ingestion path input has no label — accessibility failure | `admin/tab_ingestion.html` | 14-15 | WARNING |
| No visual feedback for successful config save | `admin/_config_table.html` | — | WARNING |
| No undo for destructive actions (revoke key, data erasure) | `admin/_profile_content.html` | — | WARNING |
| `tab_admin.html` has non-functional badge examples | `admin/tab_admin.html` | 4-7 | WARNING |

**Score Rationale:** Many good UX patterns are in place (loading, empty, error states, confirmations, pagination). However, the search results lack critical metadata which is a BLOCKER for a RAG system. The malformed HTML and `alert()` usage are notable gaps. The score is pulled down by the primary user flow failure.

---

## Registry Safety

`components.json` not found — shadcn not initialized. Registry audit skipped.

---

## Files Audited

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
- `kb_server/ui/static/styles.css`

---

## Summary

The UI is **not production-ready** (score 16/24, below 22 threshold). While the admin panel, browse page, and document detail page have good UX patterns, the search results page — the primary user flow for a RAG system — is critically inadequate. It dumps raw text without source attribution, relevance scores, or chunk metadata. Additionally, the ingestion form has malformed HTML and a missing label that could break functionality or fail accessibility audits.

### Fix Completeness Assessment
- **Status badge fixes:** Complete — badges are consistent across all templates.
- **Search results layout fixes:** Incomplete — the `search-result-text` class improves rendering but the layout still lacks source metadata, scores, and chunk index. This is a partial fix, not a complete resolution.
- **New issues found:** Malformed HTML in `tab_ingestion.html`, missing label on ingestion path input, `alert()` in config table, leftover badge examples in `tab_admin.html`.
