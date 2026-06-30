"""
Job management commands for KB-RAG CLI.

Commands:
- create: Create a new ingestion job
- list: List all jobs with status
- show: Show detailed job information
- pause: Pause a running job
- resume: Resume a paused job
- cancel: Cancel a job
- clean: Clean up completed/failed jobs
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ingest.core.metadata import MetadataStore
from ingest.job.manager import JobManager
from ingest.job.models import JobPriority, JobStatus

console = Console()


@click.group(name="job")
def job_group() -> None:
    """Job management commands."""
    pass


@job_group.command()
@click.option(
    "--docs",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory to ingest",
)
@click.option(
    "--product",
    type=str,
    default=None,
    help="Product name override",
)
@click.option(
    "--workers",
    type=int,
    default=2,
    help="Number of parallel workers (default: 2)",
)
@click.option(
    "--priority",
    type=click.Choice(["low", "normal", "high", "critical"]),
    default="normal",
    help="Job priority (default: normal)",
)
@click.option(
    "--clean",
    is_flag=True,
    help="Clean KB before ingesting",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reprocessing of existing files",
)
@click.option(
    "--sync",
    is_flag=True,
    help="Run synchronously (block until complete)",
)
@click.pass_context
def create(
    ctx: click.Context,
    docs: Path,
    product: str | None,
    workers: int,
    priority: str,
    clean: bool,
    force: bool,
    sync: bool,
) -> None:
    """
    Create a new ingestion job.

    Example:
        kb-rag job create --docs /path/to/docs --priority high
    """
    db_path = ctx.obj["db_path"]

    # Map priority string to JobPriority
    priority_map = {
        "low": JobPriority.LOW,
        "normal": JobPriority.NORMAL,
        "high": JobPriority.HIGH,
        "critical": JobPriority.CRITICAL,
    }

    try:
        with MetadataStore(db_path) as store:
            manager = JobManager(store)
            job = manager.create_job(
                docs_path=str(docs),
                product_override=product,
                workers=workers,
                priority=priority_map[priority],
                clean=clean,
                force=force,
                sync=sync,
            )

        console.print(
            f"[green]✓[/green] Job created: [bold]{job.job_id}[/bold]"
        )
        console.print(f"  Path: {docs}")
        console.print(f"  Priority: {priority}")
        console.print(f"  Workers: {workers}")

        if sync:
            console.print(
                "\n[yellow]Note:[/yellow] Sync mode not yet "
                "implemented. Job queued for async execution."
            )

        console.print("\nUse 'kb-rag job show <job_id>' to check status")

    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error creating job:[/red] {e}")
        sys.exit(1)


@job_group.command(name="list")
@click.option(
    "--status",
    type=click.Choice(
        ["pending", "running", "completed", "failed", "paused", "cancelled"]
    ),
    default=None,
    help="Filter by status",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of jobs to show (default: 20)",
)
@click.pass_context
def list_jobs(ctx: click.Context, status: str | None, limit: int) -> None:
    """
    List all jobs.

    Example:
        kb-rag job list
        kb-rag job list --status running
    """
    db_path = ctx.obj["db_path"]

    try:
        with MetadataStore(db_path) as store:
            manager = JobManager(store)

            # Get jobs
            jobs = manager.list_jobs(
                status=JobStatus(status) if status else None, limit=limit
            )

        if not jobs:
            console.print("[yellow]No jobs found[/yellow]")
            return

        # Create table
        table = Table(title="Jobs", show_lines=False)
        table.add_column("Job ID", style="cyan", width=12)
        table.add_column("Status", width=10)
        table.add_column("Priority", width=8)
        table.add_column("Path", overflow="fold")
        table.add_column("Progress", width=12)
        table.add_column("Created", width=10)

        for job in jobs:
            # Status with color
            status_color = {
                "pending": "yellow",
                "running": "blue",
                "completed": "green",
                "failed": "red",
                "paused": "magenta",
                "cancelled": "dim",
            }.get(job.status.value, "white")

            # Progress
            if job.total_files > 0:
                pct = (job.processed_files / job.total_files) * 100
                progress = f"{job.processed_files}/{job.total_files}"
                progress += f" ({pct:.0f}%)"
            else:
                progress = "0/0"

            # Created timestamp  - Job model already has datetime objects
            created_str = job.created_at.strftime("%Y-%m-%d")

            # Short job ID (first 8 chars)
            short_id = job.job_id[:8]

            table.add_row(
                short_id,
                f"[{status_color}]{job.status.value}[/]",
                str(job.priority.value),
                str(Path(job.docs_path).name),
                progress,
                created_str,
            )

        console.print(table)
        console.print(f"\nShowing {len(jobs)} job(s)")

    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error listing jobs:[/red] {e}")
        sys.exit(1)


@job_group.command()
@click.argument("job_id")
@click.pass_context
def show(ctx: click.Context, job_id: str) -> None:
    """
    Show detailed job information.

    Example:
        kb-rag job show abc12345
    """
    db_path = ctx.obj["db_path"]

    try:
        with MetadataStore(db_path) as store:
            manager = JobManager(store)

            # Try to find job by prefix
            jobs = manager.list_jobs()
            matching = [j for j in jobs if j.job_id.startswith(job_id)]

            if not matching:
                console.print(f"[red]✗ Job not found:[/red] {job_id}")
                sys.exit(1)
            elif len(matching) > 1:
                console.print(
                    f"[red]✗ Ambiguous job ID:[/red] {job_id} "
                    f"matches {len(matching)} jobs"
                )
                sys.exit(1)

            job = matching[0]

        # Display job details
        console.print("\n[bold]Job Details[/bold]")
        console.print("─" * 50)
        console.print(f"Job ID:       {job.job_id}")
        console.print(f"Status:       {job.status.value}")
        console.print(f"Priority:     {job.priority.value}")
        console.print(f"Path:         {job.docs_path}")
        console.print(f"Product:      {job.product_override or '(auto)'}")
        console.print(f"Workers:      {job.workers}")
        console.print(f"Clean:        {job.clean}")
        console.print(f"Force:        {job.force}")

        # Timestamps - job already has datetime objects
        console.print(
            f"Created:      {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if job.started_at:
            console.print(
                "Started:      "
                f"{job.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        if job.completed_at:
            console.print(
                "Completed:    "
                f"{job.completed_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Duration
            assert job.started_at is not None
            duration = (job.completed_at - job.started_at).total_seconds()
            console.print(f"Duration:     {duration:.1f}s")

        # Progress
        console.print("\n[bold]Progress[/bold]")
        console.print("─" * 50)
        console.print(f"Total files:      {job.total_files}")
        console.print(f"Processed files:  {job.processed_files}")
        console.print(f"Total chunks:     {job.total_chunks}")

        if job.total_files > 0:
            pct = (job.processed_files / job.total_files) * 100
            console.print(f"Progress:         {pct:.1f}%")

        # Error
        if job.error:
            console.print("\n[bold red]Error[/bold red]")
            console.print("─" * 50)
            console.print(job.error)

    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error showing job:[/red] {e}")
        sys.exit(1)


@job_group.command()
@click.argument("job_id")
@click.pass_context
def pause(ctx: click.Context, job_id: str) -> None:
    """
    Pause a running job.

    Example:
        kb-rag job pause abc12345
    """
    db_path = ctx.obj["db_path"]

    try:
        with MetadataStore(db_path) as store:
            manager = JobManager(store)

            # Find job by prefix
            jobs = manager.list_jobs()
            matching = [j for j in jobs if j.job_id.startswith(job_id)]

            if not matching:
                console.print(f"[red]✗ Job not found:[/red] {job_id}")
                sys.exit(1)
            elif len(matching) > 1:
                console.print(f"[red]✗ Ambiguous job ID:[/red] {job_id}")
                sys.exit(1)

            full_job_id = matching[0].job_id
            manager.pause_job(full_job_id)

        console.print(
            f"[green]✓[/green] Job paused: [bold]{full_job_id[:8]}[/bold]"
        )

    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error pausing job:[/red] {e}")
        sys.exit(1)


@job_group.command()
@click.argument("job_id")
@click.pass_context
def resume(ctx: click.Context, job_id: str) -> None:
    """
    Resume a paused job.

    Example:
        kb-rag job resume abc12345
    """
    db_path = ctx.obj["db_path"]

    try:
        with MetadataStore(db_path) as store:
            manager = JobManager(store)

            # Find job by prefix
            jobs = manager.list_jobs()
            matching = [j for j in jobs if j.job_id.startswith(job_id)]

            if not matching:
                console.print(f"[red]✗ Job not found:[/red] {job_id}")
                sys.exit(1)
            elif len(matching) > 1:
                console.print(f"[red]✗ Ambiguous job ID:[/red] {job_id}")
                sys.exit(1)

            full_job_id = matching[0].job_id
            manager.resume_job(full_job_id)

        console.print(
            f"[green]✓[/green] Job resumed: [bold]{full_job_id[:8]}[/bold]"
        )

    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error resuming job:[/red] {e}")
        sys.exit(1)


@job_group.command()
@click.argument("job_id")
@click.pass_context
def cancel(ctx: click.Context, job_id: str) -> None:
    """
    Cancel a job.

    Example:
        kb-rag job cancel abc12345
    """
    db_path = ctx.obj["db_path"]

    try:
        with MetadataStore(db_path) as store:
            manager = JobManager(store)

            # Find job by prefix
            jobs = manager.list_jobs()
            matching = [j for j in jobs if j.job_id.startswith(job_id)]

            if not matching:
                console.print(f"[red]✗ Job not found:[/red] {job_id}")
                sys.exit(1)
            elif len(matching) > 1:
                console.print(f"[red]✗ Ambiguous job ID:[/red] {job_id}")
                sys.exit(1)

            full_job_id = matching[0].job_id
            manager.cancel_job(full_job_id)

        console.print(
            f"[green]✓[/green] Job cancelled: "
            f"[bold]{full_job_id[:8]}[/bold]"
        )

    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error cancelling job:[/red] {e}")
        sys.exit(1)


@job_group.command()
@click.option(
    "--status",
    type=click.Choice(["completed", "failed", "cancelled"]),
    default="completed",
    help="Status of jobs to clean (default: completed)",
)
@click.option(
    "--days",
    type=int,
    default=7,
    help="Clean jobs older than N days (default: 7)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without deleting",
)
@click.pass_context
def clean(ctx: click.Context, status: str, days: int, dry_run: bool) -> None:
    """
    Clean up old completed/failed/cancelled jobs.

    Example:
        kb-rag job clean --status completed --days 7
        kb-rag job clean --dry-run
    """
    db_path = ctx.obj["db_path"]

    try:
        from datetime import datetime, timedelta

        cutoff_dt = datetime.now() - timedelta(days=days)

        with MetadataStore(db_path) as store:
            manager = JobManager(store)

            # Find jobs to clean
            jobs = manager.list_jobs(status=JobStatus(status))
            to_clean = [
                j
                for j in jobs
                if j.completed_at and j.completed_at < cutoff_dt
            ]

        if not to_clean:
            console.print(
                f"[yellow]No {status} jobs older than "
                f"{days} days found[/yellow]"
            )
            return

        if dry_run:
            console.print(
                f"[yellow]Dry run: would delete {len(to_clean)} "
                "job(s)[/yellow]"
            )
            for job in to_clean:
                console.print(f"  - {job.job_id[:8]} ({job.docs_path})")
            return

        # Delete jobs
        with MetadataStore(db_path) as store:
            for job in to_clean:
                store.conn.execute(
                    "DELETE FROM jobs WHERE job_id = ?", (job.job_id,)
                )
            store.commit()

        console.print(f"[green]✓[/green] Cleaned {len(to_clean)} job(s)")

    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error cleaning jobs:[/red] {e}")
        sys.exit(1)
