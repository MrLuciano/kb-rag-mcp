# Phase 28c — UI Review

**Audited:** 2026-06-16
**Baseline:** 28c-UI-SPEC.md (approved design contract)
**Screenshots:** Not captured (no dev server running)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | Multiple label/empty-state mismatches with spec; tab names diverge |
| 2. Visuals | 2/4 | Sidebar width wrong, missing document table features, monitor lights incomplete |
| 3. Color | 3/4 | Missing warning (yellow) state in monitor lights; profile status uses text-* not bg-* |
| 4. Typography | 2/4 | Table headers not semibold; modal title undersized; text-white vs spec text-light |
| 5. Spacing | 2/4 | Sidebar 220px instead of 280px; mobile collapse not icon-only |
| 6. Experience Design | 1/4 | BLOCKER: Auth flow diverges from spec — no JWT session cookie exchange |

**Overall: 12/24**

---

## Top 3 Priority Fixes

1. **BLOCKER: Auth flow does not exchange API key for JWT session cookie** — `shell.html:authenticate()` stores the raw API key in `localStorage` and calls `/api/v1/users/me` directly. It never POSTs to `/api/v1/auth/session` to receive the HttpOnly JWT session cookie. This breaks the designed security model (8h expiry, SameSite=Lax, server-side session validation). The login modal also uses Bootstrap JS API instead of Alpine.js `x-show` for visibility control. **Fix:** Rewrite `authenticate()` to POST to `/api/v1/auth/session`, handle 200/401/403 responses, and use Alpine.js `x-show="!isAuthenticated"` on the modal.

2. **Document browse table lacks checkbox column, bulk toolbar, and per-document actions** — The spec (SPA-09) requires a checkbox column with "select all" header, a toolbar that appears when ≥1 row is selected (Delete, Re-ingest, Delete Failed), and a per-document Actions dropdown. `_documents_table.html` only has a "View" button. **Fix:** Add checkbox column, selection state tracking, bulk action toolbar, and per-row dropdown with View, Delete (with `hx-confirm`), and Re-ingest actions.

3. **CSP nonce and SRI gaps on two templates** — `tab_ragas.html:36` has a `<script>` tag without `nonce="{{ get_nonce(request) }}"`, which violates the strict CSP and will cause the script to be blocked. `login.html:7` loads Bootstrap CSS without an `integrity` attribute, breaking the SRI contract. **Fix:** Add `nonce` to `tab_ragas.html` script and add SRI hash to `login.html` Bootstrap CSS link.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**What the spec required vs. what was implemented:**

| Element | Spec Copy | Actual Copy | File:Line |
|---------|-----------|-------------|-----------|
| Login modal heading | "Login to Admin Panel" | "Authentication Required" | shell.html:69 |
| API key placeholder | `kb_xxxxxxxx...` | "Enter API key" | shell.html:74 |
| Login error | "Invalid API key. Please check..." | "Failed to load content. Please try again later." | base.html:94 |
| Empty state — documents | "No documents found. No documents match your search filters. Try adjusting your filter criteria or clear all filters." | "No documents found. Ingest documents to populate the knowledge base." | _documents_table.html:43 |
| Empty state — RAGAS | "No evaluation results yet. Run an evaluation to see results here." | "No evaluation run yet." | tab_ragas.html:29 |
| Config search placeholder | "Search config keys..." | "Search config..." | _config_table.html:4 |
| Ingestion CTA | "Ingest Now" | "Start Ingest" | tab_ingestion.html:18 |
| Sidebar tab — RAGAS | "RAGAS Evaluation" | "Evaluation" | shell.html:25 |
| Sidebar tab — Admin | "Admin" | "Settings" | shell.html:29 |
| Revoke API key confirm | "Revoke API key: Are you sure you want to revoke this key? Applications using this key will lose access immediately." | "Revoke this API key?" | _profile_content.html:75 |
| New key — copy button | "Copy" | *(missing entirely)* | — |
| Config reset button | "Reset All" with `hx-confirm` | *(missing entirely)* | — |
| Empty state — schedules | "No ingestion schedules configured. Add a schedule above." | *(no schedule UI exists)* | — |
| Empty state — jobs | "No ingestion jobs found. Start a manual ingestion to create one." | "Loading job status..." | tab_ingestion.html:32 |

