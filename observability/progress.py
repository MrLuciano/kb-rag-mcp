"""
Progress tracking for job execution.

Provides real-time progress updates with ETA estimation
and terminal-friendly display.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from ingest.core.metadata import MetadataStore
from ingest.job.manager import JobManager
from ingest.job.models import JobStatus

log = logging.getLogger("kb-ingest.observability.progress")


class ProgressTracker:
    """
    Tracks and displays job progress in real-time.

    Features:
    - ETA estimation based on processing rate
    - Progress bar with percentage
    - Files processed / total
    - Chunks generated
    - Status updates
    """

    def __init__(
        self,
        store: MetadataStore,
        update_interval: float = 2.0,
    ):
        """
        Initialize progress tracker.

        Args:
            store: Metadata store instance
            update_interval: Update interval in seconds
        """
        self.store = store
        self.update_interval = update_interval
        self.manager = JobManager(store)
        self.console = Console()

    def get_job_progress(self, job_id: str) -> Optional[dict]:
        """
        Get current job progress.

        Args:
            job_id: Job identifier

        Returns:
            Dict with progress info or None if job not found
        """
        job = self.manager.get_job(job_id)
        if job is None:
            return None

        total = job.total_files
        processed = job.processed_files
        chunks = job.total_chunks

        # Calculate percentage
        percentage = (processed / total * 100.0) if total > 0 else 0.0

        # Calculate ETA
        eta = None
        if job.started_at and processed > 0 and total > 0:
            elapsed = (datetime.now() - job.started_at).total_seconds()
            rate = processed / elapsed  # files per second
            remaining = total - processed
            if rate > 0:
                eta_seconds = remaining / rate
                eta = timedelta(seconds=int(eta_seconds))

        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "total_files": total,
            "processed_files": processed,
            "chunks_generated": chunks,
            "percentage": percentage,
            "eta": eta,
            "error": job.error,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }

    def display_progress(self, job_id: str) -> None:
        """
        Display job progress once.

        Args:
            job_id: Job identifier
        """
        progress_data = self.get_job_progress(job_id)
        if progress_data is None:
            self.console.print(f"[red]Job {job_id} not found[/red]")
            return

        # Create table
        table = Table(title=f"Job {job_id[:8]}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", progress_data["status"])
        table.add_row(
            "Progress",
            f"{progress_data['processed_files']}/"
            f"{progress_data['total_files']} files "
            f"({progress_data['percentage']:.1f}%)",
        )
        table.add_row("Chunks", str(progress_data["chunks_generated"]))

        if progress_data["eta"]:
            table.add_row("ETA", str(progress_data["eta"]))

        if progress_data["error"]:
            table.add_row("Error", progress_data["error"])

        self.console.print(table)

    async def follow_progress(
        self, job_id: str, stop_on_complete: bool = True
    ) -> None:
        """
        Follow job progress with live updates.

        Args:
            job_id: Job identifier
            stop_on_complete: Stop when job completes
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )

        task_id: Optional[TaskID] = None

        with Live(progress, console=self.console, refresh_per_second=4):
            while True:
                progress_data = self.get_job_progress(job_id)

                if progress_data is None:
                    progress.console.print(
                        f"[red]Job {job_id} not found[/red]"
                    )
                    break

                # Create or update progress task
                total = progress_data["total_files"]
                processed = progress_data["processed_files"]

                if task_id is None and total > 0:
                    task_id = progress.add_task(
                        f"Job {job_id[:8]}",
                        total=total,
                        completed=processed,
                    )
                elif task_id is not None:
                    progress.update(task_id, total=total, completed=processed)

                # Check if complete
                status = JobStatus(progress_data["status"])
                if status.value in [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]:
                    if progress_data["error"]:
                        progress.console.print(
                            f"[red]Job failed: "
                            f"{progress_data['error']}[/red]"
                        )
                    else:
                        progress.console.print(
                            f"[green]Job completed: "
                            f"{processed} files, "
                            f"{progress_data['chunks_generated']} "
                            f"chunks[/green]"
                        )

                    if stop_on_complete:
                        break

                # Wait before next update
                await asyncio.sleep(self.update_interval)

    def display_summary(self, job_id: str) -> None:
        """
        Display job summary (final stats).

        Args:
            job_id: Job identifier
        """
        job = self.manager.get_job(job_id)
        if job is None:
            self.console.print(f"[red]Job {job_id} not found[/red]")
            return

        # Calculate duration
        duration = None
        if job.started_at and job.completed_at:
            duration = job.completed_at - job.started_at

        # Create summary table
        table = Table(title=f"Job {job_id[:8]} Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", job.status.value)
        table.add_row("Files Processed", str(job.processed_files))
        table.add_row("Chunks Generated", str(job.total_chunks))

        if duration:
            table.add_row("Duration", str(duration))

        if job.error:
            table.add_row("Error", job.error)

        self.console.print(table)


class BatchProgressTracker:
    """
    Tracks progress for multiple jobs.

    Useful for monitoring entire ingestion pipeline.
    """

    def __init__(
        self,
        store: MetadataStore,
        update_interval: float = 2.0,
    ):
        self.store = store
        self.update_interval = update_interval
        self.manager = JobManager(store)
        self.console = Console()

    async def follow_all_jobs(self, limit: int = 10) -> None:
        """
        Follow progress of all active jobs.

        Args:
            limit: Max jobs to display
        """
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )

        task_ids: dict[str, TaskID] = {}

        with Live(progress, console=self.console, refresh_per_second=4):
            while True:
                # Get active jobs
                pending = self.manager.list_jobs(
                    status=JobStatus.PENDING, limit=limit
                )
                running = self.manager.list_jobs(
                    status=JobStatus.RUNNING, limit=limit
                )

                active_jobs = pending + running

                if not active_jobs:
                    progress.console.print("[yellow]No active jobs[/yellow]")
                    break

                # Update progress for each job
                current_job_ids = set()

                for job in active_jobs:
                    current_job_ids.add(job.job_id)

                    total = job.total_files
                    processed = job.processed_files

                    if job.job_id not in task_ids and total > 0:
                        task_ids[job.job_id] = progress.add_task(
                            f"Job {job.job_id[:8]} " f"({job.status.value})",
                            total=total,
                            completed=processed,
                        )
                    elif job.job_id in task_ids:
                        progress.update(
                            task_ids[job.job_id],
                            total=total,
                            completed=processed,
                            description=f"Job {job.job_id[:8]} "
                            f"({job.status.value})",
                        )

                # Remove completed jobs from display
                for job_id in list(task_ids.keys()):
                    if job_id not in current_job_ids:
                        progress.remove_task(task_ids[job_id])
                        del task_ids[job_id]

                await asyncio.sleep(self.update_interval)
