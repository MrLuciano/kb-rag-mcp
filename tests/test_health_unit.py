"""
Unit tests for kb_server/health.py — targeting uncovered lines.

Covers:
- HealthStatus.to_dict (lines 55-65)
- check_embedding_service: ok, non-ok, exception (lines 68-116)
- check_vector_store: success, exception (lines 119-165)
- check_cache: success, disabled, exception (lines 168-217)
- check_database: success, exception (lines 220-261)
- check_filesystem: success, low disk, exception (lines 264-328)
- check_all_components: normal and exception-from-gather (lines 331-356)
- is_system_healthy: all healthy, missing component, unhealthy component (lines 359-381)
- get_health_summary: healthy and degraded (lines 384-400)
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from kb_server.health import (
    HealthStatus,
    check_all_components,
    check_cache,
    check_database,
    check_embedding_service,
    check_filesystem,
    check_vector_store,
    get_health_summary,
    is_system_healthy,
)


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------


def test_health_status_to_dict_healthy():
    """to_dict includes healthy/message; latency and details when set."""
    s = HealthStatus(
        name="embedding",
        healthy=True,
        message="all good",
        latency_ms=12.5,
        details={"backend": "lmstudio"},
    )
    d = s.to_dict()
    assert d["healthy"] is True
    assert d["message"] == "all good"
    assert d["latency_ms"] == 12.5
    assert d["details"]["backend"] == "lmstudio"


def test_health_status_to_dict_no_latency_no_details():
    """to_dict omits latency_ms and details when not set."""
    s = HealthStatus(name="cache", healthy=False, message="down")
    d = s.to_dict()
    assert "latency_ms" not in d
    assert "details" not in d
    assert d["healthy"] is False


def test_health_status_defaults():
    """HealthStatus defaults: empty message, no latency, empty details."""
    s = HealthStatus(name="db", healthy=True)
    assert s.message == ""
    assert s.latency_ms is None
    assert s.details == {}


# ---------------------------------------------------------------------------
# check_embedding_service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_embedding_service_ok():
    """When health_check returns status=ok, returns healthy HealthStatus."""
    mock_result = {
        "status": "ok",
        "backend": "lmstudio",
        "model": "nomic-embed",
        "dims": 768,
    }
    with patch("kb_server.embed_client.health_check", new=AsyncMock(return_value=mock_result)):
        result = await check_embedding_service()

    assert result.name == "embedding"
    assert result.healthy is True
    assert "lmstudio" in result.message
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_check_embedding_service_non_ok_status():
    """When health_check returns non-ok status, returns unhealthy HealthStatus."""
    mock_result = {"status": "error", "error": "connection refused"}
    with patch("kb_server.embed_client.health_check", new=AsyncMock(return_value=mock_result)):
        result = await check_embedding_service()

    assert result.name == "embedding"
    assert result.healthy is False
    assert "connection refused" in result.message


@pytest.mark.asyncio
async def test_check_embedding_service_exception():
    """When health_check raises, returns unhealthy HealthStatus with error message."""
    with patch("kb_server.embed_client.health_check", new=AsyncMock(side_effect=ConnectionError("no host"))):
        result = await check_embedding_service()

    assert result.name == "embedding"
    assert result.healthy is False
    assert "no host" in result.message


# ---------------------------------------------------------------------------
# check_vector_store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_vector_store_success():
    """When VectorStore connects and returns stats, returns healthy status."""
    mock_store = AsyncMock()
    mock_store.collection = "kb_docs"
    mock_store.get_stats.return_value = {
        "total_chunks": 1000,
        "total_documents": 50,
    }

    with patch("kb_server.vector_store.VectorStore", return_value=mock_store):
        result = await check_vector_store()

    assert result.name == "vector_store"
    assert result.healthy is True
    assert "1000" in result.message
    assert result.details["collection"] == "kb_docs"


@pytest.mark.asyncio
async def test_check_vector_store_exception():
    """When VectorStore.connect raises, returns unhealthy status."""
    mock_store = AsyncMock()
    mock_store.connect.side_effect = ConnectionRefusedError("qdrant down")

    with patch("kb_server.vector_store.VectorStore", return_value=mock_store):
        result = await check_vector_store()

    assert result.name == "vector_store"
    assert result.healthy is False
    assert "qdrant down" in result.message


# ---------------------------------------------------------------------------
# check_cache
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_cache_success():
    """When get_cache_stats returns active backend, returns healthy status."""
    mock_stats = {
        "status": "active",
        "backend": "lru",
        "entries": 100,
        "size_mb": 2.5,
        "hit_rate": 0.85,
    }
    with patch("kb_server.embed_client.get_cache_stats", return_value=mock_stats):
        result = await check_cache()

    assert result.name == "cache"
    assert result.healthy is True
    assert "lru" in result.message
    assert result.details["entries"] == 100


@pytest.mark.asyncio
async def test_check_cache_disabled():
    """When cache is disabled, returns healthy status with 'disabled' message."""
    mock_stats = {"status": "disabled"}
    with patch("kb_server.embed_client.get_cache_stats", return_value=mock_stats):
        result = await check_cache()

    assert result.name == "cache"
    assert result.healthy is True
    assert "disabled" in result.message.lower()


@pytest.mark.asyncio
async def test_check_cache_exception():
    """When get_cache_stats raises, returns unhealthy status."""
    with patch("kb_server.embed_client.get_cache_stats", side_effect=RuntimeError("redis down")):
        result = await check_cache()

    assert result.name == "cache"
    assert result.healthy is False
    assert "redis down" in result.message


# ---------------------------------------------------------------------------
# check_database
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_database_success():
    """When MetadataStore returns stats, returns healthy status."""
    mock_store = MagicMock()
    mock_store.get_stats.return_value = {
        "total_jobs": 10,
        "active_jobs": 2,
        "total_files": 100,
    }

    with patch("ingest.core.metadata.MetadataStore", return_value=mock_store):
        result = await check_database()

    assert result.name == "database"
    assert result.healthy is True
    assert "10" in result.message
    assert result.details["active_jobs"] == 2


@pytest.mark.asyncio
async def test_check_database_exception():
    """When MetadataStore raises, returns unhealthy status."""
    with patch("ingest.core.metadata.MetadataStore", side_effect=Exception("sqlite error")):
        result = await check_database()

    assert result.name == "database"
    assert result.healthy is False
    assert "sqlite error" in result.message


# ---------------------------------------------------------------------------
# check_filesystem
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_filesystem_success(tmp_path):
    """Filesystem with plenty of free space returns healthy."""
    import shutil as shutil_mod

    # 100GB total, 50GB free = 50% free
    mock_usage = MagicMock()
    mock_usage.free = 50 * (1024 ** 3)
    mock_usage.total = 100 * (1024 ** 3)

    with patch("kb_server.health.Path") as MockPath:
        mock_data_dir = MagicMock()
        MockPath.return_value = mock_data_dir
        mock_test_file = MagicMock()
        mock_data_dir.__truediv__ = MagicMock(return_value=mock_test_file)

        with patch("shutil.disk_usage", return_value=mock_usage):
            result = await check_filesystem()

    assert result.name == "filesystem"
    assert result.healthy is True
    assert result.details["percent_free"] > 10


@pytest.mark.asyncio
async def test_check_filesystem_low_disk(tmp_path):
    """Filesystem with <10% free returns unhealthy."""
    import shutil as shutil_mod

    mock_usage = MagicMock()
    mock_usage.free = 5 * (1024 ** 3)   # 5GB free
    mock_usage.total = 100 * (1024 ** 3)  # 100GB total = 5% free

    with patch("kb_server.health.Path") as MockPath:
        mock_data_dir = MagicMock()
        MockPath.return_value = mock_data_dir
        mock_test_file = MagicMock()
        mock_data_dir.__truediv__ = MagicMock(return_value=mock_test_file)

        with patch("shutil.disk_usage", return_value=mock_usage):
            result = await check_filesystem()

    assert result.name == "filesystem"
    assert result.healthy is False
    assert "Low disk" in result.message


@pytest.mark.asyncio
async def test_check_filesystem_exception():
    """When filesystem check raises, returns unhealthy status."""
    with patch("kb_server.health.Path", side_effect=OSError("permission denied")):
        result = await check_filesystem()

    assert result.name == "filesystem"
    assert result.healthy is False
    assert "permission denied" in result.message


# ---------------------------------------------------------------------------
# check_all_components
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_all_components_all_healthy():
    """check_all_components returns all 6 components when all succeed."""
    mock_statuses = [
        HealthStatus("embedding", True, "ok"),
        HealthStatus("vector_store", True, "ok"),
        HealthStatus("cache", True, "ok"),
        HealthStatus("database", True, "ok"),
        HealthStatus("filesystem", True, "ok"),
        HealthStatus("grafana", True, "ok"),
    ]

    with patch("kb_server.health.check_embedding_service", new=AsyncMock(return_value=mock_statuses[0])):
        with patch("kb_server.health.check_vector_store", new=AsyncMock(return_value=mock_statuses[1])):
            with patch("kb_server.health.check_cache", new=AsyncMock(return_value=mock_statuses[2])):
                with patch("kb_server.health.check_database", new=AsyncMock(return_value=mock_statuses[3])):
                    with patch("kb_server.health.check_filesystem", new=AsyncMock(return_value=mock_statuses[4])):
                        with patch("kb_server.health.check_grafana", new=AsyncMock(return_value=mock_statuses[5])):
                            result = await check_all_components()

    assert set(result.keys()) == {
        "embedding", "vector_store", "cache", "database",
        "filesystem", "grafana",
    }
    assert all(v.healthy for v in result.values())


@pytest.mark.asyncio
async def test_check_all_components_exception_from_check_is_skipped():
    """If a component check raises an exception, it's skipped (not in result)."""
    healthy = HealthStatus("embedding", True, "ok")

    async def raise_exc():
        raise RuntimeError("network error")

    with patch("kb_server.health.check_embedding_service", new=AsyncMock(return_value=healthy)):
        with patch("kb_server.health.check_vector_store", new=AsyncMock(side_effect=RuntimeError("qdrant down"))):
            with patch("kb_server.health.check_cache", new=AsyncMock(return_value=HealthStatus("cache", True))):
                with patch("kb_server.health.check_database", new=AsyncMock(return_value=HealthStatus("database", True))):
                    with patch("kb_server.health.check_filesystem", new=AsyncMock(return_value=HealthStatus("filesystem", True))):
                        result = await check_all_components()

    # vector_store raised — it's absent from result
    assert "vector_store" not in result
    assert "embedding" in result


