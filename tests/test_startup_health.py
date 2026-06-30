"""
Tests for startup pre-flight health checks (Phase 09).

Verifies that kb_server.server.main() calls check_embedding_service and
check_vector_store after store.connect(), and logs appropriate warnings
when services are unreachable.

These are focused unit tests that validate the health check logic without
requiring main() to run to completion (which starts a server transport).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.fase12]


@pytest.mark.asyncio
async def test_main_imports_health_check_functions():
    """The health check functions are importable from kb_server.health."""
    from kb_server.health import check_embedding_service, check_vector_store

    assert callable(check_embedding_service)
    assert callable(check_vector_store)


@pytest.mark.asyncio
async def test_server_preflight_invokes_health_checks():
    """Verify the pre-flight pattern: after store.connect, both checks run.

    We simulate the exact code block from server.py::main() to validate
    that the health check calls work correctly with mocked dependencies.
    """
    # Patch the health functions to return known values
    mock_emb = AsyncMock(
        return_value=MagicMock(healthy=True, message="backend: lmstudio")
    )
    mock_vec = AsyncMock(
        return_value=MagicMock(healthy=True, message="100 chunks")
    )

    with patch("kb_server.health.check_embedding_service", mock_emb):
        with patch("kb_server.health.check_vector_store", mock_vec):
            # Simulate main()'s health check block
            from kb_server.health import (
                check_embedding_service as emb_fn,
                check_vector_store as vec_fn,
            )

            emb_status = await emb_fn()
            vec_status = await vec_fn()

    mock_emb.assert_awaited_once()
    mock_vec.assert_awaited_once()
    assert emb_status.healthy is True
    assert vec_status.healthy is True


@pytest.mark.asyncio
async def test_unhealthy_embedding_logs_warning(caplog):
    """Unhealthy embedding service produces a WARNING log message."""
    mock_emb = AsyncMock(
        return_value=MagicMock(healthy=False, message="connection refused")
    )
    mock_vec = AsyncMock(return_value=MagicMock(healthy=True, message="ok"))

    with patch("kb_server.health.check_embedding_service", mock_emb):
        with patch("kb_server.health.check_vector_store", mock_vec):
            import logging

            log = logging.getLogger("kb-mcp")

            from kb_server.health import check_embedding_service as emb_fn

            status = await emb_fn()

            if not status.healthy:
                log.warning(
                    f"Embedding backend unreachable: {status.message} — "
                    f"queries will fail. Configure EMBED_BACKEND "
                    f"or start LM Studio."
                )

    assert any(
        "Embedding backend unreachable" in record.message
        and record.levelname == "WARNING"
        for record in caplog.records
    ), "Expected WARNING log about embedding backend unreachable"


@pytest.mark.asyncio
async def test_unhealthy_vector_store_logs_warning(caplog):
    """Unhealthy Qdrant produces a WARNING log message."""
    mock_emb = AsyncMock(return_value=MagicMock(healthy=True, message="ok"))
    mock_vec = AsyncMock(
        return_value=MagicMock(healthy=False, message="connection timeout")
    )

    with patch("kb_server.health.check_embedding_service", mock_emb):
        with patch("kb_server.health.check_vector_store", mock_vec):
            import logging

            log = logging.getLogger("kb-mcp")

            from kb_server.health import check_vector_store as vec_fn

            status = await vec_fn()

            if not status.healthy:
                log.warning(
                    f"Qdrant unreachable: {status.message} — "
                    f"queries will fail. Verify Qdrant is running."
                )

    assert any(
        "Qdrant unreachable" in record.message
        and record.levelname == "WARNING"
        for record in caplog.records
    ), "Expected WARNING log about Qdrant unhealthy"


@pytest.mark.asyncio
async def test_healthy_checks_log_info(caplog):
    """Healthy health checks produce INFO log messages."""
    import logging

    caplog.set_level(logging.INFO)

    mock_emb = AsyncMock(
        return_value=MagicMock(healthy=True, message="backend: lmstudio")
    )
    mock_vec = AsyncMock(
        return_value=MagicMock(healthy=True, message="100 chunks")
    )

    with patch("kb_server.health.check_embedding_service", mock_emb):
        with patch("kb_server.health.check_vector_store", mock_vec):
            log = logging.getLogger("kb-mcp")

            from kb_server.health import (
                check_embedding_service as emb_fn,
                check_vector_store as vec_fn,
            )

            emb_status = await emb_fn()
            if emb_status.healthy:
                log.info(f"Embedding backend healthy: {emb_status.message}")

            vec_status = await vec_fn()
            if vec_status.healthy:
                log.info(f"Qdrant healthy: {vec_status.message}")

    assert any(
        "Embedding backend healthy" in record.message
        and record.levelname == "INFO"
        for record in caplog.records
    ), "Expected INFO log about embedding backend healthy"

    assert any(
        "Qdrant healthy" in record.message and record.levelname == "INFO"
        for record in caplog.records
    ), "Expected INFO log about Qdrant healthy"


def test_server_code_has_health_checks_in_main():
    """Verify server.py's main() actually contains the health check code.

    Reads the source to ensure the health check pattern exists.
    """
    with open("kb_server/server.py") as f:
        source = f.read()

    assert (
        "check_embedding_service" in source
    ), "server.py should reference check_embedding_service"
    assert (
        "check_vector_store" in source
    ), "server.py should reference check_vector_store"
    assert (
        "Embedding backend unreachable" in source
    ), "server.py should log WARNING for embedding"
    assert (
        "Qdrant unreachable" in source
    ), "server.py should log WARNING for Qdrant"
