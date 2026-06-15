"""Tests for streamable HTTP transport in the MCP server."""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_streamable_http_transport_env():
    """Server main() accepts TRANSPORT=streamable-http without error."""
    os.environ["MCP_PORT"] = "18765"
    os.environ["MCP_HOST"] = "127.0.0.1"
    os.environ["MCP_ENDPOINT"] = "/mcp-test"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    import kb_server.server

    # Override module-level TRANSPORT constant (bypasses .env override in bootstrap_env)
    kb_server.server.TRANSPORT = "streamable-http"
    from kb_server.server import main

    mock_mgr_instance = MagicMock()
    mock_mgr_instance.run.return_value.__aenter__ = AsyncMock()
    mock_mgr_instance.run.return_value.__aexit__ = AsyncMock()
    mock_mgr_cls = MagicMock(return_value=mock_mgr_instance)

    with patch("kb_server.server.store.connect", new_callable=AsyncMock), \
         patch("kb_server.health.check_embedding_service", new_callable=AsyncMock) as mock_emb, \
         patch("kb_server.health.check_vector_store", new_callable=AsyncMock) as mock_vec, \
         patch("kb_server.server.CollectionManager") as mock_cm_cls, \
         patch("kb_server.server.CollectionRouter"), \
         patch("kb_server.server.FilterTermsCache") as mock_ftc, \
         patch("mcp.server.streamable_http_manager.StreamableHTTPSessionManager", mock_mgr_cls), \
         patch("uvicorn.Server.serve", new_callable=AsyncMock) as mock_serve:
        mock_emb.return_value.healthy = True
        mock_vec.return_value.healthy = True
        mock_cm = AsyncMock()
        mock_cm_cls.return_value = mock_cm
        mock_ftc.return_value.reindex = AsyncMock()
        await main()
        assert mock_serve.called, "main() did not reach streamable-http branch"
        assert mock_mgr_cls.called, "StreamableHTTPSessionManager was not called"
        assert mock_mgr_cls.call_args[1]["app"] is not None