**Positive matches:**
- "Log out" (shell.html:41)
- "Run Evaluation" (tab_ragas.html:16)
- "Generate New Key" (_profile_content.html:10)
- "Export My Data (GDPR Art. 20)" (_profile_content.html:32)
- "Request Data Erasure" (_profile_content.html:33)
- "No configuration entries found." (_config_table.html:28)

**Findings:**
- **WARNING:** The login modal heading "Authentication Required" is generic and does not match the spec's branded "Login to Admin Panel".
- **WARNING:** Empty state for documents table points users to ingestion instead of filter adjustment, which diverges from the spec's UX guidance.
- **WARNING:** The "Copy" button for the one-time API key reveal is missing. The new key alert says "Copy this key now" but provides no mechanism to copy.
- **WARNING:** Tab labels "Evaluation" and "Settings" are ambiguous compared to the spec's "RAGAS Evaluation" and "Admin".
- **WARNING:** The `login.html` standalone page is completely unused by the SPA and uses username/password instead of API key. It should be removed or updated to match the spec.

---

### Pillar 2: Visuals (2/4)

**What the spec required vs. what was implemented:**

| Requirement | Spec | Actual | File |
|-------------|------|--------|------|
| Sidebar width | 280px fixed | 220px fixed | styles.css:22 |
| Sidebar collapsed (md) | Icon-only, 60px | Full-width column | styles.css:33-48 |
| Sidebar hidden (sm) | Hamburger toggle | Column layout | styles.css:33-48 |
| Monitor lights | 7 components (Qdrant, Embedding, LLM, Cache, Database, Filesystem, Grafana) | 6 components (missing LLM) | _monitor_lights.html:2-9 |
| Monitor latency | Displayed in ms below name | Not displayed | — |
| Monitor details | Click to expand/collapse per component | Not implemented | — |
| Document table | Checkbox + toolbar + per-doc dropdown | View button only | _documents_table.html |
| Login modal | `x-show="!isAuthenticated"` Alpine.js control | Bootstrap JS `modal.show()/hide()` | shell.html:65-83 |
| Modal mobile | `modal-fullscreen-sm-down` | Not present | — |
| ARIA — sidebar nav | `role="navigation"`, `role="tablist"` | Missing | shell.html:10 |
| ARIA — login modal | `aria-labelledby` | Missing | shell.html:65 |
| ARIA — monitor dots | `aria-label="{component} status: {healthy/unhealthy}"` | Missing | _monitor_lights.html:14 |

**Findings:**
- **WARNING:** Sidebar width is 220px (styles.css:22) instead of the spec's 280px. This reduces the available space for tab labels and makes the layout feel cramped.
- **WARNING:** Mobile responsive behavior is a simplified column stack instead of the spec's icon-only collapse (60px) at md breakpoint and hamburger toggle at sm. The nav items become horizontal wrap on mobile, which is usable but not the designed experience.
- **WARNING:** The monitor lights bar is missing the 7th component (LLM). The `check_all_components()` function in the backend may return 7 components, but the template hardcodes only 6.
- **WARNING:** No latency metric or details expansion on monitor lights. The spec requires per-component latency in ms and a click-to-expand details toggle.
- **WARNING:** Document table is missing the entire SPA-09 feature set: checkbox column, bulk selection toolbar, per-document Actions dropdown, and delete/re-ingest actions.
- **WARNING:** Login modal is controlled by Bootstrap JS API instead of Alpine.js `x-show`. This breaks the spec's animation contract (`x-transition`) and creates a disconnect between the auth state variable and the modal visibility.
- **WARNING:** The `login.html` page is a standalone form with username/password fields that is completely disconnected from the SPA's API key flow. It serves no purpose in the current architecture.

---

### Pillar 3: Color (3/4)

**What the spec required vs. what was implemented:**

