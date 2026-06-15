# Phase 28: MCP Streamable HTTP Transport

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third MCP transport (streamable HTTP) alongside existing stdio and SSE, enabling browser-based MCP clients to connect via HTTP POST/GET.

**Architecture:** A new `elif TRANSPORT == "streamable-http"` branch in `server.py:main()` creates a Starlette app with CORS middleware and routes all MCP methods through `StreamableHTTPSessionManager(app=app)`. The existing `mcp.server.Server("kb-rag")` instance is reused — no changes to tool handlers. Auth, rate limiting, and observability wrappers apply before transport dispatch.

**Tech Stack:** `mcp==1.27.1` (provides `StreamableHTTPSessionManager`, `StreamableHTTPServerTransport`, `TransportSecuritySettings`), Starlette, uvicorn, existing `auth.py`, existing rate limiter.

---

### Task 1: Add streamable-http transport branch in server.py

**Files:**
- Modify: `kb_server/server.py` (after the `elif TRANSPORT == "sse":` block, before error handling)
- Test: `tests/test_server_streamable_http.py`

- [ ] **Step 1: Write the failing test — test server starts with TRANSPORT=streamable-http**

`tests/test_server_streamable_http.py`:
```python
import os
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_streamable_http_transport_env():
    """Server main() accepts TRANSPORT=streamable-http without error."""
    os.environ["TRANSPORT"] = "streamable-http"
    os.environ["MCP_PORT"] = "18765"
    os.environ["MCP_HOST"] = "127.0.0.1"
    os.environ["MCP_ENDPOINT"] = "/mcp-test"
    from kb_server.server import main
    with patch("kb_server.server.VectorStore"), \
         patch("kb_server.server.EmbedClient"), \
         patch("kb_server.server.CollectionRouter"), \
         patch("kb_server.server.StreamableHTTPSessionManager") as mock_mgr, \
         patch("uvicorn.Server.serve", new_callable=AsyncMock) as mock_serve:
        mock_mgr.return_value.run.return_value.__aenter__ = AsyncMock()
        mock_mgr.return_value.run.return_value.__aexit__ = AsyncMock()
        await main()
        mock_mgr.assert_called_once()
        assert mock_mgr.call_args[1]["app"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_server_streamable_http.py::test_streamable_http_transport_env -x -v 2>&1 | tail -20`
Expected: `ModuleNotFoundError` or `ImportError` because the code doesn't exist yet.

- [ ] **Step 3: Add the streamable-http branch to server.py**

In `kb_server/server.py`, locate the `if TRANSPORT == "sse":` block (around line 1402). After its closing `await server.serve()` line and the `elif TRANSPORT == "stdio":` block, add the new branch. Insert before the final `else:` that raises the error.

Import `StreamableHTTPSessionManager` and `TransportSecuritySettings` conditionally:

```python
    elif TRANSPORT == "streamable-http":
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware
        from starlette.responses import Response
        from starlette.routing import Route
        from mcp.server.streamable_http_manager import (
            StreamableHTTPSessionManager,
            TransportSecuritySettings,
        )

        MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
        MCP_PORT = int(os.getenv("MCP_PORT", "8765"))
        MCP_ENDPOINT = os.getenv("MCP_ENDPOINT", "/mcp")
        MCP_JSON_RESPONSE = os.getenv("MCP_JSON_RESPONSE", "false").lower() in (
            "true", "1",
        )
        MCP_STATELESS = os.getenv("MCP_STATELESS", "false").lower() in (
            "true", "1",
        )
        MCP_SESSION_TIMEOUT = float(
            os.getenv("MCP_SESSION_TIMEOUT", "300")
        )

        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[MCP_HOST] if MCP_HOST != "0.0.0.0" else [],
            allowed_origins=[],
        )

        session_mgr = StreamableHTTPSessionManager(
            app=app,
            json_response=MCP_JSON_RESPONSE,
            stateless=MCP_STATELESS,
            security_settings=security,
            session_idle_timeout=MCP_SESSION_TIMEOUT,
        )

        async def handle_mcp(request):
            _current_transport.set("streamable-http")
            if RATE_LIMIT_ENABLED and rate_limiter is not None:
                allowed, retry_after = await rate_limiter.check(subject)
                if not allowed:
                    record_rate_limit_rejected("streamable-http")
                    return Response(
                        content='{"error":"Rate limit exceeded"}',
                        status_code=429,
                        media_type="application/json",
                        headers={"Retry-After": str(retry_after)},
                    )
                record_rate_limit_allowed("streamable-http")
            await session_mgr.handle_request(
                request.scope, request.receive, request._send
            )

        starlette_app = Starlette(
            routes=[
                Route(
                    MCP_ENDPOINT,
                    endpoint=handle_mcp,
                    methods=["GET", "POST", "DELETE", "OPTIONS"],
                ),
                Route("/health", endpoint=lambda r: Response(
                    content='{"status":"ok","service":"kb-rag"}',
                    media_type="application/json",
                )),
            ],
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                    allow_headers=[
                        "Content-Type", "Accept", "Authorization",
                        "Mcp-Session-Id", "Last-Event-ID",
                        "MCP-Protocol-Version",
                    ],
                    expose_headers=["Mcp-Session-Id", "Content-Type"],
                ),
            ],
        )

        log.info(
            f"Streamable HTTP server at http://{MCP_HOST}:{MCP_PORT}{MCP_ENDPOINT} "
            f"(json_response={MCP_JSON_RESPONSE}, stateless={MCP_STATELESS})"
        )
        async with session_mgr.run():
            config = uvicorn.Config(
                starlette_app,
                host=MCP_HOST,
                port=MCP_PORT,
                log_level="info",
            )
            server = uvicorn.Server(config)
            await server.serve()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_server_streamable_http.py::test_streamable_http_transport_env -x -v 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/server.py tests/test_server_streamable_http.py
git commit -m "feat(28): add streamable-http transport branch to server.py"
```

