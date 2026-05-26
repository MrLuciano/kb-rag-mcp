---
phase: 14-health-dashboard
plan: 04
subsystem: deployment
tags: [kubernetes, helm, prometheus, grafana, monitoring, configmap]
dependency_graph:
  requires: [14-01]
  provides: ["Prometheus StatefulSet", "Grafana Deployment", "monitoring ConfigMaps", "Helm chart toggle"]
  affects: ["deployment/helm/kb-rag-mcp"]
tech_stack:
  added: []
  patterns: ["Helm templating", "Kubernetes service discovery", "ConfigMap provisioning"]
key_files:
  created:
    - "deployment/helm/kb-rag-mcp/templates/prometheus.yaml"
    - "deployment/helm/kb-rag-mcp/templates/grafana.yaml"
    - "deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml"
    - "deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json"
    - "tests/e2e/test_helm_values.py"
    - "tests/e2e/test_helm_chart.py"
  modified:
    - "deployment/helm/kb-rag-mcp/values.yaml"
decisions:
  - "Use StatefulSet for Prometheus (persistent time-series data)"
  - "Use Deployment for Grafana (state in ConfigMaps)"
  - "Copy dashboard JSON into chart directory (Helm .Files.Get requires chart-local files)"
  - "Use Kubernetes service discovery for auto-discovering kb-rag-mcp pods"
  - "Default anonymous Grafana access for internal deployments"
  - "Port 8081 for health/metrics endpoint (matches health_server.py)"
metrics:
  duration_minutes: 70
  completed_date: 2026-05-26T02:54:27Z
  tasks_completed: 5
  commits: 6
  files_modified: 7
  tests_added: 12
---

# Phase 14 Plan 04: Kubernetes Helm Chart Integration Summary

**One-liner:** Integrated Prometheus and Grafana into Kubernetes Helm chart with auto-provisioned dashboards and service discovery

## What Was Built

### Core Functionality

**values.yaml monitoring configuration:**
- `monitoring.enabled` (default: true) - master toggle for entire monitoring stack
- `monitoring.prometheus.*` - image, service, storage (10Gi), retention (15d), scrape interval (15s)
- `monitoring.grafana.*` - image, service, ingress (optional), admin credentials, anonymous access
- Configurable via `helm install --set monitoring.prometheus.storage.size=50Gi`

**Prometheus StatefulSet (prometheus.yaml):**
- 1 replica with persistent storage via volumeClaimTemplate (10Gi default)
- ClusterIP Service on port 9090
- Liveness/readiness probes (`/-/healthy`, `/-/ready`)
- Config mounted from `prometheus-config` ConfigMap
- Retention configurable via `--storage.tsdb.retention.time`

**Grafana Deployment (grafana.yaml):**
- 1 replica with 3 ConfigMap volume mounts
- ClusterIP Service on port 3000
- Optional Ingress (disabled by default, enable with `--set monitoring.grafana.ingress.enabled=true`)
- Environment variables for admin user, password, anonymous access
- Liveness/readiness probes (`/api/health`)

**Monitoring ConfigMaps (configmap-monitoring.yaml):**
1. **prometheus-config** - Prometheus scrape configuration
   - Kubernetes service discovery (auto-discovers kb-rag-mcp pods)
   - Relabel configs filter by `app.kubernetes.io/name` label
   - Excludes prometheus/grafana pods from scraping
   - Scrapes `/metrics` on port 8081
2. **grafana-datasources** - Grafana datasource provisioning
   - Prometheus datasource at `http://<fullname>-prometheus:9090`
   - Default datasource, read-only
3. **grafana-dashboards-provisioning** - Dashboard provider config
   - Auto-load dashboards from `/etc/grafana/dashboards`
4. **grafana-dashboards** - Dashboard JSON embedded via `.Files.Get`
   - Full 6-row, 28-panel dashboard from `deployment/config/grafana-dashboard.json`

