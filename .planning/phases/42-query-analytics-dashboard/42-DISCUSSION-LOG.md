# Phase 42: Query Logging Analytics Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-06-15
**Phase:** 42-query-analytics-dashboard
**Areas discussed:** Data display, Tab placement, Refresh strategy, Data scope, Latency stats location, Content gaps

---

## Data Display

| Option | Description | Selected |
|--------|-------------|----------|
| Tables only | Server-rendered HTML tables for all data | ✓ |
| Tables + inline charts | CSS/HTML bar charts alongside tables | |
| Charts via JS lib | Chart.js CDN for interactive charts | |

**User's choice:** Tables only

---

## Tab Placement

| Option | Description | Selected |
|--------|-------------|----------|
| New dedicated tab | 7th tab 'Analytics' in sidebar | ✓ |
| Monitoring sub-section | Below monitor lights and Grafana | |
| No tab, direct route | Accessible at /admin/analytics only | |

**User's choice:** New dedicated tab

---

## Refresh Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| On tab visit only | HTMX loads on tab switch, manual refresh | ✓ |
| On visit + auto-refresh | HTMX every 60s | |

**User's choice:** On tab visit only

---

## Data Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Last 7 days, top 25, single page | Filtered to 7d, top 25 queries, all views on one page | ✓ |
| All time, top 10 | No filter, top 10 | |
| Configurable time range | User selects 24h/7d/30d | |

**User's choice:** Last 7 days, top 25, single page

---

## Latency Stats Location

| Option | Description | Selected |
|--------|-------------|----------|
| Add to QueryAnalyzer | Add get_latency_stats() method to backend | ✓ |
| Inline in route | Compute in routes_admin.py | |

**User's choice:** Add to QueryAnalyzer backend

---

## Content Gaps

| Option | Description | Selected |
|--------|-------------|----------|
| Show prominently | 'Content Gaps' section sorted by frequency | ✓ |
| Show as secondary | Below popular queries and latency | |
| Skip for now | Ship without content gaps | |

**User's choice:** Show prominently

---

## the agent's Discretion

- Exact get_latency_stats() SQL query
- Error handling for empty query log
- Whether to add analytics nav link to base.html or only admin shell
- Test strategy

## Deferred Ideas

- Interactive chart library deferred — tables sufficient initially
- Configurable time range deferred — 7-day fixed window
- Auto-refresh not needed
