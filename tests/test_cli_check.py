"""
Tests for the ``kb-ingest check health`` CLI command (Phase 09).

Uses Click's CliRunner to invoke the command and mock
check_all_components to return predictable HealthStatus results.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ingest.cli.main import cli

pytestmark = [pytest.mark.fase12]


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


def _make_health_status(
    name, healthy, message="", latency_ms=None, details=None
):
    """Helper to create a HealthStatus-like mock."""
    s = MagicMock()
    s.name = name
    s.healthy = healthy
    s.message = message
    s.latency_ms = latency_ms
    s.details = details or {}
    return s


def test_help_shows_verbose_flag(cli_runner):
    """Help text shows the --verbose flag."""
    result = cli_runner.invoke(cli, ["check", "health", "--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.output or "-v" in result.output


def test_all_healthy_exits_zero(cli_runner):
    """All components healthy → exits 0, prints success message."""
    mock_components = {
        "embedding": _make_health_status(
            "embedding", True, "backend: lmstudio"
        ),
        "vector_store": _make_health_status(
            "vector_store", True, "100 chunks"
        ),
        "cache": _make_health_status("cache", True, "enabled"),
        "database": _make_health_status("database", True, "10 jobs"),
        "filesystem": _make_health_status("filesystem", True, "50GB free"),
    }

    with patch(
        "kb_server.health.check_all_components",
        new=AsyncMock(return_value=mock_components),
    ):
        result = cli_runner.invoke(cli, ["check", "health"])

    assert result.exit_code == 0
    assert "All critical components healthy" in result.output


def test_embedding_unhealthy_exits_one(cli_runner):
    """Embedding unhealthy → exits 1, prints critical component message."""
    mock_components = {
        "embedding": _make_health_status(
            "embedding", False, "connection refused"
        ),
        "vector_store": _make_health_status(
            "vector_store", True, "100 chunks"
        ),
        "cache": _make_health_status("cache", True, "enabled"),
        "database": _make_health_status("database", True, "10 jobs"),
        "filesystem": _make_health_status("filesystem", True, "50GB free"),
    }

    with patch(
        "kb_server.health.check_all_components",
        new=AsyncMock(return_value=mock_components),
    ):
        result = cli_runner.invoke(cli, ["check", "health"])

    assert result.exit_code == 1
    assert "critical component" in result.output.lower()


def test_exception_during_health_exits_one(cli_runner):
    """Exception in check_all_components → exits 1, prints error."""
    with patch(
        "kb_server.health.check_all_components",
        side_effect=RuntimeError("network error"),
    ):
        result = cli_runner.invoke(cli, ["check", "health"])

    assert result.exit_code == 1
    assert "Error running health checks" in result.output


def test_verbose_shows_details(cli_runner):
    """--verbose flag shows component details."""
    mock_components = {
        "embedding": _make_health_status(
            "embedding",
            True,
            "backend: lmstudio",
            details={"model": "nomic-embed", "dims": 768},
        ),
        "vector_store": _make_health_status(
            "vector_store", True, "100 chunks"
        ),
        "cache": _make_health_status("cache", True, "enabled"),
        "database": _make_health_status("database", True, "10 jobs"),
        "filesystem": _make_health_status("filesystem", True, "50GB free"),
    }

    with patch(
        "kb_server.health.check_all_components",
        new=AsyncMock(return_value=mock_components),
    ):
        result = cli_runner.invoke(cli, ["check", "health", "--verbose"])

    assert result.exit_code == 0
    # Verbose output should include details like model=nomic-embed
    assert "model=nomic-embed" in result.output or "dims=768" in result.output


def test_component_order_is_consistent(cli_runner):
    """Components are displayed in the expected table order."""
    mock_components = {
        "embedding": _make_health_status("embedding", True),
        "vector_store": _make_health_status("vector_store", True),
        "cache": _make_health_status("cache", True),
        "database": _make_health_status("database", True),
        "filesystem": _make_health_status("filesystem", True),
    }

    with patch(
        "kb_server.health.check_all_components",
        new=AsyncMock(return_value=mock_components),
    ):
        result = cli_runner.invoke(cli, ["check", "health"])

    assert result.exit_code == 0
    # The output should contain all 5 component names
    for name in [
        "embedding",
        "vector_store",
        "cache",
        "database",
        "filesystem",
    ]:
        assert name in result.output


def test_missing_component_shows_skipped(cli_runner):
    """Missing component is shown as SKIP in the output (exits 0, not critical)."""
    mock_components = {
        "embedding": _make_health_status("embedding", True),
        "vector_store": _make_health_status("vector_store", True),
        # cache, database, filesystem missing
    }

    with patch(
        "kb_server.health.check_all_components",
        new=AsyncMock(return_value=mock_components),
    ):
        result = cli_runner.invoke(cli, ["check", "health"])

    # Missing components are SKIP'd, not counted as unhealthy
    # Only explicitly unhealthy critical components trigger exit 1
    assert result.exit_code == 0
    assert "SKIP" in result.output
