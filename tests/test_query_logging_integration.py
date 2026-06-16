"""Integration tests for query logging in MCP server."""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from kb_server.telemetry.query_logger import QueryLogger


@pytest.fixture
def temp_query_db():
    """Temporary database for query logging."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


def test_query_logger_can_be_initialized_from_env(temp_query_db, monkeypatch):
    """Test that QueryLogger can be initialized from environment."""
    monkeypatch.setenv("QUERY_LOG_PATH", str(temp_query_db))

    # Simulate getting path from env
    import os

    log_path = Path(os.getenv("QUERY_LOG_PATH", "kb_metadata.db"))

    logger = QueryLogger(db_path=log_path)

    # Log a query
    logger.log_query(
        query_text="How to install?",
        top_k=5,
        score_threshold=0.7,
        filters={"product": "TestProduct"},
        version_filter=None,
        result_count=1,
        scores=[0.95],
        latency_ms=45.3,
    )

    # Verify query was logged
    conn = sqlite3.connect(temp_query_db)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM query_log")
    count = cursor.fetchone()[0]
    assert count == 1

    cursor.execute("""
        SELECT query_text, result_count, max_score
        FROM query_log
        WHERE id = 1
    """)
    row = cursor.fetchone()
    assert row[0] == "How to install?"
    assert row[1] == 1
    assert row[2] == 0.95

    conn.close()
