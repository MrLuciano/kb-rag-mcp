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
    log.info(f"Reclassifying: pattern={pattern}, collection={collection}")
    
    # Resolve collection
    from kb_server.collections.router import CollectionRouter
    router = CollectionRouter()
    resolved_collection = await router.resolve(collection)
    
    # Step 1: Detect changed classifications
    console.print(f"[bold cyan]Scanning documents matching: {pattern}[/bold cyan]")
    
    # Parse metadata filter
    metadata_filter = _parse_filter_expr(filter_expr) if filter_expr else None
    
    changes = await detect_changed_classifications(
        collection_name=resolved_collection,
        pattern=pattern,
        metadata_filter=metadata_filter,
        allow_missing=allow_missing
    )
    
    if not changes:
        console.print("[green]✓ No classification changes detected.[/green]")
        return
    
    # Step 2: Show aggregated preview
    console.print(f"\n[bold]Found {len(changes)} documents with classification changes:[/bold]\n")
    _show_aggregated_preview(changes)
    
    # Step 3: Confirm (unless --yes)
    if not yes:
        response = console.input("\n[bold yellow]Apply these changes? [y/N]:[/bold yellow] ")
        if response.lower() != "y":
            console.print("[red]Aborted.[/red]")
            return
    
    # Step 4: Backup old metadata
    session_timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    console.print(f"\n[cyan]Backing up metadata (session: {session_timestamp})...[/cyan]")
    backup_metadata(session_timestamp, changes)
    
    # Step 5: Update Qdrant with progress bar
    await _apply_updates(
        resolved_collection, changes, include_custom, no_progress
    )
    
    # Step 6: Log changes to audit table
    log_changes(session_timestamp, changes)
    
    # Step 7: Cleanup old backups
    cleanup_old_backups()
    
    # Summary
    total_chunks = sum(c["chunk_count"] for c in changes)
    console.print(f"\n[bold green]✓ Updated {len(changes)} documents ({total_chunks} chunks)[/bold green]")
    console.print(f"[dim]Session: {session_timestamp}[/dim]")


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
    log.info(f"Verifying: pattern={pattern}, collection={collection}")
    
    # Resolve collection
    from kb_server.collections.router import CollectionRouter
    router = CollectionRouter()
    resolved_collection = await router.resolve(collection)
    
    console.print(f"[bold cyan]Verifying documents matching: {pattern}[/bold cyan]")
    
    # Parse metadata filter
    metadata_filter = _parse_filter_expr(filter_expr) if filter_expr else None
    
    # Detect mismatches
    changes = await detect_changed_classifications(
        collection_name=resolved_collection,
        pattern=pattern,
        metadata_filter=metadata_filter,
        allow_missing=False  # verify requires files on disk
    )
    
    if not changes:
        console.print("[green]✓ All documents match expected classifications.[/green]")
        return
    
    # Show mismatches
    console.print(f"\n[bold yellow]Found {len(changes)} documents with mismatches:[/bold yellow]\n")
    
    # Detailed table (not aggregated — show per-document for verify)
    table = Table(title="Metadata Mismatches")
    table.add_column("Source File", style="cyan")
    table.add_column("Field", style="magenta")
    table.add_column("Current", style="red")
    table.add_column("Expected", style="green")
    
    for change in changes:
        source_file = change["source_file"]
        for field_name, (current_val, expected_val) in change["fields_changed"].items():
            table.add_row(
                source_file,
                field_name,
                f"'{current_val}'" if current_val else "(empty)",
                f"'{expected_val}'" if expected_val else "(empty)"
            )
    
    console.print(table)
    
    # Hint
    console.print(
        f"\n[dim]Tip: Run 'kb-ingest reclassify run \"{pattern}\"' to apply these changes.[/dim]"
    )


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
    with MetadataStore() as store:
        # Query distinct sessions with stats
        cursor = store.conn.execute(
            """
            SELECT 
                session_timestamp,
                COUNT(DISTINCT source_file) as doc_count,
                COUNT(*) as field_count
            FROM reclassify_backups
            GROUP BY session_timestamp
            ORDER BY session_timestamp DESC
            """
        )
        sessions = cursor.fetchall()
    
    if not sessions:
        console.print("[yellow]No backup sessions found.[/yellow]")
        return
    
    # Build Rich table
    table = Table(title="Reclassification Backup Sessions")
    table.add_column("Session", style="cyan")
    table.add_column("Documents", justify="right", style="magenta")
    table.add_column("Fields Changed", justify="right", style="yellow")
    table.add_column("Date", style="dim")
    
    for row in sessions:
        session = row[0]
        doc_count = row[1]
        field_count = row[2]
        
        # Parse timestamp for human-readable date
        dt = datetime.strptime(session, "%Y-%m-%dT%H-%M-%S")
        date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        table.add_row(session, str(doc_count), str(field_count), date_str)
    
    console.print(table)
    console.print(
        f"\n[dim]Tip: Rollback a session with 'kb-ingest reclassify rollback --session <timestamp>'[/dim]"
    )


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
    # Validate arguments
    if session and (pattern or before):
        console.print("[red]Error: --session cannot be combined with pattern or --before[/red]")
        raise SystemExit(1)
    
    if not session and not (pattern and before):
        console.print("[red]Error: Either --session or (pattern + --before) required[/red]")
        raise SystemExit(1)
    
    with MetadataStore() as store:
        # Mode 1: Session-based rollback
        if session:
            # Query backups for session
            cursor = store.conn.execute(
                "SELECT source_file, field_name, old_value, chunk_index FROM reclassify_backups WHERE session_timestamp=?",
                (session,)
            )
            backups = cursor.fetchall()
            
            if not backups:
                console.print(f"[red]Error: Session not found: {session}[/red]")
                raise SystemExit(1)
            
            # Show preview
            doc_count = len(set(b[0] for b in backups))
            console.print(f"\n[bold]Session: {session}[/bold]")
            console.print(f"Documents: {doc_count}")
            console.print(f"Fields to restore: {len(backups)}")
            
            if not yes:
                response = console.input("\n[bold yellow]Restore this session? [y/N]:[/bold yellow] ")
                if response.lower() != "y":
                    console.print("[red]Aborted.[/red]")
                    return
            
            # Apply rollback
            await _apply_rollback(backups)
            
            # Log rollback to audit
            timestamp = datetime.now().isoformat()
            for backup in backups:
                store.conn.execute(
                    """
                    INSERT INTO reclassify_history 
                    (timestamp, source_file, field_name, old_value, new_value, session_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        backup[0],  # source_file
                        backup[1],  # field_name
                        backup[2],  # old_value (now being restored as new_value)
                        "(rollback)",  # marker
                        f"rollback-{session}"
                    )
                )
            store.conn.commit()
            
            console.print(f"[bold green]✓ Rolled back {doc_count} documents[/bold green]")
        
        # Mode 2: Selective rollback (pattern + --before)
        else:
            # Query backups matching pattern before timestamp
            # For now, simplified version using session_timestamp filter
            cursor = store.conn.execute(
                "SELECT source_file, field_name, old_value, chunk_index FROM reclassify_backups WHERE session_timestamp < ?",
                (before,)
            )
            all_backups = cursor.fetchall()
            
            if not all_backups:
                console.print(f"[yellow]No backups found before {before}[/yellow]")
                return
            
            # Filter by pattern (simple glob match)
            import fnmatch
            backups = [b for b in all_backups if fnmatch.fnmatch(b[0], pattern)]
            
            if not backups:
                console.print(f"[yellow]No backups found matching pattern '{pattern}' before {before}[/yellow]")
                return
            
            # Show preview
            doc_count = len(set(b[0] for b in backups))
            console.print(f"\n[bold]Selective Rollback[/bold]")
            console.print(f"Pattern: {pattern}")
            console.print(f"Before: {before}")
            console.print(f"Documents: {doc_count}")
            console.print(f"Fields to restore: {len(backups)}")
            
            if not yes:
                response = console.input("\n[bold yellow]Restore these documents? [y/N]:[/bold yellow] ")
                if response.lower() != "y":
                    console.print("[red]Aborted.[/red]")
                    return
            
            # Apply rollback
            await _apply_rollback(backups)
            
            # Log rollback to audit
            timestamp = datetime.now().isoformat()
            for backup in backups:
                store.conn.execute(
                    """
                    INSERT INTO reclassify_history 
                    (timestamp, source_file, field_name, old_value, new_value, session_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        backup[0],  # source_file
                        backup[1],  # field_name
                        backup[2],  # old_value
                        "(selective-rollback)",  # marker
                        f"selective-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}"
                    )
                )
            store.conn.commit()
            
            console.print(f"[bold green]✓ Rolled back {doc_count} documents[/bold green]")


