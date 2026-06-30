"""Tests for tags CLI commands.

Covers:
- tags list (no Qdrant needed)
- tags update (mocked Qdrant)
- tags remove (mocked Qdrant)
- tags reingest (mocked Qdrant)
- tags delete-tag (mocked Qdrant)
- Filter parsing and tag validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from ingest.cli.tags import _parse_filter_expr, _validate_tags, tags_group
from ingest.core.metadata import IngestRegistry


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def files_base(tmp_path):
    """Create a base directory for test files."""
    base = tmp_path / "files"
    base.mkdir()
    return base


@pytest.fixture
def populated_db(tmp_path, files_base):
    """Create a registry with sample files and tags."""
    db_path = tmp_path / "test_tags.db"
    # Create actual files for mark_ok
    files = {
        "doc1.pdf": "pdf content 1",
        "doc2.pdf": "pdf content 2",
        "doc3.docx": "docx content",
    }
    paths = {}
    for name, content in files.items():
        fp = files_base / name
        fp.write_text(content)
        paths[name] = fp

    with IngestRegistry(db_path) as reg:
        reg.mark_ok(
            paths["doc1.pdf"], "doc1.pdf", 3, "pdf", "WebReports",
        )
        reg._conn.execute(
            "UPDATE files SET tags = ? WHERE path = ?",
            ('["guide", "web"]', "doc1.pdf"),
        )
        reg.mark_ok(
            paths["doc2.pdf"], "doc2.pdf", 5, "pdf", "xECM",
        )
        reg._conn.execute(
            "UPDATE files SET tags = ? WHERE path = ?",
            ('["guide", "ecm"]', "doc2.pdf"),
        )
        reg.mark_ok(
            paths["doc3.docx"], "doc3.docx", 2, "docx", "WebReports",
        )
        reg._conn.execute(
            "UPDATE files SET tags = ? WHERE path = ?",
            ('[]', "doc3.docx"),
        )
        # Create tags_history table for log_tag_history() calls
        reg._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tags_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                user_id TEXT,
                source_file TEXT NOT NULL,
                action TEXT NOT NULL,
                tag_values TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tags_history_file
                ON tags_history(source_file);
            CREATE INDEX IF NOT EXISTS idx_tags_history_timestamp
                ON tags_history(timestamp);
        """)
        reg._conn.commit()
    return db_path


# ─── Tags Help & Registration ─────────────────────────────────────────


