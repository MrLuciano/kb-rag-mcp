"""
Tests for file watcher.

Tests cover:
- Debouncer logic (single/multiple events, batching)
- DocWatcher event handling (create, modify, delete)
- Ignore patterns (temp files, unsupported extensions)
- Job creation on file changes
"""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ingest.watcher.file_watcher import Debouncer, DocWatcher


class TestDebouncer:
    """Test debouncing logic."""

    def test_single_event(self):
        """Single event triggers callback after window."""
        debouncer = Debouncer(seconds=0.1)
        callback = Mock()

        debouncer.schedule("/path/file.pdf", "created", callback)
        time.sleep(0.15)

        callback.assert_called_once_with("/path/file.pdf", ["created"])

    def test_multiple_events_batched(self):
        """Multiple events within window are batched."""
        debouncer = Debouncer(seconds=0.1)
        callback = Mock()

        debouncer.schedule("/path/file.pdf", "created", callback)
        time.sleep(0.05)
        debouncer.schedule("/path/file.pdf", "modified", callback)
        time.sleep(0.15)

        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == "/path/file.pdf"
        assert "created" in args[1]
        assert "modified" in args[1]

    def test_different_files_independent(self):
        """Different files trigger separate callbacks."""
        debouncer = Debouncer(seconds=0.1)
        callback = Mock()

        debouncer.schedule("/path/file1.pdf", "created", callback)
        debouncer.schedule("/path/file2.pdf", "created", callback)
        time.sleep(0.15)

        assert callback.call_count == 2

    def test_cancel_all(self):
        """cancel_all() stops all pending timers."""
        debouncer = Debouncer(seconds=0.2)
        callback = Mock()

        debouncer.schedule("/path/file.pdf", "created", callback)
        time.sleep(0.05)
        debouncer.cancel_all()
        time.sleep(0.2)

        callback.assert_not_called()


