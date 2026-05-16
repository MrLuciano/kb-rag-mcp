"""
E2E tests for health check system.

Tests complete health check functionality including:
- Component health checks
- HTTP endpoints
- Health aggregation
- Failure detection
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
        from server.health import EmbeddingHealthCheck
        
        # Mock embedding client
        mock_client = AsyncMock()
        mock_client.embed_text.return_value = [0.1] * 384
        
        checker = EmbeddingHealthCheck(mock_client)
        result = await checker.check()
        
        assert result["healthy"] is True
        assert "latency_ms" in result
        assert result["latency_ms"] > 0
        assert "details" in result
    
    @pytest.mark.asyncio
    async def test_embedding_health_check_failure(self):
        """Test embedding health check with service failure."""
        from server.health import EmbeddingHealthCheck
        
        # Mock failing embedding client
        mock_client = AsyncMock()
        mock_client.embed_text.side_effect = Exception("Service unavailable")
        
        checker = EmbeddingHealthCheck(mock_client)
        result = await checker.check()
        
        assert result["healthy"] is False
        assert "error" in result
        assert "Service unavailable" in result["error"]
    
    @pytest.mark.asyncio
    async def test_vector_store_health_check(self):
        """Test vector store health check."""
        from server.health import VectorStoreHealthCheck
        
        # Mock Qdrant client
        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = [
            MagicMock(name="kb_docs")
        ]
        mock_client.get_collection.return_value.points_count = 1000
        
        checker = VectorStoreHealthCheck(mock_client, "kb_docs")
        result = await checker.check()
        
        assert result["healthy"] is True
        assert result["details"]["collection"] == "kb_docs"
        assert result["details"]["points_count"] == 1000
    
    @pytest.mark.asyncio
    async def test_cache_health_check(self):
        """Test cache health check."""
        from server.health import CacheHealthCheck
        
        # Mock cache
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {
            "entries": 100,
            "hits": 800,
            "misses": 200,
            "hit_rate": 0.8,
            "size_bytes": 1024000
        }
        
        checker = CacheHealthCheck(mock_cache)
        result = await checker.check()
        
        assert result["healthy"] is True
        assert result["details"]["hit_rate"] == 0.8
        assert result["details"]["entries"] == 100
    
    @pytest.mark.asyncio
    async def test_database_health_check(self, e2e_temp_db):
        """Test database health check."""
        from server.health import DatabaseHealthCheck
        
        checker = DatabaseHealthCheck(str(e2e_temp_db))
        result = await checker.check()
        
        assert result["healthy"] is True
        assert "latency_ms" in result
        assert "details" in result
    
    @pytest.mark.asyncio
    async def test_filesystem_health_check(self, tmp_path):
        """Test filesystem health check."""
        from server.health import FilesystemHealthCheck
        
        checker = FilesystemHealthCheck(str(tmp_path))
        result = await checker.check()
        
        assert result["healthy"] is True
        assert result["details"]["free_bytes"] > 0
        assert result["details"]["total_bytes"] > 0
        assert 0 <= result["details"]["free_percent"] <= 100


class TestHealthAggregation:
    """Test health check aggregation and overall status."""
    
    @pytest.mark.asyncio
    async def test_all_healthy(self):
        """Test when all components are healthy."""
        from server.health import HealthChecker
        
        # Mock all checkers as healthy
        mock_checkers = {
            "embedding": AsyncMock(
                return_value={"healthy": True, "latency_ms": 10.0}
            ),
            "vector_store": AsyncMock(
                return_value={"healthy": True, "latency_ms": 5.0}
            ),
            "cache": AsyncMock(
                return_value={"healthy": True, "latency_ms": 1.0}
            ),
            "database": AsyncMock(
                return_value={"healthy": True, "latency_ms": 2.0}
            ),
            "filesystem": AsyncMock(
                return_value={"healthy": True, "latency_ms": 1.0}
            ),
        }
        
        checker = HealthChecker()
        checker.checkers = mock_checkers
        
        result = await checker.check_all()
        
        assert result["status"] == "ok"
        assert result["healthy"] is True
        assert len(result["components"]) == 5
        assert all(
            c["healthy"] for c in result["components"].values()
        )
    
    @pytest.mark.asyncio
    async def test_critical_component_unhealthy(self):
        """Test when critical component is unhealthy."""
        from server.health import HealthChecker
        
        # Mock critical component as unhealthy
        mock_checkers = {
            "embedding": AsyncMock(
                return_value={
                    "healthy": False,
                    "error": "Connection refused"
                }
            ),
            "vector_store": AsyncMock(
                return_value={"healthy": True, "latency_ms": 5.0}
            ),
            "cache": AsyncMock(
                return_value={"healthy": True, "latency_ms": 1.0}
            ),
            "database": AsyncMock(
                return_value={"healthy": True, "latency_ms": 2.0}
            ),
            "filesystem": AsyncMock(
                return_value={"healthy": True, "latency_ms": 1.0}
            ),
        }
        
        checker = HealthChecker()
        checker.checkers = mock_checkers
        
        result = await checker.check_all()
        
        assert result["status"] == "degraded"
        assert result["healthy"] is False
        assert result["components"]["embedding"]["healthy"] is False
    
    @pytest.mark.asyncio
    async def test_non_critical_component_unhealthy(self):
        """Test when non-critical component is unhealthy."""
        from server.health import HealthChecker
        
        # Mock non-critical component (cache) as unhealthy
        mock_checkers = {
            "embedding": AsyncMock(
                return_value={"healthy": True, "latency_ms": 10.0}
            ),
            "vector_store": AsyncMock(
                return_value={"healthy": True, "latency_ms": 5.0}
            ),
            "cache": AsyncMock(
                return_value={
                    "healthy": False,
                    "error": "Redis connection failed"
                }
            ),
            "database": AsyncMock(
                return_value={"healthy": True, "latency_ms": 2.0}
            ),
            "filesystem": AsyncMock(
                return_value={"healthy": True, "latency_ms": 1.0}
            ),
        }
        
        checker = HealthChecker()
        checker.checkers = mock_checkers
        
        result = await checker.check_all()
        
        # System should still be healthy (cache is non-critical)
        assert result["status"] == "ok"
        assert result["healthy"] is True
        # But cache component shows as unhealthy
        assert result["components"]["cache"]["healthy"] is False


class TestHealthHTTPEndpoints:
    """Test health check HTTP endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_basic(self):
        """Test basic /health endpoint."""
        from server.health_server import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert data["service"] == "kb-rag"
    
    @pytest.mark.asyncio
    async def test_health_endpoint_detailed(self):
        """Test detailed /health/detailed endpoint."""
        from server.health_server import app
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
    
    @pytest.mark.asyncio
    async def test_ready_endpoint(self):
        """Test /ready endpoint for Kubernetes readiness."""
        from server.health_server import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/ready")
        
        # Should return 200 if ready, 503 if not
        assert response.status_code in [200, 503]
        data = response.json()
        assert "ready" in data
    
    @pytest.mark.asyncio
    async def test_alive_endpoint(self):
        """Test /alive endpoint for Kubernetes liveness."""
        from server.health_server import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/alive")
        
        # Should always return 200 if server is responding
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


