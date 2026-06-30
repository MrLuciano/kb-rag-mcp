# Phase 39: Observability Backlog

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Grafana connectivity check to health system, request ID middleware for traceability, and per-operation percentile latency metrics (p50/p95/p99).

**Architecture:** Three independent features in the observability layer: (1) a new `check_grafana()` function in `kb_server/health.py` and a restructured `/ready` endpoint in `health_server.py`, (2) a Starlette middleware generating `X-Request-Id` on every request, and (3) a `PercentileTracker` using sorted-list histograms exposed via existing Prometheus `/metrics` endpoint.

**Tech Stack:** FastAPI, Starlette middleware, Prometheus, asyncio, `uuid`, `bisect`.

---

### Task 1: Add Grafana connectivity check to health system

**Files:**
- Modify: `kb_server/health.py`
- Modify: `kb_server/health_server.py`
- Test: `tests/test_health_grafana.py`

- [ ] **Step 1: Write the failing test — Grafana check returns HealthStatus**

`tests/test_health_grafana.py`:
```python
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_check_grafana_success():
    from kb_server.health import check_grafana
    with patch("kb_server.health.asyncio.open_connection",
               new_callable=AsyncMock) as mock_conn:
        mock_conn.return_value = (AsyncMock(), AsyncMock())
        result = await check_grafana()
        assert result.healthy is True
        assert result.name == "grafana"


@pytest.mark.asyncio
async def test_check_grafana_failure():
    from kb_server.health import check_grafana
    with patch("kb_server.health.asyncio.open_connection",
               side_effect=ConnectionRefusedError("No connection")):
        result = await check_grafana()
        assert result.healthy is False
        assert "No connection" in result.message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_health_grafana.py -x -v 2>&1 | tail -10`
Expected: `ImportError` or `AttributeError`

- [ ] **Step 3: Add check_grafana to health.py**

Add to `kb_server/health.py` after `check_filesystem()`:

```python
import asyncio
from urllib.parse import urlparse


async def check_grafana() -> HealthStatus:
    """
    Check Grafana connectivity via TCP connection test.

    Uses GRAFANA_URL config (or env var) to extract host:port.
    Falls back to healthy=True if GRAFANA_URL is not configured.
    """
    import os
    start = time.time()
    grafana_url = os.getenv("GRAFANA_URL", "")
    if not grafana_url:
        return HealthStatus(
            name="grafana",
            healthy=True,
            message="Not configured",
            latency_ms=0.0,
        )
    try:
        parsed = urlparse(grafana_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 3000
        reader, writer = await asyncio.open_connection(host, port)
        writer.close()
        await writer.wait_closed()
        latency = (time.time() - start) * 1000
        return HealthStatus(
            name="grafana",
            healthy=True,
            message=f"Connected to {host}:{port}",
            latency_ms=latency,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        log.error(f"Grafana health check failed: {e}")
        return HealthStatus(
            name="grafana",
            healthy=False,
            message=str(e),
            latency_ms=latency,
        )
```

Then add `check_grafana` to `check_all_components()`:
```python
    checks = [
        check_embedding_service(),
        check_vector_store(),
        check_cache(),
        check_database(),
        check_filesystem(),
        check_grafana(),
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_health_grafana.py -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/health.py tests/test_health_grafana.py
git commit -m "feat(39): add Grafana connectivity health check"
```

---

### Task 2: Request ID middleware

**Files:**
- Create: `kb_server/observability/middleware.py`
- Test: `tests/test_request_id_middleware.py`

- [ ] **Step 1: Write the failing test — request ID is generated and returned**

`tests/test_request_id_middleware.py`:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI


@pytest.fixture
def app_with_middleware():
    app = FastAPI()
    from kb_server.observability.middleware import RequestIDMiddleware
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    async def test_route():
        from kb_server.observability.middleware import _current_request_id
        return {"request_id": _current_request_id.get()}

    return app


@pytest.mark.asyncio
async def test_request_id_generated(app_with_middleware):
    transport = ASGITransport(app=app_with_middleware)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/test")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    rid = resp.headers["x-request-id"]
    assert len(rid) == 36  # UUID v4
    assert rid == resp.json()["request_id"]


