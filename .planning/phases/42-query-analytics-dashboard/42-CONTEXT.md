# Phase 42: Query Logging Analytics Dashboard - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Connect the existing QueryAnalyzer backend to the Admin SPA as a new Analytics tab. Show popular queries, zero-result content gaps, and latency distribution using server-rendered HTML tables.

Requirements: SPA-02

</domain>

<decisions>
## Implementation Decisions

### Tab Placement
- **D-01:** New dedicated Analytics tab — 7th tab in the Admin SPA sidebar, loaded via HTMX partial at `/admin/tabs/analytics`.

### Data Display
- **D-02:** Server-rendered HTML tables only — no JavaScript charting libraries. Popular Queries table (rank, query text, frequency), Content Gaps table (query text, frequency), Latency table (operation, count, p50, p95, p99).

### Data Scope
- **D-03:** Last 7 days of query log data. Top 25 most popular queries. All three views on a single scrollable page: Popular Queries → Content Gaps → Latency Statistics.

### Refresh Strategy
- **D-04:** On tab visit only — HTMX loads on tab switch. Manual refresh button. No auto-refresh interval.

### QueryAnalyzer Backend
- **D-05:** Add `get_latency_stats()` method to `QueryAnalyzer` for computing p50/p95/p99 aggregates from `query_log.latency_ms`. Keep analytics computation in the backend module, not in route handlers.

### Content Gaps
- **D-06:** Show zero-result queries prominently as a "Content Gaps" section, sorted by frequency descending. Most valuable insight for KB admins to identify missing documentation.

### the agent's Discretion
- Exact `get_latency_stats()` SQL query and percentile computation method (SQLite percentile vs Python computation).
- Error handling for empty query log or missing database.
- Whether to add the analytics nav link to `base.html` or only in the admin shell sidebar.
- Test strategy for the analytics tab endpoint and new QueryAnalyzer methods.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Backend
- `kb_server/analytics/query_analyzer.py` — Existing `QueryAnalyzer` class with `get_most_common_queries()`, `get_zero_result_queries()`, `get_low_score_queries()`. Add `get_latency_stats()` here.
- `kb_server/telemetry/query_logger.py` — Query log schema and storage. The `query_log` table is the data source.

### Admin SPA Integration
- `.planning/phases/28c-admin-spa-panel/28c-CONTEXT.md` — Admin SPA design decisions (D-04: HTMX partials per tab, D-05: server-rendered Jinja2 partials)
- `kb_server/ui/templates/admin/shell.html` — Sidebar Alpine.js component — add Analytics tab entry
- `kb_server/ui/routes_admin.py` — Admin router — add `/admin/tabs/analytics` endpoint
- `kb_server/ui/templates/base.html` — Base template (admin nav already exists)

### Requirements
- `.planning/ROADMAP.md` §Phase 42 — Phase goal, success criteria
- `.planning/REQUIREMENTS.md` — SPA-02 definition

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `QueryAnalyzer` class — 3 existing analysis methods ready to use; add `get_latency_stats()`.
- `query_log` SQLite table — Contains timestamp, query_text, result_count, latency_ms, max_score for analysis.
- Admin SPA shell with HTMX tab loading pattern — Follow existing tab pattern (monitoring, profile, etc.) for adding Analytics tab.

### Established Patterns
- **Tab loading**: HTMX `hx-get="/admin/tabs/{name}"` loads Jinja2 partial into `#tab-content`. Add `analytics` to `template_map` in `routes_admin.py`.
- **Sidebar entries**: Alpine.js `x-data` in `shell.html` with `switchTab(tab)` method. Add `<li>` entry.
- **Server-rendered tables**: All admin tabs use Jinja2 template partials with `TemplateResponse`.

### Integration Points
- `kb_server/ui/routes_admin.py:34-41` — `template_map` dict — add "analytics" mapping to new template
- `kb_server/ui/templates/admin/shell.html:12-34` — sidebar nav list — add Analytics tab link
- `kb_server/analytics/query_analyzer.py` — Add `get_latency_stats(time_range_days=7)` method

</code_context>

<specifics>
## Specific Ideas

- Tab layout: h3 heading + description, Popular Queries table, Content Gaps table, Latency Statistics table
- Tables should be striped Bootstrap tables with responsive wrapper
- Empty state: "No query data available for the last 7 days. Query data appears after users search the knowledge base." with illustration of expected content
- Content Gaps section: Consider adding a small form/button to quickly investigate a gap — e.g., "Search for '{query_text}'" link

</specifics>

<deferred>
## Deferred Ideas

- Interactive charts / Chart.js integration deferred — tables sufficient for initial analytics
- Configurable time range selector deferred — 7-day fixed window for simplicity
- Auto-refresh not needed — analytics data changes infrequently

</deferred>

---

*Phase: 42-query-analytics-dashboard*
*Context gathered: 2026-06-15 via discuss-phase*
