"""
Job Scheduler with priority-based queue and concurrency control.

Selects jobs from the queue based on priority and enforces
maximum concurrent job limits.
"""

import logging
from typing import List, Optional

from ingest.core.metadata import MetadataStore
from ingest.job.manager import JobManager
from ingest.job.models import Job, JobStatus

log = logging.getLogger("kb-ingest.job.scheduler")


class JobScheduler:
    """
    Priority-based job scheduler with concurrency control.

    Responsibilities:
    - Select next job to run based on priority
    - Enforce max concurrent jobs limit
    - Track running job count
    - Respect job lifecycle constraints
    """

    def __init__(
        self,
        store: MetadataStore,
        max_concurrent_jobs: int = 2,
    ):
        """
        Initialize scheduler.

        Args:
            store: Metadata store instance
            max_concurrent_jobs: Maximum parallel jobs
        """
        self.store = store
        self.max_concurrent_jobs = max_concurrent_jobs
        self.manager = JobManager(store)

    # ── Job Selection

    def get_next_job(self) -> Optional[Job]:
        """
        Select next job to run based on priority and concurrency.

        Returns:
            Job to run, or None if queue empty or at capacity
        """
        # Check current running count
        running_count = self._count_running_jobs()
        if running_count >= self.max_concurrent_jobs:
            log.debug(
                f"At capacity: {running_count}/"
                f"{self.max_concurrent_jobs} jobs"
            )
            return None

        # Get highest priority pending job
        pending_jobs = self.manager.get_pending_jobs(limit=1)
        if not pending_jobs:
            log.debug("No pending jobs")
            return None

        job = pending_jobs[0]
        log.info(
            f"Selected job {job.job_id[:8]} " f"(priority={job.priority.name})"
        )
        return job

    def get_runnable_jobs(self, limit: Optional[int] = None) -> List[Job]:
        """
        Get all jobs that can run now (respecting concurrency).

        Args:
            limit: Max jobs to return (None = all available slots)

        Returns:
            List of jobs ready to run
        """
        running_count = self._count_running_jobs()
        available_slots = self.max_concurrent_jobs - running_count

        if available_slots <= 0:
            return []

        actual_limit = (
            min(limit, available_slots) if limit else available_slots
        )

        jobs = self.manager.get_pending_jobs(limit=actual_limit)
        return jobs

    # ── Status Queries

    def _count_running_jobs(self) -> int:
        """Count currently running jobs."""
        row = self.store.conn.execute(
            """
            SELECT COUNT(*) as cnt FROM jobs
            WHERE status = ?
            """,
            (JobStatus.RUNNING.value,),
        ).fetchone()
        return int(row["cnt"]) if row else 0

    def get_queue_stats(self) -> dict:
        """
        Get queue statistics.

        Returns:
            Dict with pending, running, completed, failed counts
        """
        stats = {}
        for status in JobStatus:
            row = self.store.conn.execute(
                """
                SELECT COUNT(*) as cnt FROM jobs
                WHERE status = ?
                """,
                (status.value,),
            ).fetchone()
            stats[status.name.lower()] = int(row["cnt"]) if row else 0

        stats["capacity"] = self.max_concurrent_jobs
        stats["available_slots"] = max(
            0, self.max_concurrent_jobs - stats["running"]
        )

        return stats

    # ── Concurrency Control

    def set_max_concurrent_jobs(self, max_jobs: int) -> None:
        """
        Update maximum concurrent jobs limit.

        Args:
            max_jobs: New limit (must be >= 1)
        """
        if max_jobs < 1:
            raise ValueError("max_concurrent_jobs must be >= 1")

        old_max = self.max_concurrent_jobs
        self.max_concurrent_jobs = max_jobs

        log.info(f"Concurrency limit changed: {old_max} → {max_jobs}")

    def can_schedule_more(self) -> bool:
        """Check if scheduler can accept more running jobs."""
        return self._count_running_jobs() < self.max_concurrent_jobs

    # ── Bulk Operations

    def cancel_all_pending(self) -> int:
        """
        Cancel all pending jobs.

        Returns:
            Number of jobs cancelled
        """
        pending = self.manager.list_jobs(status=JobStatus.PENDING, limit=10000)
        cancelled = 0

        for job in pending:
            if self.manager.cancel_job(job.job_id):
                cancelled += 1

        log.info(f"Cancelled {cancelled} pending jobs")
        return cancelled

    def pause_all_running(self) -> int:
        """
        Pause all running jobs.

        Returns:
            Number of jobs paused
        """
        running = self.manager.list_jobs(status=JobStatus.RUNNING, limit=10000)
        paused = 0

        for job in running:
            if self.manager.pause_job(job.job_id):
                paused += 1

        log.info(f"Paused {paused} running jobs")
        return paused

    def resume_all_paused(self) -> int:
        """
        Resume all paused jobs.

        Returns:
            Number of jobs resumed
        """
        paused_jobs = self.manager.list_jobs(
            status=JobStatus.PAUSED, limit=10000
        )
        resumed = 0

        for job in paused_jobs:
            if self.manager.resume_job(job.job_id):
                resumed += 1

        log.info(f"Resumed {resumed} paused jobs")
        return resumed
