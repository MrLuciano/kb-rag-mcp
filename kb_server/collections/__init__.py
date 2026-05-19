"""Multi-collection support for KB-RAG-MCP."""

from .manager import CollectionManager
from .router import CollectionRouter, CollectionNotFoundError

__all__ = ["CollectionManager", "CollectionRouter", "CollectionNotFoundError"]
