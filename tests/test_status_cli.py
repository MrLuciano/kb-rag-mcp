"""
Tests for the kb-ingest status CLI command.

Covers:
- Empty database handling
- Per-source summary data accuracy
- CLI invocation and help output
- Source filtering
"""

import pathlib
import tempfile

import pytest
from click.testing import CliRunner

from ingest.cli.status import status_group
from ingest.core.metadata import IngestRegistry

pytestmark = pytest.mark.integration


class TestStatusCommand:
    """Tests for the status CLI command and per_source_summary()."""

    # ── Fixtures ──────────────────────────────────────────────────────

    @pytest.fixture
    def cli_runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database path for testing."""
        return tmp_path / "test_status.db"

    # ── Helper ────────────────────────────────────────────────────────

    def _create_test_files(self, base: pathlib.Path) -> None:
        """Create test document files needed for registry operations."""
        for rel in [
            "webreports/doc.pdf",
            "xecm/manual.pdf",
            "webreports/error.pdf",
        ]:
            fp = base / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text("test content")

    # ── per_source_summary Tests ──────────────────────────────────────

    def test_per_source_summary_empty(self, tmp_path):
        """Empty database returns empty list from per_source_summary()."""
        db = tmp_path / "empty.db"
        with IngestRegistry(db) as reg:
            rows = reg.per_source_summary()
        assert rows == []

    def test_per_source_summary_with_data(self, tmp_path):
        """Verify per_source_summary returns correct counts."""
        db = tmp_path / "data.db"
        files_base = tmp_path / "files"
        self._create_test_files(files_base)

        with IngestRegistry(db) as reg:
            reg.mark_ok(
                files_base / "webreports/doc.pdf",
                "webreports/doc.pdf",
                3,
                "pdf",
                "WebReports",
            )
            reg.mark_ok(
                files_base / "xecm/manual.pdf",
                "xecm/manual.pdf",
                5,
                "pdf",
                "xECM",
            )
            reg.mark_error(
                files_base / "webreports/error.pdf",
                "webreports/error.pdf",
                "parse failed",
                "pdf",
                "WebReports",
            )

            rows = reg.per_source_summary()
            # Sort for deterministic assertion order
            rows.sort(key=lambda r: r["source"])

            assert len(rows) == 2
            wr = [r for r in rows if r["source"] == "webreports"][0]
            assert wr["files"] == 2
            assert wr["ok"] == 1
            assert wr["errors"] == 1
            assert wr["chunks"] == 3

            xe = [r for r in rows if r["source"] == "xecm"][0]
            assert xe["files"] == 1
            assert xe["ok"] == 1
            assert xe["errors"] == 0
            assert xe["chunks"] == 5

    # ── CLI Invocation Tests ──────────────────────────────────────────

    def test_status_cli_invocation(self, cli_runner):
        """Status command --help shows correct description text."""
        result = cli_runner.invoke(status_group, ["--help"])
        assert result.exit_code == 0
        assert "Show ingest status" in result.output

    def test_status_with_source_filter(self, tmp_path):
        """Filtering per_source_summary by source returns only matching."""
        db = tmp_path / "filter.db"
        files_base = tmp_path / "files2"
        self._create_test_files(files_base)

        with IngestRegistry(db) as reg:
            reg.mark_ok(
                files_base / "webreports/doc.pdf",
                "webreports/doc.pdf",
                3,
                "pdf",
                "WebReports",
            )
            reg.mark_ok(
                files_base / "xecm/manual.pdf",
                "xecm/manual.pdf",
                5,
                "pdf",
                "xECM",
            )

        # Get all rows then filter (Python-side, matching status.py logic)
        with IngestRegistry(db) as reg:
            all_rows = reg.per_source_summary()
            filtered = [r for r in all_rows if "xecm" in r["source"].lower()]

        assert len(filtered) == 1
        assert filtered[0]["source"] == "xecm"
        assert filtered[0]["files"] == 1
