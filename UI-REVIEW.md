# KB-RAG Web UI — UI Review

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md)
**Screenshots:** Captured from running server at http://localhost:8001
**Note:** The running server on port 8001 reflects the `/ui/browse`, `/ui/search`, and `/ui/document` routes, but the `/admin` route and custom error handlers (404/500) return raw JSON (`{"detail":"Not Found"}`), indicating the server process is running older code than the templates in the repo. The audit below assesses the **implemented templates and CSS** as they exist in the codebase.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Minor technical jargon in user-facing labels; empty/error states are contextual and actionable |
| 2. Visuals | 3/4 | Minor inconsistency in status display (badges vs. colored text); search results lack meaningful titles |
| 3. Color | 4/4 | Consistent Bootstrap 5 palette, no hardcoded stray colors |
| 4. Typography | 3/4 | Standard Bootstrap hierarchy, a few custom sizes in CSS |
| 5. Spacing | 3/4 | Bootstrap utilities used well; some necessary arbitrary values in CSS |
| 6. Experience Design | 2/4 | Notable gaps in loading states, missing empty state for Qdrant failures, double-submission risk |

**Overall: 18/24**

---

## Top 3 Priority Fixes

1. **Add loading states and disable buttons during admin actions** — Ingest, Evaluation, and Config load buttons remain clickable and show no spinner while HTMX requests are in flight. Users cannot tell if their action was registered. — Add `hx-indicator` and `disabled` state to the Quick Ingest form, Run Evaluation button, and Config table load.

2. **Give search results meaningful titles/headers** — `search_results.html` renders every result as "Result 1", "Result 2", etc. This is useless for scanning. — Extract the document source or first sentence from `result.text` as the card title.

3. **Fix empty state when chunks fail to load from Qdrant** — In `document.html`, when `chunks` is `None` (Qdrant failure), the template skips both the accordion and the "Chunks Unavailable" empty state, leaving a blank gap. — Add an `{% else %}` branch for `chunks is none` that renders an alert with a retry link.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- Empty states are contextual and actionable:
  - `browse.html:121` — "No documents found matching the current filters. Clear filters or ingest documents."
  - `search_results.html:19` — "No results found for '<strong>{{ query }}</strong>'"
  - `admin/_documents_table.html:39` — "No documents found. Ingest documents to populate the knowledge base."
  - `tab_analytics.html:13` — "No query data available for the last 7 days. Query data appears after users search the knowledge base."
- Error states in `base.html` cover network errors, 401 auth, and generic failures with clear messages.
- `error.html` provides contextual error codes and recovery links ("Try searching" / "browse documents").

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| "Top K" is technical jargon | `search.html` | 24 | WARNING |
| "Hybrid Search (Dense + BM25)" and "Cross-encoder Reranking" are overly technical for a general UI | `search.html` | 51, 59 | WARNING |
| "RAGAS Evaluation" is jargon | `tab_ragas.html` | 1 | WARNING |
| "N/A" fallback used in browse table; could be more descriptive (e.g., "Not specified") | `browse.html` | 99-101 | MINOR |

**Score rationale:** 3/4 — Most copy is clear and contextual, but several labels use backend terminology that end users may not understand.

---

### Pillar 2: Visuals (3/4)

**Strengths**
- Clear visual hierarchy via Bootstrap cards, headings (`h1`, `h2.h5`, `h3.h5`), and alerts.
- Accessibility: `visually-hidden` headings for screen readers (`browse.html:8`, `search_results.html:2`).
- Status colors are applied consistently via CSS classes (`status-completed`, `status-failed`, `status-pending`).
- Admin shell has a clean sidebar layout with active-tab highlighting via Alpine.js.
- Monitor lights in `_monitor_lights.html` use small colored circles with labels — a good compact health indicator.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Inconsistent status display: public browse uses colored text spans, admin table uses solid badges | `browse.html:103` vs `_documents_table.html:23-27` | — | WARNING |
| Search result cards have no meaningful title — "Result 1" is not scannable | `search_results.html` | 10 | WARNING |
| No favicon declared in `base.html` | `base.html` | — | MINOR |
| `tab_profile.html` uses outline badges (`border border-success`) while admin table uses solid badges — minor inconsistency | `tab_profile.html:9` vs `_documents_table.html:23` | — | MINOR |

**Score rationale:** 3/4 — Visual hierarchy is solid, but the status-badge inconsistency and meaningless search-result titles degrade scannability.

---

### Pillar 3: Color (4/4)

**Strengths**
- Entire UI relies on Bootstrap 5 color system (`primary`, `secondary`, `success`, `danger`, `warning`, `info`, `dark`).
- Custom CSS (`styles.css`) only uses Bootstrap-mapped hex values:
  - `#198754` (success)
  - `#dc3545` (danger)
  - `#ffc107` (warning)
  - `#fd7e14` (orange)
  - `#6c757d` (secondary)
- No hardcoded stray colors in templates.
- Accent color (primary/blue) is reserved for main actions: Search, Filter, View, Start Ingest, Run Evaluation, Generate Key.

**Issues**
- None found.

**Score rationale:** 4/4 — Color usage is disciplined, consistent, and fully aligned with Bootstrap 5.

