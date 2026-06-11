"""CollectionRouter — resolves and ensures Qdrant collections for MCP tool calls."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import CollectionManager

log = logging.getLogger(__name__)


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
        log.info("CollectionRouter initialized: default='%s'", default_collection)

    async def resolve(self, collection: str | None) -> str:
        """Return the effective collection name, raising if it is missing."""
        name = collection if collection is not None else self.default
        if not await self.manager.collection_exists(name):
            log.warning("Collection '%s' does not exist", name)
            raise CollectionNotFoundError(
                f"Collection '{name}' does not exist. "
                "Use list_collections to see available collections."
            )
        log.debug("Resolved collection: '%s'", name)
        return name

    async def ensure(self, collection: str | None) -> str:
        """Return the effective collection name, creating it if necessary."""
        name = collection if collection is not None else self.default
        await self.manager.create_collection(name)  # no-op if already exists
        log.info("Ensured collection: '%s'", name)
        return name

    async def resolve_multi(self, kb_ids: list[str] | None) -> list[str]:
        """Resolve multiple KB identifiers to collection names.

        Each ``kb_id`` is expected to correspond to a Qdrant collection
        name (matching the ``kb_<id>`` naming convention from Phase 27).
        Collections are validated to exist; missing ones raise
        ``CollectionNotFoundError`` with the first failure.

        Args:
            kb_ids: List of KB identifiers, or ``None`` for single-KB mode.

        Returns:
            List of resolved collection names.

        Raises:
            CollectionNotFoundError: If any kb_id maps to a non-existent
                collection.
        """
        if kb_ids is None:
            return [self.default]
        if not kb_ids:
            return []

        names: list[str] = []
        for kb_id in kb_ids:
            name = kb_id if kb_id is not None else self.default
            if not await self.manager.collection_exists(name):
                log.warning(
                    "Collection for kb_id '%s' does not exist", name
                )
                raise CollectionNotFoundError(
                    f"Knowledge base '{name}' does not exist. "
                    "Use list_collections to see available collections."
                )
            names.append(name)
        log.debug("Resolved %d KB IDs to collections", len(names))
        return names