@pytest.mark.asyncio
async def test_request_id_preserved(app_with_middleware):
    transport = ASGITransport(app=app_with_middleware)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/test", headers={"X-Request-Id": "my-custom-id"})
    assert resp.status_code == 200
    assert resp.headers["x-request-id"] == "my-custom-id"


@pytest.mark.asyncio
async def test_request_id_isolation(app_with_middleware):
    transport = ASGITransport(app=app_with_middleware)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp1 = await ac.get("/test")
        resp2 = await ac.get("/test")
    assert resp1.headers["x-request-id"] != resp2.headers["x-request-id"]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_request_id_middleware.py -x -v 2>&1 | tail -10`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create RequestIDMiddleware**

`kb_server/observability/middleware.py`:
```python
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_current_request_id: ContextVar[str] = ContextVar("_current_request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that ensures every request has an X-Request-Id header.

    If the client sends one, it is preserved. Otherwise a UUID v4 is generated.
    The value is set in a ContextVar for propagation to downstream code.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", "") or str(uuid.uuid4())
        _current_request_id.set(request_id)

        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


def get_current_request_id() -> str:
    """Get the current request ID from context."""
    return _current_request_id.get()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_request_id_middleware.py -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/observability/middleware.py tests/test_request_id_middleware.py
git commit -m "feat(39): add request ID middleware with ContextVar"
```

---

### Task 3: Per-operation percentile metrics (p50/p95/p99)

**Files:**
- Create: `kb_server/observability/percentiles.py`
- Modify: `kb_server/server.py` (add tracking to tool handlers)
- Test: `tests/test_percentile_metrics.py`

- [ ] **Step 1: Write the failing test — PercentileTracker records and reports**

`tests/test_percentile_metrics.py`:
```python
import pytest
import asyncio


@pytest.mark.asyncio
async def test_tracker_records_latency():
    from kb_server.observability.percentiles import PercentileTracker
    tracker = PercentileTracker(window_size=100)
    tracker.record("search_kb", 0.05)
    tracker.record("search_kb", 0.10)
    tracker.record("search_kb", 0.20)
    stats = tracker.get_stats("search_kb")
    assert stats["count"] == 3
    assert stats["p50"] <= stats["p95"] <= stats["p99"]


@pytest.mark.asyncio
async def test_tracker_empty():
    from kb_server.observability.percentiles import PercentileTracker
    tracker = PercentileTracker()
    stats = tracker.get_stats("nonexistent")
    assert stats["count"] == 0


@pytest.mark.asyncio
async def test_tracker_window_limits():
    from kb_server.observability.percentiles import PercentileTracker
    tracker = PercentileTracker(window_size=5)
    for i in range(10):
        tracker.record("op", float(i))
    stats = tracker.get_stats("op")
    assert stats["count"] == 10  # we don't discard, we snapshot


@pytest.mark.asyncio
async def test_tracker_reset():
    from kb_server.observability.percentiles import PercentileTracker
    tracker = PercentileTracker(window_size=10)
    tracker.record("op", 0.1)
    tracker.reset("op")
    stats = tracker.get_stats("op")
    assert stats["count"] == 0


@pytest.mark.asyncio
async def test_tracker_prometheus_export():
    from kb_server.observability.percentiles import PercentileTracker
    tracker = PercentileTracker()
    tracker.record("search_kb", 0.05)
    tracker.record("list_documents", 0.02)
    metrics_text = tracker.export_prometheus()
    assert "kb_tool_latency_p50" in metrics_text
    assert "kb_tool_latency_p95" in metrics_text
    assert "kb_tool_latency_p99" in metrics_text
    assert 'tool="search_kb"' in metrics_text
    assert 'tool="list_documents"' in metrics_text
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_percentile_metrics.py -x -v 2>&1 | tail -10`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create PercentileTracker**

`kb_server/observability/percentiles.py`:
```python
"""Per-operation percentile latency tracking.

Uses sorted-list histograms (no HDR dependency) to track p50/p95/p99
latency per MCP tool operation. Resets after each scrape to avoid
unbounded memory growth.
"""

import bisect
import time
from collections import defaultdict
from typing import List


class PercentileTracker:
    """Tracks latency percentiles per operation.

    Maintains a sorted list of latency samples per operation key.
    Uses `export_prometheus()` to generate Prometheus gauge lines and
    reset the internal state.
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self._data: dict[str, List[float]] = defaultdict(list)

    def record(self, operation: str, latency_s: float) -> None:
        """Record a latency sample for an operation."""
        samples = self._data[operation]
        bisect.insort(samples, latency_s)
        # Trim to window_size to bound memory
        if len(samples) > self.window_size:
            self._data[operation] = samples[-self.window_size:]

    def get_stats(self, operation: str) -> dict:
        """Get stats for an operation without resetting."""
        samples = self._data.get(operation, [])
        if not samples:
            return {"count": 0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
        n = len(samples)
        return {
            "count": n,
            "p50": samples[int(n * 0.50)],
            "p95": samples[int(n * 0.95)],
            "p99": samples[int(n * 0.99)],
        }

    def reset(self, operation: str) -> None:
        """Clear recorded samples for an operation."""
        self._data.pop(operation, None)

    def reset_all(self) -> None:
        """Clear all recorded samples."""
        self._data.clear()

    def export_prometheus(self) -> str:
        """Export current stats as Prometheus gauge lines and reset.

        Returns:
            Prometheus-format text with gauge metrics per operation.
        """
        lines = []
        for operation in list(self._data.keys()):
            stats = self.get_stats(operation)
            if stats["count"] == 0:
                continue
            labels = f'tool="{operation}"'
            lines.append(
                f'# HELP kb_tool_latency_p50 P50 latency in seconds\n'
                f'# TYPE kb_tool_latency_p50 gauge\n'
                f'kb_tool_latency_p50{{{labels}}} {stats["p50"]}\n'
                f'# HELP kb_tool_latency_p95 P95 latency in seconds\n'
                f'# TYPE kb_tool_latency_p95 gauge\n'
                f'kb_tool_latency_p95{{{labels}}} {stats["p95"]}\n'
                f'# HELP kb_tool_latency_p99 P99 latency in seconds\n'
                f'# TYPE kb_tool_latency_p99 gauge\n'
                f'kb_tool_latency_p99{{{labels}}} {stats["p99"]}'
            )
        self.reset_all()
        return "\n".join(lines)


# Module-level singleton
_tracker: PercentileTracker | None = None


def get_percentile_tracker() -> PercentileTracker:
    global _tracker
    if _tracker is None:
        _tracker = PercentileTracker()
    return _tracker
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_percentile_metrics.py -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Integrate with health_server.py /metrics endpoint**

Modify `kb_server/health_server.py` metrics endpoint to include percentile data. Add after the existing `generate_latest()` call:

```python
    # Append percentile metrics
    from kb_server.observability.percentiles import get_percentile_tracker
    tracker = get_percentile_tracker()
    extra = tracker.export_prometheus()
    if extra:
        existing = generate_latest()
        combined = existing + b"\n" + extra.encode()
        return Response(combined, media_type=CONTENT_TYPE_LATEST)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

- [ ] **Step 6: Integrate with server.py tool handlers**

In `kb_server/server.py`, in each tool handler (search_kb, list_documents, get_chunk, kb_stats), add latency tracking around the core logic:

```python
    from kb_server.observability.percentiles import get_percentile_tracker
    _start = time.time()
    # ... existing handler logic ...
    latency = time.time() - _start
    get_percentile_tracker().record("search_kb", latency)
```

This should be applied in `_search_kb`, `_list_documents_tool`, `_get_chunk_tool`, and `_kb_stats_tool`.

- [ ] **Step 7: Commit**

```bash
git add kb_server/observability/percentiles.py tests/test_percentile_metrics.py
git commit -m "feat(39): add per-operation percentile latency tracking"
```

---

### Task 4: Expose health summary via admin API

**Files:**
- Modify: `kb_server/health_server.py` or create new endpoint in existing API router

- [ ] **Step 1: Add health summary endpoint to admin API**

If a `kb_server/router.py` exists or will exist for admin APIs, add:

```python
@router.get("/api/v1/health")
async def admin_health_summary():
    from kb_server.health import get_health_summary
    return await get_health_summary()
```

Otherwise, the existing `/health/detailed` on the health server already provides this. This step is a note for integration during Phase 28c (Admin SPA Shell) when the admin API router is set up.

- [ ] **Step 2: Commit (if any changes)**

```bash
git add kb_server/health_server.py
git commit -m "feat(39): expose health summary via /api/v1/health"
```