async def _apply_rollback(backups: list[tuple]) -> None:
    """Apply rollback by restoring old metadata to Qdrant."""
    store = VectorStore()
    await store.connect()
    
    # Group by source_file
    by_file = {}
    for source_file, field_name, old_value, chunk_index in backups:
        if source_file not in by_file:
            by_file[source_file] = {}
        by_file[source_file][field_name] = old_value
    
    # Update each file
    from os import getenv
    default_collection = getenv("QDRANT_COLLECTION", "kb-default")
    
    for source_file, updates in by_file.items():
        await store.update_chunk_metadata(
            collection_name=default_collection,
            source_file=source_file,
            metadata_updates=updates
        )


def _parse_filter_expr(filter_expr: str) -> dict[str, str]:
    """
    Parse filter expression like 'vendor=""' into dict.
    
    Supports simple syntax: field="value" or field=value or field='value'
    """
    import re
    
    # Match: field="value" or field='value' or field=value
    match = re.match(r'(\w+)=(\"[^\"]*\"|\'[^\']*\'|[^\s]+)', filter_expr.strip())
    if not match:
        raise ValueError(f"Invalid filter expression: {filter_expr}")
    
    field = match.group(1)
    value = match.group(2)
    
    # Remove quotes if present
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    elif value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
    
    return {field: value}


