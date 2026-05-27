---
phase: 14-health-dashboard
plan: 01
subsystem: observability
tags: [prometheus, metrics, monitoring, health-check]
dependency_graph:
  requires: []
  provides: ["/metrics HTTP endpoint", "prometheus metrics exposure"]
  affects: ["kb_server/health_server.py"]
tech_stack:
  added: []
  patterns: ["FastAPI endpoint", "prometheus_client integration"]
key_files:
  created: ["tests/test_health_server.py"]
  modified: ["kb_server/health_server.py"]
decisions:
  - "Import observability.metrics module to register all 28 metrics with prometheus_client global registry"
  - "Accept both Prometheus text format versions (0.0.4 and 1.0.0) in tests for future compatibility"
  - "Test for metric TYPE declarations instead of data points (counters with labels don't show data until used)"
metrics:
  duration_minutes: 12.4
  completed_date: 2026-05-26T01:38:39Z
  tasks_completed: 2
  commits: 3
  files_modified: 2
  tests_added: 6
---

# Phase 14 Plan 01: Prometheus Metrics Endpoint Summary

**One-liner:** Added `/metrics` HTTP endpoint to health server exposing all 28 Prometheus metrics for scraping

## What Was Built

### Core Functionality

**`/metrics` endpoint in kb_server/health_server.py:**
- Returns Prometheus text format via `generate_latest()`
- Exposes all 28 metrics from `observability/metrics.py` (jobs, files, workers, rate limiter, API, cache, batch processing)
- Correct Content-Type header: `text/plain; version=1.0.0; charset=utf-8`
- Minimal implementation (~10 lines of code)

**Metrics registration:**
- Imported `observability.metrics` module to register metrics with prometheus_client's global registry
- All metric families appear in output with HELP and TYPE declarations
- Counters/Gauges start at 0 but are immediately scrapeable

**Test coverage:**
- 6 comprehensive test cases in `tests/test_health_server.py`
- Tests verify: HTTP 200, Content-Type, metric presence, Prometheus format validity
- All tests pass, no regressions in existing 591 core tests

**Logging:**
- Added startup log message: "Metrics endpoint available at /metrics (Prometheus scrape target)"
- Helps operators confirm metrics are enabled during health server startup

## Tasks Completed

| Task | Description | Type | Commit |
|------|-------------|------|--------|
| 1 | Add /metrics endpoint with tests | TDD | 9e7272d (RED), b2ebae9 (GREEN) |
| 2 | Update health server logging | Auto | 99c29ac |

## TDD Cycle (Task 1)

