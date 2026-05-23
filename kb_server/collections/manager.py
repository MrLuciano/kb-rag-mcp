"""CollectionManager — CRUD operations for Qdrant collections."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient  # type: ignore[import]

log = logging.getLogger(__name__)

# HNSW settings — mirrors VectorStore._ensure_collection
_HNSW_M = 16
_HNSW_EF = 100
_PAYLOAD_INDEXES = ["product", "doc_type", "source"]


class CollectionManager:
    """Wraps AsyncQdrantClient with collection lifecycle helpers."""

    def __init__(self, client: "AsyncQdrantClient", vector_size: int = 1024) -> None:
        self.client = client
        self.vector_size = vector_size
        log.info("CollectionManager initialized: vector_size=%d", vector_size)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_collections(self) -> list[str]:
        """Return names of all existing collections."""
        response = await self.client.get_collections()
        names = [c.name for c in response.collections]
        log.debug("Listed %d collections", len(names))
        return names

    async def collection_exists(self, name: str) -> bool:
        """Return True if the named collection exists."""
        existing = await self.list_collections()
        exists = name in existing
        log.debug("Collection '%s' exists=%s", name, exists)
        return exists

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_collection(
        self,
        name: str,
        vector_size: int | None = None,
        vectors_config=None,
        hnsw_config=None,
    ) -> bool:
        """Create a collection if it does not exist.

        ``vectors_config`` and ``hnsw_config`` are optional; if omitted they are
        built from qdrant_client.models using ``vector_size``.

        Returns:
            True  — collection was created now.
            False — collection already existed; no action taken.
        """
        if await self.collection_exists(name):
            log.debug("Collection '%s' already exists, skipping create.", name)
            return False

        if vectors_config is None or hnsw_config is None:
            # Lazy import so tests can stub qdrant_client.models freely
            from qdrant_client.models import (  # type: ignore[import]
                Distance,
                HnswConfigDiff,
                VectorParams,
            )
            size = vector_size if vector_size is not None else self.vector_size
            if vectors_config is None:
                vectors_config = VectorParams(size=size, distance=Distance.COSINE)
            if hnsw_config is None:
                hnsw_config = HnswConfigDiff(m=_HNSW_M, ef_construct=_HNSW_EF)
        else:
            size = vector_size if vector_size is not None else self.vector_size

        await self.client.create_collection(
            collection_name=name,
            vectors_config=vectors_config,
            hnsw_config=hnsw_config,
        )
        log.info("Collection '%s' created (dim=%d).", name, size)

        # Create payload indexes to mirror existing single-collection setup
        for field in _PAYLOAD_INDEXES:
            try:
                await self.client.create_payload_index(
                    collection_name=name,
                    field_name=field,
                    field_schema="keyword",
                )
            except Exception as exc:  # pylint: disable=broad-except
                log.warning("Could not create payload index '%s' on '%s': %s", field, name, exc)

        return True

    async def delete_collection(self, name: str) -> bool:
        """Delete a collection.

        Returns:
            True  — collection was deleted.
            False — collection did not exist.
        """
        if not await self.collection_exists(name):
            log.debug("Collection '%s' does not exist, nothing to delete.", name)
            return False
        await self.client.delete_collection(collection_name=name)
        log.info("Collection '%s' deleted.", name)
        return True
