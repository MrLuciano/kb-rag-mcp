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


# Step 3 tests

@pytest.mark.asyncio
async def test_verify_command_shows_no_mismatches_message():
    """RECLASSIFY-05: verify shows success message when no mismatches."""
    from ingest.cli.reclassify import _verify_impl
    
    with patch("ingest.cli.reclassify.detect_changed_classifications") as mock_detect:
        with patch("kb_server.collections.router.CollectionRouter") as mock_router_class:
            # Mock router instance
            mock_router = AsyncMock()
            mock_router.resolve = AsyncMock(return_value="kb-default")
            mock_router_class.return_value = mock_router
            
            mock_detect.return_value = []
            
            # Should not crash, prints success message
            await _verify_impl(pattern="docs/*.pdf", collection=None, filter_expr=None)


@pytest.mark.asyncio
async def test_verify_command_shows_mismatches_table():
    """RECLASSIFY-05: verify shows per-document mismatches in table."""
    from ingest.cli.reclassify import _verify_impl
    
    changes = [
        {
            "source_file": "docs/test.pdf",
            "fields_changed": {"vendor": ("", "OpenText")},
            "chunk_count": 5
        }
    ]
    
    with patch("ingest.cli.reclassify.detect_changed_classifications") as mock_detect:
        with patch("kb_server.collections.router.CollectionRouter") as mock_router_class:
            # Mock router instance
            mock_router = AsyncMock()
            mock_router.resolve = AsyncMock(return_value="kb-default")
            mock_router_class.return_value = mock_router
            
            mock_detect.return_value = changes
            
            # Should not crash, prints mismatch table
            await _verify_impl(pattern="docs/*.pdf", collection=None, filter_expr=None)


# Step 4 tests

def test_sessions_command_shows_no_sessions_message():
    """RECLASSIFY-06: sessions shows message when no backups exist."""
    from ingest.cli.reclassify import _sessions_impl
    
    with patch("ingest.cli.reclassify.MetadataStore") as mock_store_class:
        # Mock store with empty results
        mock_store = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_store.conn.execute.return_value = mock_cursor
        mock_store.__enter__.return_value = mock_store
        mock_store.__exit__.return_value = None
        mock_store_class.return_value = mock_store
        
        # Should not crash, prints empty message
        _sessions_impl()


def test_sessions_command_shows_sessions_table():
    """RECLASSIFY-06: sessions shows table with backup sessions."""
    from ingest.cli.reclassify import _sessions_impl
    
    with patch("ingest.cli.reclassify.MetadataStore") as mock_store_class:
        # Mock store with session data
        mock_store = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("2026-05-27T15-30-00", 10, 25),  # session_timestamp, doc_count, field_count
            ("2026-05-27T14-00-00", 5, 12),
        ]
        mock_store.conn.execute.return_value = mock_cursor
        mock_store.__enter__.return_value = mock_store
        mock_store.__exit__.return_value = None
        mock_store_class.return_value = mock_store
        
        # Should not crash, prints session table
        _sessions_impl()


# Step 5 tests

@pytest.mark.asyncio
async def test_rollback_session_validation():
    """RECLASSIFY-06: rollback validates arguments."""
    from ingest.cli.reclassify import _rollback_impl
    
    # Test: --session and pattern cannot be combined
    with pytest.raises(SystemExit):
        await _rollback_impl(
            pattern="docs/*.pdf",
            session="2026-05-27T15-30-00",
            before=None,
            yes=True
        )
    
    # Test: either --session or (pattern + --before) required
    with pytest.raises(SystemExit):
        await _rollback_impl(
            pattern=None,
            session=None,
            before=None,
            yes=True
        )


@pytest.mark.asyncio
async def test_rollback_session_not_found():
    """RECLASSIFY-06: rollback shows error for non-existent session."""
    from ingest.cli.reclassify import _rollback_impl
    
    with patch("ingest.cli.reclassify.MetadataStore") as mock_store_class:
        # Mock store with empty results
        mock_store = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_store.conn.execute.return_value = mock_cursor
        mock_store.__enter__.return_value = mock_store
        mock_store.__exit__.return_value = None
        mock_store_class.return_value = mock_store
        
        with pytest.raises(SystemExit):
            await _rollback_impl(
                pattern=None,
                session="2026-05-27T15-30-00",
                before=None,
                yes=True
            )


@pytest.mark.asyncio
async def test_rollback_session_restores_metadata():
    """RECLASSIFY-06: rollback --session restores full session."""
    from ingest.cli.reclassify import _rollback_impl
    
    with patch("ingest.cli.reclassify.MetadataStore") as mock_store_class:
        with patch("ingest.cli.reclassify._apply_rollback") as mock_apply:
            # Mock store with backup data
            mock_store = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                ("docs/test.pdf", "vendor", "", 0),
            ]
            mock_store.conn.execute.return_value = mock_cursor
            mock_store.__enter__.return_value = mock_store
            mock_store.__exit__.return_value = None
            mock_store_class.return_value = mock_store
            
            await _rollback_impl(
                pattern=None,
                session="2026-05-27T15-30-00",
                before=None,
                yes=True
            )
            
            # Verify _apply_rollback was called
            mock_apply.assert_called_once()
