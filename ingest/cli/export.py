"""Registry export functionality for observability."""
import json
import csv
import sqlite3
from pathlib import Path
from typing import Optional, TextIO, List, Dict, Any


def export_registry_json(
    db_path: Path,
    output: TextIO,
    product: Optional[str] = None,
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    version: Optional[str] = None
) -> int:
    """
    Export registry to JSON format.
    
    Args:
        db_path: Path to metadata database
        output: Output file or stream
        product: Filter by product
        doc_type: Filter by document type
        status: Filter by status (completed, failed, pending)
        version: Filter by version
        
    Returns:
        Number of records exported
    """
    records = _query_registry(
        db_path, product, doc_type, status, version
    )
    json.dump(records, output, indent=2)
    return len(records)


def export_registry_csv(
    db_path: Path,
    output: TextIO,
    product: Optional[str] = None,
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    version: Optional[str] = None
) -> int:
    """
    Export registry to CSV format.
    
    Args:
        db_path: Path to metadata database
        output: Output file or stream
        product: Filter by product
        doc_type: Filter by document type
        status: Filter by status
        version: Filter by version
        
    Returns:
        Number of records exported
    """
    records = _query_registry(
        db_path, product, doc_type, status, version
    )
    
    if not records:
        return 0
    
    # Use first record to get field names
    fieldnames = list(records[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
    
    return len(records)


def _query_registry(
    db_path: Path,
    product: Optional[str],
    doc_type: Optional[str],
    status: Optional[str],
    version: Optional[str]
) -> List[Dict[str, Any]]:
    """Query registry with filters."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Build query with filters
    query = "SELECT * FROM files WHERE 1=1"
    params = []
    
    if product:
        query += " AND product = ?"
        params.append(product)
    if doc_type:
        query += " AND doc_type = ?"
        params.append(doc_type)
    if status:
        query += " AND status = ?"
        params.append(status)
    # version filter omitted — files table has no version column
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Convert to list of dicts
    return [dict(row) for row in rows]
