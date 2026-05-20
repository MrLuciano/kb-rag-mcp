"""
Progress monitoring commands for KB-RAG CLI.

Commands:
- show: Show current progress for a job
- follow: Follow job progress in real-time (--interval N seconds)
"""

import sys
import time

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from ingest.core.metadata import MetadataStore
from ingest.job.manager import JobManager

console = Console()


@click.group(name="progress")
def progress_group() -> None:
    """Progress monitoring commands."""
    pass


@progress_group.command()
@click.argument("job_id")
@click.pass_context
def show(ctx: click.Context, job_id: str) -> None:
    """
    Show current progress for a job.

    Example:
        kb-rag progress show abc12345
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

            job = matching[0]

        # Display progress
        _display_progress(job)

    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error showing progress:[/red] {e}")
        sys.exit(1)


@progress_group.command()
@click.argument("job_id")
@click.option(
    "--interval",
    type=float,
    default=2.0,
    help="Update interval in seconds (default: 2.0)",
)
@click.pass_context
def follow(ctx: click.Context, job_id: str, interval: float) -> None:
    """
    Follow job progress in real-time.

    Updates every N seconds (default: 2.0). Press Ctrl+C to stop.

    Example:
        kb-rag progress follow abc12345
        kb-rag progress follow abc12345 --interval 1.0
    """
    db_path = ctx.obj["db_path"]

    try:
        # Find job by prefix first
        with MetadataStore(db_path) as store:
            manager = JobManager(store)
            jobs = manager.list_jobs()
            matching = [j for j in jobs if j.job_id.startswith(job_id)]

            if not matching:
                console.print(f"[red]✗ Job not found:[/red] {job_id}")
                sys.exit(1)
            elif len(matching) > 1:
                console.print(f"[red]✗ Ambiguous job ID:[/red] {job_id}")
                sys.exit(1)

            full_job_id = matching[0].job_id

        # Follow progress
        console.print(
            f"[dim]Following job {full_job_id[:8]}... "
            "(Ctrl+C to stop)[/dim]\n"
        )

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.fields[status]}"),
            TimeElapsedColumn(),
            console=console,
        )

        with Live(progress, console=console, refresh_per_second=4):
            task_id = None

            while True:
                with MetadataStore(db_path) as store:
                    manager = JobManager(store)
                    job = manager.get_job(full_job_id)

                if job is None:
                    console.print("[red]Job no longer exists[/red]")
                    break

                # Update or create progress task
                if task_id is None:
                    task_id = progress.add_task(
                        f"Job {full_job_id[:8]}",
                        total=max(job.total_files, 1),
                        status=job.status.value,
                    )
                else:
                    progress.update(
                        task_id,
                        completed=job.processed_files,
                        total=max(job.total_files, 1),
                        status=job.status.value,
                    )

                # Stop if job is terminal
                if job.status.value in (
                    "completed",
                    "failed",
                    "cancelled",
                ):
                    console.print(
                        f"\n[bold]Job {job.status.value}![/bold]"
                    )
                    _display_progress(job)
                    break

                time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped following[/dim]")
    except Exception as e:  # noqa: F841
        console.print(f"[red]✗ Error following progress:[/red] {e}")
        sys.exit(1)


def _display_progress(job) -> None:
    """Display progress details for a job."""
    # Status with color
    status_color = {
        "pending": "yellow",
        "running": "blue",
        "completed": "green",
        "failed": "red",
        "paused": "magenta",
        "cancelled": "dim",
    }.get(job.status.value, "white")

    # Progress stats
    if job.total_files > 0:
        pct = (job.processed_files / job.total_files) * 100
        progress_text = (
            f"{job.processed_files}/{job.total_files} files ({pct:.0f}%)"
        )
    else:
        progress_text = "0/0 files"

    # Build table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value")

    table.add_row("Job ID", job.job_id[:8])
    table.add_row(
        "Status", f"[{status_color}]{job.status.value}[/]"
    )
    table.add_row("Progress", progress_text)
    table.add_row("Total chunks", str(job.total_chunks))

    if job.started_at:
        started_str = job.started_at.strftime("%Y-%m-%d %H:%M:%S")
        table.add_row("Started", started_str)

        # Duration or ETA
        if job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            table.add_row("Duration", f"{duration:.1f}s")
        elif job.status.value == "running" and job.processed_files > 0:
            # Estimate ETA
            import time

            elapsed = time.time() - job.started_at.timestamp()
            rate = job.processed_files / elapsed
            remaining = job.total_files - job.processed_files
            eta_seconds = remaining / rate if rate > 0 else 0
            table.add_row("ETA", f"~{eta_seconds:.0f}s")

    if job.error:
        table.add_row("Error", f"[red]{job.error}[/red]")

    # Display in panel
    panel = Panel(
        table,
        title="[bold]Job Progress[/bold]",
        border_style="blue",
    )
    console.print(panel)
