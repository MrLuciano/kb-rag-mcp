"""Config package — database-backed configuration loader."""

from kb_server.config.loader import ConfigLoader
from kb_server.config.router import router

config = ConfigLoader()

__all__ = ["ConfigLoader", "router", "config"]