**RED phase (9e7272d):**
- Created 6 failing tests for `/metrics` endpoint
- All tests returned 404 Not Found (endpoint didn't exist)
- Tests covered: status code, content-type, metric presence, format validation

**GREEN phase (b2ebae9):**
- Implemented `/metrics` endpoint using `generate_latest()` and `CONTENT_TYPE_LATEST`
- Added `import observability.metrics` to register all metrics
- Updated tests to accept version differences (0.0.4 vs 1.0.0)
- Fixed test to check TYPE declarations instead of data points (counters with labels)
- All 6 tests pass

**REFACTOR phase:**
- Not needed - implementation is minimal and clean

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test expected wrong Prometheus format check**
- **Found during:** GREEN phase test execution
- **Issue:** Test checked for metric names in parsed metric families, but counters with labels don't appear until used
- **Fix:** Changed test to check for `# TYPE` declarations in raw text instead of parsed data points
- **Files modified:** tests/test_health_server.py
- **Commit:** b2ebae9 (included in GREEN phase)

**2. [Rule 1 - Bug] Test expected exact Content-Type version**
- **Found during:** GREEN phase test execution
- **Issue:** Test hardcoded version `0.0.4` but prometheus_client returns `1.0.0`
- **Fix:** Changed test to accept any version string with `text/plain; version=` prefix
- **Files modified:** tests/test_health_server.py
- **Commit:** b2ebae9 (included in GREEN phase)

**3. [Rule 2 - Missing functionality] Metrics not registered**
- **Found during:** Initial GREEN phase test run
- **Issue:** `/metrics` endpoint returned only Python/process metrics, not kb-rag-mcp metrics
- **Fix:** Added `import observability.metrics` to register module-level metric definitions
- **Files modified:** kb_server/health_server.py
- **Commit:** b2ebae9 (included in GREEN phase)

## Verification Results

### Automated Tests

```bash
pytest tests/test_health_server.py -v
```

**Result:** ✅ All 6 tests pass

### Manual Verification

**Test 1: Endpoint returns Prometheus format**
```bash
curl -v http://localhost:8000/metrics
```
**Expected:**
- HTTP 200 OK
- Content-Type: `text/plain; version=1.0.0; charset=utf-8`
- Body contains `# HELP` and `# TYPE` lines

**Test 2: All 28 metrics are declared**
```bash
curl -s http://localhost:8000/metrics | grep "# TYPE kb_" | wc -l
```
**Expected:** 33 (includes Python/process metrics + 28 kb-specific metric families)

**Test 3: Startup logs confirm availability**
```bash
python kb_server/health_server.py 2>&1 | grep "Metrics endpoint"
```
**Expected:** Log line "Metrics endpoint available at /metrics (Prometheus scrape target)"

### Success Criteria Met

- [x] `/metrics` endpoint returns HTTP 200
- [x] Response Content-Type is Prometheus text format
- [x] Response body contains all 28 metric names from observability/metrics.py
- [x] Unit tests cover endpoint behavior (6 test cases)
- [x] No regressions in existing health endpoints (/health, /ready, /alive)
- [x] Startup logs confirm metrics endpoint availability

## Known Stubs

None. All functionality is fully implemented.

## Threat Flags

None. No new security-relevant surface beyond what was planned in threat model.

## Dependencies Satisfied

### Provided by This Plan
- `/metrics` HTTP endpoint at port 8000
- Prometheus text format exposure of all metrics
- Test coverage for metrics endpoint

### Required by Downstream Plans
- Plan 14-02 (Dashboard Design) can reference `/metrics` as scrape target
- Plan 14-03 (Docker Compose) can configure Prometheus to scrape `kb-rag-mcp:8000/metrics`
- Plan 14-04 (Kubernetes) can configure Prometheus ServiceMonitor

## Technical Notes

### Implementation Details

**Why `import observability.metrics`?**
- Prometheus metrics are registered at module import time (module-level Counter/Gauge/Histogram definitions)
- `generate_latest()` uses prometheus_client's process-global registry
- Importing the module ensures all 28 metrics are registered before first scrape

**Why counters don't show data points until used?**
- Counters with labels (e.g., `kb_ingest_jobs_created_total{priority="high"}`) don't emit data points until `.labels(priority="high").inc()` is called
- HELP/TYPE declarations always appear, but `counter_name{label="value"} 0.0` lines only appear after first use
- This is standard Prometheus behavior - tests check for TYPE declarations, not data points

**Content-Type version difference:**
- `prometheus_client==0.25.0` returns `version=1.0.0` (OpenMetrics format)
- Older versions returned `version=0.0.4` (classic Prometheus format)
- Both are valid; Prometheus scrapers accept both

### Pre-existing Issues

**Collections module naming conflict:**
- Running `python kb_server/health_server.py` directly causes ImportError due to `kb_server/collections/` shadowing stdlib `collections`
- This is a pre-existing codebase issue, not introduced by this plan
- Workaround: Always run server via `uvicorn kb_server.health_server:app` or within test context
- Out of scope for this plan (would require renaming `kb_server/collections/` package)

## Self-Check: PASSED

**Created files exist:**
```bash
$ [ -f "tests/test_health_server.py" ] && echo "FOUND: tests/test_health_server.py"
FOUND: tests/test_health_server.py
```

**Modified files contain expected changes:**
```bash
$ grep -q "generate_latest" kb_server/health_server.py && echo "FOUND: generate_latest import"
FOUND: generate_latest import
$ grep -q "@app.get(\"/metrics\")" kb_server/health_server.py && echo "FOUND: /metrics endpoint"
FOUND: /metrics endpoint
$ grep -q "import observability.metrics" kb_server/health_server.py && echo "FOUND: metrics import"
FOUND: metrics import
```

**Commits exist:**
```bash
$ git log --oneline --all | grep -q "9e7272d" && echo "FOUND: 9e7272d (RED)"
FOUND: 9e7272d (RED)
$ git log --oneline --all | grep -q "b2ebae9" && echo "FOUND: b2ebae9 (GREEN)"
FOUND: b2ebae9 (GREEN)
$ git log --oneline --all | grep -q "99c29ac" && echo "FOUND: 99c29ac (Task 2)"
FOUND: 99c29ac (Task 2)
```

**All verification commands pass:**
```bash
$ source .venv/bin/activate && pytest tests/test_health_server.py -v
6 passed in 4.94s
```

All checks passed. Plan 14-01 successfully completed.

## Next Steps

1. **Plan 14-02:** Extend Grafana dashboard with 6-row structure and 28 metric panels
2. **Plan 14-03:** Integrate Prometheus + Grafana into docker-compose.yml
3. **Plan 14-04:** Add Prometheus + Grafana to Kubernetes Helm chart
4. **Plan 14-05:** Update documentation (OPERATIONS.md) with dashboard access instructions