class TestTagsRegistration:
    """Verify tags command group is properly registered."""

    def test_tags_command_exists(self):
        """tags command is registered with --help."""
        runner = CliRunner()
        result = runner.invoke(tags_group, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "update" in result.output
        assert "remove" in result.output
        assert "reingest" in result.output
        assert "delete-tag" in result.output

    def test_tags_list_help(self):
        """tags list has expected flags."""
        runner = CliRunner()
        result = runner.invoke(tags_group, ["list", "--help"])
        assert result.exit_code == 0
        assert "--product" in result.output
        assert "--type" in result.output
        assert "--vendor" in result.output

    def test_tags_update_help(self):
        """tags update has expected flags."""
        runner = CliRunner()
        result = runner.invoke(tags_group, ["update", "--help"])
        assert result.exit_code == 0
        assert "--add" in result.output
        assert "--remove" in result.output
        assert "--replace" in result.output
        assert "--filter" in result.output
        assert "--collection" in result.output
        assert "--dry-run" in result.output
        assert "--yes" in result.output or "-y" in result.output

    def test_tags_remove_help(self):
        """tags remove has expected flags."""
        runner = CliRunner()
        result = runner.invoke(tags_group, ["remove", "--help"])
        assert result.exit_code == 0
        assert "--filter" in result.output
        assert "--collection" in result.output
        assert "--dry-run" in result.output
        assert "--yes" in result.output or "-y" in result.output

    def test_tags_reingest_help(self):
        """tags reingest has expected flags."""
        runner = CliRunner()
        result = runner.invoke(tags_group, ["reingest", "--help"])
        assert result.exit_code == 0
        assert "--filter" in result.output
        assert "--collection" in result.output
        assert "--dry-run" in result.output
        assert "--yes" in result.output or "-y" in result.output

    def test_tags_delete_tag_help(self):
        """tags delete-tag has expected flags."""
        runner = CliRunner()
        result = runner.invoke(tags_group, ["delete-tag", "--help"])
        assert result.exit_code == 0
        assert "TAG_NAME" in result.output
        assert "--collection" in result.output
        assert "--dry-run" in result.output
        assert "--yes" in result.output or "-y" in result.output


# ─── Tags List Tests ──────────────────────────────────────────────────


class TestTagsList:
    """Tests for 'tags list' command (no Qdrant needed)."""

    def test_tags_list_empty_db(self, cli_runner, tmp_path):
        """List with empty database shows no documents."""
        db = tmp_path / "empty.db"
        db_env = {"REGISTRY_DB": str(db)}
        result = cli_runner.invoke(tags_group, ["list"], env=db_env)
        assert result.exit_code == 0
        assert "No documents found matching filters" in result.output

    def test_tags_list_no_tags(self, cli_runner, tmp_path, files_base):
        """List with files but no tags shows no tags."""
        db = tmp_path / "notags.db"
        fp = files_base / "a.pdf"
        fp.write_text("content")
        with IngestRegistry(db) as reg:
            reg.mark_ok(fp, "a.pdf", 1, "pdf", "Test")
            reg._conn.execute(
                "UPDATE files SET tags = '[]' WHERE path = ?",
                ("a.pdf",),
            )
            reg._conn.commit()

        db_env = {"REGISTRY_DB": str(db)}
        result = cli_runner.invoke(tags_group, ["list"], env=db_env)
        assert result.exit_code == 0
        assert "No tags found on matching documents" in result.output

    def test_tags_list_with_tags(self, cli_runner, populated_db):
        """List shows tags aggregated across documents."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(tags_group, ["list"], env=db_env)
        assert result.exit_code == 0
        assert "guide" in result.output
        assert "web" in result.output
        assert "ecm" in result.output
        assert "Total documents: 3" in result.output

    def test_tags_list_filtered_by_product(self, cli_runner, populated_db):
        """List filtered by product returns only matching."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group, ["list", "--product", "WebReports"], env=db_env
        )
        assert result.exit_code == 0
        assert "guide" in result.output
        assert "web" in result.output
        assert "ecm" not in result.output

    def test_tags_list_filtered_no_match(self, cli_runner, populated_db):
        """List with non-matching filter shows no documents."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group, ["list", "--type", "unknown"], env=db_env
        )
        assert result.exit_code == 0
        assert "No documents found matching filters" in result.output


# ─── Tags Update Tests ────────────────────────────────────────────────


class TestTagsUpdate:
    """Tests for 'tags update' command (Qdrant mocked)."""

    def test_update_no_tags_shows_error(self, cli_runner, tmp_path):
        """Update without --add/--remove/--replace shows error."""
        db = tmp_path / "empty.db"
        db_env = {"REGISTRY_DB": str(db)}
        result = cli_runner.invoke(
            tags_group,
            ["update", "--filter", "product=Test"],
            env=db_env,
        )
        assert result.exit_code != 0
        assert "No tags specified" in result.output

    def test_update_dry_run(self, cli_runner, populated_db):
        """Update with --dry-run shows preview without applying."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group,
            [
                "update",
                "--add",
                "new",
                "--filter",
                "product=WebReports",
                "--dry-run",
            ],
            env=db_env,
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_update_no_match(self, cli_runner, populated_db):
        """Update with non-matching filter shows no documents."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group,
                [
                    "update",
                    "--add",
                    "new",
                    "--filter",
                    "product=Nonexistent",
                    "--dry-run",
                ],
            env=db_env,
        )
        assert result.exit_code == 0
        assert "No documents match the filter" in result.output

    def test_update_yes_applies_changes(self, cli_runner, populated_db):
        """Update with --yes applies changes (mocked Qdrant)."""
        with patch("ingest.cli.tags.VectorStore") as mock_vs:
            mock_store = MagicMock()
            mock_store.connect = AsyncMock()
            mock_store.client = MagicMock()
            mock_store.dim = 384
            mock_store.collection = "kb_docs"
            mock_store.update_tags = AsyncMock()
            mock_coll = MagicMock()
            mock_coll.name = "kb_docs"
            mock_store.client.get_collections = AsyncMock(
                return_value=MagicMock(
                    collections=[mock_coll]
                )
            )
            mock_vs.return_value = mock_store

            db_env = {"REGISTRY_DB": str(populated_db)}
            result = cli_runner.invoke(
                tags_group,
                [
                    "update",
                    "--add",
                    "new",
                    "--filter",
                    "product=WebReports",
                    "--yes",
                ],
                env=db_env,
            )
            assert result.exit_code == 0
            assert "Updated tags" in result.output
            assert mock_store.update_tags.await_count >= 1

    def test_update_remove_tag(self, cli_runner, populated_db):
        """Update with --remove removes tags (mocked Qdrant)."""
        with patch("ingest.cli.tags.VectorStore") as mock_vs:
            mock_store = MagicMock()
            mock_store.connect = AsyncMock()
            mock_store.client = MagicMock()
            mock_store.dim = 384
            mock_store.collection = "kb_docs"
            mock_store.update_tags = AsyncMock()
            mock_coll = MagicMock()
            mock_coll.name = "kb_docs"
            mock_store.client.get_collections = AsyncMock(
                return_value=MagicMock(
                    collections=[mock_coll]
                )
            )
            mock_vs.return_value = mock_store

            db_env = {"REGISTRY_DB": str(populated_db)}
            result = cli_runner.invoke(
                tags_group,
                [
                    "update",
                    "--remove",
                    "web",
                    "--filter",
                    "product=WebReports",
                    "--yes",
                ],
                env=db_env,
            )
            assert result.exit_code == 0
            assert "Updated tags" in result.output

    def test_update_replace_tag(self, cli_runner, populated_db):
        """Update with --replace replaces all tags (mocked Qdrant)."""
        with patch("ingest.cli.tags.VectorStore") as mock_vs:
            mock_store = MagicMock()
            mock_store.connect = AsyncMock()
            mock_store.client = MagicMock()
            mock_store.dim = 384
            mock_store.collection = "kb_docs"
            mock_store.update_tags = AsyncMock()
            mock_coll = MagicMock()
            mock_coll.name = "kb_docs"
            mock_store.client.get_collections = AsyncMock(
                return_value=MagicMock(
                    collections=[mock_coll]
                )
            )
            mock_vs.return_value = mock_store

            db_env = {"REGISTRY_DB": str(populated_db)}
            result = cli_runner.invoke(
                tags_group,
                [
                    "update",
                    "--replace",
                    "replacement",
                    "--filter",
                    "product=WebReports",
                    "--yes",
                ],
                env=db_env,
            )
            assert result.exit_code == 0
            assert "Updated tags" in result.output


# ─── Tags Remove Tests ────────────────────────────────────────────────


class TestTagsRemove:
    """Tests for 'tags remove' command (Qdrant mocked)."""

    def test_remove_dry_run(self, cli_runner, populated_db):
        """Remove with --dry-run shows preview without applying."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group,
            ["remove", "--filter", "product=WebReports", "--dry-run"],
            env=db_env,
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_remove_no_match(self, cli_runner, populated_db):
        """Remove with non-matching filter shows no documents."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group,
            ["remove", "--filter", "product=Nonexistent", "--dry-run"],
            env=db_env,
        )
        assert result.exit_code == 0
        assert "No documents match the filter" in result.output

    def test_remove_yes_deletes_documents(self, cli_runner, populated_db):
        """Remove with --yes deletes documents (mocked Qdrant)."""
        with patch("ingest.cli.tags.VectorStore") as mock_vs:
            mock_store = MagicMock()
            mock_store.connect = AsyncMock()
            mock_store.client = MagicMock()
            mock_store.dim = 384
            mock_store.collection = "kb_docs"
            mock_store.delete_document = AsyncMock()
            mock_coll = MagicMock()
            mock_coll.name = "kb_docs"
            mock_store.client.get_collections = AsyncMock(
                return_value=MagicMock(
                    collections=[mock_coll]
                )
            )
            mock_vs.return_value = mock_store

            db_env = {"REGISTRY_DB": str(populated_db)}
            result = cli_runner.invoke(
                tags_group,
                ["remove", "--filter", "product=WebReports", "--yes"],
                env=db_env,
            )
            assert result.exit_code == 0
            assert "Deleted" in result.output
            assert mock_store.delete_document.await_count >= 1


# ─── Tags Reingest Tests ──────────────────────────────────────────────


class TestTagsReingest:
    """Tests for 'tags reingest' command (Qdrant mocked)."""

    def test_reingest_dry_run(self, cli_runner, populated_db):
        """Reingest with --dry-run shows preview without queueing."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group,
            ["reingest", "--filter", "product=WebReports", "--dry-run"],
            env=db_env,
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_reingest_no_match(self, cli_runner, populated_db):
        """Reingest with non-matching filter shows no documents."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group,
            ["reingest", "--filter", "product=Nonexistent", "--dry-run"],
            env=db_env,
        )
        assert result.exit_code == 0
        assert "No documents match the filter" in result.output

    def test_reingest_yes_queues_documents(self, cli_runner, populated_db):
        """Reingest with --yes queues documents (mocked Qdrant)."""
        with patch("ingest.cli.tags.VectorStore") as mock_vs:
            mock_store = MagicMock()
            mock_store.connect = AsyncMock()
            mock_store.client = MagicMock()
            mock_store.dim = 384
            mock_store.collection = "kb_docs"
            mock_store.delete_document = AsyncMock()
            mock_coll = MagicMock()
            mock_coll.name = "kb_docs"
            mock_store.client.get_collections = AsyncMock(
                return_value=MagicMock(
                    collections=[mock_coll]
                )
            )
            mock_vs.return_value = mock_store

            db_env = {"REGISTRY_DB": str(populated_db)}
            result = cli_runner.invoke(
                tags_group,
                ["reingest", "--filter", "product=WebReports", "--yes"],
                env=db_env,
            )
            assert result.exit_code == 0
            assert "Queued" in result.output or "queued" in result.output

            # Verify documents were marked as pending
            with IngestRegistry(populated_db) as reg:
                rows = reg.list_all()
                for r in rows:
                    if r.get("product") == "WebReports":
                        assert r["status"] == "pending"


# ─── Tags Delete-Tag Tests ────────────────────────────────────────────


class TestTagsDeleteTag:
    """Tests for 'tags delete-tag' command (Qdrant mocked)."""

    def test_delete_tag_dry_run(self, cli_runner, populated_db):
        """Delete-tag with --dry-run shows preview."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group, ["delete-tag", "guide", "--dry-run"], env=db_env
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_delete_tag_no_match(self, cli_runner, populated_db):
        """Delete-tag with non-existent tag shows no documents."""
        db_env = {"REGISTRY_DB": str(populated_db)}
        result = cli_runner.invoke(
            tags_group,
            ["delete-tag", "nonexistent", "--dry-run"],
            env=db_env,
        )
        assert result.exit_code == 0
        assert "No documents have the tag" in result.output

    def test_delete_tag_yes_removes_tag(self, cli_runner, populated_db):
        """Delete-tag with --yes removes tag from all docs (mocked Qdrant)."""
        with patch("ingest.cli.tags.VectorStore") as mock_vs:
            mock_store = MagicMock()
            mock_store.connect = AsyncMock()
            mock_store.client = MagicMock()
            mock_store.dim = 384
            mock_store.collection = "kb_docs"
            mock_store.update_tags = AsyncMock()
            mock_coll = MagicMock()
            mock_coll.name = "kb_docs"
            mock_store.client.get_collections = AsyncMock(
                return_value=MagicMock(
                    collections=[mock_coll]
                )
            )
            mock_vs.return_value = mock_store

            db_env = {"REGISTRY_DB": str(populated_db)}
            result = cli_runner.invoke(
                tags_group, ["delete-tag", "web", "--yes"], env=db_env
            )
            assert result.exit_code == 0
            assert "Removed" in result.output or "removed" in result.output
            assert mock_store.update_tags.await_count >= 1


