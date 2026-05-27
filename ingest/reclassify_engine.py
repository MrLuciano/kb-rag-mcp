"""
Reclassification engine for updating document metadata.

Detects changed classifications, backs up old metadata, updates Qdrant,
and logs changes for audit and rollback.

Phase 16: Core reclassification capability.
"""

import asyncio
import glob
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from ingest.classifier import classify
from ingest.core.metadata import MetadataStore
from kb_server.vector_store import VectorStore
from qdrant_client.models import FieldCondition, Filter, MatchValue

log = logging.getLogger("kb-ingest.reclassify")


# Environment config
import os

RECLASSIFY_BACKUP_RETENTION_DAYS = int(
    os.getenv("RECLASSIFY_BACKUP_RETENTION_DAYS", "30")
)


async def detect_changed_classifications(
    collection_name: str,
    pattern: str,
    metadata_filter: Optional[dict[str, str]] = None,
    allow_missing: bool = False,
) -> list[dict[str, Any]]:
    """
    Detect documents where current Qdrant metadata differs from classify() output.

    Compares classification fields (vendor, product, subsystem, doc_type, version)
    between Qdrant payload and what classify() would return today. Only returns
    documents with at least one field difference.

    Args:
        collection_name: Qdrant collection to query.
        pattern: File glob pattern (e.g., 'docs/**/*.pdf').
        metadata_filter: Optional dict of field->value filters to apply.
        allow_missing: If True, process docs even if source file missing on disk.

    Returns:
        List of dicts with keys:
            - source_file: str (file path)
            - fields_changed: dict[field_name, (old_value, new_value)]
            - chunk_count: int (number of chunks for this document)

    Raises:
        RuntimeError: If VectorStore connection fails.
    """
    log.info(
        f"Detecting changed classifications: pattern={pattern}, "
        f"collection={collection_name}"
    )

    store = VectorStore()
    await store.connect()

    # Build Qdrant filter
    conditions = []
    if metadata_filter:
        for field, value in metadata_filter.items():
            conditions.append(
                FieldCondition(key=field, match=MatchValue(value=value))
            )

    query_filter = Filter(must=conditions) if conditions else None

    # Scroll through collection to get all matching documents
    offset = None
    docs_metadata: dict[str, dict] = {}

    while True:
        points, offset = await store.client.scroll(
            collection_name=collection_name,
            scroll_filter=query_filter,
            limit=1000,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        for point in points:
            source_file = point.payload.get("source_file", "")
            if not source_file:
                continue

            # Aggregate metadata per document (use first chunk's metadata)
            if source_file not in docs_metadata:
                docs_metadata[source_file] = {
                    "vendor": point.payload.get("vendor", ""),
                    "product": point.payload.get("product", ""),
                    "subsystem": point.payload.get("subsystem", ""),
                    "doc_type": point.payload.get("doc_type", "document"),
                    "version": point.payload.get("version", ""),
                    "chunk_count": 0,
                }
            docs_metadata[source_file]["chunk_count"] += 1

        if offset is None:
            break

    log.info(f"Found {len(docs_metadata)} documents in Qdrant")

    # Filter by glob pattern
    matched_files = set(glob.glob(pattern, recursive=True))
    log.info(f"Pattern '{pattern}' matched {len(matched_files)} files on disk")

    # Detect changes
    changes = []

    for source_file, current_meta in docs_metadata.items():
        # Check if file exists on disk
        file_path = Path(source_file)
        if not file_path.exists():
            if allow_missing:
                log.warning(
                    f"File missing but allow_missing=True: {source_file}"
                )
                # For missing files with allow_missing, we can't re-run classify()
                # so we skip them (could be enhanced to use metadata-only logic)
                continue
            else:
                log.warning(f"Skipping missing file: {source_file}")
                continue

        # Check if file matches glob pattern
        if source_file not in matched_files:
            # File in Qdrant but doesn't match current pattern
            continue

        # Run classify() to get expected metadata
        try:
            expected_meta = classify(source_file)
        except Exception as e:
            log.error(f"classify() failed for {source_file}: {e}")
            continue

        # Compare classification fields
        fields_changed = {}
        for field in ["vendor", "product", "subsystem", "doc_type", "version"]:
            old_value = current_meta.get(field, "")
            new_value = expected_meta.get(field, "")
            if old_value != new_value:
                fields_changed[field] = (old_value, new_value)

        # Only include documents with changes
        if fields_changed:
            changes.append(
                {
                    "source_file": source_file,
                    "fields_changed": fields_changed,
                    "chunk_count": current_meta["chunk_count"],
                }
            )

    log.info(f"Detected {len(changes)} documents with classification changes")
    return changes


def backup_metadata(
    session_timestamp: str, changes: list[dict[str, Any]]
) -> None:
    """
    Write old metadata to reclassify_backups table before Qdrant update.

    Creates backup records for rollback capability. Each changed field
    for each document gets a backup entry.

    Args:
        session_timestamp: ISO timestamp for this reclassification session
            (format: YYYY-MM-DDTHH-MM-SS for filesystem-safe names).
        changes: List of change dicts from detect_changed_classifications().

    Raises:
        sqlite3.Error: If database write fails.
    """
    if not changes:
        log.info("No changes to backup")
        return

    log.info(f"Backing up metadata for {len(changes)} documents")

    with MetadataStore() as store:
        # Batch insert for performance
        backup_records = []
        for change in changes:
            source_file = change["source_file"]
            for field_name, (old_value, new_value) in change[
                "fields_changed"
            ].items():
                # One backup record per field per document
                backup_records.append(
                    (
                        session_timestamp,
                        source_file,
                        field_name,
                        old_value,
                        0,  # chunk_index (0 for document-level metadata)
                    )
                )

        # Insert all backups
        store.conn.executemany(
            """
            INSERT INTO reclassify_backups
            (session_timestamp, source_file, field_name, old_value, chunk_index)
            VALUES (?, ?, ?, ?, ?)
            """,
            backup_records,
        )
        store.conn.commit()

    log.info(f"Backed up {len(backup_records)} field changes")


def log_changes(session_timestamp: str, changes: list[dict[str, Any]]) -> None:
    """
    Write metadata changes to reclassify_history audit table.

    Creates audit trail of all changes for compliance and analysis.

    Args:
        session_timestamp: ISO timestamp for this reclassification session.
        changes: List of change dicts from detect_changed_classifications().

    Raises:
        sqlite3.Error: If database write fails.
    """
    if not changes:
        log.info("No changes to log")
        return

    log.info(f"Logging {len(changes)} document changes to audit history")

    timestamp = datetime.utcnow().isoformat()

    with MetadataStore() as store:
        # Batch insert for performance
        history_records = []
        for change in changes:
            source_file = change["source_file"]
            for field_name, (old_value, new_value) in change[
                "fields_changed"
            ].items():
                history_records.append(
                    (
                        timestamp,
                        source_file,
                        field_name,
                        old_value,
                        new_value,
                        session_timestamp,
                    )
                )

        # Insert all history entries
        store.conn.executemany(
            """
            INSERT INTO reclassify_history
            (timestamp, source_file, field_name, old_value, new_value, session_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            history_records,
        )
        store.conn.commit()

    log.info(f"Logged {len(history_records)} field changes to audit history")


def cleanup_old_backups(retention_days: int | None = None) -> int:
    """
    Delete backup sessions older than retention_days.

    Auto-cleanup runs on each reclassification to prevent unbounded
    backup growth. Configurable via RECLASSIFY_BACKUP_RETENTION_DAYS
    environment variable (default 30 days).

    Args:
        retention_days: Days to keep backups (default from env var).

    Returns:
        Number of backup records deleted.

    Raises:
        sqlite3.Error: If database operation fails.
    """
    if retention_days is None:
        retention_days = RECLASSIFY_BACKUP_RETENTION_DAYS

    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_str = cutoff_date.isoformat()[:10]  # YYYY-MM-DD prefix

    log.info(
        f"Cleaning up backups older than {retention_days} days "
        f"(before {cutoff_str})"
    )

    with MetadataStore() as store:
        # Count before deletion
        cursor = store.conn.execute(
            """
            SELECT COUNT(*)
            FROM reclassify_backups
            WHERE session_timestamp < ?
            """,
            (cutoff_str,),
        )
        count_before = cursor.fetchone()[0]

        if count_before == 0:
            log.info("No old backups to clean up")
            return 0

        # Delete old backups
        store.conn.execute(
            """
            DELETE FROM reclassify_backups
            WHERE session_timestamp < ?
            """,
            (cutoff_str,),
        )

        # Delete corresponding history entries (cascade should handle this,
        # but explicit delete for safety)
        store.conn.execute(
            """
            DELETE FROM reclassify_history
            WHERE session_timestamp < ?
            """,
            (cutoff_str,),
        )

        store.conn.commit()

    log.info(f"Cleaned up {count_before} old backup records")
    return count_before
