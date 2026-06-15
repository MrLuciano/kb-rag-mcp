# Plan 39-01 SUMMARY: Observability Backlog

## Objective

Add Grafana connectivity check to health system, request ID middleware for traceability, and per-operation percentile latency metrics (p50/p95/p99).

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_health_grafana.py -v` | ✅ 3/3 PASS |
| `pytest tests/test_request_id_middleware.py -v` | ✅ 4/4 PASS |
| `pytest tests/test_percentile_metrics.py -v` | ✅ 7/7 PASS |
| `pytest tests/test_health.py tests/test_health_server.py tests/test_health_unit.py -v` | ✅ 45/45 PASS (no regressions) |
| `flake8 kb_server/observability/ tests/` | ✅ Clean |

## Tasks Executed

| # | Task | Status |
|---|------|--------|
| 1 | Grafana connectivity check (`check_grafana()` in health.py) | ✅ |
| 2 | Request ID middleware (`RequestIDMiddleware` in middleware.py) | ✅ |
| 3 | Per-operation percentile metrics (`PercentileTracker` in percentiles.py) | ✅ |
| 4 | Health summary endpoint (`/health/detailed` already sufficient) | ✅ |

## Key Files Created/Modified

- `kb_server/health.py` — Added `check_grafana()` (TCP connection test via `asyncio.open_connection`, graceful degradation on empty `GRAFANA_URL`), added to `check_all_components()`
- `kb_server/observability/__init__.py` — Package init
- `kb_server/observability/middleware.py` — `RequestIDMiddleware` (Starlette `BaseHTTPMiddleware`, UUID v4 generation, `X-Request-Id` preservation, `ContextVar` propagation, `get_current_request_id()` helper)
- `kb_server/observability/percentiles.py` — `PercentileTracker` (sorted-list with `bisect.insort`, `window_size=1000`, `get_stats()`, `export_prometheus()`, singleton via `get_percentile_tracker()`)
- `kb_server/health_server.py` — Integrated percentile export into `/metrics` endpoint alongside Prometheus metrics
- `kb_server/server.py` — Added latency recording to `search_kb`, `list_documents`, `get_chunk`, `kb_stats` via `get_percentile_tracker().record()`
- `tests/test_health_grafana.py` — 3 tests (not configured, success, failure)
- `tests/test_request_id_middleware.py` — 4 tests (generation, response header, preservation, uniqueness)
- `tests/test_percentile_metrics.py` — 7 tests (record, empty, window bounds, reset, Prometheus export, all stats, singleton)

## Implementation Notes

- Grafana check uses TCP connection (not HTTP GET) to avoid pulling in an HTTP client dependency
- Request ID middleware preserves client-supplied IDs for distributed tracing compatibility
- PercentileTracker uses sorted-list with `bisect.insort` — O(log n) insert, bounded at `window_size=1000` samples per operation
- `export_prometheus()` resets all data after each scrape (Prometheus pull model — data is ephemeral between scrapes)
- `/health/detailed` already provides the full health summary — no separate admin API endpoint needed