# ─── Unit tests for helper functions ──────────────────────────────────


class TestValidateTags:
    """Unit tests for _validate_tags()."""

    def test_validates_and_normalizes(self):
        """Tags are trimmed and lowercased."""
        result = _validate_tags(["  Guide ", "WEB  "])
        assert result == ["guide", "web"]

    def test_deduplicates(self):
        """Duplicate tags are removed."""
        result = _validate_tags(["guide", "guide", "web"])
        assert result == ["guide", "web"]

    def test_skips_empty(self):
        """Empty strings are skipped."""
        result = _validate_tags(["guide", "", "  "])
        assert result == ["guide"]

    def test_rejects_long_tags(self):
        """Tags exceeding MAX_TAG_LENGTH raise error."""
        from ingest.cli.tags import MAX_TAG_LENGTH

        long_tag = "a" * (MAX_TAG_LENGTH + 1)
        with pytest.raises(click.BadParameter, match="exceeds"):
            _validate_tags([long_tag])

    def test_rejects_whitespace_in_tag(self):
        """Tags with spaces raise error."""
        with pytest.raises(click.BadParameter, match="whitespace"):
            _validate_tags(["bad tag"])

    def test_rejects_too_many_tags(self):
        """Exceeding MAX_TAGS_PER_DOC raises error."""
        from ingest.cli.tags import MAX_TAGS_PER_DOC

        tags = [str(i) for i in range(MAX_TAGS_PER_DOC + 1)]
        with pytest.raises(click.BadParameter, match="Too many tags"):
            _validate_tags(tags)

    def test_empty_list_returns_empty(self):
        """Empty input returns empty list."""
        assert _validate_tags([]) == []


