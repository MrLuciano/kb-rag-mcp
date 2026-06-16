# Phase — UI Review

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md)
**Screenshots:** Captured (desktop, mobile, tablet)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Domain-specific, clear labels; empty/error states well-written |
| 2. Visuals | 2/4 | Search results lack metadata cards; status display inconsistent between browse and admin |
| 3. Color | 3/4 | Bootstrap palette consistent; minor hardcoded hex values in CSS instead of vars |
| 4. Typography | 3/4 | Good heading hierarchy; minor jump from h3 to h6 in profile page |
| 5. Spacing | 3/4 | Bootstrap utilities used well; some arbitrary fixed widths/heights in CSS |
| 6. Experience Design | 2/4 | Search results omit critical source/score metadata; no skeleton loading states |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Add source metadata to search results** — Search results show only raw chunk text with no source document, relevance score, or "View Document" link. In a RAG system, provenance is critical for user trust. Add a card header showing `source_file`, `score`, `chunk_id`, and a link to `/ui/document/{doc_id}`. Score: 2/4 → 3/4 for Visuals and Experience Design.

2. **Standardize status display across tables** — `browse.html` uses plain text `<span class="status-{status}">` while `admin/_documents_table.html` uses Bootstrap badges (`bg-success`, `bg-danger`, `bg-warning`). Unify on badges for consistency and stronger visual scanning. Score: bumps Visuals.

3. **Replace `alert()` in config editor with inline toast** — `admin/_config_table.html` uses `alert()` for save errors. Browser alerts block the UI and feel jarring. Use an inline Bootstrap `alert` or toast component. Score: bumps Experience Design.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

**Strengths:**
- All CTA labels are domain-specific: "Search Tester", "Browse Documents", "Run Evaluation", "Start Ingest".
- Empty states are helpful and actionable: "No documents found matching the current filters. Clear filters or ingest documents." (`browse.html:121`)
- Error recovery is clear: "Try searching or browse documents." (`error.html:12`)
- Admin panel labels are precise: "Query Analytics", "RAGAS Evaluation", "System configuration (admin only)."
- Accessibility labels use `visually-hidden` for screen readers (`browse.html:8`, `search_results.html:2`, `document_chunks.html:2`).

**Issues:**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| "Start Ingest" is slightly awkward phrasing | `admin/tab_ingestion.html` | 40 | MINOR |
| Unicode refresh symbol `↻` may not render on all systems | `admin/tab_analytics.html` | 8 | MINOR |

**Score Rationale:** Minor phrasing quirks do not affect comprehension. All user-facing text is specific, actionable, and appropriately friendly for an internal admin tool.

---

### Pillar 2: Visuals (2/4)

**Strengths:**
- Clean Bootstrap 5 admin shell with sidebar navigation (`admin/shell.html`).
- Monitor lights provide an at-a-glance health dashboard (`admin/_monitor_lights.html`).
- Document detail page uses accordion chunks with progressive disclosure (`document.html`).
- Pagination on browse page is well-structured with ellipsis truncation (`browse.html:153`).
- Login modal is centered and focused (`admin/shell.html:65`).

**Issues:**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| **Search results show only raw text with no source, score, or provenance** — critical gap for RAG trust | `search_results.html` | 7-14 | **BLOCKER** |
| Status in browse table uses plain colored text instead of badges (inconsistent with admin table) | `browse.html` | 103 | WARNING |
| Profile config section lacks visual grouping/card (raw text with badges) | `admin/tab_profile.html` | 4-29 | WARNING |
| Search results lack any heading/title per result card | `search_results.html` | 7-14 | WARNING |
| RAGAS "Last Run" card is plain text with no visual prominence when empty | `admin/tab_ragas.html` | 28 | MINOR |

**Score Rationale:** The **BLOCKER** issue is significant. Search results are the primary output of a RAG system; presenting them as anonymous text blocks without source attribution or confidence scores undermines the entire value proposition. The status inconsistency and profile page rawness are notable secondary issues.

---

### Pillar 3: Color (3/4)

**Strengths:**
- Uses Bootstrap 5 semantic color classes (`btn-primary`, `alert-success`, `bg-danger`, `text-muted`) consistently.
- Status colors map to Bootstrap palette: `#198754` (success), `#dc3545` (danger), `#ffc107` (warning), `#6c757d` (gray), `#fd7e14` (orange), `#212529` (dark).
- Admin badges use proper semantic backgrounds: `bg-success`, `bg-danger`, `bg-warning`, `bg-info`.

**Issues:**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| Hardcoded hex values in CSS instead of Bootstrap CSS variables (`--bs-success`, `--bs-danger`) | `styles.css` | 34-39 | WARNING |
| `.search-result-text h2` hardcodes `#212529` instead of inheriting | `styles.css` | 54 | MINOR |
| `.search-result-text code` hardcodes `#f8f9fa` | `styles.css` | 63 | MINOR |

