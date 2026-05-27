"""
Utility helpers for ingest pipelines.

PHASE 17: Provides write_filter_cache_bust() for cache-bust marker
management used by FilterTermsCache in the MCP server.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("kb-ingest")


def write_filter_cache_bust(path: Path | str | None = None) -> None:
    """Write a cache-bust marker to trigger FilterTermsCache refresh.

    PHASE 17: Called after successful ingest or reclassify runs.
    The MCP server's FilterTermsCache checks this file's mtime on
    each list_tools() call to decide if re-indexing is needed.

    Args:
        path: Path to marker file. Defaults to data/.filter_cache_bust.
    """
    marker_path = Path(path) if path else Path("data/.filter_cache_bust")
    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(
            f"{datetime.now(timezone.utc).isoformat()}\n"
        )
        log.info(f"Filter cache-bust marker written: {marker_path}")
    except OSError as e:
        log.warning(f"Failed to write cache-bust marker: {e}")
