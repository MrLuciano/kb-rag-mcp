# Plan 38-01 SUMMARY: Grafana Dashboard Embedding

## Objective

Embed a Grafana dashboard in the Admin SPA Monitoring tab with time range selector (1h, 6h, 24h, 7d) that updates the iframe URL via Alpine.js.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_admin_ui.py::TestGrafana -v` | ✅ 3/3 PASS |
| Full UI + Health test suite | ✅ 46/46 PASS |

## Key Files Created/Modified

- `kb_server/ui/routes_admin.py` — Added `build_grafana_embed_url()` and `build_grafana_embed_url_with_range(time_range)` helper functions using `GRAFANA_URL` and `GRAFANA_DASHBOARD_UID` env vars
- `kb_server/ui/templates/admin/tab_monitoring.html` — Updated with Grafana iframe embed, time range selector button group, Alpine.js `x-data` for URL switching, info alert when not configured
- `kb_server/ui/app.py` — Registered Grafana URL builders as Jinja2 globals
- `tests/test_admin_ui.py` — Added `TestGrafana` class (3 tests: empty without env, empty with range, globals registered)

## Implementation Notes

- Helper functions return empty string when `GRAFANA_URL` or `GRAFANA_DASHBOARD_UID` is not set
- Time ranges: 1h, 6h, 24h, 7d with `from`/`to` Unix timestamps in milliseconds
- URL params: orgId=1, kiosk=t, theme=light for Grafana solo-panel kiosk mode
- Monitoring tab already has health lights (Phase 39) — Grafana embed added below the lights
- CSP `frame-src` already configured in Phase 28c CSP middleware to allow `https:` origins