**Helm chart validation tests:**
- 6 tests in `tests/e2e/test_helm_values.py` (values.yaml structure)
- 6 tests in `tests/e2e/test_helm_chart.py` (rendered manifests)
- All 12 tests pass

## Tasks Completed

| Task | Description | Type | Commit |
|------|-------------|------|--------|
| 1 | Add monitoring configuration to values.yaml | TDD | 3b0294b (RED), a42a8ad (GREEN) |
| 2 | Create Prometheus Kubernetes manifests | Auto | a0c2115 |
| 3 | Create Grafana Kubernetes manifests | Auto | 5bec523 |
| 4 | Create monitoring ConfigMaps | Auto | 637c856 |
| 5 | Create Helm chart validation tests | Auto | 02e8a4c |

## TDD Cycle (Task 1)

**RED phase (3b0294b):**
- Created 6 failing tests for values.yaml monitoring section
- Tests checked for prometheus.enabled, grafana.enabled, retention, storage.size
- 4 tests failed (prometheus/grafana sections didn't exist)

**GREEN phase (a42a8ad):**
- Added monitoring.prometheus.* and monitoring.grafana.* sections to values.yaml
- All 6 tests pass
- helm lint passes with 0 errors

**REFACTOR phase:**
- Not needed - values.yaml structure is clean and well-organized

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Dashboard JSON path resolution**
- **Found during:** Task 4 (ConfigMap creation)
- **Issue:** `.Files.Get "../../config/grafana-dashboard.json"` returned empty - Helm cannot access files outside chart directory
- **Fix:** Copied `deployment/config/grafana-dashboard.json` to `deployment/helm/kb-rag-mcp/dashboards/` and updated path to `dashboards/grafana-dashboard.json`
- **Files modified:** deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml
- **Files created:** deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json
- **Commit:** 637c856 (included in Task 4)
- **Rationale:** Helm's `.Files.Get` can only read files within the chart directory tree. Copying the dashboard JSON into the chart makes it accessible to the template engine.

**2. [Rule 2 - Missing functionality] Health port correction**
- **Found during:** Task 4 (Prometheus config creation)
- **Issue:** Plan specified port 8000 for metrics scraping, but health_server.py binds to port 8081 (from values.yaml service.healthPort)
- **Fix:** Updated relabel_configs to replace port with `:8081` instead of `:8000`
- **Files modified:** deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml
- **Commit:** 637c856 (included in Task 4)
- **Rationale:** Matches actual health server configuration in deployment.yaml

## Verification Results

### Automated Tests

**values.yaml validation (test_helm_values.py):**
```bash
pytest tests/e2e/test_helm_values.py -v
```
**Result:** ✅ All 6 tests pass

**Helm chart rendering (test_helm_chart.py):**
```bash
pytest tests/e2e/test_helm_chart.py -v
```
**Result:** ✅ All 6 tests pass

**Helm lint:**
```bash
helm lint deployment/helm/kb-rag-mcp
```
**Result:** ✅ 1 chart(s) linted, 0 chart(s) failed

### Manual Verification

**Test 1: Monitoring enabled by default**
```bash
helm template test-release deployment/helm/kb-rag-mcp | grep "kind: StatefulSet" | grep prometheus
```
**Result:** ✅ Prometheus StatefulSet found

**Test 2: Monitoring can be disabled**
```bash
helm template test-release deployment/helm/kb-rag-mcp --set monitoring.enabled=false | grep -c "prometheus\|grafana"
```
**Result:** ✅ 0 resources (monitoring disabled)

**Test 3: Grafana Ingress renders when enabled**
```bash
helm template test-release deployment/helm/kb-rag-mcp --set monitoring.grafana.ingress.enabled=true | grep -c "kind: Ingress"
```
**Result:** ✅ 1 Ingress resource found

**Test 4: Dashboard JSON embedded correctly**
```bash
helm template test-release deployment/helm/kb-rag-mcp | grep -A 5 "grafana-dashboard.json"
```
**Result:** ✅ Dashboard JSON content present (22KB embedded)

**Test 5: Prometheus config uses Kubernetes service discovery**
```bash
helm template test-release deployment/helm/kb-rag-mcp | grep -A 10 "prometheus.yml" | grep "kubernetes_sd_configs"
```
**Result:** ✅ kubernetes_sd_configs with pod role found

### Success Criteria Met

- [x] values.yaml has monitoring configuration section
- [x] Prometheus StatefulSet with PVC (10Gi) renders correctly
- [x] Grafana Deployment with 3 ConfigMap mounts renders correctly
- [x] Prometheus config uses Kubernetes service discovery for kb-rag-mcp pods
- [x] Grafana datasource ConfigMap points to Prometheus Service
- [x] Grafana dashboard ConfigMap embeds dashboard JSON via .Files.Get
- [x] Optional Grafana Ingress renders when enabled
- [x] Monitoring can be disabled via --set monitoring.enabled=false
- [x] helm lint passes with 0 errors
- [x] E2E tests validate chart structure (12 tests total, all pass)

## Known Stubs

None. All functionality is fully implemented.

## Threat Flags

None. No new security-relevant surface beyond what was planned in threat model.

## Dependencies Satisfied

### Provided by This Plan
- Prometheus StatefulSet with persistent storage
- Grafana Deployment with auto-provisioned datasource and dashboard
- Kubernetes-native service discovery (auto-detects kb-rag-mcp pods)
- Configurable monitoring stack via values.yaml
- Optional Grafana Ingress for external access

### Required by Downstream Plans
- Plan 14-05 (Documentation) can reference Helm deployment instructions
- Future plans can extend monitoring with additional dashboards or alerts

## Technical Notes

### Implementation Details

**Why StatefulSet for Prometheus?**
- Prometheus stores time-series data that should persist across pod restarts
- StatefulSet provides stable pod identity and persistent volume claims
- Alternative (Deployment + PVC) works but StatefulSet is idiomatic for stateful workloads

**Why Deployment for Grafana?**
- Grafana state (datasources, dashboards) is stored in ConfigMaps
- No persistent storage needed beyond ConfigMaps
- Deployment is simpler and sufficient for this use case

**Kubernetes service discovery vs static targets:**
- Plan specified using Kubernetes SD to auto-discover kb-rag-mcp pods
- Relabel configs filter by `app.kubernetes.io/name` label (matches selector labels)
- Excludes prometheus/grafana pods via `app.kubernetes.io/component` drop filter
- Automatically adjusts to HPA scaling (no manual target updates needed)

**Dashboard JSON embedding:**
- Helm's `.Files.Get` only reads files inside the chart directory
- Copied dashboard JSON from `deployment/config/` to `deployment/helm/kb-rag-mcp/dashboards/`
- This creates a single source of truth but requires keeping files in sync
- Alternative: Generate dashboard JSON at template time (complex, rejected)

**Port 8081 for metrics:**
- `deployment/helm/kb-rag-mcp/templates/deployment.yaml` exposes port 8081 as `healthPort`
- `kb_server/health_server.py` binds to port 8081
- Prometheus scrape config uses relabel to replace port with 8081
- Plan incorrectly specified 8000 (MCP SSE port) - corrected during implementation

### Helm Templating Patterns Used

**Conditional rendering:**
```yaml
{{- if and .Values.monitoring.enabled .Values.monitoring.prometheus.enabled }}
```
- Renders Prometheus resources only if both `monitoring.enabled` and `monitoring.prometheus.enabled` are true
- Same pattern for Grafana resources
- Allows granular control (disable entire monitoring stack OR individual components)

**Template functions:**
- `{{ include "kb-rag-mcp.fullname" . }}` - generates unique resource names per release
- `{{ include "kb-rag-mcp.labels" . }}` - applies standard labels to all resources
- `{{ include "kb-rag-mcp.selectorLabels" . }}` - selector labels for Services
- `{{ .Values.monitoring.prometheus.* }}` - accesses values.yaml configuration
- `{{ .Release.Name }}` - current Helm release name
- `{{ .Release.Namespace }}` - current namespace
- `{{ .Files.Get "path" }}` - embeds file content from chart directory
- `{{ toYaml .Values.resources | nindent 12 }}` - YAML formatting with indentation

**ConfigMap data embedding:**
```yaml
data:
  prometheus.yml: |
    global:
      scrape_interval: {{ .Values.monitoring.prometheus.scrapeInterval }}
```
- Pipe `|` preserves multi-line YAML strings
- Nested templates inject values into config files

**Ingress conditional:**
```yaml
{{- if .Values.monitoring.grafana.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
...
{{- end }}
```
- Entire Ingress resource conditionally rendered
- Allows opt-in external access to Grafana

## Self-Check: PASSED

**Created files exist:**
```bash
$ ls deployment/helm/kb-rag-mcp/templates/prometheus.yaml
deployment/helm/kb-rag-mcp/templates/prometheus.yaml
$ ls deployment/helm/kb-rag-mcp/templates/grafana.yaml
deployment/helm/kb-rag-mcp/templates/grafana.yaml
$ ls deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml
deployment/helm/kb-rag-mcp/templates/configmap-monitoring.yaml
$ ls deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json
deployment/helm/kb-rag-mcp/dashboards/grafana-dashboard.json
$ ls tests/e2e/test_helm_values.py
tests/e2e/test_helm_values.py
$ ls tests/e2e/test_helm_chart.py
tests/e2e/test_helm_chart.py
```
✅ All files found

**Modified files contain expected changes:**
```bash
$ grep -q "prometheus:" deployment/helm/kb-rag-mcp/values.yaml && echo "FOUND: prometheus section"
FOUND: prometheus section
$ grep -q "grafana:" deployment/helm/kb-rag-mcp/values.yaml && echo "FOUND: grafana section"
FOUND: grafana section
```
✅ values.yaml updated

**Commits exist:**
```bash
$ git log --oneline --all | grep "3b0294b" && echo "FOUND: 3b0294b (RED)"
FOUND: 3b0294b (RED)
$ git log --oneline --all | grep "a42a8ad" && echo "FOUND: a42a8ad (GREEN)"
FOUND: a42a8ad (GREEN)
$ git log --oneline --all | grep "a0c2115" && echo "FOUND: a0c2115 (Task 2)"
FOUND: a0c2115 (Task 2)
$ git log --oneline --all | grep "5bec523" && echo "FOUND: 5bec523 (Task 3)"
FOUND: 5bec523 (Task 3)
$ git log --oneline --all | grep "637c856" && echo "FOUND: 637c856 (Task 4)"
FOUND: 637c856 (Task 4)
$ git log --oneline --all | grep "02e8a4c" && echo "FOUND: 02e8a4c (Task 5)"
FOUND: 02e8a4c (Task 5)
```
✅ All commits found

**All verification commands pass:**
```bash
$ pytest tests/e2e/test_helm_values.py -v
6 passed
$ pytest tests/e2e/test_helm_chart.py -v
6 passed
$ helm lint deployment/helm/kb-rag-mcp
1 chart(s) linted, 0 chart(s) failed
```
✅ All verifications pass

All checks passed. Plan 14-04 successfully completed.

## Next Steps

1. **Plan 14-05:** Update documentation (OPERATIONS.md, KUBERNETES.md) with monitoring stack instructions
2. **Manual testing:** Deploy chart to test cluster, verify Grafana dashboard loads
3. **Future enhancements:**
   - Add Prometheus alerting rules (alertmanager integration)
   - Add ServiceMonitor CRD support for Prometheus Operator
   - Add custom Grafana dashboards for specific use cases
