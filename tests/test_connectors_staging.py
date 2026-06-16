"""
Tests for connector staging helpers.
"""

import os
import time
from pathlib import Path

from ingest.connectors.models import RemoteDocument
from ingest.connectors.staging import (
    _safe_path_component,
    cleanup_stale_staging,
    get_staging_root,
    resolve_staged_metadata,
    stage_document,
    stage_documents,
)


class TestSafePathComponent:
    """Tests for _safe_path_component."""

    def test_keeps_alphanumeric(self):
        """Alphanumeric chars pass through unchanged."""
        assert _safe_path_component("hello123") == "hello123"

    def test_replaces_special_chars(self):
        """Special characters become underscores."""
        result = _safe_path_component("my:space/page@1")
        assert ":" not in result
        assert "/" not in result
        assert "@" not in result
        assert result == "my_space_page_1"

    def test_keeps_dash_underscore(self):
        """Dashes and underscores are preserved."""
        assert _safe_path_component("my-space_page") == "my-space_page"


class TestGetStagingRoot:
    """Tests for get_staging_root."""

    def test_uses_env_var(self, monkeypatch, tmp_path):
        """When KB_CONNECTOR_STAGING_DIR is set, uses that path."""
        custom_dir = tmp_path / "my-staging"
        monkeypatch.setenv("KB_CONNECTOR_STAGING_DIR", str(custom_dir))
        root = get_staging_root()
        assert root == custom_dir
        assert root.exists()

    def test_default_under_temp(self):
        """Default staging root is under system temp."""
        root = get_staging_root()
        assert "kb-rag-connectors" in str(root)
        assert root.exists()


class TestStageDocument:
    """Tests for stage_document."""

    def test_stage_single_document(self, tmp_path):
        """Single document is staged to a file with metadata header."""
        doc = RemoteDocument(
            remote_id="page-123",
            source_key="confluence://myspace",
            connector_type="confluence",
            title="My Page",
            content="This is the page content.",
            remote_url="https://confluence.example.com/pages/123",
            remote_etag='"etag1"',
            remote_mtime=5000.0,
        )
        staged_path = stage_document(doc, staging_root=tmp_path)

        assert staged_path.exists()
        text = staged_path.read_text(encoding="utf-8")

        # Metadata header present
        assert "source_key: confluence://myspace" in text
        assert "remote_id: page-123" in text
        assert "connector_type: confluence" in text
        assert "title: My Page" in text
        assert "remote_url: https://confluence.example.com/pages/123" in text
        assert 'remote_etag: "etag1"' in text
        assert "remote_mtime: 5000.0" in text

        # Separator and content
        assert "---" in text
        assert "This is the page content." in text

    def test_stage_with_metadata(self, tmp_path):
        """Document with metadata dict is staged with meta_ fields."""
        doc = RemoteDocument(
            remote_id="PROJ-42",
            source_key="jira://PROJ",
            connector_type="jira",
            title="Fix bug",
            content="Bug description here",
            metadata={"priority": "P1", "status": "open"},
        )
        staged_path = stage_document(doc, staging_root=tmp_path)

        text = staged_path.read_text(encoding="utf-8")
        assert "meta_priority: P1" in text
        assert "meta_status: open" in text

    def test_stage_documents_batch(self, tmp_path):
        """Multiple documents are staged to separate files."""
        docs = [
            RemoteDocument(
                remote_id=f"page-{i}",
                source_key="confluence://myspace",
                connector_type="confluence",
                title=f"Page {i}",
                content=f"Content {i}",
            )
            for i in range(3)
        ]
        paths = stage_documents(docs, staging_root=tmp_path)

        assert len(paths) == 3
        for p in paths:
            assert p.exists()
        # Each file has different content
        contents = {p.read_text(encoding="utf-8") for p in paths}
        assert len(contents) == 3


class TestCleanupStaleStaging:
    """Tests for cleanup_stale_staging."""

    def test_removes_old_files(self, tmp_path):
        """Files older than max_age are removed."""
        old_file = tmp_path / "stale-1.md"
        old_file.write_text("old content")
        # Set mtime to 48 hours ago
        old_mtime = time.time() - 48 * 3600
        os.utime(str(old_file), (old_mtime, old_mtime))

        fresh_file = tmp_path / "fresh-1.md"
        fresh_file.write_text("fresh content")

        removed = cleanup_stale_staging(
            staging_root=tmp_path, max_age_hours=24
        )
        assert removed == 1
        assert not old_file.exists()
        assert fresh_file.exists()

    def test_no_op_with_fresh_files(self, tmp_path):
        """No files removed when all are recent."""
        fresh = tmp_path / "fresh.md"
        fresh.write_text("fresh content")

        removed = cleanup_stale_staging(
            staging_root=tmp_path, max_age_hours=24
        )
        assert removed == 0
        assert fresh.exists()

    def test_no_op_nonexistent_dir(self, tmp_path):
        """Non-existent staging root does not error."""
        removed = cleanup_stale_staging(staging_root=tmp_path / "nonexistent")
        assert removed == 0


class TestResolveStagedMetadata:
    """Tests for resolve_staged_metadata."""

    def test_parses_metadata(self, tmp_path):
        """Metadata header is correctly parsed from staged file."""
        doc = RemoteDocument(
            remote_id="page-1",
            source_key="confluence://space",
            connector_type="confluence",
            title="Test",
            content="Body text",
        )
        staged = stage_document(doc, staging_root=tmp_path)
        metadata = resolve_staged_metadata(staged)

        assert metadata["source_key"] == "confluence://space"
        assert metadata["remote_id"] == "page-1"
        assert metadata["title"] == "Test"

    def test_nonexistent_file(self, tmp_path):
        """Non-existent file returns empty dict."""
        metadata = resolve_staged_metadata(tmp_path / "nope.md")
        assert metadata == {}
