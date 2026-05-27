---
id: 18-01
phase: 18
status: complete
completed: 2026-05-27
task_count: 4
commits:
  - 1a51555 fix(deployment): add uid prometheus to Docker Compose datasource provisioning
  - d1bf774 fix(deployment): replace DS_PROMETHEUS refs and remove __inputs in Docker Compose dashboard
  - 4cfc0ed fix(deployment): add uid prometheus to Helm datasource provisioning
  - 9ca0be3 fix(deployment): replace DS_PROMETHEUS refs and remove __inputs in Helm dashboard
---

# Plan 18-01: Fix Grafana Datasource Error — Summary

## What was built

Fixed `Datasource ${DS_PROMETHEUS} was not found` Grafana error across both deployment paths:

### Docker Compose path
- `deployment/config/grafana-provisioning/datasources/prometheus.yml` — Added `uid: prometheus`
- `deployment/config/grafana-dashboard.json` — Replaced 63 `${DS_PROMETHEUS}` references with `"prometheus"`, removed `__inputs` section

### Helm path
- `deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml` — Added `uid: prometheus`
- `deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json` — Replaced 63 `${DS_PROMETHEUS}` references with `"prometheus"`, removed `__inputs` section

## Key decisions honored
- D-01: Stable UID + hardcoded reference approach
- D-02: `__inputs` section removed (not needed for provisioning-based deployment)
- D-03: Both Docker Compose and Helm copies fixed
- D-04: Both datasource provisioning configs have explicit UID

## Self-Check: PASSED
- [x] All 4 files modified, each committed individually
- [x] All JSON files valid (verified via `python -m json.tool`)
- [x] Zero `${DS_PROMETHEUS}` references remain in any file
- [x] `__inputs` section removed from both dashboard JSONs
- [x] No formatting drift — surgical regex replacements preserved original layout