| Role | Spec | Actual | File |
|------|------|--------|------|
| Warning (yellow) | `bg-warning` for degraded monitor components | Not implemented — only green/red/gray | _monitor_lights.html:18-30 |
| Profile status badges | `bg-success`/`bg-danger` badges | `text-success`/`text-danger` plain text | _profile_content.html:23 |
| Sidebar text | `text-light` (#f8f9fa) | `text-white` (#ffffff) | shell.html:8 |
| Accent (10%) | Reserved for primary actions, active tabs, links, focus rings | Used correctly on login, ingest, evaluation, generate key buttons | — |

**Findings:**
- **WARNING:** Monitor lights template only has three states: healthy (green), unhealthy (red), and not configured (gray). The spec requires a fourth "degraded/warning" state with `bg-warning` (yellow). This reduces the granularity of health status display.
- **WARNING:** Profile API key status uses `text-success`/`text-danger` plain text instead of `bg-success`/`bg-danger` badge styling. The spec's color contract says status indicators should use background-colored badges for visual weight.
- **WARNING:** Sidebar uses `text-white` instead of `text-light`. While contrast is still excellent (15.3:1), the spec explicitly calls for `text-light` (#f8f9fa) on `bg-dark`.
- **POSITIVE:** Accent color usage is restrained. Primary (`btn-primary`) is used only for login, ingest, evaluation, and generate key CTAs. No decorative elements misuse the accent.

---

### Pillar 4: Typography (2/4)

**What the spec required vs. what was implemented:**

| Role | Spec | Actual | File |
|------|------|--------|------|
| Table headers (`<th>`) | 600 (Semibold) | Default (bold/700) | _config_table.html:7 |
| Modal title | 24-28px (Display) | 20px (Heading) | shell.html:69 |
| Sidebar title | 20px (Heading) | 20px (Heading) | shell.html:9 |
| Page title (tab) | 24-28px (Display) | 24-28px (h3) | tab_*.html:1 |
| Card title | 20px (Heading) | 20px (h5) | tab_*.html:8 |
| Sidebar text | `text-light` | `text-white` | shell.html:8 |

**Findings:**
- **WARNING:** Table headers in `_config_table.html` use default Bootstrap `<th>` styling (font-weight: 700/bold) instead of the spec's 600 (semibold). The spec explicitly says "All headings, tab labels, sidebar items, button text, active state indicators, `<th>` table headers, modal titles, alert headings, destructive action emphasis" should use 600.
- **WARNING:** Login modal title "Authentication Required" uses `h5` (20px) which is Heading size. The spec says modal titles should use Display size (24-28px, h3 or h4).
- **WARNING:** Sidebar uses `text-white` instead of spec's `text-light`. This is a color/typography crossover issue.
- **POSITIVE:** Page titles across all tabs use `h2 class="h3"` (28px), matching the Display role. Card titles use `h3 class="h5"` (20px), matching the Heading role.
- **POSITIVE:** Body text uses default Bootstrap body sizing (16px/400/1.5) throughout.

---

### Pillar 5: Spacing (2/4)

**What the spec required vs. what was implemented:**

| Token | Spec | Actual | File |
|-------|------|--------|------|
| Sidebar width | 280px | 220px | styles.css:22 |
| Sidebar padding | `p-3` (16px) | `p-3` (16px) | shell.html:8 |
| Tab content padding | `p-4` (24px) | `p-4` (24px) | shell.html:47 |
| Monitor gap | `gap-3` (16px) | `gap-3` (16px) | _monitor_lights.html:1 |
| Mobile sidebar | Icon-only 60px (md), hidden hamburger (sm) | Column stack | styles.css:33-48 |
| Modal size | `modal-lg` for config table | `modal-sm` for login | shell.html:66 |
| Page section breaks | `mt-5` / `mb-5` (48px) | `hr` without margin classes | _profile_content.html:7,30 |

**Findings:**
- **WARNING:** Sidebar width is 220px (styles.css:22) instead of spec's 280px. This is a 60px reduction (21% narrower) that affects readability of tab labels and overall layout balance.
- **WARNING:** Mobile responsive behavior is a simplified column stack instead of the spec's designed collapse states. At md breakpoint (768-991px), the spec requires an icon-only sidebar (60px). At sm (<768px), the spec requires a hamburger toggle. The implementation simply stacks the sidebar above the content.
- **WARNING:** Profile tab uses bare `<hr>` elements for section breaks without margin classes (`my-4` or `my-5`). This creates inconsistent spacing between Account, API Keys, and GDPR sections.
- **POSITIVE:** Bootstrap utility classes are used consistently for spacing. `p-3`, `p-4`, `gap-3`, `mb-2`, `mb-3`, `mb-4` are all standard Bootstrap tokens.
- **POSITIVE:** Monitor light cards use `monitor-card` CSS class for the 160px width exception, which is explicitly allowed by the spec.

---

### Pillar 6: Experience Design (1/4)

**What the spec required vs. what was implemented:**

#### Auth Flow (SPA-02, SPA-03, SPA-12) — BLOCKER

The spec requires:
1. `init()` checks `localStorage` for saved API key
2. **Key found:** POST `/api/v1/auth/session` with Bearer token, receive HttpOnly JWT session cookie (8h, SameSite=Lax), set `isAuthenticated = true`
3. **Key not found:** Show login modal
4. **401 interceptor:** HTMX global handler shows login modal
5. **Logout:** Clear `localStorage`, reset state, show login modal

The actual implementation (shell.html:108-160):
- `init()` checks `localStorage` and calls `/api/v1/users/me` with Bearer token directly
- **authenticate()** stores the API key in `localStorage` and calls `/api/v1/users/me` — **never POSTs to `/api/v1/auth/session`**
- **No JWT session cookie exchange** — no HttpOnly cookie, no 8h expiry, no SameSite=Lax
- The `/api/v1/auth/session` endpoint exists (per 28c-01 summary) but the frontend never calls it
- The login modal is controlled by Bootstrap JS (`modal.show()/hide()`) instead of Alpine.js `x-show`

**Impact:** The auth model is fundamentally different from the spec. The server-side session cookie is unused. The frontend relies entirely on localStorage + Bearer token, which is a different security posture.

#### Tab Navigation (SPA-04, SPA-05)

- **URL hash history:** Not implemented. `switchTab()` sets `activeTab` and loads via HTMX but never updates `window.location.hash`.
- **Role gating:** Client-side only (`x-show="isAdmin"`). The spec expects server-side role gating (`x-show="!tab.admin_only || userRole === 'admin'"`).
- **Active tab indicator:** Uses Bootstrap `nav-pills` `active` class which applies `bg-primary` (correct).

#### Monitor Lights (SPA-06)

- **Auto-refresh:** `hx-trigger="every 30s"` is present (tab_monitoring.html:7).
- **Missing 7th component:** LLM component is missing from the template's hardcoded label map.
- **Missing latency:** No ms latency display below component names.
- **Missing details toggle:** No click-to-expand/collapse per component.
- **Missing ARIA:** No `aria-label` on status badges.

#### Config Inline Editing (SPA-08)

- **Search filter:** Present (`x-model="search"`, correct).
- **Double-click edit:** Present (`@dblclick="startEdit(entry)"`, correct).
- **Save on Enter/Blur:** Present (`@keydown.enter="saveEdit(entry)"`, correct).
- **Cancel on Escape:** Present (`@keydown.escape="cancelEdit()"`, correct).
- **Missing Reset All:** No "Reset All" button with `hx-confirm`.
- **Missing Type badges:** The "Type" column shows `bg-secondary` badge, but the "Group" column shows plain text instead of a Group badge.
- **Error handling:** Uses manual `d-none` class toggling instead of `aria-live="assertive"`.
- **Save mechanism:** Uses `fetch()` instead of HTMX PUT as specified.

#### Document Browse Cleanup (SPA-09)

- **Missing entirely:** No checkbox column, no selection toolbar, no bulk actions, no per-document dropdown.
- **Delete confirmation:** Not implemented.
- **Re-ingest action:** Not implemented.
- **Delete Failed:** Not implemented.

#### Profile Tab (SPA-07)

- **Account info:** Present (username, role badge, created date).
- **API keys table:** Present (prefix, created, status, revoke button).
- **Generate New Key:** Present but missing "Copy" button.
- **GDPR Export:** Present (blob + anchor click).
- **Erasure:** Present (confirm dialog + POST).
- **Extra content:** The `tab_profile.html` has a "Config" section with Qdrant K/BM25/Reranker validation that is not in the spec.

#### Security / CSP

- **CSP nonce missing:** `tab_ragas.html:36` has `<script>` without `nonce`. This violates the strict CSP and will cause the script to be blocked by browsers.
- **SRI missing:** `login.html:7` loads Bootstrap CSS without `integrity` attribute.
- **Alpine.js version mismatch:** Spec requires 3.14.8 CSP build; base.html loads 3.13.3.
- **CSP `frame-src` too broad:** `app.py:28` sets `frame-src 'self' https:` which allows any HTTPS iframe. The spec requires `https://{grafana_url}` only.
- **No `aria-live` regions:** HTMX target containers lack `aria-live="polite"` for screen reader announcements.

#### Missing Partials

The spec lists these as required components but they were not created:
- `_ingestion_manual.html`
- `_ingestion_schedule.html`
- `_ingestion_monitor.html`
- `_ragas_editor.html`
- `_ragas_results.html`

The ingestion and RAGAS tabs have inline content instead of loading these partials.

---

## Registry Safety

`components.json` not found. No shadcn registry. Audit skipped.

CDN Safety Gate: All CDN scripts in `base.html` have pinned versions and SRI hashes:
- Bootstrap CSS 5.3.0: `integrity` present
- HTMX 1.9.10: `integrity` present
- Alpine.js 3.13.3 CSP: `integrity` present
- Bootstrap JS 5.3.0: `integrity` present

⚠️ **Exception:** `login.html` loads Bootstrap CSS without `integrity` (line 7).
⚠️ **Exception:** `tab_ragas.html` inline script lacks `nonce` (line 36), which will fail under the strict CSP.

---

## Files Audited

### Templates
- `kb_server/ui/templates/base.html` (111 lines)
- `kb_server/ui/templates/admin/shell.html` (162 lines)
- `kb_server/ui/templates/admin/login.html` (33 lines)
- `kb_server/ui/templates/admin/tab_documents.html` (12 lines)
- `kb_server/ui/templates/admin/tab_monitoring.html` (40 lines)
- `kb_server/ui/templates/admin/tab_ingestion.html` (57 lines)
- `kb_server/ui/templates/admin/tab_ragas.html` (54 lines)
- `kb_server/ui/templates/admin/tab_admin.html` (9 lines)
- `kb_server/ui/templates/admin/tab_profile.html` (37 lines)
- `kb_server/ui/templates/admin/tab_analytics.html` (84 lines)
- `kb_server/ui/templates/admin/_monitor_lights.html` (34 lines)
- `kb_server/ui/templates/admin/_config_table.html` (89 lines)
- `kb_server/ui/templates/admin/_profile_content.html` (101 lines)
- `kb_server/ui/templates/admin/_documents_table.html` (45 lines)
- `kb_server/ui/templates/admin/_job_status.html` (19 lines)
- `kb_server/ui/templates/browse.html` (217 lines)

### Python
- `kb_server/ui/app.py` (180 lines)
- `kb_server/ui/routes_admin.py` (435 lines)

### CSS
- `kb_server/ui/static/styles.css` (153 lines)

### Spec
- `28c-UI-SPEC.md` (398 lines)

---

## Summary

Phase 28c implemented the core admin SPA shell with Alpine.js, HTMX, and Bootstrap 5, but diverges significantly from the approved UI-SPEC.md in several critical areas:

1. **The auth flow is the most critical gap.** The spec designed a JWT session cookie exchange (`POST /api/v1/auth/session` → HttpOnly cookie) that the frontend never invokes. The implementation falls back to storing the raw API key in `localStorage` and using Bearer tokens on every request. This is a different (and less secure) auth model.

2. **Several tab features are incomplete.** The document browse table lacks the entire SPA-09 feature set (checkboxes, bulk toolbar, per-doc actions). The monitor lights are missing the LLM component, latency metrics, and details toggle. The config editor lacks the "Reset All" button.

3. **Security gaps exist.** The `tab_ragas.html` script lacks a CSP nonce, `login.html` lacks SRI, and the `frame-src` CSP directive is too broad.

4. **Copy and spacing divergences** are widespread but individually minor. Tab labels, empty states, placeholder text, and sidebar width don't match the spec.

**Recommendation:** Before shipping, fix the auth flow (BLOCKER), add the missing document browse features (WARNING), and close the CSP/SRI gaps (WARNING). The remaining copy and spacing issues are polish items that can be addressed in a follow-up.
