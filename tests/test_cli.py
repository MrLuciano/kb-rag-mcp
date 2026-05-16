"""
Tests for KB-RAG CLI commands.

Tests cover:
- Job creation, listing, show, pause, resume, cancel
- Progress monitoring
- Info command
- Legacy CLI wrapper
"""

import re
import time

import pytest
from click.testing import CliRunner

from ingest.cli.main import cli
from ingest.core.metadata import MetadataStore
from ingest.job.manager import JobManager
from ingest.job.models import JobPriority


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_cli.db"
    return db_path


class TestInfoCommand:
    """Tests for 'info' command."""

    def test_info_no_database(self, cli_runner, temp_db):
        """Test info command with non-existent database."""
        result = cli_runner.invoke(cli, ["--db", str(temp_db), "info"])
        assert result.exit_code == 0
        assert "KB-RAG System Information" in result.output
        assert "Exists: False" in result.output

    def test_info_with_database(self, cli_runner, temp_db):
        """Test info command with existing database."""
        # Create database
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            manager.create_job(
                docs_path="/tmp/test",
                priority=JobPriority.NORMAL,
            )

        result = cli_runner.invoke(cli, ["--db", str(temp_db), "info"])
        assert result.exit_code == 0
        assert "Total jobs: 1" in result.output
        assert "Active jobs: 1" in result.output


class TestJobCreateCommand:
    """Tests for 'job create' command."""

    def test_job_create_basic(self, cli_runner, temp_db, tmp_path):
        """Test basic job creation."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        result = cli_runner.invoke(
            cli,
            [
                "--db",
                str(temp_db),
                "job",
                "create",
                "--docs",
                str(docs_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Job created:" in result.output
        assert "Priority: normal" in result.output
        assert "Workers: 2" in result.output

    def test_job_create_with_options(self, cli_runner, temp_db, tmp_path):
        """Test job creation with all options."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        result = cli_runner.invoke(
            cli,
            [
                "--db",
                str(temp_db),
                "job",
                "create",
                "--docs",
                str(docs_dir),
                "--product",
                "test-product",
                "--workers",
                "4",
                "--priority",
                "high",
                "--clean",
                "--force",
            ],
        )

        assert result.exit_code == 0
        assert "Job created:" in result.output
        assert "Priority: high" in result.output
        assert "Workers: 4" in result.output

    def test_job_create_missing_docs(self, cli_runner, temp_db):
        """Test job creation without --docs fails."""
        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "create"]
        )

        assert result.exit_code != 0
        assert "Missing option '--docs'" in result.output


class TestJobListCommand:
    """Tests for 'job list' command."""

    def test_job_list_empty(self, cli_runner, temp_db):
        """Test listing when no jobs exist."""
        # Create empty database
        with MetadataStore(temp_db):
            pass

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "list"]
        )

        assert result.exit_code == 0
        assert "No jobs found" in result.output

    def test_job_list_with_jobs(self, cli_runner, temp_db):
        """Test listing jobs."""
        # Create test jobs
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job1 = manager.create_job(
                docs_path="/tmp/test1", priority=JobPriority.NORMAL
            )
            job2 = manager.create_job(
                docs_path="/tmp/test2", priority=JobPriority.HIGH
            )

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "list"]
        )

        assert result.exit_code == 0
        assert "Jobs" in result.output
        assert job1.job_id[:8] in result.output
        assert job2.job_id[:8] in result.output
        assert "Showing 2 job(s)" in result.output

    def test_job_list_with_status_filter(self, cli_runner, temp_db):
        """Test listing jobs filtered by status."""
        # Create test jobs
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path="/tmp/test1", priority=JobPriority.NORMAL
            )
            manager.start_job(job.job_id)

        result = cli_runner.invoke(
            cli,
            ["--db", str(temp_db), "job", "list", "--status", "running"],
        )

        assert result.exit_code == 0
        assert job.job_id[:8] in result.output


class TestJobShowCommand:
    """Tests for 'job show' command."""

    def test_job_show_success(self, cli_runner, temp_db):
        """Test showing job details."""
        # Create test job
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path="/tmp/test",
                product_override="test-product",
                priority=JobPriority.HIGH,
            )

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "show", job.job_id[:8]]
        )

        assert result.exit_code == 0
        assert "Job Details" in result.output
        assert job.job_id in result.output
        assert "Status:" in result.output
        assert "Priority:" in result.output

    def test_job_show_not_found(self, cli_runner, temp_db):
        """Test showing non-existent job."""
        with MetadataStore(temp_db):
            pass

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "show", "nonexist"]
        )

        assert result.exit_code == 1
        assert "Job not found" in result.output


