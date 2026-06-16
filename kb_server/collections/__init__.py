"""Multi-collection support for KB-RAG-MCP."""

from .manager import CollectionManager
from .router import CollectionNotFoundError, CollectionRouter

__all__ = ["CollectionManager", "CollectionRouter", "CollectionNotFoundError"]
