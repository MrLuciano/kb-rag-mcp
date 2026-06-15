# Plan 42-01 SUMMARY: Query Logging Analytics Dashboard

## Objective

Add a Query Analytics tab to the Admin SPA that visualizes query log data — popular queries, zero-result content gaps, and latency distribution using server-rendered HTML tables.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_admin_ui.py -v` | ✅ 15/15 PASS |
| `pytest tests/test_ui_routes.py -v` | ✅ 14/14 PASS |
| Full health + UI test suite | ✅ 49/49 PASS |

## Key Files Created/Modified

- `kb_server/analytics/query_analyzer.py` — Added `get_latency_stats(time_range_days=7)` computing p50/p95/p99; added `time_range_days` param to `get_most_common_queries()` and `get_zero_result_queries()` (backward compatible)
- `kb_server/ui/routes_admin.py` — Added "analytics" to template_map, analytics data injection route handler calling all three QueryAnalyzer methods, logging import
- `kb_server/ui/templates/admin/shell.html` — Added Analytics tab (📈) to sidebar nav list
- `kb_server/ui/templates/admin/tab_analytics.html` — New template: Popular Queries table (top 25), Content Gaps table (zero-result), Latency Statistics table (p50/p95/p99), empty state banner, manual refresh button
- `tests/test_admin_ui.py` — Added TestAnalyticsTab class (6 tests)

## Implementation Notes

- All analytics data is filtered to last 7 days (D-03), backward compatible (time_range_days=0 = no filter)
- Percentile computation uses linear interpolation between nearest ranks
- Empty state shows info alert when no query data exists
- Manual refresh button uses HTMX `hx-get` (D-04 — no auto-refresh)
- Three sections on a single scrollable page: Popular Queries → Content Gaps → Latency (D-03)
