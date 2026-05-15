"""
Job Manager for CRUD operations on jobs.

Handles job lifecycle: create, read, update, cancel, pause, resume.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from ingest.core.metadata import MetadataStore
from ingest.job.models import Job, JobPriority, JobStatus

log = logging.getLogger("kb-ingest.job.manager")


class JobManager:
    """
    Manages job CRUD operations and lifecycle transitions.

    Responsibilities:
    - Create new jobs
    - Query jobs by ID or status
    - Update job status and progress
    - Cancel/pause/resume jobs
    - Track file-level progress
    """

    def __init__(self, store: MetadataStore):
        self.store = store

    # ── Job Creation

    def create_job(
        self,
        docs_path: str,
        priority: JobPriority = JobPriority.NORMAL,
        product_override: Optional[str] = None,
        workers: int = 2,
        clean: bool = False,
        force: bool = False,
        sync: bool = False,
    ) -> Job:
        """
        Create a new job in PENDING state.

        Args:
            docs_path: Path to documents directory
            priority: Job priority level
            product_override: Optional product name override
            workers: Number of parallel workers
            clean: Whether to clean KB before ingesting
            force: Whether to force re-ingestion
            sync: Whether to sync deleted files

        Returns:
            Created Job instance
        """
        job_id = str(uuid.uuid4())
        now = datetime.now()

        job = Job(
            job_id=job_id,
            status=JobStatus.PENDING,
            priority=priority,
            docs_path=docs_path,
            product_override=product_override,
            workers=workers,
            clean=clean,
            force=force,
            sync=sync,
            created_at=now,
        )

        self.store.conn.execute(
            """
            INSERT INTO jobs (
                job_id, status, priority, docs_path,
                product_override, workers, clean, force, sync,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id,
                job.status.value,
                job.priority.value,
                job.docs_path,
                job.product_override,
                job.workers,
                int(job.clean),
                int(job.force),
                int(job.sync),
                job.created_at.timestamp(),
            ),
        )
        self.store.commit()

        log.info(
            f"Created job {job_id[:8]} "
            f"(priority={priority.name}, path={docs_path})"
        )
        return job

    # ── Job Retrieval

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        row = self.store.conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()

        if row is None:
            return None

        return self._row_to_job(row)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100,
    ) -> List[Job]:
        """
        List jobs, optionally filtered by status.

        Args:
            status: Filter by job status (None = all)
            limit: Maximum jobs to return

        Returns:
            List of Job instances
        """
        if status is not None:
            rows = self.store.conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = ?
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
                """,
                (status.value, limit),
            ).fetchall()
        else:
            rows = self.store.conn.execute(
                """
                SELECT * FROM jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [self._row_to_job(row) for row in rows]

    def get_pending_jobs(self, limit: int = 100) -> List[Job]:
        """Get pending jobs ordered by priority."""
        return self.list_jobs(status=JobStatus.PENDING, limit=limit)

    # ── Job Updates

    def start_job(self, job_id: str) -> bool:
        """
        Transition job to RUNNING state.

        Returns:
            True if transition succeeded
        """
        now = datetime.now()
        cursor = self.store.conn.execute(
            """
            UPDATE jobs
            SET status = ?, started_at = ?
            WHERE job_id = ? AND status = ?
            """,
            (
                JobStatus.RUNNING.value,
                now.timestamp(),
                job_id,
                JobStatus.PENDING.value,
            ),
        )
        self.store.commit()

        success = cursor.rowcount > 0
        if success:
            log.info(f"Started job {job_id[:8]}")
        else:
            log.warning(f"Could not start job {job_id[:8]} (not pending)")
        return success

    def complete_job(self, job_id: str, error: Optional[str] = None) -> bool:
        """
        Mark job as COMPLETED or FAILED.

        Args:
            job_id: Job identifier
            error: Error message (if failed)

        Returns:
            True if transition succeeded
        """
        now = datetime.now()
        status = JobStatus.FAILED if error else JobStatus.COMPLETED

        cursor = self.store.conn.execute(
            """
            UPDATE jobs
            SET status = ?, completed_at = ?, error = ?
            WHERE job_id = ? AND status = ?
            """,
            (
                status.value,
                now.timestamp(),
                error,
                job_id,
                JobStatus.RUNNING.value,
            ),
        )
        self.store.commit()

        success = cursor.rowcount > 0
        if success:
            log.info(f"Completed job {job_id[:8]} (status={status.name})")
        else:
            log.warning(f"Could not complete job {job_id[:8]} (not running)")
        return success

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job (only if pending/running/paused).

        Returns:
            True if cancellation succeeded
        """
        now = datetime.now()
        cursor = self.store.conn.execute(
            """
            UPDATE jobs
            SET status = ?, completed_at = ?
            WHERE job_id = ? AND status IN (?, ?, ?)
            """,
            (
                JobStatus.CANCELLED.value,
                now.timestamp(),
                job_id,
                JobStatus.PENDING.value,
                JobStatus.RUNNING.value,
                JobStatus.PAUSED.value,
            ),
        )
        self.store.commit()

        success = cursor.rowcount > 0
        if success:
            log.info(f"Cancelled job {job_id[:8]}")
        else:
            log.warning(
                f"Could not cancel job {job_id[:8]} (already terminal)"
            )
        return success

    def pause_job(self, job_id: str) -> bool:
        """
        Pause a running job.

        Returns:
            True if pause succeeded
        """
        cursor = self.store.conn.execute(
            """
            UPDATE jobs
            SET status = ?
            WHERE job_id = ? AND status IN (?, ?)
            """,
            (
                JobStatus.PAUSED.value,
                job_id,
                JobStatus.PENDING.value,
                JobStatus.RUNNING.value,
            ),
        )
        self.store.commit()

        success = cursor.rowcount > 0
        if success:
            log.info(f"Paused job {job_id[:8]}")
        else:
            log.warning(f"Could not pause job {job_id[:8]} (not active)")
        return success

    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.

        Returns:
            True if resume succeeded
        """
        cursor = self.store.conn.execute(
            """
            UPDATE jobs
            SET status = ?
            WHERE job_id = ? AND status = ?
            """,
            (
                JobStatus.PENDING.value,
                job_id,
                JobStatus.PAUSED.value,
            ),
        )
        self.store.commit()

        success = cursor.rowcount > 0
        if success:
            log.info(f"Resumed job {job_id[:8]}")
        else:
            log.warning(f"Could not resume job {job_id[:8]} (not paused)")
        return success

    def update_progress(
        self,
        job_id: str,
        total_files: Optional[int] = None,
        processed_files: Optional[int] = None,
        total_chunks: Optional[int] = None,
    ) -> None:
        """
        Update job progress counters.

        Args:
            job_id: Job identifier
            total_files: Total files (if known)
            processed_files: Files processed so far
            total_chunks: Total chunks generated
        """
        updates = []
        params = []

        if total_files is not None:
            updates.append("total_files = ?")
            params.append(total_files)
        if processed_files is not None:
            updates.append("processed_files = ?")
            params.append(processed_files)
        if total_chunks is not None:
            updates.append("total_chunks = ?")
            params.append(total_chunks)

        if not updates:
            return

        params.append(job_id)
        sql = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"

        self.store.conn.execute(sql, params)
        self.store.commit()

    # ── Helper Methods

    def _row_to_job(self, row) -> Job:
        """Convert SQLite row to Job instance."""
        return Job(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            priority=JobPriority(row["priority"]),
            docs_path=row["docs_path"],
            product_override=row["product_override"],
            workers=row["workers"],
            clean=bool(row["clean"]),
            force=bool(row["force"]),
            sync=bool(row["sync"]),
            created_at=datetime.fromtimestamp(row["created_at"]),
            started_at=(
                datetime.fromtimestamp(row["started_at"])
                if row["started_at"]
                else None
            ),
            completed_at=(
                datetime.fromtimestamp(row["completed_at"])
                if row["completed_at"]
                else None
            ),
            error=row["error"],
            total_files=row["total_files"],
            processed_files=row["processed_files"],
            total_chunks=row["total_chunks"],
        )
