"""
Staging helpers that materialize remote connector content into local files.

The staging layer bridges the gap between connector-fetched remote documents
and the existing ingest parser pipeline. It writes remote content to
temporary files under a staging directory so that the existing
``process_file`` and parser flow can consume them without modification.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from ingest.connectors.models import RemoteDocument

log = logging.getLogger("kb-ingest.connectors.staging")

# Default staging directory under system temp
_STAGING_ROOT_ENV = "KB_CONNECTOR_STAGING_DIR"


def get_staging_root() -> Path:
    """Get the staging root directory for connector temp files.

    Uses ``KB_CONNECTOR_STAGING_DIR`` env var if set, otherwise
    creates a dedicated directory under the system temp directory.

    Returns:
        Path to the staging root.
    """
    env_dir = os.getenv(_STAGING_ROOT_ENV)
    if env_dir:
        path = Path(env_dir)
    else:
        path = Path(tempfile.gettempdir()) / "kb-rag-connectors"
    path.mkdir(parents=True, exist_ok=True)
    return path


def stage_document(
    doc: RemoteDocument,
    staging_root: Optional[Path] = None,
) -> Path:
    """Write a remote document's content to a staged local file.

    The file path encodes the connector type, source key, and remote ID
    for traceability. Content is written as UTF-8 text with a ``.md``
    extension by default (suitable for the existing text parser).

    Args:
        doc: The remote document to stage.
        staging_root: Override staging root directory. Uses
            :func:`get_staging_root` if not provided.

    Returns:
        Path to the staged local file.
    """
    root = staging_root or get_staging_root()
    safe_source = _safe_path_component(doc.source_key)
    safe_remote = _safe_path_component(doc.remote_id)
    filename = f"{doc.connector_type}__{safe_source}__{safe_remote}.md"
    file_path = root / filename

    # Add remote metadata as a frontmatter-like header
    header_lines = [
        f"source_key: {doc.source_key}",
        f"remote_id: {doc.remote_id}",
        f"connector_type: {doc.connector_type}",
        f"title: {doc.title}",
    ]
    if doc.remote_url:
        header_lines.append(f"remote_url: {doc.remote_url}")
    if doc.remote_etag:
        header_lines.append(f"remote_etag: {doc.remote_etag}")
    if doc.remote_mtime is not None:
        header_lines.append(f"remote_mtime: {doc.remote_mtime}")
    if doc.metadata:
        for k, v in doc.metadata.items():
            header_lines.append(f"meta_{k}: {v}")

    header = "\n".join(header_lines)
    content = f"{header}\n\n---\n\n{doc.content}"

    file_path.write_text(content, encoding="utf-8")
    log.debug("Staged document: %s -> %s", doc.remote_id, file_path)
    return file_path


def stage_documents(
    documents: list[RemoteDocument],
    staging_root: Optional[Path] = None,
) -> list[Path]:
    """Stage multiple remote documents into local files.

    Args:
        documents: List of remote documents to stage.
        staging_root: Override staging root directory.

    Returns:
        List of paths to staged local files.
    """
    return [stage_document(d, staging_root) for d in documents]


def cleanup_stale_staging(
    staging_root: Optional[Path] = None,
    max_age_hours: int = 24,
) -> int:
    """Remove staged files older than ``max_age_hours``.

    Args:
        staging_root: Staging root directory. Uses
            :func:`get_staging_root` if not provided.
        max_age_hours: Maximum age in hours before a staged file is
            considered stale.

    Returns:
        Number of files removed.
    """
    root = staging_root or get_staging_root()
    if not root.exists():
        return 0

    import time

    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0

    for f in root.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1

    if removed:
        log.info("Cleaned up %d stale staged files from %s", removed, root)
    return removed


def resolve_staged_metadata(staged_path: Path) -> dict:
    """Parse the metadata header from a staged file.

    Reads the leading metadata lines (before the ``---`` separator)
    and returns them as a dict.

    Args:
        staged_path: Path to a staged file.

    Returns:
        Dict of metadata key-value pairs.
    """
    metadata: dict[str, str] = {}
    try:
        text = staged_path.read_text(encoding="utf-8")
        lines = text.split("\n")
        for line in lines:
            if line.strip() == "---":
                break
            if ":" in line:
                key, _, value = line.partition(":")
                metadata[key.strip()] = value.strip()
    except Exception:
        log.warning("Could not parse metadata from %s", staged_path)
    return metadata


def _safe_path_component(name: str) -> str:
    """Sanitize a string for use as a filesystem path component.

    Replaces non-alphanumeric characters (except ``-`` and ``_``)
    with underscores.

    Args:
        name: Raw string to sanitize.

    Returns:
        Sanitized string safe for filenames.
    """
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
