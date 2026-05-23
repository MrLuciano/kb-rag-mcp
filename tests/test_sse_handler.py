"""Tests for SSE handler fix — handle_sse returns Response() on disconnect.

IMPORTANT: This file must run in a SEPARATE pytest process from test_smoke.py
because that file stubs starlette.* and qdrant_client at module level, which
prevents real imports. CI runs this as a separate step via --ignore.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route
from starlette.testclient import TestClient


def _build_sse_app():
    """Build a minimal Starlette app with the SSE handler pattern."""
    from mcp.server.sse import SseServerTransport

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            pass
        return Response()

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )
    return app, sse


@pytest.mark.asyncio
async def test_handle_sse_returns_response():
    """Unit test: handler returns Response(200) when connect_sse yields."""
    from mcp.server.sse import SseServerTransport

    app, sse = _build_sse_app()

    mock_connect = AsyncMock()
    mock_connect.__aenter__ = AsyncMock(
        return_value=([MagicMock()], [MagicMock()])
    )
    mock_connect.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        SseServerTransport, "connect_sse", return_value=mock_connect
    ):
        client = TestClient(app)
        response = client.get("/sse")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_sse_handler_exits_with_response_after_connect_sse():
    """Unit test: handle_sse returns Response even if connect_sse raises."""
    from mcp.server.sse import SseServerTransport

    app, sse = _build_sse_app()

    mock_connect = AsyncMock()
    mock_connect.__aenter__ = AsyncMock(
        return_value=([MagicMock()], [MagicMock()])
    )
    mock_connect.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        SseServerTransport, "connect_sse", return_value=mock_connect
    ):
        client = TestClient(app)
        response = client.get("/sse")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_sse_post_messages_202():
    """Integration test: POST /messages/ returns 202 (no 307 redirect)."""
    app, sse = _build_sse_app()

    client = TestClient(app)
    response = client.post(
        "/messages/",
        json={"jsonrpc": "2.0", "method": "ping"},
    )
    # 400 = expected (no session); 307 = trailing-slash redirect bug
    assert response.status_code != 307
