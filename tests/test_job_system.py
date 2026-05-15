"""
Tests for FASE 2: Job Management and Scheduler.

Tests metadata store, job manager, and scheduler functionality.
"""

import tempfile
from pathlib import Path

import pytest

from ingest.core.metadata import SCHEMA_VERSION, MetadataStore
from ingest.job.manager import JobManager
from ingest.job.models import Job, JobPriority, JobStatus
from ingest.job.scheduler import JobScheduler


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def metadata_store(temp_db):
    """Create and connect metadata store."""
    store = MetadataStore(db_path=temp_db)
    store.connect()
    yield store
    store.close()


@pytest.fixture
def job_manager(metadata_store):
    """Create job manager with test store."""
    return JobManager(metadata_store)


@pytest.fixture
def scheduler(metadata_store):
    """Create scheduler with test store."""
    return JobScheduler(metadata_store, max_concurrent_jobs=2)


# ── MetadataStore Tests


def test_metadata_store_initialization(temp_db):
    """Test database initialization and schema creation."""
    store = MetadataStore(db_path=temp_db)
    store.connect()

    # Check schema version
    row = store.conn.execute("SELECT version FROM schema_version").fetchone()
    assert row["version"] == SCHEMA_VERSION

    # Check tables exist
    tables = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {row["name"] for row in tables}

    assert "schema_version" in table_names
    assert "jobs" in table_names
    assert "job_progress" in table_names
    assert "files" in table_names

    store.close()


def test_metadata_store_wal_mode(metadata_store):
    """Test that WAL mode is enabled for concurrency."""
    row = metadata_store.conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0].lower() == "wal"


# ── JobManager Tests


def test_create_job(job_manager):
    """Test job creation with default parameters."""
    job = job_manager.create_job(docs_path="/test/docs")

    assert job.job_id is not None
    assert job.status == JobStatus.PENDING
    assert job.priority == JobPriority.NORMAL
    assert job.docs_path == "/test/docs"
    assert job.workers == 2
    assert not job.clean
    assert not job.force
    assert not job.sync
    assert job.created_at is not None


def test_create_job_with_options(job_manager):
    """Test job creation with custom options."""
    job = job_manager.create_job(
        docs_path="/test/docs",
        priority=JobPriority.HIGH,
        product_override="TestProduct",
        workers=4,
        clean=True,
        force=True,
        sync=True,
    )

    assert job.priority == JobPriority.HIGH
    assert job.product_override == "TestProduct"
    assert job.workers == 4
    assert job.clean
    assert job.force
    assert job.sync


def test_get_job(job_manager):
    """Test retrieving job by ID."""
    created = job_manager.create_job(docs_path="/test/docs")
    retrieved = job_manager.get_job(created.job_id)

    assert retrieved is not None
    assert retrieved.job_id == created.job_id
    assert retrieved.status == JobStatus.PENDING


def test_get_job_nonexistent(job_manager):
    """Test retrieving non-existent job returns None."""
    job = job_manager.get_job("nonexistent-id")
    assert job is None


def test_list_jobs(job_manager):
    """Test listing jobs."""
    job1 = job_manager.create_job(docs_path="/test/1")
    job2 = job_manager.create_job(docs_path="/test/2")
    job3 = job_manager.create_job(docs_path="/test/3")

    jobs = job_manager.list_jobs()
    assert len(jobs) == 3

    job_ids = {job.job_id for job in jobs}
    assert job1.job_id in job_ids
    assert job2.job_id in job_ids
    assert job3.job_id in job_ids


def test_list_jobs_by_status(job_manager):
    """Test listing jobs filtered by status."""
    job1 = job_manager.create_job(docs_path="/test/1")
    job2 = job_manager.create_job(docs_path="/test/2")

    # Start one job
    job_manager.start_job(job1.job_id)

    pending = job_manager.list_jobs(status=JobStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].job_id == job2.job_id

    running = job_manager.list_jobs(status=JobStatus.RUNNING)
    assert len(running) == 1
    assert running[0].job_id == job1.job_id


def test_start_job(job_manager):
    """Test starting a pending job."""
    job = job_manager.create_job(docs_path="/test/docs")
    success = job_manager.start_job(job.job_id)

    assert success
    updated = job_manager.get_job(job.job_id)
    assert updated.status == JobStatus.RUNNING
    assert updated.started_at is not None


def test_start_job_already_running(job_manager):
    """Test starting an already running job fails."""
    job = job_manager.create_job(docs_path="/test/docs")
    job_manager.start_job(job.job_id)

    # Try to start again
    success = job_manager.start_job(job.job_id)
    assert not success


