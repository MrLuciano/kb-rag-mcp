"""Cache subsystem for embedding vectors and search results."""

from kb_server.cache.lru import LRUCache
from kb_server.cache.manager import CacheManager

try:
    from kb_server.cache.redis import RedisCache  # noqa: F401

    __all__ = ["LRUCache", "CacheManager", "RedisCache"]
except ImportError:
    __all__ = ["LRUCache", "CacheManager"]
