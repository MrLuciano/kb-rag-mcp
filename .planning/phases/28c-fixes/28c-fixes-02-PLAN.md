---
phase: 28c-fixes
plan: 02
type: execute
wave: 2
depends_on:
  - 28c-fixes-01
files_modified:
  - kb_server/ui/templates/admin/_monitor_lights.html
  - kb_server/ui/templates/admin/_config_table.html
  - kb_server/ui/templates/admin/tab_ingestion.html
  - kb_server/ui/templates/admin/tab_ragas.html
  - kb_server/ui/templates/admin/shell.html
  - kb_server/ui/templates/admin/_profile_content.html
  - kb_server/ui/static/styles.css
  - kb_server/ui/routes_admin.py
  - tests/test_admin_ui.py
autonomous: true
gap_closure: true
requirements:
  - SPA-06
  - SPA-08
  - SPA-04
  - SPA-07
must_haves:
  truths:
    - Monitor lights show 7 components with latency in ms and click-to-expand details toggle
    - Config editor has "Reset All" button, Group badges, HTMX PUT save, and aria-live errors
    - Missing ingestion and RAGAS partials exist and are loaded by their parent tabs
    - Sidebar width is 280px with icon-only 60px at md and hamburger at sm breakpoints
    - Specific routes like /tabs/documents-content, /tabs/monitor-lights, /tabs/profile-content resolve correctly (not shadowed by /tabs/{tab_name})
  artifacts:
    - path: kb_server/ui/templates/admin/_monitor_lights.html
      provides: 7-component health monitor with latency and ARIA
      contains: "LLM"
    - path: kb_server/ui/templates/admin/_config_table.html
      provides: Config inline editor with reset and HTMX PUT
      contains: "Reset All"
    - path: kb_server/ui/templates/admin/_ingestion_manual.html
      provides: Manual ingestion form partial
    - path: kb_server/ui/templates/admin/_ingestion_schedule.html
      provides: Ingestion schedule partial
    - path: kb_server/ui/templates/admin/_ingestion_monitor.html
      provides: Ingestion job monitor partial
    - path: kb_server/ui/templates/admin/_ragas_editor.html
      provides: RAGAS golden set editor partial
    - path: kb_server/ui/templates/admin/_ragas_results.html
      provides: RAGAS evaluation results partial
    - path: kb_server/ui/static/styles.css
      provides: Responsive sidebar layout
      contains: "width: 280px"
  key_links:
    - from: tab_ingestion.html
      to: _ingestion_manual.html
      via: hx-get
      pattern: "_ingestion_manual"
    - from: tab_ragas.html
      to: _ragas_editor.html
      via: hx-get
      pattern: "_ragas_editor"
---

<objective>
Close MEDIUM-priority gaps: monitor lights completeness, config editor polish, missing partials, and copy/spacing mismatches so the Admin SPA fully matches 28c-UI-SPEC.md.

Purpose: These gaps affect usability, accessibility, and visual fidelity. They are not blockers but represent significant divergence from the approved design contract.
Output: Updated monitor lights, config table, new partials, responsive sidebar, and corrected copy across all admin templates.
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/admin/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/phases/28c-fixes/28c-fixes-CONTEXT.md
@.planning/phases/28c-admin-spa-panel/28c-UAT.md
@.planning/phases/28c-admin-spa-panel/28c-UI-REVIEW.md
@.planning/phases/28c-admin-spa-panel/28c-UI-SPEC.md
@.planning/phases/28c-admin-spa-panel/28c-01-SUMMARY.md

