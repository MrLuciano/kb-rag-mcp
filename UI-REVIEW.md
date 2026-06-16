# Phase — UI Review

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md)
**Screenshots:** Captured (search-desktop, search-mobile, browse-desktop, admin-desktop from fresh server on port 8002)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | No generic labels; empty/error states are descriptive and actionable |
| 2. Visuals | 3/4 | Admin shell is not responsive on mobile (fixed sidebar causes horizontal scroll); search results lack visual separation |
| 3. Color | 4/4 | Bootstrap 5 palette used consistently; primary accent reserved for CTAs; no arbitrary colors |
| 4. Typography | 4/4 | Semantic heading hierarchy with utility classes; scale stays within 5 sizes |
| 5. Spacing | 3/4 | Bootstrap utilities used consistently; missing margin-bottom on search results |
| 6. Experience Design | 3/4 | Loading and error states present; missing admin document management actions; login modal lacks validation |

**Overall: 21/24**

---

## Top 3 Priority Fixes

1. **Make admin shell responsive** — Mobile users cannot access the admin panel because the fixed-width sidebar (`220px`) does not collapse, causing horizontal overflow. Add a breakpoint to switch `admin-shell` to `flex-column` on viewports < 768px, or use a collapsible offcanvas sidebar.
2. **Add margin to search results** — Multiple search results stack with zero gap because `.search-result-text` has no `margin-bottom`. Add `margin-bottom: 1rem` to `styles.css` for `.search-result-text` so users can visually distinguish results.
3. **Add management actions to admin documents table** — The admin documents tab is read-only even though API endpoints exist for delete, re-ingest, and export. Add "Delete" and "Re-ingest" action buttons to `_documents_table.html` with `hx-confirm` for destructive actions, and wire them to the existing `/api/v1` endpoints.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)
**Strengths**
- No generic CTAs like "Submit" or "Click Here" anywhere in the templates.
- Placeholders are descriptive: "How to install...", "e.g., ArchiveCenter", "e.g., 23.4".
- Empty states explain next steps: "No documents found matching the current filters. Clear filters or ingest documents." (`browse.html:125`)
- Error messages are specific: "Error 404: Not Found — The page you requested does not exist." (`error.html:8`)
- Loading messages are contextual: "Searching knowledge base...", "Loading documents..."

**Issues**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| None found | — | — | — |

---

### Pillar 2: Visuals (3/4)
**Strengths**
- Clear visual hierarchy: dark navbar (`bg-dark`) and white content area create strong contrast.
- Status badges use color-coded Bootstrap classes (`bg-success`, `bg-danger`, `bg-warning`) for instant recognition.
- Loading spinners are present on every primary action (Search, Filter, Ingest, Evaluation).
- Empty states use `alert` components with distinct background colors so they stand out from content.
- Monitor lights use colored circles (`bg-success`/`bg-danger`/`bg-secondary`) with labels for quick health scanning.

**Issues**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin shell sidebar is fixed-width (`220px`) and does not collapse on mobile, causing horizontal overflow | `shell.html` + `styles.css` | `admin-shell` class | **WARNING** |
| Search results have zero margin between them, making multiple results hard to distinguish | `styles.css` | `42` | **WARNING** |

**Rationale:** The mobile responsiveness gap is a notable usability issue for admins who might check the panel on a phone. The missing margin on search results is a minor but repeated visual defect.

---

### Pillar 3: Color (4/4)
**Strengths**
- Bootstrap 5 color system is used throughout: `btn-primary` for CTAs, `btn-secondary` for secondary actions, `alert-*` for states, `text-muted` for metadata.
- CSS custom classes use Bootstrap hex values (e.g., `#198754`, `#dc3545`, `#ffc107`) rather than arbitrary colors.
- Accent color (blue) is used only on declared interactive elements: Search, Filter, Start Ingest, Run Evaluation, Edit, Generate New Key, Log in.
- The 60/30/10 distribution is roughly met: ~60% white/light gray content, ~30% dark gray navbar/sidebar, ~10% blue/green/red accents.

**Issues**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| None found | — | — | — |

---

