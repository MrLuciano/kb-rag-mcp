"""
Tests for reclassification CLI commands.

Phase 16: Reclassification capability.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock, MagicMock

from ingest.cli.main import cli
from ingest.cli.reclassify import _parse_filter_expr, _show_aggregated_preview


def test_reclassify_command_exists():
    """RECLASSIFY-04: kb-ingest reclassify command is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reclassify", "--help"])
    assert result.exit_code == 0
    assert "reclassify" in result.output.lower()
    assert "update metadata" in result.output.lower()


def test_reclassify_run_requires_pattern_argument():
    """RECLASSIFY-04: reclassify run requires pattern argument."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reclassify", "run"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output or "PATTERN" in result.output


def test_reclassify_run_has_required_flags():
    """RECLASSIFY-04: reclassify run has all expected flags."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reclassify", "run", "--help"])
    assert result.exit_code == 0
    assert "--collection" in result.output
    assert "--filter" in result.output
    assert "--yes" in result.output
    assert "--allow-missing" in result.output
    assert "--include-custom" in result.output
    assert "--no-progress" in result.output


def test_verify_subcommand_exists():
    """RECLASSIFY-05: verify subcommand is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reclassify", "verify", "--help"])
    assert result.exit_code == 0
    assert "verify" in result.output.lower()
    assert "metadata" in result.output.lower()


def test_sessions_subcommand_exists():
    """RECLASSIFY-06: sessions subcommand is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reclassify", "sessions", "--help"])
    assert result.exit_code == 0
    assert "sessions" in result.output.lower() or "session" in result.output.lower()


def test_rollback_subcommand_exists():
    """RECLASSIFY-06: rollback subcommand is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reclassify", "rollback", "--help"])
    assert result.exit_code == 0
    assert "rollback" in result.output.lower()
    assert "restore" in result.output.lower()


# Step 2 tests

def test_parse_filter_expr_quoted_value():
    """Filter parser handles quoted values."""
    result = _parse_filter_expr('vendor=""')
    assert result == {"vendor": ""}
    
    result = _parse_filter_expr('vendor="OpenText"')
    assert result == {"vendor": "OpenText"}


def test_parse_filter_expr_single_quotes():
    """Filter parser handles single quotes."""
    result = _parse_filter_expr("vendor='OpenText'")
    assert result == {"vendor": "OpenText"}


def test_parse_filter_expr_unquoted_value():
    """Filter parser handles unquoted values."""
    result = _parse_filter_expr("vendor=OpenText")
    assert result == {"vendor": "OpenText"}


def test_parse_filter_expr_invalid():
    """Filter parser raises ValueError for invalid syntax."""
    with pytest.raises(ValueError):
        _parse_filter_expr("invalid syntax here")


def test_show_aggregated_preview():
    """Aggregated preview renders without crashing."""
    changes = [
        {
            "source_file": "docs/test1.pdf",
            "fields_changed": {"vendor": ("", "OpenText"), "subsystem": ("", "Admin")},
            "chunk_count": 5
        },
        {
            "source_file": "docs/test2.pdf",
            "fields_changed": {"vendor": ("", "OpenText")},
            "chunk_count": 3
        }
    ]
    # Should not crash
    _show_aggregated_preview(changes)
