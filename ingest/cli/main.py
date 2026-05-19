"""
KB-RAG CLI - Main entry point.

Modern Click-based CLI with job management commands.
"""

import sys
from pathlib import Path

import click

# Load .env before any imports that need env vars
_project_root = Path(__file__).parent.parent.parent
from config.bootstrap_env import bootstrap_env
bootstrap_env()

# Add server/ to path for imports
sys.path.insert(0, str(_project_root / "server"))

# Import subcommands after path setup (noqa to ignore E402)
from ingest.cli.db import db_group  # noqa: E402
from ingest.cli.job import job_group  # noqa: E402
from ingest.cli.progress import progress_group  # noqa: E402


@click.group()
@click.version_option(version="0.10.0-dev", prog_name="kb-rag")
@click.option(
    "--db",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    default=None,
    help="Path to metadata database (default: kb_metadata.db)",
)
@click.pass_context
def cli(ctx: click.Context, db: Path | None) -> None:
    """
    KB-RAG - Knowledge Base RAG system with job management.

    Use 'kb-rag COMMAND --help' for command-specific help.
    """
    # Store db path in context for subcommands
    ctx.ensure_object(dict)
    if db is None:
        db = _project_root / "kb_metadata.db"
    ctx.obj["db_path"] = db


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show system information and configuration."""
    from ingest.core.metadata import MetadataStore

    db_path = ctx.obj["db_path"]
    click.echo("KB-RAG System Information")
    click.echo("=" * 50)
    click.echo(f"Version: 2.0.0")
    click.echo(f"Database: {db_path}")
    click.echo(f"Exists: {db_path.exists()}")

    if db_path.exists():
        # MetadataStore expects Path, not str
        with MetadataStore(db_path) as store:
            stats = store.get_stats()
            click.echo(f"\nDatabase Statistics:")
            click.echo(f"  Total jobs: {stats.get('total_jobs', 0)}")
            click.echo(f"  Active jobs: {stats.get('active_jobs', 0)}")
            click.echo(f"  Total files: {stats.get('total_files', 0)}")


# Register subcommands
cli.add_command(db_group)
cli.add_command(job_group)
cli.add_command(progress_group)


if __name__ == "__main__":
    cli()
