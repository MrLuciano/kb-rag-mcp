# Plan 28c-02 SUMMARY: Tab Content — Monitor, Config, Profile, Browse Cleanup

## Objective

Implement four tab content panels: Monitor Lights bar (7 health components with auto-refresh), Admin Config page (inline editing with Alpine.js), Profile tab (API key management, GDPR export/erasure), and Document browse cleanup (toolbar actions, sortable columns).

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_admin_ui.py -v` | ✅ 6/6 PASS |
| `pytest tests/test_ui_routes.py -v` | ✅ 14/14 PASS |
| Full UI + Auth + Config test suite | ✅ 119+ PASS |

## Key Files Created/Modified

### Monitor Lights
- `kb_server/ui/templates/admin/_monitor_lights.html` — 7 health cards with color-coded indicators, HTMX 30s poll from `/health/detailed`
- `kb_server/ui/templates/admin/tab_monitoring.html` — Updated to load monitor-lights partial via HTMX
- `kb_server/ui/routes_admin.py` — Added `GET /admin/tabs/monitor-lights` calling `check_all_components()`

### Admin Config
- `kb_server/ui/templates/admin/_config_table.html` — Alpine.js component with inline dblclick editing, search filter, PUT save
- `kb_server/ui/templates/admin/tab_admin.html` — Updated to load config-table partial via HTMX

### Profile Tab
- `kb_server/ui/templates/admin/_profile_content.html` — Alpine.js component with API key CRUD (create/list/revoke), GDPR data export (JSON download), erasure request (confirmation + API call)
- `kb_server/ui/templates/admin/tab_profile.html` — Updated to load profile-content partial via HTMX
- `kb_server/ui/routes_admin.py` — Added `GET /admin/tabs/profile-content` endpoint

### Document Browse Cleanup & Sortable Columns
- `kb_server/ui/routes.py` — Added `sort_by`/`sort_order` params to `get_documents()` and `browse_documents()` with sortable columns mapping (name, file_type, vendor, product, date, status) per D-08; limit changed to 25 per D-09
- `kb_server/ui/routes_admin.py` — Added `DELETE /api/v1/documents/{source_file}`, `POST /api/v1/documents/{source_file}/re-ingest`, `POST /api/v1/documents/delete-failed`

## Implementation Notes

- Monitor lights poll `/health/detailed` directly — no intermediate caching layer needed
- Config inline editing uses Alpine.js `x-data` with `dblclick` to activate edit mode, `@keydown.enter` to save
- Profile API key CRUD uses fetch() with Bearer token from localStorage
- Sortable columns use query params `sort_by` and `sort_order` with column name mapping
- Document cleanup endpoints interact directly with Qdrant and SQLite registry