---

### Task 2: Auth middleware on streamable-http endpoint

**Files:**
- Modify: `kb_server/server.py` (handle_mcp function)
- Modify: `tests/test_server_streamable_http.py`

- [ ] **Step 1: Write the failing test — auth check on /mcp when AUTH_ENABLED=true**

Append to `tests/test_server_streamable_http.py`:
```python
@pytest.mark.asyncio
async def test_streamable_http_auth_rejection():
    """Streamable HTTP returns 401 when AUTH_ENABLED and no key provided."""
    os.environ["TRANSPORT"] = "streamable-http"
    os.environ["MCP_PORT"] = "18766"
    os.environ["MCP_HOST"] = "127.0.0.1"
    os.environ["MCP_ENDPOINT"] = "/mcp-auth-test"
    os.environ["AUTH_ENABLED"] = "true"
    from kb_server.server import _current_subject, _current_transport
    _current_subject.set("test")
    _current_transport.set("test")
    mock_request = AsyncMock()
    mock_request.headers = {"Authorization": ""}
    mock_request.scope = {"type": "http", "method": "POST", "path": "/mcp-auth-test"}
    mock_request.receive = AsyncMock()
    mock_request._send = AsyncMock()

    with patch("kb_server.server.VectorStore"), \
         patch("kb_server.server.EmbedClient"), \
         patch("kb_server.server.CollectionRouter"), \
         patch("kb_server.server.StreamableHTTPSessionManager") as mock_mgr, \
         patch("kb_server.server.is_auth_enabled", return_value=True), \
         patch("kb_server.server.verify_request", return_value=(False, "Missing API key")):
        mock_mgr.return_value.run.return_value.__aenter__ = AsyncMock()
        mock_mgr.return_value.run.return_value.__aexit__ = AsyncMock()
        from kb_server.server import main
        await main()
    del os.environ["AUTH_ENABLED"]
```

You'll need to add the auth check inside `handle_mcp` in `server.py`. Replace the current `handle_mcp` with auth-guarded version.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_server_streamable_http.py::test_streamable_http_auth_rejection -x -v 2>&1 | tail -20`
Expected: FAIL

- [ ] **Step 3: Add auth check to handle_mcp**

Modify the `handle_mcp` function in server.py to include auth check:
```python
        async def handle_mcp(request):
            from kb_server.auth import is_auth_enabled, verify_request
            _current_transport.set("streamable-http")

            if is_auth_enabled():
                auth_header = request.headers.get("Authorization", "")
                ok, err = verify_request(auth_header)
                if not ok:
                    return Response(
                        content=f'{{"error":"{err}"}}',
                        status_code=401,
                        media_type="application/json",
                    )

            if RATE_LIMIT_ENABLED and rate_limiter is not None:
                allowed, retry_after = await rate_limiter.check(subject)
                if not allowed:
                    record_rate_limit_rejected("streamable-http")
                    return Response(
                        content='{"error":"Rate limit exceeded"}',
                        status_code=429,
                        media_type="application/json",
                        headers={"Retry-After": str(retry_after)},
                    )
                record_rate_limit_allowed("streamable-http")

            await session_mgr.handle_request(
                request.scope, request.receive, request._send
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_server_streamable_http.py::test_streamable_http_auth_rejection -x -v 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/server.py tests/test_server_streamable_http.py
git commit -m "feat(28): add auth middleware to streamable-http endpoint"
```

---

### Task 3: Subject resolution and rate limiting for streamable-http

**Files:**
- Modify: `kb_server/server.py` (subject resolution)
- Modify: `tests/test_server_streamable_http.py`

- [ ] **Step 1: Write the failing test — subject is set for rate limiting**

