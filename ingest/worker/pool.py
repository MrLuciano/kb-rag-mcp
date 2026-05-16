"""
Worker pool for parallel file processing.

Manages multiple async workers with task queue and graceful shutdown.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from ingest.worker.limiter import RateLimiter
from ingest.worker.worker import FileWorker, WorkerResult, WorkerStats

log = logging.getLogger("kb-ingest.worker.pool")


class WorkerTask:
    """
    Task to be processed by worker pool.

    Encapsulates file path and processing parameters.
    """

    def __init__(
        self,
        file_path: Path,
        docs_root: Path,
        store,
        registry,
        product_override: Optional[str] = None,
        force: bool = False,
    ):
        self.file_path = file_path
        self.docs_root = docs_root
        self.store = store
        self.registry = registry
        self.product_override = product_override
        self.force = force


class WorkerPool:
    """
    Pool of async workers for parallel file processing.

    Features:
    - Configurable number of workers
    - Task queue with backpressure
    - Shared rate limiter across workers
    - Graceful shutdown
    - Statistics tracking
    """

    def __init__(
        self,
        num_workers: int = 4,
        rate_limiter: Optional[RateLimiter] = None,
        max_queue_size: int = 1000,
        max_retries: int = 3,
        skip_validation: bool = False,
    ):
        """
        Initialize worker pool.

        Args:
            num_workers: Number of parallel workers
            rate_limiter: Shared rate limiter
            max_queue_size: Max tasks in queue
            max_retries: Max retry attempts per file
            skip_validation: Skip file validation (for testing)
        """
        self.num_workers = num_workers
        self.rate_limiter = rate_limiter
        self.max_queue_size = max_queue_size
        self.max_retries = max_retries
        self.skip_validation = skip_validation

        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.result_queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.stats = WorkerStats()
        self.running = False

        log.info(f"WorkerPool initialized with {num_workers} workers")

    async def start(self) -> None:
        """Start worker pool."""
        if self.running:
            log.warning("Worker pool already running")
            return

        self.running = True

        # Start worker tasks
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker)

        log.info(f"Started {self.num_workers} workers")

    async def stop(self, timeout: float = 30.0) -> None:
        """
        Stop worker pool gracefully.

        Args:
            timeout: Max seconds to wait for workers
        """
        if not self.running:
            return

        log.info("Stopping worker pool...")
        self.running = False

        # Send stop signals to all workers
        for _ in range(self.num_workers):
            await self.task_queue.put(None)

        # Wait for workers to finish with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.workers, return_exceptions=True),
                timeout=timeout,
            )
            log.info("All workers stopped gracefully")
        except asyncio.TimeoutError:
            log.warning("Worker shutdown timeout, cancelling tasks")
            for worker in self.workers:
                worker.cancel()
            await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers.clear()

    async def submit(self, task: WorkerTask) -> None:
        """
        Submit task to worker pool.

        Args:
            task: WorkerTask to process

        Blocks if queue is full (backpressure).
        """
        await self.task_queue.put(task)

    async def submit_batch(self, tasks: List[WorkerTask]) -> None:
        """
        Submit multiple tasks to pool.

        Args:
            tasks: List of WorkerTask instances
        """
        for task in tasks:
            await self.submit(task)

    async def get_result(
        self, timeout: Optional[float] = None
    ) -> Optional[WorkerResult]:
        """
        Get next result from pool.

        Args:
            timeout: Max seconds to wait (None = wait forever)

        Returns:
            WorkerResult or None if timeout
        """
        try:
            if timeout:
                result = await asyncio.wait_for(
                    self.result_queue.get(), timeout=timeout
                )
            else:
                result = await self.result_queue.get()
            return result
        except asyncio.TimeoutError:
            return None

    async def get_all_results(
        self, expected_count: int, timeout: float = 300.0
    ) -> List[WorkerResult]:
        """
        Get all expected results with timeout.

        Args:
            expected_count: Number of results to wait for
            timeout: Total timeout in seconds

        Returns:
            List of WorkerResult instances
        """
        results = []
        deadline = asyncio.get_event_loop().time() + timeout

        for _ in range(expected_count):
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                log.warning("Timeout waiting for results")
                break

            result = await self.get_result(timeout=remaining)
            if result:
                results.append(result)
                self.stats.record_result(result)
            else:
                break

        return results

    async def _worker_loop(self, worker_id: int) -> None:
        """
        Worker loop that processes tasks from queue.

        Args:
            worker_id: Worker identifier
        """
        worker = FileWorker(
            rate_limiter=self.rate_limiter,
            max_retries=self.max_retries,
            skip_validation=self.skip_validation,
        )

        log.debug(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get task from queue
                task = await self.task_queue.get()

                # None signals shutdown
                if task is None:
                    log.debug(f"Worker {worker_id} received stop signal")
                    break

                # Process task
                log.debug(
                    f"Worker {worker_id} " f"processing {task.file_path.name}"
                )

                result = await worker.process_file(
                    file_path=task.file_path,
                    docs_root=task.docs_root,
                    store=task.store,
                    registry=task.registry,
                    product_override=task.product_override,
                    force=task.force,
                )

                # Put result in output queue
                await self.result_queue.put(result)

                # Mark task as done
                self.task_queue.task_done()

            except asyncio.CancelledError:
                log.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                log.error(f"Worker {worker_id} error: {e}", exc_info=True)

        log.debug(f"Worker {worker_id} stopped")

    async def wait_completion(self, timeout: Optional[float] = None):
        """
        Wait for all queued tasks to complete.

        Args:
            timeout: Max seconds to wait (None = forever)
        """
        try:
            if timeout:
                await asyncio.wait_for(self.task_queue.join(), timeout=timeout)
            else:
                await self.task_queue.join()
        except asyncio.TimeoutError:
            log.warning("Task completion timeout")

    def get_stats(self) -> WorkerStats:
        """Get worker pool statistics."""
        return self.stats

    def queue_size(self) -> int:
        """Get current queue size."""
        return self.task_queue.qsize()

    def is_running(self) -> bool:
        """Check if pool is running."""
        return self.running

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
