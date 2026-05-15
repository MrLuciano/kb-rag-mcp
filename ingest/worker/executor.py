"""
Job executor that integrates scheduler, workers, and progress tracking.

Orchestrates job execution by pulling jobs from scheduler,
distributing work to worker pool, and reporting progress.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from ingest.core.metadata import MetadataStore
from ingest.job.manager import JobManager
from ingest.job.models import Job
from ingest.job.scheduler import JobScheduler
from ingest.worker.limiter import RateLimiter
from ingest.worker.pool import WorkerPool, WorkerTask

log = logging.getLogger("kb-ingest.worker.executor")


class JobExecutor:
    """
    Executes jobs using worker pool with progress tracking.

    Responsibilities:
    - Pull jobs from scheduler
    - Distribute files to worker pool
    - Track progress and update job status
    - Handle errors and job completion
    """

    def __init__(
        self,
        store: MetadataStore,
        vector_store,
        registry,
        num_workers: int = 2,
        requests_per_minute: float = 60.0,
        max_retries: int = 3,
    ):
        """
        Initialize job executor.

        Args:
            store: Metadata store instance
            vector_store: Qdrant vector store
            registry: File registry
            num_workers: Number of parallel workers
            requests_per_minute: Rate limit for API calls
            max_retries: Max retry attempts per file
        """
        self.store = store
        self.vector_store = vector_store
        self.registry = registry
        self.num_workers = num_workers

        # Create components
        self.manager = JobManager(store)
        self.scheduler = JobScheduler(store, max_concurrent_jobs=num_workers)
        self.rate_limiter = RateLimiter(requests_per_minute)
        self.worker_pool = WorkerPool(
            num_workers=num_workers,
            rate_limiter=self.rate_limiter,
            max_retries=max_retries,
        )

        self.running = False

        log.info(
            f"JobExecutor: {num_workers} workers, "
            f"{requests_per_minute:.1f} req/min"
        )

    async def start(self) -> None:
        """Start executor and worker pool."""
        if self.running:
            log.warning("Executor already running")
            return

        self.running = True
        await self.worker_pool.start()
        log.info("JobExecutor started")

    async def stop(self) -> None:
        """Stop executor and worker pool."""
        if not self.running:
            return

        log.info("Stopping JobExecutor...")
        self.running = False
        await self.worker_pool.stop()
        log.info("JobExecutor stopped")

    async def execute_job(self, job: Job) -> bool:
        """
        Execute a single job.

        Args:
            job: Job to execute

        Returns:
            True if successful, False if failed
        """
        log.info(f"Executing job {job.job_id[:8]}: {job.docs_path}")

        # Mark job as running
        if not self.manager.start_job(job.job_id):
            log.error(f"Failed to start job {job.job_id[:8]}")
            return False

        try:
            # Collect files to process
            docs_path = Path(job.docs_path)
            if not docs_path.exists():
                raise FileNotFoundError(f"Path not found: {docs_path}")

            files = self._collect_files(docs_path, job.force)
            total_files = len(files)

            if total_files == 0:
                log.warning(f"No files to process in {docs_path}")
                self.manager.complete_job(job.job_id)
                return True

            log.info(f"Found {total_files} files to process")

            # Update total file count
            self.manager.update_progress(job.job_id, total_files=total_files)

            # Submit tasks to worker pool
            tasks = [
                WorkerTask(
                    file_path=file_path,
                    docs_root=docs_path,
                    store=self.vector_store,
                    registry=self.registry,
                    product_override=job.product_override,
                    force=job.force,
                )
                for file_path in files
            ]

            await self.worker_pool.submit_batch(tasks)

            # Collect results and update progress
            processed = 0
            total_chunks = 0
            errors = []

            for _ in range(total_files):
                result = await self.worker_pool.get_result(timeout=300.0)

                if result is None:
                    log.error("Timeout waiting for worker result")
                    break

                processed += 1
                total_chunks += result.chunks_generated

                if not result.success:
                    errors.append(f"{result.file_path.name}: {result.error}")

                # Update progress every 10 files or at end
                if processed % 10 == 0 or processed == total_files:
                    self.manager.update_progress(
                        job.job_id,
                        processed_files=processed,
                        total_chunks=total_chunks,
                    )

            # Complete job
            if errors:
                error_summary = (
                    f"{len(errors)} files failed: " f"{'; '.join(errors[:3])}"
                )
                if len(errors) > 3:
                    error_summary += f"... and {len(errors) - 3} more"
                self.manager.complete_job(job.job_id, error=error_summary)
                return False
            else:
                self.manager.complete_job(job.job_id)
                log.info(
                    f"Job {job.job_id[:8]} completed: "
                    f"{processed} files, {total_chunks} chunks"
                )
                return True

        except Exception as e:
            log.error(f"Job {job.job_id[:8]} failed: {e}", exc_info=True)
            self.manager.complete_job(job.job_id, error=str(e))
            return False

    def _collect_files(self, docs_path: Path, force: bool) -> List[Path]:
        """
        Collect files to process from directory.

        Args:
            docs_path: Root directory
            force: Include already-indexed files

        Returns:
            List of file paths to process
        """
        from ingest.ingest import EXT_TYPE_MAP

        files = []

        if docs_path.is_file():
            # Single file
            if docs_path.suffix.lower() in EXT_TYPE_MAP:
                files.append(docs_path)
        else:
            # Directory - recursively collect supported files
            for ext in EXT_TYPE_MAP.keys():
                files.extend(docs_path.rglob(f"*{ext}"))

        log.debug(f"Collected {len(files)} candidate files")
        return sorted(files)

    async def execute_next_job(self) -> Optional[Job]:
        """
        Execute next pending job from scheduler.

        Returns:
            Job that was executed, or None if queue empty
        """
        job = self.scheduler.get_next_job()
        if job is None:
            return None

        await self.execute_job(job)
        return job

    async def run_loop(
        self, interval: float = 5.0, max_iterations: Optional[int] = None
    ) -> None:
        """
        Run continuous job execution loop.

        Args:
            interval: Seconds between scheduler checks
            max_iterations: Max loop iterations (None = forever)
        """
        log.info(f"Starting execution loop (interval={interval}s)")

        iterations = 0

        while self.running:
            if max_iterations and iterations >= max_iterations:
                log.info("Max iterations reached")
                break

            # Check for jobs to execute
            if self.scheduler.can_schedule_more():
                job = await self.execute_next_job()
                if job:
                    iterations += 1
                    continue  # Check immediately for more jobs

            # No jobs ready, wait before checking again
            await asyncio.sleep(interval)

        log.info("Execution loop stopped")

    async def execute_all_pending(self, timeout: float = 3600.0) -> int:
        """
        Execute all pending jobs and wait for completion.

        Args:
            timeout: Max seconds to wait

        Returns:
            Number of jobs executed
        """
        pending = self.manager.get_pending_jobs(limit=1000)
        count = len(pending)

        if count == 0:
            log.info("No pending jobs to execute")
            return 0

        log.info(f"Executing {count} pending jobs...")

        for job in pending:
            await self.execute_job(job)

        return count

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