**Score Rationale:** Colors are consistent and on-brand, but the hardcoded hex values reduce theme flexibility. If the project ever switches to a dark mode or custom Bootstrap theme, these colors will not adapt. This is a maintainability issue, not a user-facing one.

---

### Pillar 4: Typography (3/4)

**Strengths:**
- Good heading hierarchy: `h1` for page titles, `h2` with `.h5` for card titles, `h3` with `.h5` for sub-sections.
- `search-result-text` uses `font-size: 0.9rem` and `line-height: 1.6` for readability.
- `code` elements inside search results use `font-size: 0.85em` for subtle differentiation.
- System font stack (Bootstrap default) ensures fast rendering and native feel.

**Issues:**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| Large heading jump from `h3` to `h6` in profile page | `admin/tab_profile.html` | 5 | MINOR |
| Search result cards have no internal heading hierarchy (no title or metadata label) | `search_results.html` | 7-14 | WARNING |
| `h4` used for large stat numbers in job status — semantically odd but visually okay | `admin/_job_status.html` | 6, 10, 14 | MINOR |

**Score Rationale:** Typography is generally solid and consistent with Bootstrap's scale. The main gap is the lack of headings within search result cards, which hurts scannability. The `h3` → `h6` jump is a minor hierarchy violation.

---

### Pillar 5: Spacing (3/4)

**Strengths:**
- Heavy use of Bootstrap utility spacing: `mt-4`, `mb-4`, `mb-3`, `mb-2`, `p-3`, `p-4`, `py-3`, `gap-2`, `gap-3`, `ms-2`.
- Consistent card padding and margin rhythm across pages.
- `table-responsive` wrappers used correctly for data tables.

**Issues:**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| Arbitrary fixed widths: `220px` sidebar, `160px` monitor cards, `300px` config search | `styles.css` | 22, 75, 93 | MINOR |
| Arbitrary iframe height `600px` | `styles.css` | 29 | MINOR |
| `max-width: 400px` on chunk titles | `styles.css` | 12 | MINOR |

**Score Rationale:** The arbitrary values are reasonable for the layout (220px is a standard sidebar, 600px is a reasonable iframe height). However, using Bootstrap's spacing scale or CSS `clamp()` would improve responsiveness. No spacing inconsistencies that break layouts.

---

### Pillar 6: Experience Design (2/4)

**Strengths:**
- **Loading states:** Spinners on search, filter, ingest, and RAGAS buttons. Button disabled during load.
- **Empty states:** Excellent coverage across browse, search, analytics, documents table, config table, and profile.
- **Error states:** HTMX error handlers show contextual messages (`base.html:82`, `search.html:116`).
- **Confirmation dialogs:** `confirm()` used for destructive actions: revoke API key and request data erasure (`admin/_profile_content.html:75`, `93`).
- **Auto-refresh:** Job status refreshes every 10s, monitor lights every 30s.
- **Progressive disclosure:** Accordion chunks with "Show next 10 chunks" and "Show less" pagination.
- **Auth flow:** Login modal, API key storage, logout, admin role gating.

**Issues:**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| **Search results omit critical metadata (source, score, chunk ID)** — users cannot verify provenance | `search_results.html` | 7-14 | **BLOCKER** |
| `alert()` blocks UI thread for config save errors | `admin/_config_table.html` | 71 | WARNING |
| No skeleton loading states (only generic spinners) | Multiple | — | WARNING |
| Search results do not indicate if hybrid/rerank was applied | `search_results.html` | — | MINOR |
| No error boundary for chunk loading failures beyond `alert` | `document.html` | 106-110 | MINOR |

**Score Rationale:** The search results **BLOCKER** is an experience design failure: a RAG system that cannot show where an answer came from is fundamentally incomplete. The `alert()` usage and lack of skeleton screens are notable gaps. The empty state coverage is excellent, which prevents the score from dropping to 1.

---

## Files Audited

### Core Templates
- `kb_server/ui/templates/base.html`
- `kb_server/ui/templates/search.html`
- `kb_server/ui/templates/browse.html`
- `kb_server/ui/templates/document.html`
- `kb_server/ui/templates/error.html`
- `kb_server/ui/templates/search_results.html`
- `kb_server/ui/templates/document_chunks.html`

### Admin Templates
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

### Styles
- `kb_server/ui/static/styles.css`

### Backend (reference for result schema)
- `kb_server/ui/routes.py`
- `kb_server/server.py`

---

## Production Readiness

**Not production-ready.** Score is **17/24**, below the 22/24 threshold.

The UI is functional and well-structured for an admin tool, but the **search results lack source attribution and scores**, which is a critical gap for a RAG system. Users cannot verify where answers come from, which undermines trust and utility. Fixing the top 3 issues (especially #1) would raise the score to approximately **21/24**.
