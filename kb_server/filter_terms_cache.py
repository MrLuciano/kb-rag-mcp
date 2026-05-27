"""
Filter terms cache for MCP capability negotiation.

PHASE 17: Caches distinct filter values from Qdrant payloads and
provides formatted strings for dynamic MCP tool descriptions.

Uses a cache-bust marker file (written by ingest/reclassify pipelines)
to trigger re-scan on the next list_tools() call.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("kb-mcp")

# Fields that can be advertised via capability negotiation
ADVERTISED_FIELDS = [
    "vendor",
    "product",
    "doc_type",
    "subsystem",
    "module",
    "version",
    "filter_type",
]

STABLE_FIELDS = {"doc_type", "filter_type"}

DEFAULT_CACHE_BUST_PATH = Path("data/.filter_cache_bust")


class FilterTermsCache:
    """In-memory cache of distinct filter values from Qdrant payloads.

    Scans Qdrant on startup and re-scans when the cache-bust marker
    file's mtime changes (written by ingest/reclassify pipelines).
    """

    def __init__(
        self,
        store: Any,
        cache_bust_path: Path | None = None,
    ):
        self.store = store
        self.terms: dict[str, list[dict]] = {}
        self.last_scan_mtime: float = 0.0
        self.cache_bust_path = cache_bust_path or DEFAULT_CACHE_BUST_PATH
        self._scan_lock = asyncio.Lock()

    async def reindex(self) -> None:
        """Scan Qdrant and rebuild the terms table for all advertised fields."""
        if self.store is None:
            return

        async with self._scan_lock:
            self.terms = {}
            for field in ADVERTISED_FIELDS:
                try:
                    values = await self.store.get_distinct_values(
                        field=field,
                        with_counts=True,
                    )
                    self.terms[field] = values
                except Exception as e:
                    log.error(f"Failed to scan field '{field}': {e}")
                    self.terms[field] = []

            self.last_scan_mtime = self._get_marker_mtime()

    def _get_marker_mtime(self) -> float:
        """Get mtime of the cache-bust marker file, or 0 if absent."""
        try:
            if self.cache_bust_path.exists():
                return self.cache_bust_path.stat().st_mtime
        except OSError:
            pass
        return 0.0

    def _needs_refresh(self) -> bool:
        """Check if the cache-bust marker file changed since last scan."""
        current_mtime = self._get_marker_mtime()
        return current_mtime > self.last_scan_mtime

    async def refresh_if_needed(self) -> None:
        """Re-index if the cache-bust marker file has changed."""
        if self._needs_refresh():
            log.info("Cache-bust marker changed -- re-indexing filter terms")
            await self.reindex()

    def get_formatted(
        self,
        field: str,
        top_n: int = 20,
    ) -> str:
        """Get a compact, formatted string of top values for a field.

        Returns something like:
            "Available products: AppServer (142), DataSync (89), ... (+12 more)"

        Args:
            field: The attribute field name.
            top_n: Maximum number of values to include.

        Returns:
            Formatted string, or empty string if no values.
        """
        values = self.terms.get(field, [])
        if not values:
            return ""

        if field in STABLE_FIELDS:
            top_n = len(values)

        top_values = values[:top_n]
        remaining = len(values) - top_n

        parts = []
        field_label = field.replace("_", " ").title()
        for item in top_values:
            parts.append(f"{item['value']} ({item['count']})")

        result = ", ".join(parts)

        if remaining > 0:
            result += f" (+{remaining} more)"

        return f"Available {field_label}: {result}"

    def get_all_formatted(self, top_n: int = 20) -> dict[str, str]:
        """Get formatted descriptions for all advertised fields.

        Returns dict of {field_name: formatted_description}.
        """
        return {
            field: self.get_formatted(field, top_n)
            for field in ADVERTISED_FIELDS
        }
