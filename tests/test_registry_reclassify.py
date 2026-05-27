"""
Tests for reclassification schema migration in MetadataStore.

RECLASSIFY-02: reclassify_backups and reclassify_history tables.
"""

import pytest
from ingest.core.metadata import MetadataStore


def test_reclassify_backups_table_exists(tmp_path):
    """RECLASSIFY-02: reclassify_backups table created on init."""
    db_path = tmp_path / "test_registry.db"
    store = MetadataStore(db_path=db_path)
    store.connect()
    
    cursor = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reclassify_backups'"
    )
    assert cursor.fetchone() is not None, "reclassify_backups table should exist"
    
    store.close()


def test_reclassify_history_table_exists(tmp_path):
    """RECLASSIFY-02: reclassify_history table created on init."""
    db_path = tmp_path / "test_registry.db"
    store = MetadataStore(db_path=db_path)
    store.connect()
    
    cursor = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reclassify_history'"
    )
    assert cursor.fetchone() is not None, "reclassify_history table should exist"
    
    store.close()


def test_reclassify_backups_schema(tmp_path):
    """RECLASSIFY-02: reclassify_backups table has correct schema."""
    db_path = tmp_path / "test_registry.db"
    store = MetadataStore(db_path=db_path)
    store.connect()
    
    cursor = store.conn.execute("PRAGMA table_info(reclassify_backups)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    assert "session_timestamp" in columns
    assert "source_file" in columns
    assert "field_name" in columns
    assert "old_value" in columns
    assert "chunk_index" in columns
    
    store.close()


def test_reclassify_history_schema(tmp_path):
    """RECLASSIFY-02: reclassify_history table has correct schema."""
    db_path = tmp_path / "test_registry.db"
    store = MetadataStore(db_path=db_path)
    store.connect()
    
    cursor = store.conn.execute("PRAGMA table_info(reclassify_history)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    assert "id" in columns
    assert "timestamp" in columns
    assert "source_file" in columns
    assert "field_name" in columns
    assert "old_value" in columns
    assert "new_value" in columns
    assert "session_timestamp" in columns
    
    store.close()


def test_reclassify_history_indexes(tmp_path):
    """RECLASSIFY-02: reclassify_history has session and timestamp indexes."""
    db_path = tmp_path / "test_registry.db"
    store = MetadataStore(db_path=db_path)
    store.connect()
    
    cursor = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='reclassify_history'"
    )
    indexes = [row[0] for row in cursor.fetchall()]
    
    assert "idx_reclassify_history_session" in indexes
    assert "idx_reclassify_history_timestamp" in indexes
    
    store.close()
