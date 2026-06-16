"""
Health check commands for KB-RAG CLI.

Provides the ``check`` command group with a ``health`` subcommand that
validates connectivity to all external dependencies (embedding service,
vector store, cache, database, filesystem).  Follows the same Click +
Rich pattern as :mod:`ingest.cli.status`.
"""

import asyncio
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group(name="check")
def check_group() -> None:
    """Check system health and connectivity."""
    pass


@check_group.command()
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed component info"
)
def health(verbose: bool) -> None:
    """
    Check all system component health.

    Validates connectivity to:
    - Embedding service (LM Studio / Ollama / OpenAI-compat)
    - Vector store (Qdrant)
    - Cache (LRU/Redis)
    - Database (SQLite)
    - Filesystem

    Exits with code 0 if all critical components are healthy,
    1 if any critical component is unhealthy.
    """
    try:
        from kb_server.health import check_all_components

        components = asyncio.run(check_all_components())
    except Exception as e:
        console.print(f"[red]✗ Error running health checks:[/red] {e}")
        sys.exit(1)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Details")
    table.add_column("Latency")

    critical_unhealthy = 0

    for name in [
        "embedding",
        "vector_store",
        "cache",
        "database",
        "filesystem",
    ]:
        status = components.get(name)
        if status is None:
            table.add_row(
                name, "[yellow]SKIP[/yellow]", "Not checked", "\u2014"
            )
            continue

        status_text = (
            "[green]Healthy[/green]"
            if status.healthy
            else "[red]Unhealthy[/red]"
        )
        latency = (
            f"{status.latency_ms:.0f}ms"
            if status.latency_ms is not None
            else "\u2014"
        )

        # Show message; if verbose, show details
        details = status.message
        if verbose and status.details:
            extra = "; ".join(f"{k}={v}" for k, v in status.details.items())
            details = f"{details} | {extra}"

        table.add_row(name, status_text, details, latency)

        if not status.healthy and name in (
            "embedding",
            "vector_store",
            "database",
        ):
            critical_unhealthy += 1

    panel = Panel(
        table,
        title="[bold]System Health[/bold]",
        border_style="green" if critical_unhealthy == 0 else "red",
    )
    console.print(panel)

    if critical_unhealthy > 0:
        console.print(
            f"[red]✗ {critical_unhealthy} critical "
            f"component(s) unhealthy[/red]"
        )
        sys.exit(1)
    else:
        console.print("[green]✓ All critical components healthy[/green]")
