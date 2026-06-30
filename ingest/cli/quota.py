"""
PHASE 34: CLI commands for upload/index quota management.

Usage:
    kb-rag quota show                  # Show current limits + usage
    kb-rag quota set --max-chunks 50000
    kb-rag quota reset                 # Zero out usage counters
"""

import time

import click

from ingest.core.metadata import MetadataStore


def _fmt(val: int | None) -> str:
    """Format a quota value: ``None`` → ``"unlimited"``."""
    return str(val) if val is not None else "unlimited"


def _human(n: int) -> str:
    """Format a count in human-readable form."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


@click.group()
def quota_group() -> None:
    """Manage upload/index quotas."""


@quota_group.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """Display current quota limits and usage."""
    db_path = ctx.obj["db_path"]
    with MetadataStore(db_path) as mds:
        quotas = mds.get_quotas()
        usage = mds.get_quota_usage()

    click.echo("Upload / Index Quotas")
    click.echo("=" * 50)
    click.echo(
        (
            f"  Max files per upload:    "
            f"{_fmt(quotas.get('max_files_per_upload'))}"
        )
    )
    click.echo(
        f"  Max bytes per upload:    "
        f"{_fmt(quotas.get('max_bytes_per_upload'))}"
    )
    click.echo(
        f"  Max bytes per file:      "
        f"{_fmt(quotas.get('max_bytes_per_file'))}"
    )
    click.echo(
        f"  Max documents per index: "
        f"{_fmt(quotas.get('max_documents_per_index'))}"
    )
    click.echo(
        f"  Max chunks per index:    "
        f"{_fmt(quotas.get('max_chunks_per_index'))}"
    )
    click.echo(
        f"  Max chars per index:     "
        f"{_fmt(quotas.get('max_chars_per_index'))}"
    )
    click.echo("")
    click.echo("Current Usage")
    click.echo("-" * 50)
    click.echo(f"  Files:      {_human(usage.get('total_files', 0))}")
    click.echo(f"  Bytes:      {_human(usage.get('total_bytes', 0))}")
    click.echo(f"  Documents:  {_human(usage.get('total_documents', 0))}")
    click.echo(f"  Chunks:     {_human(usage.get('total_chunks', 0))}")
    click.echo(f"  Chars:      {_human(usage.get('total_chars', 0))}")
    updated = usage.get("updated_at")
    if updated:
        click.echo(
            f"  Updated:    "
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated))}"
        )


@quota_group.command()
@click.option(
    "--max-files-per-upload",
    type=int,
    default=None,
    help="Max files per ingest call",
)
@click.option(
    "--max-bytes-per-upload",
    type=int,
    default=None,
    help="Max bytes per ingest call",
)
@click.option(
    "--max-bytes-per-file", type=int, default=None, help="Max bytes per file"
)
@click.option(
    "--max-documents-per-index",
    type=int,
    default=None,
    help="Max documents in KB",
)
@click.option(
    "--max-chunks-per-index", type=int, default=None, help="Max chunks in KB"
)
@click.option(
    "--max-chars-per-index", type=int, default=None, help="Max chars in KB"
)
@click.pass_context
def set(
    ctx: click.Context,
    max_files_per_upload: int | None,
    max_bytes_per_upload: int | None,
    max_bytes_per_file: int | None,
    max_documents_per_index: int | None,
    max_chunks_per_index: int | None,
    max_chars_per_index: int | None,
) -> None:
    """Configure quota limits. Omit a flag to leave it unchanged."""
    db_path = ctx.obj["db_path"]
    with MetadataStore(db_path) as mds:
        existing = mds.get_quotas()
        mds.set_quotas(
            max_files_per_upload=(
                max_files_per_upload
                if max_files_per_upload is not None
                else existing.get("max_files_per_upload")
            ),
            max_bytes_per_upload=(
                max_bytes_per_upload
                if max_bytes_per_upload is not None
                else existing.get("max_bytes_per_upload")
            ),
            max_bytes_per_file=(
                max_bytes_per_file
                if max_bytes_per_file is not None
                else existing.get("max_bytes_per_file")
            ),
            max_documents_per_index=(
                max_documents_per_index
                if max_documents_per_index is not None
                else existing.get("max_documents_per_index")
            ),
            max_chunks_per_index=(
                max_chunks_per_index
                if max_chunks_per_index is not None
                else existing.get("max_chunks_per_index")
            ),
            max_chars_per_index=(
                max_chars_per_index
                if max_chars_per_index is not None
                else existing.get("max_chars_per_index")
            ),
        )
    click.echo("Quotas updated.")


@quota_group.command()
@click.pass_context
def reset(ctx: click.Context) -> None:
    """Reset all usage counters to zero."""
    click.confirm("Reset all quota usage counters to zero?", abort=True)
    db_path = ctx.obj["db_path"]
    with MetadataStore(db_path) as mds:
        prev = mds.reset_quota_usage()
    click.echo(
        f"Usage reset. Previous: "
        f"{_human(prev.get('total_chunks', 0))} chunks, "
        f"{_human(prev.get('total_documents', 0))} documents"
    )
