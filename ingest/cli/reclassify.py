"""
CLI commands for reclassifying ingested documents.

Provides reclassify, verify, sessions, and rollback subcommands.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ingest.reclassify_engine import (
    backup_metadata,
    cleanup_old_backups,
    detect_changed_classifications,
    log_changes,
)
from ingest.core.metadata import MetadataStore
from kb_server.vector_store import VectorStore

log = logging.getLogger("kb-ingest")
console = Console()


@click.group()
def reclassify_group() -> None:
    """Reclassify ingested documents (update metadata without re-embedding)."""
    pass


@reclassify_group.command(name="run")
@click.argument("pattern", type=str)
@click.option("--collection", type=str, default=None, help="Target Qdrant collection")
@click.option("--filter", "filter_expr", type=str, default=None, help="Metadata filter (e.g., 'vendor=\"\"')")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--allow-missing", is_flag=True, help="Process documents even if source file missing")
@click.option("--include-custom", is_flag=True, help="Update custom fields beyond classification fields")
@click.option("--no-progress", is_flag=True, help="Disable progress bar (for scripting)")
def reclassify_command(
    pattern: str,
    collection: Optional[str],
    filter_expr: Optional[str],
    yes: bool,
    allow_missing: bool,
    include_custom: bool,
    no_progress: bool,
) -> None:
    """
    Reclassify documents by updating metadata in-place.
    
    Detects changed classifications, shows aggregated preview, backs up old metadata,
    updates Qdrant payloads, and logs changes for audit/rollback.
    
    Examples:
        kb-ingest reclassify run "docs/OT*.pdf"
        kb-ingest reclassify run "**/*.pdf" --filter 'vendor=""' --yes
        kb-ingest reclassify run "docs/**/*" --collection kb-custom --allow-missing
    """
    asyncio.run(_reclassify_impl(
        pattern, collection, filter_expr, yes, allow_missing, include_custom, no_progress
    ))


async def _reclassify_impl(
    pattern: str,
    collection: Optional[str],
    filter_expr: Optional[str],
    yes: bool,
    allow_missing: bool,
    include_custom: bool,
    no_progress: bool
) -> None:
    """Async implementation of reclassify command."""
    # Implementation in Step 2
    pass


@reclassify_group.command(name="verify")
@click.argument("pattern", type=str)
@click.option("--collection", type=str, default=None, help="Target Qdrant collection")
@click.option("--filter", "filter_expr", type=str, default=None, help="Metadata filter")
def verify_command(
    pattern: str,
    collection: Optional[str],
    filter_expr: Optional[str],
) -> None:
    """
    Verify current Qdrant metadata matches expected classify() output.
    
    Shows mismatches without making changes. Useful before/after reclassification.
    
    Examples:
        kb-ingest reclassify verify "docs/**/*.pdf"
        kb-ingest reclassify verify "**/*" --filter 'vendor="OpenText"'
    """
    asyncio.run(_verify_impl(pattern, collection, filter_expr))


async def _verify_impl(
    pattern: str,
    collection: Optional[str],
    filter_expr: Optional[str]
) -> None:
    """Async implementation of verify command."""
    # Implementation in Step 3
    pass


@reclassify_group.command(name="sessions")
def sessions_command() -> None:
    """
    List all reclassification backup sessions.
    
    Shows session timestamps, document counts, and date for rollback reference.
    
    Example:
        kb-ingest reclassify sessions
    """
    _sessions_impl()


def _sessions_impl() -> None:
    """Implementation of sessions command."""
    # Implementation in Step 4
    pass


@reclassify_group.command(name="rollback")
@click.argument("pattern", type=str, required=False)
@click.option("--session", type=str, default=None, help="Session timestamp to restore (full rollback)")
@click.option("--before", type=str, default=None, help="Restore to state before this timestamp (selective rollback)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def rollback_command(
    pattern: Optional[str],
    session: Optional[str],
    before: Optional[str],
    yes: bool,
) -> None:
    """
    Rollback reclassification changes by restoring metadata from backup.
    
    Two modes:
    1. Session-based: --session <timestamp> (restores entire session)
    2. Selective: <pattern> --before <timestamp> (restores specific documents)
    
    Examples:
        kb-ingest reclassify rollback --session 2026-05-26T15-30-00
        kb-ingest reclassify rollback "docs/OT*.pdf" --before 2026-05-26T16-00-00
    """
    asyncio.run(_rollback_impl(pattern, session, before, yes))


async def _rollback_impl(
    pattern: Optional[str],
    session: Optional[str],
    before: Optional[str],
    yes: bool
) -> None:
    """Async implementation of rollback command."""
    # Implementation in Step 5
    pass