def _show_aggregated_preview(changes: list[dict]) -> None:
    """Show aggregated summary by field using Rich table."""
    # Group changes by field
    field_stats = {}  # field_name -> {(old, new): count}
    
    for change in changes:
        for field_name, (old_val, new_val) in change["fields_changed"].items():
            if field_name not in field_stats:
                field_stats[field_name] = {}
            key = (old_val, new_val)
            field_stats[field_name][key] = field_stats[field_name].get(key, 0) + 1
    
    # Build Rich table
    table = Table(title="Classification Changes")
    table.add_column("Field", style="cyan")
    table.add_column("Documents", justify="right", style="magenta")
    table.add_column("Change", style="yellow")
    
    for field_name, transitions in field_stats.items():
        for (old_val, new_val), count in transitions.items():
            old_display = f"'{old_val}'" if old_val else "(empty)"
            new_display = f"'{new_val}'" if new_val else "(empty)"
            table.add_row(
                field_name,
                str(count),
                f"{old_display} → {new_display}"
            )
    
    console.print(table)


async def _apply_updates(
    collection: str,
    changes: list[dict],
    include_custom: bool,
    no_progress: bool
) -> None:
    """Apply metadata updates to Qdrant with progress bar."""
    store = VectorStore()
    await store.connect()
    
    if no_progress:
        # No progress bar — just iterate
        for change in changes:
            updates = change["fields_changed"]
            # Convert (old, new) tuples to {field: new_value}
            update_payload = {k: v[1] for k, v in updates.items()}
            
            await store.update_chunk_metadata(
                collection_name=collection,
                source_file=change["source_file"],
                metadata_updates=update_payload
            )
    else:
        # Rich progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Updating {len(changes)} documents...",
                total=len(changes)
            )
            
            for change in changes:
                updates = change["fields_changed"]
                update_payload = {k: v[1] for k, v in updates.items()}
                
                await store.update_chunk_metadata(
                    collection_name=collection,
                    source_file=change["source_file"],
                    metadata_updates=update_payload
                )
                
                progress.advance(task)
