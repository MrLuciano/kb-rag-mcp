"""
Status monitoring commands for KB-RAG CLI.
"""

import sys
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ingest.core.metadata import IngestRegistry

console = Console()


@click.group(name="status")
def status_group() -> None:
    """Show ingest status and statistics."""
    pass


@status_group.command()
@click.option(
    "--source",
    type=str,
    default=None,
    help="Filter by source directory",
)
@click.pass_context
def status(ctx: click.Context, source: str | None) -> None:
    """
    Show ingest status per source directory.

    Displays a table with per-source file counts, chunk counts, error
    counts, and last ingestion timestamp.  Use ``--source`` to filter
    by a specific source directory.
    """
    db_path = ctx.obj["db_path"]

    try:
        with IngestRegistry(db_path) as reg:
            rows = reg.per_source_summary()
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)

    # Filter by source if requested (case-insensitive partial match)
    if source:
        source_lower = source.lower()
        rows = [
            r for r in rows if source_lower in r["source"].lower()
        ]

    if not rows:
        console.print("No ingest data found.")
        return

    # Build table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Source")
    table.add_column("Files", justify="right")
    table.add_column("Chunks", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Last Ingest")

    total_files = 0
    total_chunks = 0
    total_errors = 0

    for r in rows:
        last_ts = r.get("last_indexed")
        if last_ts is not None:
            last_str = datetime.fromtimestamp(last_ts).strftime(
                "%Y-%m-%d %H:%M"
            )
        else:
            last_str = "\u2014"

        total_files += r["files"]
        total_chunks += r["chunks"]
        total_errors += r["errors"]

        table.add_row(
            r["source"],
            str(r["files"]),
            str(r["chunks"]),
            str(r["errors"]),
            last_str,
        )

    # Total row
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_files}[/bold]",
        f"[bold]{total_chunks}[/bold]",
        f"[bold]{total_errors}[/bold]",
        "",
        style="dim",
    )

    panel = Panel(
        table,
        title="[bold]Ingest Status[/bold]",
        border_style="green",
    )
    console.print(panel)
