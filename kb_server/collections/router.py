"""CollectionRouter — resolves and ensures Qdrant collections for MCP tool calls."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import CollectionManager


class CollectionNotFoundError(Exception):
    """Raised when a specified collection does not exist."""


class CollectionRouter:
    """Routes MCP tool calls to the correct Qdrant collection.

    - If ``collection`` is ``None``, the default collection is used.
    - ``resolve()`` raises ``CollectionNotFoundError`` if the collection does
      not exist (strict — for read paths).
    - ``ensure()`` creates the collection if it does not exist (for ingest paths).
    """

    def __init__(self, manager: "CollectionManager", default_collection: str) -> None:
        self.manager = manager
        self.default = default_collection

    async def resolve(self, collection: str | None) -> str:
        """Return the effective collection name, raising if it is missing."""
        name = collection if collection is not None else self.default
        if not await self.manager.collection_exists(name):
            raise CollectionNotFoundError(
                f"Collection '{name}' does not exist. "
                "Use list_collections to see available collections."
            )
        return name

    async def ensure(self, collection: str | None) -> str:
        """Return the effective collection name, creating it if necessary."""
        name = collection if collection is not None else self.default
        await self.manager.create_collection(name)  # no-op if already exists
        return name