class TestJobControlCommands:
    """Tests for pause/resume/cancel commands."""

    def test_job_pause(self, cli_runner, temp_db):
        """Test pausing a job."""
        # Create and start a job
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path="/tmp/test", priority=JobPriority.NORMAL
            )
            manager.start_job(job.job_id)

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "pause", job.job_id[:8]]
        )

        assert result.exit_code == 0
        assert "Job paused" in result.output

        # Verify job is paused
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job_updated = manager.get_job(job.job_id)
            assert job_updated.status.value == "paused"

    def test_job_resume(self, cli_runner, temp_db):
        """Test resuming a paused job."""
        # Create, start, and pause a job
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path="/tmp/test", priority=JobPriority.NORMAL
            )
            manager.start_job(job.job_id)
            manager.pause_job(job.job_id)

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "resume", job.job_id[:8]]
        )

        assert result.exit_code == 0
        assert "Job resumed" in result.output

        # Verify job is pending
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job_updated = manager.get_job(job.job_id)
            assert job_updated.status.value == "pending"

    def test_job_cancel(self, cli_runner, temp_db):
        """Test cancelling a job."""
        # Create a job
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path="/tmp/test", priority=JobPriority.NORMAL
            )

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "cancel", job.job_id[:8]]
        )

        assert result.exit_code == 0
        assert "Job cancelled" in result.output

        # Verify job is cancelled
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job_updated = manager.get_job(job.job_id)
            assert job_updated.status.value == "cancelled"


class TestJobCleanCommand:
    """Tests for 'job clean' command."""

    def test_job_clean_dry_run(self, cli_runner, temp_db):
        """Test clean command in dry-run mode."""
        # Create and complete a job
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path="/tmp/test", priority=JobPriority.NORMAL
            )
            manager.start_job(job.job_id)
            manager.complete_job(job.job_id)

            # Make it old by backdating
            store.conn.execute(
                "UPDATE jobs SET completed_at = ? WHERE job_id = ?",
                (time.time() - 10 * 86400, job.job_id),
            )
            store.commit()

        result = cli_runner.invoke(
            cli,
            [
                "--db",
                str(temp_db),
                "job",
                "clean",
                "--days",
                "7",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "would delete 1 job(s)" in result.output

    def test_job_clean_actual(self, cli_runner, temp_db):
        """Test clean command deleting jobs."""
        # Create and complete a job
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path="/tmp/test", priority=JobPriority.NORMAL
            )
            manager.start_job(job.job_id)
            manager.complete_job(job.job_id)

            # Make it old
            store.conn.execute(
                "UPDATE jobs SET completed_at = ? WHERE job_id = ?",
                (time.time() - 10 * 86400, job.job_id),
            )
            store.commit()

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "clean", "--days", "7"]
        )

        assert result.exit_code == 0
        assert "Cleaned 1 job(s)" in result.output

        # Verify job was deleted
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job_deleted = manager.get_job(job.job_id)
            assert job_deleted is None


class TestProgressCommands:
    """Tests for progress monitoring commands."""

    def test_progress_show(self, cli_runner, temp_db):
        """Test showing progress for a job."""
        # Create a job with progress
        with MetadataStore(temp_db) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path="/tmp/test", priority=JobPriority.NORMAL
            )
            manager.start_job(job.job_id)

            # Update progress
            store.conn.execute(
                "UPDATE jobs SET total_files = 10, processed_files = 5 "
                "WHERE job_id = ?",
                (job.job_id,),
            )
            store.commit()

        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "progress", "show", job.job_id[:8]]
        )

        assert result.exit_code == 0
        assert "Job Progress" in result.output
        assert "5/10" in result.output


class TestLegacyCLI:
    """Tests for legacy CLI wrapper."""

    def test_legacy_shows_deprecation_warning(self, cli_runner):
        """Test that legacy CLI shows deprecation warning."""
        import io
        import sys

        from ingest.cli.legacy import show_deprecation_warning

        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()

        show_deprecation_warning()

        output = sys.stderr.getvalue()
        sys.stderr = old_stderr

        assert "DEPRECATION WARNING" in output
        assert "kb-rag" in output
        assert "ingest.py" in output


# Integration tests


class TestCLIIntegration:
    """Integration tests for CLI workflows."""

    def test_full_job_workflow(self, cli_runner, temp_db, tmp_path):
        """Test complete workflow: create, show, pause, resume, cancel."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create job
        result = cli_runner.invoke(
            cli,
            [
                "--db",
                str(temp_db),
                "job",
                "create",
                "--docs",
                str(docs_dir),
            ],
        )
        assert result.exit_code == 0

        # Extract job ID from output
        job_id_line = [
            line
            for line in result.output.split("\n")
            if "Job created:" in line
        ][0]
        # Extract the job ID (it's in bold tags in rich output)
        match = re.search(r"Job created: (.+)", job_id_line)
        if not match:
            pytest.fail("Could not extract job ID from output")

        # List jobs
        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "list"]
        )
        assert result.exit_code == 0
        assert "pending" in result.output

    def test_concurrent_cli_access(self, cli_runner, temp_db, tmp_path):
        """Test that multiple CLI commands can access DB concurrently."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create multiple jobs
        for i in range(3):
            result = cli_runner.invoke(
                cli,
                [
                    "--db",
                    str(temp_db),
                    "job",
                    "create",
                    "--docs",
                    str(docs_dir),
                ],
            )
            assert result.exit_code == 0

        # List all jobs
        result = cli_runner.invoke(
            cli, ["--db", str(temp_db), "job", "list"]
        )
        assert result.exit_code == 0
        assert "Showing 3 job(s)" in result.output
