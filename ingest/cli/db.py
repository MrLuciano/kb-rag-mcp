"""
CLI commands for database operations.

PHASE 12: Payload indexing and database maintenance commands.
"""

import asyncio
import logging
import sys
from pathlib import Path

import click

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

log = logging.getLogger("kb-mcp.cli.db")


@click.group(name="db")
def db_group():
    """Database operations and maintenance."""
    pass


@db_group.command(name="create-indexes")
@click.option(
    "--collection",
    type=str,
    default=None,
    help="Collection name (default: from QDRANT_COLLECTION env var)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be created without making changes",
)
def create_indexes(collection: str | None, dry_run: bool):
    """
    Create payload indexes on product and doc_type fields.
    
    Indexes accelerate filtered queries from O(n) to O(log n).
    Safe to run multiple times (idempotent).
    
    Examples:
        kb-rag db create-indexes
        kb-rag db create-indexes --dry-run
        kb-rag db create-indexes --collection custom_collection
    """
    from scripts.migrations.create_payload_indexes import main
    
    exit_code = asyncio.run(main(collection=collection, dry_run=dry_run))
    sys.exit(exit_code)


if __name__ == "__main__":
    db_group()
