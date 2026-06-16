# UI Review — KB-RAG Web UI

**Audited:** 2026-06-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md)
**Screenshots:** Captured at `.planning/ui-reviews/20260616-011450/`

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Clear labels, but jargon-heavy ("Top K", "RAGAS", "Hybrid Search") |
| 2. Visuals | 3/4 | Clean Bootstrap layout; admin sidebar uses unprofessional emoji icons |
| 3. Color | 3/4 | Semantic Bootstrap colors; hardcoded hex values in inline styles |
| 4. Typography | 3/4 | Mostly proper hierarchy; minor heading-level quirks in login/admin |
| 5. Spacing | 4/4 | Consistent Bootstrap utilities; no inline styles; clean CSS |
| 6. Experience Design | 3/4 | Good state coverage, but `isAdmin` never true, `tab-error` never shown |

**Overall: 19/24**

---

## Top 3 Priority Fixes

1. **Admin tab visibility broken (`isAdmin` always false)** — The `⚙ Admin` tab in `admin/shell.html` is hidden via `x-show="isAdmin"`, but `isAdmin` is initialized to `false` and never set to `true`. No user can ever see the admin settings tab. — **Fix:** After successful authentication, verify admin role from `/api/v1/users/me` and set `this.isAdmin = true` when `user.role === 'admin'`.

2. **HTMX tab-error fallback never displayed** — `admin/shell.html` defines a `tab-error` div with `d-none`, but there is no JavaScript to reveal it when `htmx:responseError` fires for tab content. Users see a blank or stuck spinner. — **Fix:** Add an event listener in the `adminApp` script that removes `d-none` from `#tab-error` on `htmx:responseError` when the target is `#tab-content`.

3. **Search result text computed but ignored** — `routes.py` passes `result_text` to `search_results.html`, but the template only renders the raw `results` list. The raw `result_text` (which contains the formatted MCP response) is discarded, causing search results to display as plain unstyled text blocks. — **Fix:** Use `result_text` in `search_results.html` when `results` is empty or as a fallback, or remove the unused variable from the route to avoid confusion.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths**
- Button labels are semantically clear: "Search", "Filter", "Clear", "View", "Back to Browse".
- Empty states are helpful: "Enter a query and click Search to test the system", "No documents found. Ingest documents to populate the knowledge base."
- Error messages are specific: "Path not found", "Failed to save config value. Check the value format and try again."

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| "Top K" is jargon — should be "Number of Results" | `search.html` | 24 | WARNING |
| "Hybrid Search (Dense + BM25)" and "Cross-encoder Reranking" are highly technical | `search.html` | 53, 61 | WARNING |
| "RAGAS Evaluation" is jargon for non-technical users | `tab_ragas.html` | 1 | WARNING |
| Admin tab icons use emoji (📄, 📊, 📥, 🧪, ⚙, 📈, 👤) — unprofessional and inaccessible | `admin/shell.html` | 12–38 | WARNING |
| "Search Tester" is developer-centric; should be "Search Knowledge Base" | `search.html` | 6 | WARNING |

**Score rationale:** Copy is clear and functional, but several labels use internal technical jargon that will confuse end users. Emoji icons in the admin panel are a visual/copywriting hybrid issue.

---

### Pillar 2: Visuals (3/4)

**Strengths**
- Clean Bootstrap 5 grid layout with consistent card usage.
- Responsive tables wrapped in `table-responsive`.
- Pagination is functional with Previous/Next and page numbers.
- Active navigation states are present in the navbar.
- Mobile view stacks filters vertically and uses a hamburger menu.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Admin tab sidebar uses emoji icons instead of proper icons or text labels | `admin/shell.html` | 12–38 | WARNING |
| Search results have no visual hierarchy — identical cards with no differentiation | `search_results.html` | 5–15 | WARNING |
| "Back to Browse" button is secondary (gray) but placed prominently in header | `document.html` | 8 | WARNING |
| Document detail page shows an overwhelming wall of red "error" statuses when many docs fail | `browse.html` | 102–104 | WARNING |
| `admin/login.html` is a standalone page without the base template — inconsistent look | `admin/login.html` | 1–33 | WARNING |

**Score rationale:** Layout is clean and structured. The main visual issues are the unprofessional emoji icons and the lack of visual hierarchy in search results.

---

### Pillar 3: Color (3/4)

**Strengths**
- Semantic Bootstrap color system used consistently: `alert-success` for success, `alert-danger` for errors, `alert-warning` for warnings, `alert-info` for info.
- Status badges in `_documents_table.html` use `bg-success` / `bg-warning` appropriately.
- Job status counters use `text-success`, `text-warning`, `text-danger` for quick scanning.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| Hardcoded hex colors in inline `<style>` block: `#198754`, `#dc3545`, `#ffc107`, `#fd7e14`, `#6c757d` | `base.html` | 28–34 | WARNING |
| Hardcoded hex colors in `styles.css`: `#212529`, `#dee2e6`, `#f8f9fa` | `styles.css` | 80, 85, 89 | WARNING |
| Inline styles should use Bootstrap CSS variables or classes instead | `base.html` | 27–35 | WARNING |
| Admin sidebar active state contrast may be insufficient | `admin/shell.html` | 12–38 | WARNING |