def test_complete_job_success(job_manager):
    """Test completing a job successfully."""
    job = job_manager.create_job(docs_path="/test/docs")
    job_manager.start_job(job.job_id)
    success = job_manager.complete_job(job.job_id)

    assert success
    updated = job_manager.get_job(job.job_id)
    assert updated.status == JobStatus.COMPLETED
    assert updated.completed_at is not None
    assert updated.error is None


def test_complete_job_with_error(job_manager):
    """Test completing a job with error."""
    job = job_manager.create_job(docs_path="/test/docs")
    job_manager.start_job(job.job_id)
    success = job_manager.complete_job(job.job_id, error="Test error")

    assert success
    updated = job_manager.get_job(job.job_id)
    assert updated.status == JobStatus.FAILED
    assert updated.error == "Test error"


def test_cancel_job(job_manager):
    """Test cancelling a job."""
    job = job_manager.create_job(docs_path="/test/docs")
    success = job_manager.cancel_job(job.job_id)

    assert success
    updated = job_manager.get_job(job.job_id)
    assert updated.status == JobStatus.CANCELLED


def test_cancel_completed_job(job_manager):
    """Test cancelling completed job fails."""
    job = job_manager.create_job(docs_path="/test/docs")
    job_manager.start_job(job.job_id)
    job_manager.complete_job(job.job_id)

    success = job_manager.cancel_job(job.job_id)
    assert not success


def test_pause_job(job_manager):
    """Test pausing a running job."""
    job = job_manager.create_job(docs_path="/test/docs")
    job_manager.start_job(job.job_id)
    success = job_manager.pause_job(job.job_id)

    assert success
    updated = job_manager.get_job(job.job_id)
    assert updated.status == JobStatus.PAUSED


def test_resume_job(job_manager):
    """Test resuming a paused job."""
    job = job_manager.create_job(docs_path="/test/docs")
    job_manager.start_job(job.job_id)
    job_manager.pause_job(job.job_id)
    success = job_manager.resume_job(job.job_id)

    assert success
    updated = job_manager.get_job(job.job_id)
    assert updated.status == JobStatus.PENDING


def test_update_progress(job_manager):
    """Test updating job progress counters."""
    job = job_manager.create_job(docs_path="/test/docs")
    job_manager.update_progress(
        job.job_id,
        total_files=10,
        processed_files=5,
        total_chunks=100,
    )

    updated = job_manager.get_job(job.job_id)
    assert updated.total_files == 10
    assert updated.processed_files == 5
    assert updated.total_chunks == 100


# ── JobScheduler Tests


def test_scheduler_initialization(scheduler):
    """Test scheduler initialization."""
    assert scheduler.max_concurrent_jobs == 2
    assert scheduler.manager is not None


def test_get_next_job_priority(scheduler):
    """Test scheduler respects priority order."""
    # Create jobs with different priorities
    scheduler.manager.create_job(
        docs_path="/test/low", priority=JobPriority.LOW
    )
    job_high = scheduler.manager.create_job(
        docs_path="/test/high", priority=JobPriority.HIGH
    )
    scheduler.manager.create_job(
        docs_path="/test/normal", priority=JobPriority.NORMAL
    )

    # Next job should be high priority
    next_job = scheduler.get_next_job()
    assert next_job is not None
    assert next_job.job_id == job_high.job_id


def test_get_next_job_at_capacity(scheduler):
    """Test scheduler returns None when at capacity."""
    # Create and start 2 jobs (at capacity)
    job1 = scheduler.manager.create_job(docs_path="/test/1")
    job2 = scheduler.manager.create_job(docs_path="/test/2")
    scheduler.manager.start_job(job1.job_id)
    scheduler.manager.start_job(job2.job_id)

    # Create pending job
    scheduler.manager.create_job(docs_path="/test/3")

    # Should return None (at capacity)
    next_job = scheduler.get_next_job()
    assert next_job is None


def test_get_next_job_empty_queue(scheduler):
    """Test scheduler returns None when queue is empty."""
    next_job = scheduler.get_next_job()
    assert next_job is None


def test_get_runnable_jobs(scheduler):
    """Test getting multiple runnable jobs."""
    # Create 5 pending jobs
    for i in range(5):
        scheduler.manager.create_job(docs_path=f"/test/{i}")

    # Should return up to 2 (max_concurrent_jobs)
    runnable = scheduler.get_runnable_jobs()
    assert len(runnable) <= 2


