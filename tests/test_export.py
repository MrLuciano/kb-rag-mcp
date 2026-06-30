"""Tests for registry export CLI."""

import json
import csv
import tempfile
import sqlite3
from pathlib import Path
from io import StringIO

import pytest

# Load export module via normal import (stdlib-only, no heavy deps)
from ingest.cli import export as export


@pytest.fixture
def temp_metadata_db():
    """Create temporary metadata database with sample data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create schema and insert sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            source_file TEXT NOT NULL,
            status TEXT NOT NULL,
            product TEXT,
            doc_type TEXT,
            version TEXT,
            file_type TEXT,
            chunks_stored INTEGER,
            hash TEXT
        )
    """)

    # Insert sample data
    sample_files = [
        (
            "doc1.pdf",
            "completed",
            "Product A",
            "install_guide",
            "1.0.0",
            "pdf",
            10,
            "hash1",
        ),
        (
            "doc2.pdf",
            "completed",
            "Product B",
            "api_guide",
            "2.0.0",
            "pdf",
            15,
            "hash2",
        ),
        (
            "doc3.pdf",
            "failed",
            "Product A",
            "install_guide",
            "1.0.0",
            "pdf",
            0,
            "hash3",
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO files (
            source_file, status, product, doc_type,
            version, file_type, chunks_stored, hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        sample_files,
    )

    conn.commit()
    conn.close()

    yield db_path
    db_path.unlink(missing_ok=True)


def test_export_registry_json_all_records(temp_metadata_db):
    """Test exporting all records to JSON."""
    output = StringIO()
    export.export_registry_json(
        db_path=temp_metadata_db,
        output=output,
        product=None,
        doc_type=None,
        status=None,
    )

    output.seek(0)
    data = json.load(output)

    assert len(data) == 3
    assert data[0]["source_file"] == "doc1.pdf"
    assert data[0]["product"] == "Product A"
    assert data[1]["source_file"] == "doc2.pdf"


def test_export_registry_json_filtered_by_product(temp_metadata_db):
    """Test filtering by product."""
    output = StringIO()
    export.export_registry_json(
        db_path=temp_metadata_db,
        output=output,
        product="Product A",
        doc_type=None,
        status=None,
    )

    output.seek(0)
    data = json.load(output)

    assert len(data) == 2
    assert all(r["product"] == "Product A" for r in data)


def test_export_registry_json_filtered_by_status(temp_metadata_db):
    """Test filtering by status."""
    output = StringIO()
    export.export_registry_json(
        db_path=temp_metadata_db,
        output=output,
        product=None,
        doc_type=None,
        status="completed",
    )

    output.seek(0)
    data = json.load(output)

    assert len(data) == 2
    assert all(r["status"] == "completed" for r in data)


def test_export_registry_csv(temp_metadata_db):
    """Test exporting to CSV format."""
    output = StringIO()
    export.export_registry_csv(
        db_path=temp_metadata_db,
        output=output,
        product=None,
        doc_type=None,
        status=None,
    )

    output.seek(0)
    reader = csv.DictReader(output)
    rows = list(reader)

    assert len(rows) == 3
    assert rows[0]["source_file"] == "doc1.pdf"
    assert rows[0]["product"] == "Product A"
    assert "chunks_stored" in rows[0]


def test_export_registry_csv_empty(temp_metadata_db):
    """Test CSV export with no matching records returns 0."""
    output = StringIO()
    count = export.export_registry_csv(
        db_path=temp_metadata_db,
        output=output,
        product="NonExistentProduct",
    )
    assert count == 0
    assert output.getvalue() == ""


def test_export_registry_json_filtered_by_doc_type(temp_metadata_db):
    """Test filtering by document type."""
    output = StringIO()
    export.export_registry_json(
        db_path=temp_metadata_db,
        output=output,
        doc_type="api_guide",
    )
    output.seek(0)
    data = json.load(output)
    assert len(data) == 1
    assert data[0]["doc_type"] == "api_guide"
    assert data[0]["source_file"] == "doc2.pdf"