---

### Pillar 4: Typography (3/4)

**Strengths**
- Uses Bootstrap heading classes (`h1`, `h2.h3`, `h2.h5`, `h3.h5`, `h3.h6`) for clear hierarchy.
- `fs-6` used for navbar links.
- `small` and `text-muted` used appropriately for secondary text.
- `search-result-text` uses `font-family: inherit` and `line-height: 1.6` for readable body text.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Custom font sizes outside Bootstrap scale: `0.9rem`, `0.85em`, `1.1rem` | `styles.css` | 47, 51, 66 | MINOR |
| `h4` used for chunk count in `document.html` alongside `h5` card titles — slight size proximity | `document.html` | 59 | MINOR |

**Score rationale:** 3/4 — Mostly standard Bootstrap typography; a few custom sizes in CSS that slightly expand the scale.

---

### Pillar 5: Spacing (3/4)

**Strengths**
- Bootstrap spacing utilities are used consistently: `mt-4`, `mb-4`, `mb-3`, `mb-2`, `ms-2`, `py-3`, `p-4`, `gap-2`, `gap-3`.
- No inline spacing styles in any template.
- All layout dimensions (sidebar width, iframe height, card width) are extracted to `styles.css`.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Arbitrary `max-width: 400px` on chunk titles | `styles.css` | 12 | MINOR |
| Arbitrary `width: 220px` on admin sidebar | `styles.css` | 22 | MINOR |
| Arbitrary `height: 600px` on monitoring iframe | `styles.css` | 29 | MINOR |
| Arbitrary `width: 160px` on monitor cards | `styles.css` | 75 | MINOR |

**Score rationale:** 3/4 — Spacing is well-organized, but several necessary layout values are arbitrary and not part of a formal spacing scale.

---

### Pillar 6: Experience Design (2/4)

**Strengths**
- Loading states present on search page (`search.html:66-80`), browse filter button (`browse.html:56-59`), and admin shell initial load (`shell.html:52-55`).
- Empty states handled for documents, search results, chunks, analytics, and admin tables.
- Error handling for HTMX failures in `base.html` (401, network, generic) and `shell.html` (tab load errors).
- Confirmation dialogs for destructive actions: RAGAS run (`tab_ragas.html:16`), API key revocation (`_profile_content.html:75`), and GDPR erasure (`_profile_content.html:93`).
- Auth-aware UI: login modal in `shell.html`, `x-show="isAuthenticated"` for logout button.
- Pagination with Previous/Next and page numbers in `browse.html`.
- Disabled button state during search in `search.html`.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| No loading indicator on Quick Ingest form — user cannot tell submission is in progress | `tab_ingestion.html` | 10-20 | BLOCKER |
| No loading indicator on Run Evaluation button — double-submission risk | `tab_ragas.html` | 12-17 | BLOCKER |
| No loading indicator on Config table initial load — just "Loading configuration..." text | `tab_admin.html` | 12 | WARNING |
| Search results have no meaningful titles — users cannot scan results | `search_results.html` | 10 | BLOCKER |
| When `chunks` is `None` (Qdrant failure), no empty state is shown — blank gap | `document.html` | 58-106 | WARNING |
| `search_results.html` renders raw `result.text` without truncation or max-height — very long results can break layout | `search_results.html` | 11-13 | WARNING |
| Admin `/admin` route and custom error handlers (404/500) are not served by the running server — returns raw JSON | `routes_admin.py` / `app.py` | — | BLOCKER |

**Score rationale:** 2/4 — Core states are handled, but critical gaps in loading states and search-result scannability degrade the user experience. The running server not reflecting the latest code is an operational blocker for the admin panel and error pages.

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
- `kb_server/ui/app.py`
- `kb_server/ui/routes.py`
- `kb_server/ui/routes_admin.py`

---

## Screenshots Captured

- `.planning/ui-reviews/20250616-000001/search-desktop.png`
- `.planning/ui-reviews/20250616-000001/search-mobile.png`
- `.planning/ui-reviews/20250616-000001/browse-desktop.png`
- `.planning/ui-reviews/20250616-000001/admin-desktop.png` (returns JSON — server out of sync)
- `.planning/ui-reviews/20250616-000001/document-desktop.png`
- `.planning/ui-reviews/20250616-000001/error-404.png` (returns JSON — server out of sync)

---

## Registry Safety

No `components.json` found. Project uses Bootstrap 5 (CDN) and vanilla JS frameworks (HTMX, Alpine.js). No shadcn or third-party registries to audit.

---

## Production Readiness

**Score: 18/24 — Not production-ready.**

The UI is structurally sound and uses Bootstrap 5 consistently, but the **running server does not reflect the latest code** (admin routes and custom error handlers return JSON instead of HTML). Additionally, the missing loading states on admin actions and the meaningless search-result titles are user-facing blockers that should be resolved before declaring the UI production-ready.

**Required before shipping:**
1. Restart/redeploy the UI server so `/admin` and custom error handlers are active.
2. Add `hx-indicator` and button disabled states to Quick Ingest and Run Evaluation.
3. Improve search-result titles to show document source or meaningful snippet.
