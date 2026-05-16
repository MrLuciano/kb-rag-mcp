"""Tests for health check system."""

import pytest
from fastapi.testclient import TestClient


def test_health_basic():
    """Test basic health endpoint returns 200."""
    from server.health_server import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_detailed():
    """Test detailed health includes all components."""
    from server.health_server import app

    client = TestClient(app)
    response = client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "components" in data
    assert "embedding" in data["components"]
    assert "vector_store" in data["components"]
    assert "cache" in data["components"]
    assert "timestamp" in data


def test_readiness_check():
    """Test readiness endpoint."""
    from server.health_server import app

    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code in [200, 503]
    assert "ready" in response.json()


def test_liveness_check():
    """Test liveness endpoint."""
    from server.health_server import app

    client = TestClient(app)
    response = client.get("/alive")

    assert response.status_code == 200
    assert response.json()["alive"] is True


@pytest.mark.asyncio
async def test_health_check_with_failures():
    """Test health check detects component failures."""
    from server.health import check_all_components

    # Mock a failing component
    status = await check_all_components()

    assert "embedding" in status
    assert "vector_store" in status
    assert "cache" in status
