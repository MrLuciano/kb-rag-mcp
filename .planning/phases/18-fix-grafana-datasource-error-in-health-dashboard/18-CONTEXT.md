# Phase 18: Fix Grafana "Datasource ${DS_PROMETHEUS} was not found" error - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the Prometheus datasource variable resolution error in the "KB-RAG MCP Health Dashboard" Grafana dashboard when loaded via `docker compose up -d`. The dashboard JSON uses Grafana's export-import template variable `${DS_PROMETHEUS}` which doesn't resolve when the dashboard is provisioned from a file (the standard deployment path). This is a pure configuration fix — no code changes needed.

</domain>

<decisions>
## Implementation Decisions

### Fix Approach
- **D-01:** Use **stable UID + hardcoded reference** approach — assign `uid: "prometheus"` to the Prometheus datasource in the provisioning YAML, then replace all `${DS_PROMETHEUS}` references in dashboard JSONs with `"prometheus"` directly.
- **D-02:** Remove the `__inputs` section entirely from both dashboard JSONs — it's only relevant for UI import, which is not the deployment path. Leaving it unused after the fix would be misleading.
- **D-03:** Fix **both** dashboard copies:
  - `deployment/config/grafana-dashboard.json` (used by Docker Compose)
  - `deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json` (used by Helm chart)

### Datasource UID
- **D-04:** Add `uid: "prometheus"` to **both** datasource provisioning configs:
  - `deployment/config/grafana-provisioning/datasources/prometheus.yml` (Docker Compose)
  - `deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml` — datasource ConfigMap inline (Helm)

### Verification
- **D-05:** Manual verification: `docker compose up -d`, open Grafana at localhost:3000, confirm no datasource errors and panels populate with data. Document steps in plan.

### the agent's Discretion
- Exact search-and-replace approach for `${DS_PROMETHEUS}` → `"prometheus"` (sed or script — 60+ occurrences per file)
- Keep or remove `__requires` section (no functional impact either way)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dashboard & Datasource (Docker Compose)
- `deployment/config/grafana-dashboard.json` — Dashboard JSON with `${DS_PROMETHEUS}` references (739 lines, ~60+ occurrences to fix)
- `deployment/config/grafana-provisioning/datasources/prometheus.yml` — Datasource provisioning (no explicit UID — needs `uid: "prometheus"` added)

### Dashboard & Datasource (Helm)
- `deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json` — Identical dashboard JSON in Helm chart (same issue)
- `deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml` — Helm ConfigMap with datasource provisioning inline (lines 54-65, no explicit UID)

### Prior Phase Context
- `.planning/phases/14/CONTEXT.md` — Phase 14 Health Dashboard context (Grafana-centric approach, datasource config decisions, architecture)

### Project Constraints
- `.planning/PROJECT.md` — No new dependencies, backward-compatible, test baseline
- `.planning/ROADMAP.md` §Phase 17 — Phase 18 goal definition
- `.planning/ROADMAP.md` §Phase 14 — Health Dashboard delivered dashboard + Prometheus stack

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deployment/config/grafana-provisioning/datasources/prometheus.yml` — 15-line datasource provisioning file; just needs `uid:` field added
- `deployment/config/grafana-dashboard.json` — 739-line Grafana dashboard JSON; templating uses `"uid": "${DS_PROMETHEUS}"` in every panel
- `deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml` — Helm-equivalent datasource provisioning at lines 54-65
- `deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json` — Helm-equivalent dashboard JSON (same DS_PROMETHEUS pattern)

### Integration Points
- **Docker Compose:** `docker-compose.yml` brings up 4 services (Qdrant, kb-rag-mcp, Prometheus, Grafana). Dashboard loads from `deployment/config/`. Datasource provisions from `deployment/config/grafana-provisioning/datasources/`.
- **Helm:** Grafana Deployment mounts ConfigMaps for datasources, dashboards provisioning, and dashboard JSON. ConfigMap is defined in `configmap-monitoring.yaml`.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond fixing the datasource resolution error — standard Grafana provisioning approach applies.

</specifics>

<deferred>
## Deferred Ideas

- Prometheus alerting rules (out of scope — belongs in its own phase)
- Grafana authentication (Phase 14 decision: anonymous access sufficient)

</deferred>

---

*Phase: 18-Fix-Grafana-Datasource-Error*
*Context gathered: 2026-05-27*
