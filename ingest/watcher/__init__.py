"""
File watcher for automatic document ingestion.

Monitors filesystem for changes and triggers ingestion jobs.
"""

from ingest.watcher.file_watcher import Debouncer, DocWatcher

__all__ = ["DocWatcher", "Debouncer"]