# Source files (current state; shell.html already updated by Plan 01)
@kb_server/ui/templates/admin/_monitor_lights.html
@kb_server/ui/templates/admin/_config_table.html
@kb_server/ui/templates/admin/tab_ingestion.html
@kb_server/ui/templates/admin/tab_ragas.html
@kb_server/ui/templates/admin/shell.html
@kb_server/ui/templates/admin/_profile_content.html
@kb_server/ui/static/styles.css
@kb_server/ui/routes_admin.py
@tests/test_admin_ui.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Complete monitor lights bar (D-04)</name>
  <files>
    kb_server/ui/templates/admin/_monitor_lights.html
    kb_server/ui/routes_admin.py
  </files>
  <behavior>
    - Test: test_monitor_lights_has_llm — _monitor_lights.html contains "LLM" in the component labels
    - Test: test_monitor_lights_shows_latency — Each component card shows latency in ms (e.g., `<small class="text-muted">12ms</small>`)
    - Test: test_monitor_lights_click_to_expand — Component cards have `@click` toggle for details expansion
    - Test: test_monitor_lights_aria_labels — Status badges have `aria-label` with component name and status
    - Test: test_monitor_lights_warning_state — Degraded/warning state renders `bg-warning` when status is degraded
  </behavior>
  <action>
    1. In _monitor_lights.html: Add `"llm": "LLM"` to the `labels` map and `all_components` map so 7 components render.
    2. In _monitor_lights.html: Add latency display. Expect `status.latency_ms` from the backend. Render `<small class="text-muted" x-text="status.latency_ms + 'ms'"></small>` below the component name label. If `latency_ms` is missing, show nothing.
    3. In _monitor_lights.html: Wrap each card in an Alpine.js `x-data="{ expanded: false }"` scope. Add `@click="expanded = !expanded"` on the card body. Add a details div below the card that shows `x-show="expanded"` with component data (`status.message`, `status.latency_ms`, etc.).
    4. In _monitor_lights.html: Add `aria-label="{{ label }} status: {{ 'healthy' if status and status.healthy else 'unhealthy' if status else 'not configured' }}"` to the status dot `<div>`.
    5. In _monitor_lights.html: Add a fourth state for degraded/warning: `{% elif status and status.degraded %}` → `bg-warning` dot and `text-warning` label.
    6. In routes_admin.py: Update `/tabs/monitor-lights` to pass the full component dict including `latency_ms` if available. If `check_all_components()` does not return latency, add a TODO comment noting that latency should be added to the health check function in a future phase (do NOT modify check_all_components() in this gap closure).
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "monitor"</automated>
  </verify>
  <done>
    - Monitor lights show 7 components including LLM
    - Latency displayed in ms when available
    - Click-to-expand details toggle works per component
    - aria-label present on all status badges
    - Degraded/warning (yellow) state renders correctly
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Improve config inline editor (D-05)</name>
  <files>
    kb_server/ui/templates/admin/_config_table.html
  </files>
  <behavior>
    - Test: test_config_has_reset_all — _config_table.html contains a "Reset All" button with `hx-confirm`
    - Test: test_config_group_badges — Group column renders `<span class="badge bg-info">` instead of plain text
    - Test: test_config_save_uses_htmx_put — Save mechanism uses HTMX `hx-put` on the input instead of `fetch()`
    - Test: test_config_error_aria_live — Error container has `aria-live="assertive"` and `role="alert"`
    - Test: test_config_search_placeholder — Search placeholder is "Search config keys..."
  </behavior>
  <action>
    1. In _config_table.html: Add a "Reset All" button above the search input: `<button class="btn btn-outline-danger btn-sm" hx-post="/api/v1/config/reset" hx-confirm="Reset all config: Reset all configuration to environment defaults? This cannot be undone." hx-target="#tab-content" hx-swap="innerHTML">Reset All</button>`. Wrap it in a flex row with the search input.
    2. In _config_table.html: Change the Group column from `<td x-text="entry.group_name"></td>` to `<td><span class="badge bg-info" x-text="entry.group_name"></span></td>`.
    3. In _config_table.html: Replace the `fetch()` save mechanism with HTMX. For each editable row, wrap the input in a form or use HTMX attributes directly on the input: `hx-put="/api/v1/config/{{ entry.key }}"`, `hx-trigger="blur, keydown[key=='Enter']"`, `hx-target="closest tr"`, `hx-swap="none"`. The config API already exists at `/api/v1/config/{key}` (Phase 40). Since HTMX PUT sends the input value automatically, the Alpine.js `saveEdit` method can be simplified or removed. Keep Alpine.js for the editing state toggle (`editing`, `editValue`) but delegate the actual HTTP request to HTMX.
    4. In _config_table.html: Replace the `d-none` error toggle with an `aria-live="assertive"` container: `<div x-show="saveError" class="alert alert-danger mt-2" role="alert" aria-live="assertive" x-text="saveError"></div>`. Listen for HTMX `htmx:responseError` to set `saveError`.
    5. In _config_table.html: Change search placeholder from "Search config..." to "Search config keys...".
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "config"</automated>
  </verify>
  <done>
    - "Reset All" button present with hx-confirm
    - Group column shows badges instead of plain text
    - Save uses HTMX PUT instead of fetch()
    - Error announcements use aria-live="assertive"
    - Search placeholder matches spec
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create missing partials and fix copy/spacing (D-06, D-07)</name>
  <files>
    kb_server/ui/templates/admin/_ingestion_manual.html
    kb_server/ui/templates/admin/_ingestion_schedule.html
    kb_server/ui/templates/admin/_ingestion_monitor.html
    kb_server/ui/templates/admin/_ragas_editor.html
    kb_server/ui/templates/admin/_ragas_results.html
    kb_server/ui/templates/admin/tab_ingestion.html
    kb_server/ui/templates/admin/tab_ragas.html
    kb_server/ui/templates/admin/shell.html
    kb_server/ui/templates/admin/_profile_content.html
    kb_server/ui/static/styles.css
    kb_server/ui/routes_admin.py
  </files>
  <behavior>
    - Test: test_new_partials_exist — All 5 new partial templates exist and are referenced by parent tabs
    - Test: test_sidebar_width_280px — styles.css sets `.admin-sidebar { width: 280px; }`
    - Test: test_sidebar_md_breakpoint — styles.css has `@media (min-width: 768px) and (max-width: 991px)` for icon-only 60px sidebar
    - Test: test_sidebar_sm_breakpoint — styles.css has `@media (max-width: 767px)` for hamburger-hidden sidebar
    - Test: test_sidebar_text_light — shell.html uses `text-light` instead of `text-white` on sidebar
    - Test: test_sidebar_aria_roles — shell.html has `role="navigation"` and `role="tablist"` on sidebar nav
    - Test: test_profile_revoke_confirm — _profile_content.html revoke confirm text matches spec
    - Test: test_profile_status_badges — _profile_content.html status uses `bg-success`/`bg-danger` badges
    - Test: test_ingestion_cta_text — tab_ingestion.html CTA reads "Ingest Now"
    - Test: test_ingestion_empty_state — tab_ingestion.html empty state reads "No ingestion jobs found. Start a manual ingestion to create one."
  </behavior>
  <action>
    1. Create `_ingestion_manual.html`: Extract the manual ingestion form from `tab_ingestion.html` into this partial. Keep the form with path input and submit button. Change CTA from "Start Ingest" to "Ingest Now".
    2. Create `_ingestion_schedule.html`: Create a placeholder partial with empty state: "No ingestion schedules configured. Add a schedule above." (the schedule feature itself is not in scope for this gap closure).
    3. Create `_ingestion_monitor.html`: Extract the job status/monitor section from `tab_ingestion.html` into this partial. Fix empty state text from "Loading job status..." to "No ingestion jobs found. Start a manual ingestion to create one.".
    4. Create `_ragas_editor.html`: Extract the evaluation dataset section from `tab_ragas.html` into this partial. Keep the Run Evaluation button and dataset count.
    5. Create `_ragas_results.html`: Create a placeholder partial with empty state: "No evaluation results yet. Run an evaluation to see results here.".
    6. Update `tab_ingestion.html`: Replace inline content with HTMX tabs or direct partial includes. Use a sub-tab nav (Manual, Schedule, Monitor) that loads the corresponding partial via `hx-get` into a container div.
    7. Update `tab_ragas.html`: Replace inline content with HTMX tabs for Editor and Results, loading `_ragas_editor.html` and `_ragas_results.html`. Keep the nonce on any remaining inline script (from Plan 01).
    8. In `shell.html`: Change sidebar classes from `text-white` to `text-light`. Add `role="navigation"` to the sidebar div and `role="tablist"` to the `<ul class="nav nav-pills">`.
    9. In `_profile_content.html`: Change revoke confirm text to "Revoke API key: Are you sure you want to revoke this key? Applications using this key will lose access immediately.". Change API key status from `text-success`/`text-danger` to `bg-success`/`bg-danger` badges.
    10. In `styles.css`: Change `.admin-sidebar { width: 220px; }` to `width: 280px;`. Add responsive breakpoints:
        - `@media (min-width: 768px) and (max-width: 991px)`: `.admin-sidebar { width: 60px; }` with icon-only display (hide text labels, show only icons). This requires adding Unicode emoji icons to the sidebar nav links and hiding text with a utility class at this breakpoint.
        - `@media (max-width: 767px)`: `.admin-sidebar { display: none; }` and add a hamburger toggle button in the shell that shows/hides the sidebar via Alpine.js `x-show`.
        Since the current sidebar uses text-only nav links without icons, add Unicode emoji icons (📄, 📊, ⚡, 🧪, ⚙️, 👤) before each label and use a CSS class to hide labels at md breakpoint.
    11. In `routes_admin.py`: Add endpoints for serving the new partials if they are loaded via HTMX (e.g., `/tabs/ingestion-manual`, `/tabs/ingestion-schedule`, etc.).
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "partial or ingestion or ragas or profile or sidebar or spacing or copy"</automated>
  </verify>
  <done>
    - 5 new partials exist and are loaded by parent tabs
    - Sidebar width is 280px with responsive icon-only and hamburger modes
    - shell.html uses text-light and has ARIA roles
    - Profile content copy and badge styling match spec
    - Ingestion and RAGAS tab CTAs and empty states match spec
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Fix route ordering so specific /tabs/ paths resolve before generic /tabs/{tab_name} (UAT Issue 2)</name>
  <files>
    kb_server/ui/routes_admin.py
    tests/test_admin_ui.py
  </files>
  <behavior>
    - Test: test_specific_routes_not_shadowed — GET /admin/tabs/documents-content returns 200 (not "Unknown tab")
    - Test: test_monitor_lights_route_works — GET /admin/tabs/monitor-lights returns 200
    - Test: test_profile_content_route_works — GET /admin/tabs/profile-content returns 200
    - Test: test_config_table_route_works — GET /admin/tabs/config-table returns 200
    - Test: test_generic_tab_route_still_works — GET /admin/tabs/documents still resolves to admin_tab_content
  </behavior>
  <action>
    1. In routes_admin.py: Reorder route definitions so specific static paths are registered BEFORE the generic `@router.get("/tabs/{tab_name}")` route. Move the specific endpoints (`documents-content`, `monitor-lights`, `config-table`, `profile-content`, `ingest-trigger`, `job-status`, `ragas-run`) to appear before `admin_tab_content`.
    The cleanest approach: move `admin_tab_content` to the end of the file (or just below the last specific route). Or define specific routes in a separate APIRouter that's included before the main admin router.
    Simplest fix: in routes_admin.py, define a second router `tab_router = APIRouter()` for specific tab paths and include it before the generic `router`. Or just move the function definitions so specific @router.get decorators are evaluated before the generic one.
    For Starlette/FastAPI, the order of route registration in the source file determines match priority when routes are on the same router and same path prefix. Moving the specific endpoint definitions above `admin_tab_content` in the source file is sufficient.
    2. Ensure every specific route path like `/tabs/documents-content` explicitly returns proper HTML content (not "Unknown tab").
    3. Add behavioral tests that curl each specific route and verify HTTP 200 with expected content fragments.
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "route"</automated>
    <manual>curl -s http://localhost:8001/admin/tabs/documents-content | head -5 (should return document table HTML, not "Unknown tab")</manual>
  </verify>
  <done>
    - curl /admin/tabs/documents-content returns document table HTML (not "Unknown tab")
    - curl /admin/tabs/monitor-lights returns monitor lights HTML
    - curl /admin/tabs/profile-content returns profile content HTML
    - curl /admin/tabs/config-table returns config table HTML
    - curl /admin/tabs/documents still resolves to generic admin_tab_content handler
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client→API | Config reset and document actions cross from browser to server |
| HTMX partials | Server-rendered fragments injected into DOM must not contain XSS |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-05 | Information Disclosure | _monitor_lights.html details toggle | accept | Details show only health check data already available to authenticated users; no PII |
| T-28c-06 | Tampering | _config_table.html "Reset All" | mitigate | hx-confirm requires user confirmation; endpoint requires auth via existing middleware |
| T-28c-07 | Denial of Service | Bulk document actions | accept | Existing rate limiting (Phase 33) applies; no new DoS vectors introduced |
| T-28c-08 | Elevation of Privilege | Missing partials loaded via hx-get | mitigate | All new partial endpoints reuse existing auth dependencies (`_verify_request_api_key` or session cookie) |
</threat_model>