class TestParseFilterExpr:
    """Unit tests for _parse_filter_expr()."""

    def test_simple_key_value(self):
        """Parses simple key=value."""
        assert _parse_filter_expr("product=MyApp") == {"product": "MyApp"}

    def test_quoted_value(self):
        """Parses quoted values."""
        assert _parse_filter_expr('vendor="Acme Corp"') == {
            "vendor": "Acme Corp"
        }

    def test_multiple_filters(self):
        """Parses comma-separated filters."""
        result = _parse_filter_expr("product=MyApp,type=pdf")
        assert result == {"product": "MyApp", "type": "pdf"}

    def test_empty_string_returns_empty(self):
        """Empty string returns empty dict."""
        assert _parse_filter_expr("") == {}

    def test_none_returns_empty(self):
        """None returns empty dict."""
        assert _parse_filter_expr(None) == {}

    def test_missing_value_is_skipped(self):
        """Keys without values are skipped."""
        assert _parse_filter_expr("product=") == {}

    def test_missing_key_is_skipped(self):
        """Entries without '=' are skipped."""
        assert _parse_filter_expr("justwords") == {}

    def test_trims_whitespace(self):
        """Whitespace around key=value is trimmed."""
        assert _parse_filter_expr("  product =  MyApp  ") == {
            "product": "MyApp"
        }
