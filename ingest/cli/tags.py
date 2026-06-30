"""
CLI commands for document tag management.

Provides list, update, remove, reingest, and delete-tag subcommands
for bulk tag editing and document lifecycle management.
"""

import asyncio
import json
import logging
import os
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ingest.core.metadata import IngestRegistry
from kb_server.vector_store import VectorStore

log = logging.getLogger("kb-ingest")
console = Console()

# ── Tag validation (D-03, D-11) ─────────────────────────────────────

MAX_TAG_LENGTH = 50
MAX_TAGS_PER_DOC = 20


def _validate_tags(tags: list[str]) -> list[str]:
    """Validate and normalize tag strings.

    Rules:
    - Max 50 characters
    - No whitespace
    - Case-insensitive (stored lowercase)
    - Max 20 tags per document

    Args:
        tags: Raw tag strings from CLI.

    Returns:
        Normalized list of valid tags.

    Raises:
        click.BadParameter: If any tag is invalid.
    """
    normalized = []
    for tag in tags:
        tag = tag.strip().lower()
        if not tag:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise click.BadParameter(
                f"Tag '{tag}' exceeds {MAX_TAG_LENGTH} character limit"
            )
        if any(c.isspace() for c in tag):
            raise click.BadParameter(
                f"Tag '{tag}' contains whitespace (not allowed)"
            )
        normalized.append(tag)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for tag in normalized:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)

    if len(deduped) > MAX_TAGS_PER_DOC:
        raise click.BadParameter(
            f"Too many tags ({len(deduped)}). Maximum is {MAX_TAGS_PER_DOC}"
        )

    return deduped


# ── Filter parsing ──────────────────────────────────────────────────


def _parse_filter_expr(filter_expr: str | None) -> dict[str, str]:
    """Parse a filter expression like 'product=MyApp' into a dict.

    Supports: key=value, key="value with spaces"
    """
    if not filter_expr:
        return {}
    result = {}
    for part in filter_expr.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            result[key] = value
    return result


@click.group(name="tags")
def tags_group() -> None:
    """Manage document tags for classification correction."""
    pass


# ── list ─────────────────────────────────────────────────────────────


@tags_group.command(name="list")
@click.option("--product", type=str, default=None, help="Filter by product")
@click.option(
    "--type", "doc_type", type=str, default=None, help="Filter by doc type"
)
@click.option("--vendor", type=str, default=None, help="Filter by vendor")
def list_tags(
    product: Optional[str],
    doc_type: Optional[str],
    vendor: Optional[str],
) -> None:
    """List tag counts across documents."""
    asyncio.run(_list_tags_impl(product, doc_type, vendor))