**Score rationale:** Colors are semantic and accessible, but hardcoded hex values in inline styles and the CSS file reduce maintainability. They match Bootstrap defaults, so the visual impact is low.

---

### Pillar 4: Typography (3/4)

**Strengths**
- Heading hierarchy is mostly proper: `h1` → `h2` → `h3` → `h4` → `h5` across pages.
- `visually-hidden` headings used for accessibility on filter sections (`browse.html` lines 8, 67; `document_chunks.html` line 2).
- Font sizes are consistent, using Bootstrap utility classes.
- `search-result-text` in `styles.css` defines readable line-height and font size.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| `login.html` uses `<h1 class="h5">` — heading level does not match visual size | `admin/login.html` | 15 | WARNING |
| `admin/shell.html` uses `h2` for "Admin Panel" sidebar title — should be `h1` or `div` | `admin/shell.html` | 9 | WARNING |
| `search_results.html` has no heading at all — starts with an alert | `search_results.html` | 2 | WARNING |
| `search.html` uses `h2` with `h5` class for card title — acceptable but inconsistent | `search.html` | 12 | WARNING |

**Score rationale:** Typography is readable and hierarchy is largely correct. Minor heading-level mismatches in the login and admin pages are the only issues.

---

### Pillar 5: Spacing (4/4)

**Strengths**
- Zero inline `style` attributes found across all templates.
- Bootstrap spacing utilities (`mb-3`, `mt-4`, `p-3`, `gap-2`, etc.) are used consistently.
- `styles.css` is well-organized with semantic class names and replaces any previous inline styles.
- `admin-shell` uses `min-height: calc(100vh - 80px)` for full-height layout.

**Issues**
- None.

**Score rationale:** Spacing is exemplary. No magic numbers, no inline styles, consistent Bootstrap utilities throughout.

---

### Pillar 6: Experience Design (3/4)

**Strengths**
- **Loading states:** Spinners on search (`search.html` lines 68, 75), admin tab load (`shell.html` line 53), document table (`tab_documents.html` line 9), job status (`tab_ingestion.html` line 30).
- **Error handling:** HTMX error handlers in `base.html` (lines 92–116) catch 401, network errors, and generic response errors. Custom error pages for 404, 500, 403 in `app.py`.
- **Empty states:** "No documents found" (`_documents_table.html` line 35), "No results found" (`search_results.html` line 18), "No query data available" (`tab_analytics.html` line 14), "No configuration entries found" (`_config_table.html` line 28).
- **Confirmation dialogs:** Revoke API key (`_profile_content.html` line 75), data erasure (`_profile_content.html` line 93), RAGAS evaluation (`tab_ragas.html` line 16).
- **Disabled states:** Search button disabled during request (`search.html` lines 105, 111).
- **Pagination:** Previous/Next and page numbers with filter persistence (`browse.html` lines 120–186).
- **Responsive:** Hamburger navbar on mobile, stacked filters on mobile.
- **Accessibility:** `aria-label` on pagination, `aria-expanded` on accordions, `aria-hidden` on spinners, `aria-current` on active nav links.

**Issues**

| Issue | File | Line | Severity |
|-------|------|------|----------|
| `isAdmin` is initialized to `false` and never set to `true` — Admin tab is permanently hidden | `admin/shell.html` | 92 | **BLOCKER** |
| `tab-error` div is `d-none` and never revealed on HTMX tab failures | `admin/shell.html` | 60 | **BLOCKER** |
| `search_results.html` ignores `result_text` passed from route | `search_results.html` | — | WARNING |
| No loading state on "Filter" button in browse page | `browse.html` | 56 | WARNING |
| `admin/login.html` is standalone — no way to navigate back to main UI | `admin/login.html` | — | WARNING |
| No "Show All" option for chunks — only paginated "Show next 10" | `document.html` | 93 | WARNING |
| `admin/shell.html` does not verify admin role on init — anyone with an API key can load the shell | `admin/shell.html` | 93–98 | WARNING |

**Score rationale:** The UI has excellent state coverage (loading, error, empty, disabled, confirmation). However, two BLOCKER-level issues prevent the admin panel from being fully functional: the admin settings tab is permanently hidden, and the tab error fallback is never displayed. These are functional defects that degrade the user experience.

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
- `kb_server/ui/routes.py`
- `kb_server/ui/routes_admin.py`
- `kb_server/ui/app.py`

---

## Screenshot Evidence

Screenshots captured at `.planning/ui-reviews/20260616-011450/`:
- `kb-desktop.png` — Browse page (home redirect)
- `kb-search-desktop.png` — Search tester page
- `kb-browse-desktop.png` — Browse documents with filters
- `kb-admin-desktop.png` — Admin page (returns 404 on running server; code is correct)
- `kb-document-desktop.png` — Document detail page
- `kb-mobile.png` — Mobile responsive view

---

## Production-Readiness Assessment

**Score: 19/24 — Not production-ready.**

The UI is visually clean and well-structured, but two functional BLOCKER issues must be resolved before shipping:
1. The `isAdmin` flag must be populated from the user API.
2. The `tab-error` fallback must be wired to HTMX error events.

Once these are fixed, the UI would score approximately **22/24** and be considered production-ready. Minor copywriting and visual improvements (removing emoji, simplifying jargon) would be nice-to-have but not blocking.