def test_get_queue_stats(scheduler):
    """Test queue statistics."""
    # Create jobs in different states
    job1 = scheduler.manager.create_job(docs_path="/test/1")
    job2 = scheduler.manager.create_job(docs_path="/test/2")
    scheduler.manager.create_job(docs_path="/test/3")

    scheduler.manager.start_job(job1.job_id)
    scheduler.manager.start_job(job2.job_id)
    scheduler.manager.complete_job(job2.job_id)

    stats = scheduler.get_queue_stats()

    assert stats["pending"] == 1
    assert stats["running"] == 1
    assert stats["completed"] == 1
    assert stats["capacity"] == 2
    assert stats["available_slots"] == 1


def test_set_max_concurrent_jobs(scheduler):
    """Test changing concurrency limit."""
    scheduler.set_max_concurrent_jobs(5)
    assert scheduler.max_concurrent_jobs == 5


def test_set_max_concurrent_jobs_invalid(scheduler):
    """Test setting invalid concurrency limit raises error."""
    with pytest.raises(ValueError):
        scheduler.set_max_concurrent_jobs(0)


def test_can_schedule_more(scheduler):
    """Test checking if scheduler can accept more jobs."""
    assert scheduler.can_schedule_more()

    # Start 2 jobs (at capacity)
    job1 = scheduler.manager.create_job(docs_path="/test/1")
    job2 = scheduler.manager.create_job(docs_path="/test/2")
    scheduler.manager.start_job(job1.job_id)
    scheduler.manager.start_job(job2.job_id)

    assert not scheduler.can_schedule_more()


def test_cancel_all_pending(scheduler):
    """Test cancelling all pending jobs."""
    # Create 3 pending jobs
    for i in range(3):
        scheduler.manager.create_job(docs_path=f"/test/{i}")

    cancelled = scheduler.cancel_all_pending()
    assert cancelled == 3

    pending = scheduler.manager.get_pending_jobs()
    assert len(pending) == 0


def test_pause_all_running(scheduler):
    """Test pausing all running jobs."""
    # Create and start 2 jobs
    job1 = scheduler.manager.create_job(docs_path="/test/1")
    job2 = scheduler.manager.create_job(docs_path="/test/2")
    scheduler.manager.start_job(job1.job_id)
    scheduler.manager.start_job(job2.job_id)

    paused = scheduler.pause_all_running()
    assert paused == 2

    stats = scheduler.get_queue_stats()
    assert stats["running"] == 0
    assert stats["paused"] == 2


def test_resume_all_paused(scheduler):
    """Test resuming all paused jobs."""
    # Create, start, and pause 2 jobs
    job1 = scheduler.manager.create_job(docs_path="/test/1")
    job2 = scheduler.manager.create_job(docs_path="/test/2")
    scheduler.manager.start_job(job1.job_id)
    scheduler.manager.start_job(job2.job_id)
    scheduler.manager.pause_job(job1.job_id)
    scheduler.manager.pause_job(job2.job_id)

    resumed = scheduler.resume_all_paused()
    assert resumed == 2

    stats = scheduler.get_queue_stats()
    assert stats["paused"] == 0
    assert stats["pending"] == 2


# ── Job Model Tests


def test_job_is_terminal():
    """Test terminal state detection."""
    job = Job(
        job_id="test",
        status=JobStatus.COMPLETED,
        priority=JobPriority.NORMAL,
        docs_path="/test",
    )
    assert job.is_terminal()

    job.status = JobStatus.RUNNING
    assert not job.is_terminal()


def test_job_is_active():
    """Test active state detection."""
    job = Job(
        job_id="test",
        status=JobStatus.RUNNING,
        priority=JobPriority.NORMAL,
        docs_path="/test",
    )
    assert job.is_active()

    job.status = JobStatus.COMPLETED
    assert not job.is_active()


def test_job_can_pause():
    """Test pause capability check."""
    job = Job(
        job_id="test",
        status=JobStatus.RUNNING,
        priority=JobPriority.NORMAL,
        docs_path="/test",
    )
    assert job.can_pause()

    job.status = JobStatus.COMPLETED
    assert not job.can_pause()


def test_job_can_resume():
    """Test resume capability check."""
    job = Job(
        job_id="test",
        status=JobStatus.PAUSED,
        priority=JobPriority.NORMAL,
        docs_path="/test",
    )
    assert job.can_resume()

    job.status = JobStatus.RUNNING
    assert not job.can_resume()


def test_job_can_cancel():
    """Test cancel capability check."""
    job = Job(
        job_id="test",
        status=JobStatus.PENDING,
        priority=JobPriority.NORMAL,
        docs_path="/test",
    )
    assert job.can_cancel()

    job.status = JobStatus.COMPLETED
    assert not job.can_cancel()
