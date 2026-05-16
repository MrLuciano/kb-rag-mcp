#!/usr/bin/env python3
"""
Create Qdrant payload indexes for fast filtered queries.

This migration creates keyword indexes on the 'product' and 'doc_type'
fields to accelerate filtered searches from O(n) to O(log n).

FASE 12: Search Quality Enhancement - Payload Indexing

Usage:
    python scripts/migrations/create_payload_indexes.py [--dry-run]
    
    --dry-run: Check what would be created without making changes
    --collection: Specify collection name (default: from QDRANT_COLLECTION)
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PayloadSchemaType

# Load .env
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("kb-mcp.migration")

# Config
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_PATH = os.getenv("QDRANT_PATH", "")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "kb_docs")

# Fields to index
INDEXED_FIELDS = ["product", "doc_type"]


async def get_client() -> AsyncQdrantClient:
    """Create Qdrant client."""
    if QDRANT_PATH:
        log.info(f"Connecting to embedded Qdrant: {QDRANT_PATH}")
        return AsyncQdrantClient(path=QDRANT_PATH)
    else:
        log.info(f"Connecting to Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
        return AsyncQdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


async def check_existing_indexes(
    client: AsyncQdrantClient, collection: str
) -> dict[str, bool]:
    """
    Check which payload indexes already exist.
    
    Returns dict mapping field name to bool (True if indexed).
    """
    log.info(f"Checking existing indexes in collection: {collection}")
    
    try:
        collection_info = await client.get_collection(collection)
    except Exception as e:
        log.error(f"Failed to get collection info: {e}")
        return {}
    
    # Check payload schema for existing indexes
    existing_indexes = {}
    payload_schema = collection_info.config.params.payload_schema or {}
    
    for field in INDEXED_FIELDS:
        # Field is indexed if it appears in payload_schema
        is_indexed = field in payload_schema
        existing_indexes[field] = is_indexed
        
        if is_indexed:
            log.info(f"  ✓ Index exists on '{field}'")
        else:
            log.info(f"  ✗ No index on '{field}'")
    
    return existing_indexes


async def create_index(
    client: AsyncQdrantClient,
    collection: str,
    field: str,
    dry_run: bool = False,
) -> bool:
    """
    Create payload index on specified field.
    
    Returns True if created, False if skipped (already exists or dry-run).
    """
    if dry_run:
        log.info(f"[DRY-RUN] Would create index on '{field}'")
        return False
    
    try:
        log.info(f"Creating index on '{field}'...")
        
        await client.create_payload_index(
            collection_name=collection,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD,
            wait=True,  # Wait for index creation to complete
        )
        
        log.info(f"  ✓ Index created on '{field}'")
        return True
        
    except Exception as e:
        log.error(f"  ✗ Failed to create index on '{field}': {e}")
        return False


async def get_collection_stats(
    client: AsyncQdrantClient, collection: str
) -> dict:
    """Get collection statistics."""
    try:
        collection_info = await client.get_collection(collection)
        return {
            "points_count": collection_info.points_count,
            "vectors_count": collection_info.vectors_count,
            "status": collection_info.status,
        }
    except Exception as e:
        log.error(f"Failed to get collection stats: {e}")
        return {}


async def main(
    collection: str | None = None, dry_run: bool = False
) -> int:
    """
    Main migration logic.
    
    Returns 0 on success, 1 on error.
    """
    collection = collection or COLLECTION_NAME
    
    log.info("=" * 60)
    log.info("Qdrant Payload Index Migration")
    log.info("=" * 60)
    log.info(f"Collection: {collection}")
    log.info(f"Fields to index: {', '.join(INDEXED_FIELDS)}")
    log.info(f"Dry-run: {dry_run}")
    log.info("")
    
    # Connect to Qdrant
    client = await get_client()
    
    # Check if collection exists
    try:
        collections = await client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if collection not in collection_names:
            log.error(f"Collection '{collection}' does not exist")
            log.info(f"Available collections: {', '.join(collection_names)}")
            return 1
    except Exception as e:
        log.error(f"Failed to list collections: {e}")
        return 1
    
    # Get collection stats
    stats = await get_collection_stats(client, collection)
    if stats:
        log.info(f"Collection stats:")
        log.info(f"  Points: {stats.get('points_count', 'unknown')}")
        log.info(f"  Status: {stats.get('status', 'unknown')}")
        log.info("")
    
    # Check existing indexes
    existing = await check_existing_indexes(client, collection)
    log.info("")
    
    # Determine which indexes to create
    to_create = [
        field for field in INDEXED_FIELDS if not existing.get(field, False)
    ]
    
    if not to_create:
        log.info("✓ All indexes already exist. Nothing to do.")
        return 0
    
    log.info(f"Indexes to create: {', '.join(to_create)}")
    log.info("")
    
    # Create indexes
    created_count = 0
    for field in to_create:
        if await create_index(client, collection, field, dry_run):
            created_count += 1
    
    # Summary
    log.info("")
    log.info("=" * 60)
    if dry_run:
        log.info(
            f"[DRY-RUN] Would create {len(to_create)} index(es)"
        )
    else:
        log.info(f"✓ Created {created_count}/{len(to_create)} index(es)")
        
        if created_count < len(to_create):
            log.warning(
                f"  {len(to_create) - created_count} index(es) "
                f"failed to create"
            )
            return 1
    
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create Qdrant payload indexes for fast filtered queries"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check what would be created without making changes",
    )
    parser.add_argument(
        "--collection",
        type=str,
        help=(
            "Collection name (default: from QDRANT_COLLECTION env var)"
        ),
    )
    
    args = parser.parse_args()
    
    exit_code = asyncio.run(
        main(collection=args.collection, dry_run=args.dry_run)
    )
    sys.exit(exit_code)
