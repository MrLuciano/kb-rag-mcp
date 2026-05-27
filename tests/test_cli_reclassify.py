"""
Tests for reclassification CLI commands.

Phase 16: Reclassification capability.
"""

import pytest
from click.testing import CliRunner

from ingest.cli.main import cli


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