Append to `tests/test_server_streamable_http.py`:
```python
@pytest.mark.asyncio
async def test_streamable_http_sets_subject():
    """Subject is derived from auth header or IP for rate limiting."""
    os.environ["TRANSPORT"] = "streamable-http"
    os.environ["MCP_PORT"] = "18767"
    os.environ["MCP_HOST"] = "127.0.0.1"
    os.environ["MCP_ENDPOINT"] = "/mcp-subject-test"
    from kb_server.server import _current_subject, _current_transport

    with patch("kb_server.server.VectorStore"), \
         patch("kb_server.server.EmbedClient"), \
         patch("kb_server.server.CollectionRouter"), \
         patch("kb_server.server.StreamableHTTPSessionManager") as mock_mgr:
        mock_mgr.return_value.run.return_value.__aenter__ = AsyncMock()
        mock_mgr.return_value.run.return_value.__aexit__ = AsyncMock()
        from kb_server.server import main
        await main()
        assert _current_subject.get() is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_server_streamable_http.py::test_streamable_http_sets_subject -x -v 2>&1 | tail -20`
Expected: FAIL

- [ ] **Step 3: Add subject resolution to handle_mcp**

Update subject resolution at the top of `handle_mcp`. It needs to derive the rate-limit subject from the auth header (key prefix) or client IP. Add this before auth check:

```python
        async def handle_mcp(request):
            from kb_server.auth import is_auth_enabled, verify_request

            subject = "unknown"
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                key = auth_header[7:]
                prefix = key[:8] if len(key) >= 8 else key
                subject = f"key:{prefix}"
            else:
                forwarded = request.headers.get("X-Forwarded-For", "")
                subject = (
                    forwarded.split(",")[0].strip()
                    or (request.client.host if request.client else "unknown")
                )
            _current_subject.set(subject)
            _current_transport.set("streamable-http")

            if is_auth_enabled():
                ok, err = verify_request(auth_header)
                if not ok:
                    return Response(
                        content=f'{{"error":"{err}"}}',
                        status_code=401,
                        media_type="application/json",
                    )

            if RATE_LIMIT_ENABLED and rate_limiter is not None:
                allowed, retry_after = await rate_limiter.check(subject)
                if not allowed:
                    return Response(...)

            await session_mgr.handle_request(...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_server_streamable_http.py::test_streamable_http_sets_subject -x -v 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/server.py tests/test_server_streamable_http.py
git commit -m "feat(28): add subject resolution and rate limiting to streamable-http"
```

---

### Task 4: Metrics recording for streamable-http

**Files:**
- Modify: `kb_server/server.py`
- Confirm: `observability/metrics.py` already has `record_rate_limit_allowed` / `record_rate_limit_rejected`

- [ ] **Step 1: Verify metrics functions exist**

Run: `cd /home/admin/kb-rag-mcp && python -c "from observability.metrics import record_rate_limit_allowed, record_rate_limit_rejected; print('OK')"`
Expected: `OK`

- [ ] **Step 2: Confirm metrics are called in handle_mcp**

The rate limit records are already called in the `handle_mcp` code (step 3 of Task 3 used `record_rate_limit_rejected`). Verify the Prometheus counter label includes `streamable-http` by checking the existing code already had `record_rate_limit_allowed("streamable-http")`.

- [ ] **Step 3: Commit**

```bash
git add kb_server/server.py
git commit -m "feat(28): add Prometheus metrics for streamable-http transport"
```

---

### Task 5: Update documentation

**Files:**
- Modify: `docs/REFERENCE.md`
- Modify: `docs/INSTRUCTIONS.md`

- [ ] **Step 1: Add Streamable HTTP config to REFERENCE.md**

Add a new section after SSE transport section in `docs/REFERENCE.md`:

```markdown
### Streamable HTTP Transport

The server supports MCP Streamable HTTP transport for browser-based clients:

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | — | Set to `streamable-http` to enable |
| `MCP_HOST` | `127.0.0.1` | Bind address |
| `MCP_PORT` | `8765` | HTTP port |
| `MCP_ENDPOINT` | `/mcp` | MCP endpoint path |
| `MCP_JSON_RESPONSE` | `false` | JSON-only mode (no SSE streaming) |
| `MCP_STATELESS` | `false` | Disable session tracking |
| `MCP_SESSION_TIMEOUT` | `300` | Idle session timeout (seconds) |

**Client usage:**

POST JSON-RPC to `http://{host}:{port}/mcp` with:
- `Content-Type: application/json`
- `Mcp-Session-Id: <session_id>` (returned from first response)
- `Authorization: Bearer <api_key>` (if auth enabled)
```

- [ ] **Step 2: Add Streamable HTTP to INSTRUCTIONS.md quickstart**

Add a note to the "Running the Server" section in `docs/INSTRUCTIONS.md`:

```markdown
**Streamable HTTP mode** (for browser-based MCP clients):
```bash
MCP_TRANSPORT=streamable-http python -m kb_server.server
```
```

- [ ] **Step 3: Commit**

```bash
git add docs/REFERENCE.md docs/INSTRUCTIONS.md
git commit -m "docs(28): add Streamable HTTP transport documentation"
```