# ---------------------------------------------------------------------------
# is_system_healthy
# ---------------------------------------------------------------------------


def test_is_system_healthy_all_healthy():
    """All critical components healthy → True."""
    components = {
        "embedding": HealthStatus("embedding", True),
        "vector_store": HealthStatus("vector_store", True),
        "database": HealthStatus("database", True),
        "cache": HealthStatus("cache", False),  # non-critical
    }
    assert is_system_healthy(components) is True


def test_is_system_healthy_missing_critical():
    """Missing critical component → False."""
    components = {
        "embedding": HealthStatus("embedding", True),
        "vector_store": HealthStatus("vector_store", True),
        # "database" missing
    }
    assert is_system_healthy(components) is False


def test_is_system_healthy_critical_unhealthy():
    """Unhealthy critical component → False."""
    components = {
        "embedding": HealthStatus("embedding", False, "down"),
        "vector_store": HealthStatus("vector_store", True),
        "database": HealthStatus("database", True),
    }
    assert is_system_healthy(components) is False


def test_is_system_healthy_empty():
    """Empty components dict → False (missing all critical)."""
    assert is_system_healthy({}) is False


# ---------------------------------------------------------------------------
# get_health_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_health_summary_healthy():
    """get_health_summary returns status=ok when all critical components healthy."""
    mock_components = {
        "embedding": HealthStatus("embedding", True, "ok", latency_ms=5.0),
        "vector_store": HealthStatus("vector_store", True, "ok", latency_ms=10.0),
        "database": HealthStatus("database", True, "ok", latency_ms=2.0),
        "cache": HealthStatus("cache", True, "ok"),
        "filesystem": HealthStatus("filesystem", True, "ok"),
    }

    with patch("kb_server.health.check_all_components", new=AsyncMock(return_value=mock_components)):
        result = await get_health_summary()

    assert result["status"] == "ok"
    assert result["healthy"] is True
    assert "timestamp" in result
    assert "components" in result
    assert "embedding" in result["components"]


@pytest.mark.asyncio
async def test_get_health_summary_degraded():
    """get_health_summary returns status=degraded when a critical component is down."""
    mock_components = {
        "embedding": HealthStatus("embedding", False, "down"),
        "vector_store": HealthStatus("vector_store", True, "ok"),
        "database": HealthStatus("database", True, "ok"),
    }

    with patch("kb_server.health.check_all_components", new=AsyncMock(return_value=mock_components)):
        result = await get_health_summary()

    assert result["status"] == "degraded"
    assert result["healthy"] is False


@pytest.mark.asyncio
async def test_get_health_summary_includes_component_dicts():
    """Components in summary are serialized via to_dict()."""
    mock_components = {
        "embedding": HealthStatus(
            "embedding", True, "backend: lmstudio",
            latency_ms=7.3, details={"dims": 768}
        ),
        "vector_store": HealthStatus("vector_store", True),
        "database": HealthStatus("database", True),
    }

    with patch("kb_server.health.check_all_components", new=AsyncMock(return_value=mock_components)):
        result = await get_health_summary()

    emb = result["components"]["embedding"]
    assert emb["healthy"] is True
    assert emb["latency_ms"] == 7.3
    assert emb["details"]["dims"] == 768