async def _list_tags_impl(
    product: Optional[str],
    doc_type: Optional[str],
    vendor: Optional[str],
) -> None:
    """Async implementation of list tags."""
    with IngestRegistry() as store:

        # Build query
        conditions = []
        params = []
        if product:
            conditions.append("product = ?")
            params.append(product)
        if doc_type:
            conditions.append("doc_type = ?")
            params.append(doc_type)
        if vendor:
            conditions.append("vendor = ?")
            params.append(vendor)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Get all files with their tags
        query = (
            f"SELECT path, tags, product, doc_type FROM files {where_clause}"
        )
        rows = store._conn.execute(query, params).fetchall()

        if not rows:
            console.print(
                "[yellow]No documents found matching filters.[/yellow]"
            )
            return

        # Aggregate tag counts
        tag_counts: dict[str, int] = {}
        tag_products: dict[str, set[str]] = {}
        tag_types: dict[str, set[str]] = {}

        for row in rows:
            tags = json.loads(row[1]) if row[1] else []
            file_product = row[2] or "N/A"
            file_type = row[3] or "N/A"
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                tag_products.setdefault(tag, set()).add(file_product)
                tag_types.setdefault(tag, set()).add(file_type)

        if not tag_counts:
            console.print(
                "[yellow]No tags found on matching documents.[/yellow]"
            )
            return

        # Display table
        table = Table(title="Document Tags")
        table.add_column("Tag", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Products", style="dim")
        table.add_column("Types", style="dim")

        for tag in sorted(tag_counts.keys()):
            table.add_row(
                tag,
                str(tag_counts[tag]),
                ", ".join(sorted(tag_products[tag]))[:30],
                ", ".join(sorted(tag_types[tag]))[:30],
            )

        console.print(table)
        console.print(f"[dim]Total documents: {len(rows)}[/dim]")


# ── update ───────────────────────────────────────────────────────────


@tags_group.command(name="update")
@click.option(
    "--add",
    "add_tags",
    type=str,
    default=None,
    help="Comma-separated tags to add",
)
@click.option(
    "--remove",
    "remove_tags",
    type=str,
    default=None,
    help="Comma-separated tags to remove",
)
@click.option(
    "--replace",
    "replace_tags",
    type=str,
    default=None,
    help="Comma-separated tags to replace all existing",
)
@click.option(
    "--filter",
    "filter_expr",
    type=str,
    default=None,
    help="Filter documents (e.g., 'product=MyApp,type=doc')",
)
@click.option(
    "--collection",
    type=str,
    default=None,
    help="Target Qdrant collection",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def update_tags(
    add_tags: Optional[str],
    remove_tags: Optional[str],
    replace_tags: Optional[str],
    filter_expr: Optional[str],
    collection: Optional[str],
    dry_run: bool,
    yes: bool,
) -> None:
    """Update tags on documents matching a filter."""
    asyncio.run(
        _update_tags_impl(
            add_tags,
            remove_tags,
            replace_tags,
            filter_expr,
            collection,
            dry_run,
            yes,
        )
    )


async def _update_tags_impl(
    add_tags_str: Optional[str],
    remove_tags_str: Optional[str],
    replace_tags_str: Optional[str],
    filter_expr: Optional[str],
    collection: Optional[str],
    dry_run: bool,
    yes: bool,
) -> None:
    """Async implementation of update tags."""
    # Parse tags
    add_list = (
        _validate_tags(
            [t.strip() for t in (add_tags_str or "").split(",") if t.strip()]
        )
        if add_tags_str
        else []
    )
    remove_list = (
        _validate_tags(
            [
                t.strip()
                for t in (remove_tags_str or "").split(",")
                if t.strip()
            ]
        )
        if remove_tags_str
        else []
    )
    replace_list = (
        _validate_tags(
            [
                t.strip()
                for t in (replace_tags_str or "").split(",")
                if t.strip()
            ]
        )
        if replace_tags_str
        else []
    )

    if not add_list and not remove_list and not replace_list:
        console.print(
            "[red]Error: No tags specified. Use --add, --remove, or --replace.[/red]"
        )
        raise click.ClickException("No tags specified")

    # Parse filter
    metadata_filter = _parse_filter_expr(filter_expr)

    # Resolve collection
    store = VectorStore()
    await store.connect()
    assert store.client is not None

    from kb_server.collections.manager import CollectionManager
    from kb_server.collections.router import CollectionRouter

    manager = CollectionManager(store.client, vector_size=store.dim)
    router = CollectionRouter(
        manager,
        default_collection=store.collection
        or os.getenv("QDRANT_COLLECTION", "kb_docs"),
    )
    resolved_collection = await router.resolve(collection)

    # Find matching documents
    with IngestRegistry() as registry:
        files = registry.list_all()
        matched = []
        for f in files:
            match = True
            for key, value in metadata_filter.items():
                if f.get(key) != value:
                    match = False
                    break
            if match:
                matched.append(f)

        if not matched:
            console.print("[yellow]No documents match the filter.[/yellow]")
            return

        # Preview
        action_str = []
        if add_list:
            action_str.append(f"add [{', '.join(add_list)}]")
        if remove_list:
            action_str.append(f"remove [{', '.join(remove_list)}]")
        if replace_list:
            action_str.append(f"replace with [{', '.join(replace_list)}]")

        console.print(
            f"[bold]Will {'preview' if dry_run else 'apply'}: {' + '.join(action_str)}[/bold]"
        )
        console.print(f"[bold]Affected documents: {len(matched)}[/bold]")
        for f in matched[:5]:
            current_tags = json.loads(f.get("tags", "[]"))
            console.print(f"  - {f['path']} (tags: {current_tags})")
        if len(matched) > 5:
            console.print(f"  ... and {len(matched) - 5} more")

        if dry_run:
            console.print("[cyan]Dry run — no changes made.[/cyan]")
            return

        # Confirm
        if not yes:
            response = console.input(
                "\n[bold yellow]Apply these changes? [y/N]:[/bold yellow] "
            )
            if response.lower() != "y":
                console.print("[red]Aborted.[/red]")
                return

        # Apply changes (best-effort per D-09)
        success_count = 0
        error_count = 0
        errors = []

        for f in matched:
            try:
                current_tags = json.loads(f.get("tags", "[]"))

                if replace_list:
                    new_tags = replace_list
                else:
                    new_tags = list(current_tags)
                    for tag in add_list:
                        if tag not in new_tags:
                            new_tags.append(tag)
                    for tag in remove_list:
                        if tag in new_tags:
                            new_tags.remove(tag)

                # Validate max tags
                if len(new_tags) > MAX_TAGS_PER_DOC:
                    raise ValueError(
                        f"Max {MAX_TAGS_PER_DOC} tags allowed (got {len(new_tags)})"
                    )

                # Update Qdrant
                await store.update_tags(
                    resolved_collection, f["path"], new_tags
                )

                # Update registry
                registry.update_file_tags(f["path"], new_tags)

                # Audit log
                registry.log_tag_history(
                    user_id=None,
                    source_file=f["path"],
                    action="update",
                    tag_values=new_tags,
                )

                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"{f['path']}: {e}")
                log.error(f"Failed to update tags for {f['path']}: {e}")

        # Summary
        if error_count == 0:
            console.print(
                f"[bold green]✓ Updated tags on {success_count} documents[/bold green]"
            )
        else:
            console.print(
                f"[bold yellow]✓ {success_count} updated, {error_count} failed[/bold yellow]"
            )
            for err in errors[:10]:
                console.print(f"  [red]✗ {err}[/red]")
            if len(errors) > 10:
                console.print(f"  ... and {len(errors) - 10} more errors")


# ── remove ───────────────────────────────────────────────────────────


@tags_group.command(name="remove")
@click.option(
    "--filter",
    "filter_expr",
    type=str,
    required=True,
    help="Filter documents to remove (e.g., 'product=BadProduct')",
)
@click.option(
    "--collection",
    type=str,
    default=None,
    help="Target Qdrant collection",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview deletions without applying",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def remove_documents(
    filter_expr: str,
    collection: Optional[str],
    dry_run: bool,
    yes: bool,
) -> None:
    """Remove documents from registry and Qdrant by filter."""
    asyncio.run(_remove_documents_impl(filter_expr, collection, dry_run, yes))


async def _remove_documents_impl(
    filter_expr: str,
    collection: Optional[str],
    dry_run: bool,
    yes: bool,
) -> None:
    """Async implementation of remove documents."""
    metadata_filter = _parse_filter_expr(filter_expr)
    if not metadata_filter:
        console.print("[red]Error: --filter is required.[/red]")
        raise click.ClickException("--filter required")

    # Resolve collection
    store = VectorStore()
    await store.connect()
    assert store.client is not None

    from kb_server.collections.manager import CollectionManager
    from kb_server.collections.router import CollectionRouter

    manager = CollectionManager(store.client, vector_size=store.dim)
    router = CollectionRouter(
        manager,
        default_collection=store.collection
        or os.getenv("QDRANT_COLLECTION", "kb_docs"),
    )
    resolved_collection = await router.resolve(collection)

    # Find matching documents
    with IngestRegistry() as registry:
        files = registry.list_all()
        matched = []
        for f in files:
            match = True
            for key, value in metadata_filter.items():
                if f.get(key) != value:
                    match = False
                    break
            if match:
                matched.append(f)

        if not matched:
            console.print("[yellow]No documents match the filter.[/yellow]")
            return

        console.print(
            f"[bold red]Will {'preview' if dry_run else 'delete'} {len(matched)} documents[/bold red]"
        )
        for f in matched[:5]:
            console.print(f"  - {f['path']}")
        if len(matched) > 5:
            console.print(f"  ... and {len(matched) - 5} more")

        if dry_run:
            console.print("[cyan]Dry run — no changes made.[/cyan]")
            return

        # Confirm
        if not yes:
            response = console.input(
                "\n[bold red]Delete these documents? [y/N]:[/bold red] "
            )
            if response.lower() != "y":
                console.print("[red]Aborted.[/red]")
                return

        # Delete (best-effort)
        success_count = 0
        error_count = 0

        for f in matched:
            try:
                # Delete from Qdrant
                await store.delete_document(f["path"])

                # Delete from registry
                registry.mark_deleted(f["path"])

                success_count += 1
            except Exception as e:
                error_count += 1
                log.error(f"Failed to delete {f['path']}: {e}")

        if error_count == 0:
            console.print(
                f"[bold green]✓ Deleted {success_count} documents[/bold green]"
            )
        else:
            console.print(
                f"[bold yellow]✓ {success_count} deleted, {error_count} failed[/bold yellow]"
            )


# ── reingest ─────────────────────────────────────────────────────────


@tags_group.command(name="reingest")
@click.option(
    "--filter",
    "filter_expr",
    type=str,
    required=True,
    help="Filter documents to re-ingest (e.g., 'product=MyApp')",
)
@click.option(
    "--collection",
    type=str,
    default=None,
    help="Target Qdrant collection",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview re-ingest without applying",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def reingest_documents(
    filter_expr: str,
    collection: Optional[str],
    dry_run: bool,
    yes: bool,
) -> None:
    """Queue documents for re-ingestion."""
    asyncio.run(
        _reingest_documents_impl(filter_expr, collection, dry_run, yes)
    )


async def _reingest_documents_impl(
    filter_expr: str,
    collection: Optional[str],
    dry_run: bool,
    yes: bool,
) -> None:
    """Async implementation of re-ingest."""
    metadata_filter = _parse_filter_expr(filter_expr)
    if not metadata_filter:
        console.print("[red]Error: --filter is required.[/red]")
        raise click.ClickException("--filter required")

    # Resolve collection
    store = VectorStore()
    await store.connect()
    assert store.client is not None

    from kb_server.collections.manager import CollectionManager
    from kb_server.collections.router import CollectionRouter

    manager = CollectionManager(store.client, vector_size=store.dim)
    router = CollectionRouter(
        manager,
        default_collection=store.collection
        or os.getenv("QDRANT_COLLECTION", "kb_docs"),
    )
    resolved_collection = await router.resolve(collection)

    # Find matching documents
    with IngestRegistry() as registry:
        files = registry.list_all()
        matched = []
        for f in files:
            match = True
            for key, value in metadata_filter.items():
                if f.get(key) != value:
                    match = False
                    break
            if match:
                matched.append(f)

        if not matched:
            console.print("[yellow]No documents match the filter.[/yellow]")
            return

        console.print(
            f"[bold]Will {'preview' if dry_run else 'queue'} re-ingest for {len(matched)} documents[/bold]"
        )
        for f in matched[:5]:
            console.print(f"  - {f['path']}")
        if len(matched) > 5:
            console.print(f"  ... and {len(matched) - 5} more")

        if dry_run:
            console.print("[cyan]Dry run — no changes made.[/cyan]")
            return

        # Confirm
        if not yes:
            response = console.input(
                "\n[bold yellow]Queue these documents for re-ingest? [y/N]:[/bold yellow] "
            )
            if response.lower() != "y":
                console.print("[red]Aborted.[/red]")
                return

        # Queue re-ingest (best-effort)
        success_count = 0
        error_count = 0

        for f in matched:
            try:
                # Delete Qdrant chunks
                await store.delete_document(f["path"])

                # Mark as pending in registry
                registry._conn.execute(
                    "UPDATE files SET status = 'pending' WHERE path = ?",
                    (f["path"],),
                )
                registry._conn.commit()

                success_count += 1
            except Exception as e:
                error_count += 1
                log.error(f"Failed to queue re-ingest for {f['path']}: {e}")

        if error_count == 0:
            console.print(
                f"[bold green]✓ Queued {success_count} documents for re-ingest[/bold green]"
            )
        else:
            console.print(
                f"[bold yellow]✓ {success_count} queued, {error_count} failed[/bold yellow]"
            )


# ── delete-tag ───────────────────────────────────────────────────────


@tags_group.command(name="delete-tag")
@click.argument("tag_name", type=str)
@click.option(
    "--collection",
    type=str,
    default=None,
    help="Target Qdrant collection",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview deletions without applying",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def delete_tag(
    tag_name: str,
    collection: Optional[str],
    dry_run: bool,
    yes: bool,
) -> None:
    """Delete a tag from ALL documents (cascade)."""
    asyncio.run(_delete_tag_impl(tag_name, collection, dry_run, yes))


async def _delete_tag_impl(
    tag_name: str,
    collection: Optional[str],
    dry_run: bool,
    yes: bool,
) -> None:
    """Async implementation of delete-tag (cascade per D-13)."""
    tag_name = tag_name.strip().lower()
    if not tag_name:
        console.print("[red]Error: Tag name cannot be empty.[/red]")
        raise click.ClickException("Empty tag name")

    # Resolve collection
    store = VectorStore()
    await store.connect()
    assert store.client is not None

    from kb_server.collections.manager import CollectionManager
    from kb_server.collections.router import CollectionRouter

    manager = CollectionManager(store.client, vector_size=store.dim)
    router = CollectionRouter(
        manager,
        default_collection=store.collection
        or os.getenv("QDRANT_COLLECTION", "kb_docs"),
    )
    resolved_collection = await router.resolve(collection)

    # Find documents with this tag
    with IngestRegistry() as registry:
        files = registry.list_all()
        matched = []
        for f in files:
            tags = json.loads(f.get("tags", "[]"))
            if tag_name in tags:
                matched.append(f)

        if not matched:
            console.print(
                f"[yellow]No documents have the tag '{tag_name}'.[/yellow]"
            )
            return

        console.print(
            f"[bold red]Will {'preview' if dry_run else 'remove'} tag '{tag_name}' from {len(matched)} documents[/bold red]"
        )
        for f in matched[:5]:
            console.print(f"  - {f['path']}")
        if len(matched) > 5:
            console.print(f"  ... and {len(matched) - 5} more")

        if dry_run:
            console.print("[cyan]Dry run — no changes made.[/cyan]")
            return

        # Confirm
        if not yes:
            response = console.input(
                f"\n[bold red]Remove tag '{tag_name}' from all documents? [y/N]:[/bold red] "
            )
            if response.lower() != "y":
                console.print("[red]Aborted.[/red]")
                return

        # Remove tag from all documents (best-effort)
        success_count = 0
        error_count = 0

        for f in matched:
            try:
                current_tags = json.loads(f.get("tags", "[]"))
                new_tags = [t for t in current_tags if t != tag_name]

                # Update Qdrant
                await store.update_tags(
                    resolved_collection, f["path"], new_tags
                )

                # Update registry
                registry.update_file_tags(f["path"], new_tags)

                # Audit log
                registry.log_tag_history(
                    user_id=None,
                    source_file=f["path"],
                    action="delete-tag",
                    tag_values=[tag_name],
                )

                success_count += 1
            except Exception as e:
                error_count += 1
                log.error(f"Failed to remove tag from {f['path']}: {e}")

        if error_count == 0:
            console.print(
                f"[bold green]✓ Removed '{tag_name}' from {success_count} documents[/bold green]"
            )
        else:
            console.print(
                f"[bold yellow]✓ {success_count} updated, {error_count} failed[/bold yellow]"
            )