<verification>
- Run full test suite: `pytest tests/test_admin_ui.py -v`
- Run UI regression tests: `pytest tests/test_ui_routes.py -v`
- Verify no new flake8/mypy errors: `flake8 kb_server/ui/ kb_server/auth/router.py && mypy kb_server/ui/ kb_server/auth/router.py`
- Verify all templates render without Jinja2 syntax errors: `python -c "from kb_server.ui.app import templates; [templates.get_template(f'admin/{t}') for t in ['shell.html','_monitor_lights.html','_config_table.html','tab_ingestion.html','tab_ragas.html','_ingestion_manual.html','_ingestion_schedule.html','_ingestion_monitor.html','_ragas_editor.html','_ragas_results.html']]"`
</verification>

<success_criteria>
- [ ] Monitor lights show 7 components with latency, details toggle, ARIA labels, and warning state
- [ ] Config editor has Reset All, Group badges, HTMX PUT save, aria-live errors
- [ ] 5 new partials exist and are loaded by ingestion/RAGAS tabs
- [ ] Sidebar is 280px with icon-only (md) and hamburger (sm) responsive behavior
- [ ] All copy/spacing mismatches from UI-REVIEW.md are fixed
- [ ] Specific routes (documents-content, monitor-lights, profile-content, config-table) resolve correctly, not shadowed by /tabs/{tab_name}
- [ ] All new tests pass; no regressions in existing 666 tests
- [ ] Code review passed (black, flake8, mypy clean)
</success_criteria>

<output>
Create `.planning/phases/28c-fixes/28c-fixes-02-SUMMARY.md` when done
</output>
