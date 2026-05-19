"""
Filesystem watcher for automatic document ingestion.

Monitors WATCH_PATH for file create/modify/delete events and triggers
incremental ingestion via JobManager. Uses debouncing to batch changes
within 30s window.

Features:
- Recursive directory monitoring
- Debounce: 30s window, merge multiple changes
- Ignore temp files (.tmp, .swp, .~, ~$*)
- Integration with existing job system
- Health check support

Environment Variables:
- WATCH_PATH: Directory to monitor (default: DOCS_PATH)
- WATCH_DEBOUNCE_SECONDS: Debounce window (default: 30)
- WATCH_IGNORE_PATTERNS: Comma-separated ignore patterns
- WATCH_RECURSIVE: Monitor subdirectories (default: true)

Usage:
    python -m ingest.watcher.file_watcher

    # Or via systemd:
    systemctl start kb-rag-watcher
"""

import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from threading import Timer
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

log = logging.getLogger("kb-ingest.watcher")


class Debouncer:
    """Debounce file events within a time window."""

    def __init__(self, seconds: int = 30):
        """
        Initialize debouncer.

        Args:
            seconds: Debounce window in seconds
        """
        self.seconds = seconds
        self.pending: dict[str, Timer] = {}
        self.events: dict[str, list[str]] = defaultdict(list)

    def schedule(
        self, path: str, event_type: str, callback: Callable[[str, list[str]], None]
    ):
        """
        Schedule callback after debounce window.

        Args:
            path: File path that changed
            event_type: Type of event (created, modified, deleted)
            callback: Function to call after debounce window
        """
        # Cancel existing timer for this path
        if path in self.pending:
            self.pending[path].cancel()

        # Track event
        self.events[path].append(event_type)

        # Schedule new timer
        timer = Timer(self.seconds, lambda: self._execute(path, callback))
        timer.start()
        self.pending[path] = timer

    def _execute(self, path: str, callback: Callable[[str, list[str]], None]):
        """Execute callback after debounce window."""
        events = self.events.pop(path, [])
        self.pending.pop(path, None)
        callback(path, events)

    def cancel_all(self):
        """Cancel all pending timers."""
        for timer in self.pending.values():
            timer.cancel()
        self.pending.clear()
        self.events.clear()


class DocWatcher(FileSystemEventHandler):
    """Handle filesystem events for documents."""

    # Default patterns to ignore
    IGNORE_PATTERNS = [".tmp", ".swp", ".~", "~$", ".git", "__pycache__"]

    # Supported document extensions
    SUPPORTED_EXTENSIONS = [
        ".pdf",
        ".docx",
        ".xlsx",
        ".pptx",
        ".txt",
        ".md",
    ]

    def __init__(
        self,
        job_manager,
        docs_path: Path,
        debounce_seconds: int = 30,
        ignore_patterns: list[str] | None = None,
    ):
        """
        Initialize document watcher.

        Args:
            job_manager: JobManager instance for creating jobs
            docs_path: Root path being watched (for job creation)
            debounce_seconds: Debounce window in seconds
            ignore_patterns: List of patterns to ignore
        """
        self.job_manager = job_manager
        self.docs_path = docs_path
        self.debouncer = Debouncer(debounce_seconds)
        self.ignore_patterns = (
            ignore_patterns if ignore_patterns else self.IGNORE_PATTERNS
        )
        log.info(
            f"DocWatcher initialized for {docs_path} "
            f"(debounce={debounce_seconds}s, "
            f"ignore={self.ignore_patterns})"
        )

    def should_ignore(self, path: str) -> bool:
        """
        Check if path should be ignored.

        Args:
            path: File path to check

        Returns:
            True if path should be ignored
        """
        path_obj = Path(path)

        # Ignore directories
        if path_obj.is_dir():
            return True

        # Ignore by pattern
        for pattern in self.ignore_patterns:
            if pattern in path:
                return True

        # Ignore unsupported extensions
        if path_obj.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return True

        return False

    def on_created(self, event):
        """Handle file creation."""
        if self.should_ignore(event.src_path):
            return

        log.info(f"File created: {event.src_path}")
        self.debouncer.schedule(
            event.src_path, "created", self._trigger_ingestion
        )

    def on_modified(self, event):
        """Handle file modification."""
        if self.should_ignore(event.src_path):
            return

        log.info(f"File modified: {event.src_path}")
        self.debouncer.schedule(
            event.src_path, "modified", self._trigger_ingestion
        )

    def on_deleted(self, event):
        """Handle file deletion."""
        if self.should_ignore(event.src_path):
            return

        log.info(f"File deleted: {event.src_path}")
        # TODO: Implement deletion from Qdrant (future phase)
        # For now, just log the deletion

    def _trigger_ingestion(self, path: str, events: list[str]):
        """
        Trigger ingestion job for file.

        Args:
            path: File path to ingest
            events: List of events that occurred
        """
        log.info(
            f"Triggering ingestion for {path} "
            f"(events: {', '.join(events)})"
        )

        try:
            # Create job for the parent directory
            # This ensures we use existing job system
            from ingest.job.models import JobPriority

            job = self.job_manager.create_job(
                docs_path=str(self.docs_path),
                priority=JobPriority.NORMAL,
                force=True,  # Force re-ingestion of changed files
                workers=1,  # Single worker for auto-triggered jobs
                clean=False,
                sync=False,
            )
            log.info(
                f"Job {job.job_id[:8]} created for {path} "
                f"(auto-triggered by {', '.join(events)})"
            )
        except Exception as e:
            log.error(f"Failed to create job for {path}: {e}", exc_info=True)

    def stop(self):
        """Stop the watcher and cancel pending timers."""
        log.info("Stopping watcher...")
        self.debouncer.cancel_all()


def main():
    """Run file watcher as standalone service."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load environment
    from config.bootstrap_env import bootstrap_env
    bootstrap_env()

    # Get configuration
    watch_path = os.getenv("WATCH_PATH") or os.getenv("DOCS_PATH")
    if not watch_path:
        log.error("WATCH_PATH or DOCS_PATH must be set")
        sys.exit(1)

    watch_path = Path(watch_path)
    if not watch_path.exists():
        log.error(f"Watch path does not exist: {watch_path}")
        sys.exit(1)

    debounce_seconds = int(os.getenv("WATCH_DEBOUNCE_SECONDS", "30"))
    recursive = os.getenv("WATCH_RECURSIVE", "true").lower() == "true"
    ignore_patterns_str = os.getenv("WATCH_IGNORE_PATTERNS", "")
    ignore_patterns = [p.strip() for p in ignore_patterns_str.split(",") if p.strip()]

    log.info(f"Starting file watcher on {watch_path}")
    log.info(f"Recursive: {recursive}, Debounce: {debounce_seconds}s")
    if ignore_patterns:
        log.info(f"Additional ignore patterns: {ignore_patterns}")

    # Initialize components
    from ingest.core.metadata import MetadataStore
    from ingest.job.manager import JobManager

    db_path = Path(os.getenv("KB_METADATA_DB", "kb_metadata.db"))
    store = MetadataStore(db_path)
    job_manager = JobManager(store)

    # Create handler
    handler = DocWatcher(
        job_manager,
        docs_path=watch_path,
        debounce_seconds=debounce_seconds,
        ignore_patterns=ignore_patterns or None,
    )

    # Start observer
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=recursive)
    observer.start()

    log.info(
        "File watcher started successfully. Press Ctrl+C to stop."
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping file watcher...")
        handler.stop()
        observer.stop()

    observer.join()
    store.close()
    log.info("File watcher stopped")


if __name__ == "__main__":
    main()
