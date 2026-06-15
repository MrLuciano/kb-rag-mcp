import os
from unittest.mock import AsyncMock, patch

import pytest

from kb_server.health import check_grafana


@pytest.mark.asyncio
async def test_check_grafana_not_configured():
    with patch.dict(os.environ, {}, clear=True):
        result = await check_grafana()
    assert result.healthy is True
    assert "Not configured" in result.message


@pytest.mark.asyncio
async def test_check_grafana_success():
    with patch.dict(os.environ, {"GRAFANA_URL": "http://grafana:3000"}):
        with patch(
            "kb_server.health.asyncio.open_connection", new_callable=AsyncMock
        ) as mock_conn:
            mock_writer = AsyncMock()
            mock_reader = AsyncMock()
            mock_conn.return_value = (mock_reader, mock_writer)

            result = await check_grafana()

    assert result.healthy is True
    assert "Connected" in result.message


@pytest.mark.asyncio
async def test_check_grafana_failure():
    with patch.dict(os.environ, {"GRAFANA_URL": "http://grafana:3000"}):
        with patch(
            "kb_server.health.asyncio.open_connection",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            result = await check_grafana()

    assert result.healthy is False
    assert "Connection refused" in result.message