class TestHealthCheckLatency:
    """Test health check latency measurements."""
    
    @pytest.mark.asyncio
    async def test_latency_measurement(self):
        """Test that latency is measured correctly."""
        from server.health import measure_latency
        
        async def slow_operation():
            await asyncio.sleep(0.1)  # 100ms
            return {"status": "ok"}
        
        start = time.time()
        result, latency_ms = await measure_latency(slow_operation)
        elapsed = time.time() - start
        
        assert result["status"] == "ok"
        assert 90 < latency_ms < 150  # ~100ms with tolerance
        assert abs(elapsed * 1000 - latency_ms) < 50  # Verify accuracy
    
    @pytest.mark.asyncio
    async def test_latency_on_error(self):
        """Test latency measurement when operation fails."""
        from server.health import measure_latency
        
        async def failing_operation():
            await asyncio.sleep(0.05)
            raise Exception("Operation failed")
        
        try:
            result, latency_ms = await measure_latency(failing_operation)
            # Should not reach here
            assert False, "Expected exception"
        except Exception as e:
            assert str(e) == "Operation failed"
            # Latency still measured even on failure


class TestHealthCheckCaching:
    """Test health check result caching."""
    
    @pytest.mark.asyncio
    async def test_health_check_caching(self):
        """Test that health checks are cached appropriately."""
        from server.health import CachedHealthChecker
        
        call_count = 0
        
        async def expensive_check():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return {"healthy": True}
        
        checker = CachedHealthChecker(
            check_func=expensive_check,
            cache_ttl=1.0  # 1 second cache
        )
        
        # First call - should execute
        result1 = await checker.check()
        assert call_count == 1
        
        # Second call immediately - should use cache
        result2 = await checker.check()
        assert call_count == 1  # Not incremented
        
        # Wait for cache to expire
        await asyncio.sleep(1.1)
        
        # Third call - should execute again
        result3 = await checker.check()
        assert call_count == 2


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