class TestDocWatcher:
    """Test document watcher."""

    @pytest.fixture
    def job_manager(self):
        """Mock job manager."""
        manager = Mock()
        manager.create_job = Mock(return_value=Mock(job_id="test-job-123"))
        return manager

    @pytest.fixture
    def docs_path(self, tmp_path):
        """Create temporary docs directory."""
        docs = tmp_path / "docs"
        docs.mkdir()
        return docs

    @pytest.fixture
    def watcher(self, job_manager, docs_path):
        """Create watcher instance."""
        return DocWatcher(
            job_manager, docs_path=docs_path, debounce_seconds=0.1
        )

    def test_ignore_temp_files(self, watcher):
        """Temp files should be ignored."""
        assert watcher.should_ignore("/path/file.tmp")
        assert watcher.should_ignore("/path/~$file.docx")
        assert watcher.should_ignore("/path/.swp")
        assert watcher.should_ignore("/path/.~file.pdf")

    def test_ignore_unsupported_extensions(self, watcher):
        """Unsupported extensions should be ignored."""
        assert watcher.should_ignore("/path/file.exe")
        assert watcher.should_ignore("/path/file.zip")
        assert watcher.should_ignore("/path/file.dll")
        assert not watcher.should_ignore("/path/file.pdf")
        assert not watcher.should_ignore("/path/file.docx")

    def test_ignore_directories(self, watcher, tmp_path):
        """Directories should be ignored."""
        directory = tmp_path / "test_dir"
        directory.mkdir()
        assert watcher.should_ignore(str(directory))

    def test_supported_extensions_not_ignored(self, watcher):
        """Supported extensions should not be ignored."""
        assert not watcher.should_ignore("/path/doc.pdf")
        assert not watcher.should_ignore("/path/doc.docx")
        assert not watcher.should_ignore("/path/doc.xlsx")
        assert not watcher.should_ignore("/path/doc.pptx")
        assert not watcher.should_ignore("/path/doc.txt")
        assert not watcher.should_ignore("/path/doc.md")

    def test_on_created_triggers_job(self, watcher, job_manager, tmp_path):
        """File creation should trigger ingestion job."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")

        event = Mock()
        event.src_path = str(test_file)

        watcher.on_created(event)
        time.sleep(0.15)

        job_manager.create_job.assert_called_once()
        call_kwargs = job_manager.create_job.call_args[1]
        assert call_kwargs["force"] is True
        assert call_kwargs["workers"] == 1

    def test_on_modified_triggers_job(self, watcher, job_manager, tmp_path):
        """File modification should trigger ingestion job."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")

        event = Mock()
        event.src_path = str(test_file)

        watcher.on_modified(event)
        time.sleep(0.15)

        job_manager.create_job.assert_called_once()

    def test_on_deleted_no_handler(self, job_manager, docs_path):
        """on_deleted with no handler set is a no-op."""
        watcher = DocWatcher(
            job_manager, docs_path=docs_path, debounce_seconds=0.1
        )
        event = Mock()
        event.src_path = "/path/test.pdf"
        with patch.object(Path, "is_dir", return_value=False):
            watcher.on_deleted(event)  # must not raise
        job_manager.create_job.assert_not_called()

    def test_on_deleted_with_handler_calls_callback(
        self, job_manager, docs_path, tmp_path
    ):
        """on_deleted calls delete_handler with the file path."""
        handler = Mock()
        watcher = DocWatcher(
            job_manager,
            docs_path=docs_path,
            debounce_seconds=0.1,
            delete_handler=handler,
        )
        test_file = tmp_path / "doc.pdf"
        test_file.write_text("content")
        event = Mock()
        event.src_path = str(test_file)
        with patch.object(Path, "is_dir", return_value=False):
            watcher.on_deleted(event)
        handler.assert_called_once_with(str(test_file))

    def test_on_deleted_ignored_file_skips_handler(
        self, job_manager, docs_path
    ):
        """on_deleted does not call handler for ignored files."""
        handler = Mock()
        watcher = DocWatcher(
            job_manager,
            docs_path=docs_path,
            debounce_seconds=0.1,
            delete_handler=handler,
        )
        event = Mock()
        event.src_path = "/path/file.tmp"
        watcher.on_deleted(event)
        handler.assert_not_called()

    def test_on_deleted_handler_exception_does_not_propagate(
        self, job_manager, docs_path, tmp_path
    ):
        """Exceptions in delete_handler are caught and logged."""
        handler = Mock(side_effect=Exception("qdrant unavailable"))
        watcher = DocWatcher(
            job_manager,
            docs_path=docs_path,
            debounce_seconds=0.1,
            delete_handler=handler,
        )
        test_file = tmp_path / "doc.pdf"
        test_file.write_text("content")
        event = Mock()
        event.src_path = str(test_file)
        with patch.object(Path, "is_dir", return_value=False):
            watcher.on_deleted(event)  # must NOT raise

    def test_debounce_batches_changes(self, watcher, job_manager, tmp_path):
        """Multiple changes within window create single job."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")

        event = Mock()
        event.src_path = str(test_file)

        watcher.on_created(event)
        time.sleep(0.05)
        watcher.on_modified(event)
        time.sleep(0.05)
        watcher.on_modified(event)
        time.sleep(0.15)

        # Only one job created despite 3 events
        assert job_manager.create_job.call_count == 1

    def test_custom_ignore_patterns(self, job_manager, docs_path):
        """Custom ignore patterns should be respected."""
        custom_patterns = [".custom", "backup_"]
        watcher = DocWatcher(
            job_manager,
            docs_path=docs_path,
            debounce_seconds=0.1,
            ignore_patterns=custom_patterns,
        )

        # Custom patterns should work
        assert watcher.should_ignore("/path/file.custom")
        assert watcher.should_ignore("/path/backup_file.pdf")

        # When custom patterns provided, only those patterns are used
        # (not the defaults, so user has full control)
        # But unsupported extensions are still ignored
        assert watcher.should_ignore("/path/file.exe")  # Unsupported ext

    def test_stop_cancels_pending(self, watcher, job_manager, tmp_path):
        """stop() should cancel pending timers."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")

        event = Mock()
        event.src_path = str(test_file)

        watcher.on_created(event)
        time.sleep(0.05)
        watcher.stop()
        time.sleep(0.15)

        # Job should not be created after stop
        job_manager.create_job.assert_not_called()

    def test_error_handling_in_trigger(
        self, watcher, job_manager, tmp_path, caplog
    ):
        """Errors during job creation should be logged."""
        job_manager.create_job.side_effect = Exception("Job creation failed")

        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")

        event = Mock()
        event.src_path = str(test_file)

        watcher.on_created(event)
        time.sleep(0.15)

        # Should log error
        assert "Failed to create job" in caplog.text
        assert "Job creation failed" in caplog.text
