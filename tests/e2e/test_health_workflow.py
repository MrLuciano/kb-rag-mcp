"""
E2E tests for health check system.

Tests health check functionality using the actual kb_server.health API.
"""

import os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import time


class TestHealthCheckComponents:
    """Test individual health check components."""

    @pytest.mark.asyncio
    async def test_embedding_health_check(self):
        """Test embedding service health check."""
        from kb_server.health import check_embedding_service, HealthStatus

        with patch("kb_server.embed_client.health_check") as mock_hc:
            mock_hc.return_value = {
                "status": "ok",
                "backend": "lmstudio-rest",
                "model": "test-model",
                "dims": 384,
            }
            result = await check_embedding_service()

        assert isinstance(result, HealthStatus)
        assert result.healthy is True
        assert result.name == "embedding"
        assert "lmstudio-rest" in result.message

    @pytest.mark.asyncio
    async def test_embedding_health_check_failure(self):
        """Test embedding health check with service failure."""
        from kb_server.health import check_embedding_service, HealthStatus

        with patch("kb_server.embed_client.health_check") as mock_hc:
            mock_hc.side_effect = Exception("Service unavailable")
            result = await check_embedding_service()

        assert isinstance(result, HealthStatus)
        assert result.healthy is False
        assert "Service unavailable" in result.message

    @pytest.mark.asyncio
    async def test_vector_store_health_check(self):
        """Test vector store health check."""
        from kb_server.health import check_vector_store, HealthStatus

        with patch("kb_server.vector_store.VectorStore") as mock_store_cls:
            mock_store = AsyncMock()
            mock_store.connect = AsyncMock()
            mock_store.get_stats = AsyncMock(return_value={"total_chunks": 100})
            mock_store.close = AsyncMock()
            mock_store_cls.return_value = mock_store

            result = await check_vector_store()

        assert isinstance(result, HealthStatus)
        assert result.healthy is True
        assert result.name == "vector_store"

    @pytest.mark.asyncio
    async def test_cache_health_check(self):
        """Test cache health check."""
        from kb_server.health import check_cache, HealthStatus

        with patch("kb_server.embed_client.get_cache_stats") as mock_stats:
            mock_stats.return_value = {
                "backend": "lru",
                "entries": 100,
                "size_mb": 1.0,
                "hit_rate": 0.8,
            }

            result = await check_cache()

        assert isinstance(result, HealthStatus)
        assert result.healthy is True
        assert result.name == "cache"
        assert result.details["hit_rate"] == 0.8

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check."""
        from kb_server.health import check_database, HealthStatus

        with patch("ingest.core.metadata.MetadataStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get_stats.return_value = {
                "total_jobs": 5,
                "active_jobs": 2,
                "total_files": 10,
            }
            mock_store_cls.return_value = mock_store

            result = await check_database()

        assert isinstance(result, HealthStatus)
        assert result.healthy is True
        assert result.name == "database"
        assert result.latency_ms is not None
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_filesystem_health_check(self):
        """Test filesystem health check."""
        from kb_server.health import check_filesystem, HealthStatus

        with patch("kb_server.health.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = type(
                "Usage", (), {"free": 100 * 1024**3, "total": 500 * 1024**3}
            )()

            result = await check_filesystem()

        assert isinstance(result, HealthStatus)
        assert result.healthy is True
        assert result.name == "filesystem"
        assert result.details["free_gb"] > 0
        assert result.details["total_gb"] > 0
        assert 0 <= result.details["percent_free"] <= 100


class TestHealthAggregation:
    """Test health check aggregation and overall status."""

    @pytest.mark.asyncio
    async def test_all_healthy(self):
        """Test when all components are healthy."""
        from kb_server.health import (
            check_all_components,
            is_system_healthy,
            HealthStatus,
        )

        with patch("kb_server.health.check_embedding_service") as mock_emb, \
                patch("kb_server.health.check_vector_store") as mock_vs, \
                patch("kb_server.health.check_cache") as mock_cache, \
                patch("kb_server.health.check_database") as mock_db, \
                patch("kb_server.health.check_filesystem") as mock_fs:

            mock_emb.return_value = HealthStatus(
                name="embedding", healthy=True, latency_ms=10.0
            )
            mock_vs.return_value = HealthStatus(
                name="vector_store", healthy=True, latency_ms=5.0
            )
            mock_cache.return_value = HealthStatus(
                name="cache", healthy=True, latency_ms=1.0
            )
            mock_db.return_value = HealthStatus(
                name="database", healthy=True, latency_ms=2.0
            )
            mock_fs.return_value = HealthStatus(
                name="filesystem", healthy=True, latency_ms=1.0
            )

            components = await check_all_components()
            healthy = is_system_healthy(components)

        assert healthy is True
        assert len(components) == 5
        assert all(c.healthy for c in components.values())

    @pytest.mark.asyncio
    async def test_critical_component_unhealthy(self):
        """Test when critical component is unhealthy."""
        from kb_server.health import (
            check_all_components,
            is_system_healthy,
            HealthStatus,
        )

        with patch("kb_server.health.check_embedding_service") as mock_emb, \
                patch("kb_server.health.check_vector_store") as mock_vs, \
                patch("kb_server.health.check_cache") as mock_cache, \
                patch("kb_server.health.check_database") as mock_db, \
                patch("kb_server.health.check_filesystem") as mock_fs:

            mock_emb.return_value = HealthStatus(
                name="embedding", healthy=False,
                message="Connection refused"
            )
            mock_vs.return_value = HealthStatus(
                name="vector_store", healthy=True, latency_ms=5.0
            )
            mock_cache.return_value = HealthStatus(
                name="cache", healthy=True, latency_ms=1.0
            )
            mock_db.return_value = HealthStatus(
                name="database", healthy=True, latency_ms=2.0
            )
            mock_fs.return_value = HealthStatus(
                name="filesystem", healthy=True, latency_ms=1.0
            )

            components = await check_all_components()
            healthy = is_system_healthy(components)

        assert healthy is False
        assert components["embedding"].healthy is False

    @pytest.mark.asyncio
    async def test_non_critical_component_unhealthy(self):
        """Test when non-critical component is unhealthy."""
        from kb_server.health import (
            check_all_components,
            is_system_healthy,
            HealthStatus,
        )

        with patch("kb_server.health.check_embedding_service") as mock_emb, \
                patch("kb_server.health.check_vector_store") as mock_vs, \
                patch("kb_server.health.check_cache") as mock_cache, \
                patch("kb_server.health.check_database") as mock_db, \
                patch("kb_server.health.check_filesystem") as mock_fs:

            mock_emb.return_value = HealthStatus(
                name="embedding", healthy=True, latency_ms=10.0
            )
            mock_vs.return_value = HealthStatus(
                name="vector_store", healthy=True, latency_ms=5.0
            )
            mock_cache.return_value = HealthStatus(
                name="cache", healthy=False,
                message="Redis connection failed"
            )
            mock_db.return_value = HealthStatus(
                name="database", healthy=True, latency_ms=2.0
            )
            mock_fs.return_value = HealthStatus(
                name="filesystem", healthy=True, latency_ms=1.0
            )

            components = await check_all_components()
            healthy = is_system_healthy(components)

        # Cache is non-critical — system still healthy
        assert healthy is True
        assert components["cache"].healthy is False


class TestHealthHTTPEndpoints:
    """Test health check HTTP endpoints."""

    def test_health_endpoint_basic(self):
        """Test basic /health endpoint."""
        from kb_server.health_server import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert data["service"] == "kb-rag"

    def test_health_endpoint_detailed(self):
        """Test detailed /health/detailed endpoint."""
        from kb_server.health_server import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "healthy" in data
        assert "timestamp" in data
        assert "components" in data

        # Check all expected components
        expected_components = [
            "embedding",
            "vector_store",
            "cache",
            "database",
            "filesystem"
        ]
        for component in expected_components:
            assert component in data["components"]

    def test_ready_endpoint(self):
        """Test /ready endpoint for Kubernetes readiness."""
        from kb_server.health_server import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/ready")

        # Should return 200 if ready, 503 if not
        assert response.status_code in [200, 503]
        data = response.json()
        assert "ready" in data

    def test_alive_endpoint(self):
        """Test /alive endpoint for Kubernetes liveness."""
        from kb_server.health_server import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/alive")

        # Should always return 200 if server is responding
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


class TestHealthCheckLatency:
    """Test health check latency measurements via HealthStatus."""

    @pytest.mark.asyncio
    async def test_latency_recorded(self):
        """Test that latency is recorded in HealthStatus."""
        from kb_server.health import HealthStatus

        status = HealthStatus(
            name="test",
            healthy=True,
            latency_ms=42.5,
        )
        data = status.to_dict()
        assert data["latency_ms"] == 42.5

    @pytest.mark.asyncio
    async def test_health_status_without_latency(self):
        """Test HealthStatus without latency."""
        from kb_server.health import HealthStatus

        status = HealthStatus(
            name="test",
            healthy=False,
            message="Something failed",
        )
        data = status.to_dict()
        assert "latency_ms" not in data
        assert data["message"] == "Something failed"


class TestHealthStatusCaching:
    """Test health status object behavior (no external cache in current API)."""

    def test_health_status_to_dict(self):
        """Test HealthStatus serializes correctly."""
        from kb_server.health import HealthStatus

        status = HealthStatus(
            name="embedding",
            healthy=True,
            message="ok",
            latency_ms=12.34,
            details={"backend": "lmstudio"},
        )
        d = status.to_dict()
        assert d["healthy"] is True
        assert d["message"] == "ok"
        assert d["latency_ms"] == 12.34
        assert d["details"]["backend"] == "lmstudio"


@pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION_TESTS") == "1",
    reason="Integration tests disabled"
)
class TestRealHealthChecks:
    """
    Integration tests with real services.

    Run with: pytest tests/e2e/test_health_workflow.py --run-integration
    """

    @pytest.mark.asyncio
    async def test_real_embedding_health(self):
        """Test with real embedding service."""
        pytest.skip("Requires LM Studio/Ollama running")

    @pytest.mark.asyncio
    async def test_real_qdrant_health(self):
        """Test with real Qdrant instance."""
        pytest.skip("Requires Qdrant running")