### Pillar 4: Typography (4/4)
**Strengths**
- Semantic headings are present on every page (`h1` for page title, `h2` for sections, `h3` for card titles).
- Utility classes keep visual size consistent: `h2 class="h5"`, `h2 class="h4"`, `h3 class="h5"`, `h3 class="h6"`.
- Only 5 distinct sizes are in use: `h1` (~2.5rem), `h2` (~2rem), `h3` (~1.75rem), `h4` (~1.5rem), `h5` (~1.25rem), `fs-6` (1rem), `small` (0.875em). This is well within the 4-size threshold.
- Visually hidden headings (`visually-hidden`) maintain accessibility for screen readers on filters, results, and chunks.

**Issues**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| None found | — | — | — |

---

### Pillar 5: Spacing (3/4)
**Strengths**
- Bootstrap spacing utilities are used consistently: `mb-3` for form fields, `mb-4` for section gaps, `p-4` for card padding, `gap-3` for flex gaps, `g-3` for grid gutters.
- No arbitrary pixel values (e.g., `[10px]`, `[1rem]`) are used in utility classes.
- CSS dimensions are layout-specific (e.g., `width: 220px` for sidebar, `height: 600px` for iframe) and are not used for element spacing.

**Issues**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| Missing `margin-bottom` on `.search-result-text` causes results to touch | `styles.css` | `42` | **WARNING** |
| Admin sidebar uses fixed width (`220px`) without responsive spacing adjustments | `styles.css` | `21` | **WARNING** |

---

### Pillar 6: Experience Design (3/4)
**Strengths**
- Loading states are present on all primary actions: Search (`search.html:68`), Filter (`browse.html:58`), Ingest (`tab_ingestion.html:20`), Evaluation (`tab_ragas.html:18`).
- Disabled states are applied to buttons during async requests (`search.html:105`, `browse.html:211`, `tab_ingestion.html:44`, `tab_ragas.html:42`).
- Error states are handled globally in `base.html` for HTMX failures, and locally in `search.html`, `shell.html`, and `_config_table.html`.
- Empty states are handled for browse, search results, analytics, monitoring, documents, and chunks.
- Confirmation dialogs are used for destructive actions: revoke API key (`_profile_content.html:75`), data erasure (`_profile_content.html:93`), and RAGAS evaluation (`tab_ragas.html:16`).
- The login modal is shown on 401 responses (`base.html:84`).
- Document chunks support pagination with a "Show next 10 chunks" button and a "Show less" button (`document.html:99`, `document_chunks.html:29`).

**Issues**
| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin documents table is read-only; no Delete, Re-ingest, or Export actions despite API endpoints existing | `_documents_table.html` | `1-41` | **WARNING** |
| Login modal stores API key and hides immediately without validating it; user may appear authenticated but get 401s | `shell.html` | `130-144` | **WARNING** |
| Admin config/profile tabs call `fetch` but do not display error messages on network or API failures | `_config_table.html` | `48-52` | **WARNING** |
| Admin `htmx:responseError` handler in `shell.html` conflicts with global 401 handler in `base.html` for tab loads | `shell.html` | `88-95` | **WARNING** |

**Rationale:** The missing admin management actions are the most notable gap. The login modal validation gap is a secondary UX issue that can leave users confused. The fetch error handling gap means broken APIs degrade silently.

---

## Screenshots

| Screenshot | Viewport | Description |
|------------|----------|-------------|
| `search-desktop.png` | 1440x900 | Search Tester page with form and empty-state alert |
| `search-mobile.png` | 375x812 | Search Tester page on mobile; navbar collapses, form stacks |
| `browse-desktop.png` | 1440x900 | Browse Documents page with filter card and empty-state table |
| `admin-desktop.png` | 1440x900 | Admin shell with sidebar and Documents tab loading state |

**Note:** The original server on port 8001 was serving an outdated template revision (inline styles, missing Alpine.js, missing `/static/styles.css`). Screenshots were captured from a fresh server instance started on port 8002 to reflect the current code on disk.

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

## Production Readiness

**Score: 21/24 — Not production-ready.**

The UI is well-built and polished on desktop, but the following gaps prevent a production-ready declaration:
1. **Mobile responsiveness:** The admin shell sidebar does not adapt to small viewports.
2. **Search result spacing:** Results visually merge without margin.
3. **Admin document management:** Admins cannot perform CRUD actions on documents from the UI.

All three are fixable with targeted template and CSS changes. Once resolved, the UI would score 22+/24 and be production-ready.

---

## Registry Safety

No `components.json` found; project is Python-based with no shadcn or third-party UI registries. Registry audit skipped.
