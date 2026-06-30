"""Tests for query logger."""

import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from kb_server.telemetry.query_logger import QueryLogger


@pytest.fixture
def temp_db():
    """Temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


def test_query_logger_creates_schema(temp_db):
    """Test that QueryLogger creates query_log table."""
    logger = QueryLogger(db_path=temp_db)

    # Verify table exists with correct schema
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='query_log'"
    )
    assert cursor.fetchone() is not None

    # Verify columns
    cursor.execute("PRAGMA table_info(query_log)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        "id",
        "timestamp",
        "query_text",
        "top_k",
        "score_threshold",
        "filters",
        "version_filter",
        "result_count",
        "max_score",
        "min_score",
        "avg_score",
        "latency_ms",
    }

    assert columns == expected_columns
    conn.close()


def test_log_query_stores_basic_info(temp_db):
    """Test logging a query with basic information."""
    logger = QueryLogger(db_path=temp_db)

    logger.log_query(
        query_text="How do I configure SSL?",
        top_k=5,
        score_threshold=0.7,
        filters={"product": "nginx"},
        version_filter="1.20.0",
        result_count=3,
        scores=[0.95, 0.88, 0.75],
        latency_ms=45.3,
    )

    # Verify data stored
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM query_log")
    assert cursor.fetchone()[0] == 1

    cursor.execute("""
        SELECT query_text, top_k, score_threshold, filters,
               version_filter, result_count, max_score, min_score,
               avg_score, latency_ms
        FROM query_log
        WHERE id = 1
    """)
    row = cursor.fetchone()

    assert row[0] == "How do I configure SSL?"
    assert row[1] == 5
    assert row[2] == 0.7
    assert row[3] == '{"product": "nginx"}'
    assert row[4] == "1.20.0"
    assert row[5] == 3
    assert row[6] == 0.95  # max_score
    assert row[7] == 0.75  # min_score
    assert abs(row[8] - 0.86) < 0.01  # avg_score
    assert row[9] == 45.3

    conn.close()


def test_cleanup_old_queries(temp_db):
    """Test that cleanup removes queries older than 90 days."""
    logger = QueryLogger(db_path=temp_db)

    # Insert queries with different timestamps
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Recent query (should be kept)
    recent = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    cursor.execute(
        """
        INSERT INTO query_log (
            timestamp, query_text, top_k, result_count, latency_ms
        ) VALUES (?, ?, ?, ?, ?)
    """,
        (recent, "recent query", 5, 3, 10.0),
    )

    # Old query (should be removed)
    old = (
        datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=95)
    ).isoformat()
    cursor.execute(
        """
        INSERT INTO query_log (
            timestamp, query_text, top_k, result_count, latency_ms
        ) VALUES (?, ?, ?, ?, ?)
    """,
        (old, "old query", 5, 3, 10.0),
    )

    conn.commit()
    conn.close()

    # Run cleanup
    logger.cleanup_old_queries()

    # Verify only recent query remains
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM query_log")
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT query_text FROM query_log")
    assert cursor.fetchone()[0] == "recent query"

    conn.close()


def test_get_query_stats(temp_db):
    """Test getting query statistics."""
    logger = QueryLogger(db_path=temp_db)

    # Log multiple queries
    for i in range(5):
        logger.log_query(
            query_text=f"query {i}",
            top_k=5,
            score_threshold=0.7,
            filters=None,
            version_filter=None,
            result_count=3,
            scores=[0.9, 0.8, 0.7],
            latency_ms=10.0 + i,
        )

    stats = logger.get_query_stats()

    assert stats["total_queries"] == 5
    assert stats["avg_latency_ms"] == 12.0  # (10+11+12+13+14)/5
    assert stats["avg_results"] == 3.0
    assert abs(stats["avg_max_score"] - 0.9) < 0.01
    assert abs(stats["avg_min_score"] - 0.7) < 0.01


def test_cleanup_custom_retention_days(temp_db):
    """CR-04: cleanup_old_queries respects custom retention_days parameter."""
    logger = QueryLogger(db_path=temp_db)

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Insert a query 10 days old
    ten_days_ago = (
        datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
    ).isoformat()
    cursor.execute(
        "INSERT INTO query_log (timestamp, query_text, top_k, result_count, latency_ms)"
        " VALUES (?, ?, ?, ?, ?)",
        (ten_days_ago, "old-10d", 5, 1, 5.0),
    )
    # Insert a query 3 days old
    three_days_ago = (
        datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)
    ).isoformat()
    cursor.execute(
        "INSERT INTO query_log (timestamp, query_text, top_k, result_count, latency_ms)"
        " VALUES (?, ?, ?, ?, ?)",
        (three_days_ago, "old-3d", 5, 1, 5.0),
    )
    conn.commit()
    conn.close()

    # Cleanup with 7-day retention: should remove the 10-day-old entry only
    deleted = logger.cleanup_old_queries(retention_days=7)
    assert deleted == 1

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT query_text FROM query_log")
    remaining = [r[0] for r in cursor.fetchall()]
    conn.close()

    assert remaining == ["old-3d"]


def test_log_query_no_connection_leak_on_exception(temp_db, monkeypatch):
    """WR-04: log_query must use context managers so connections close on error."""
    import sqlite3 as _sqlite3

    logger = QueryLogger(db_path=temp_db)

    original_connect = _sqlite3.connect
    connections_opened = []
    connections_closed = []

    class TrackingConnection:
        """Wraps a real sqlite3 connection and tracks close() calls."""

        def __init__(self, real_conn):
            self._real = real_conn
            connections_opened.append(self)

        def cursor(self):
            return _FailingCursor(self._real.cursor())

        def execute(self, sql, params=()):
            return _FailingCursor(self._real.cursor()).execute(sql, params)

        def commit(self):
            self._real.commit()

        def rollback(self):
            self._real.rollback()

        def close(self):
            connections_closed.append(self)
            self._real.close()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self._real.rollback()
            else:
                self._real.commit()
            self.close()
            return False

    class _FailingCursor:
        def __init__(self, real_cursor):
            self._real = real_cursor

        def execute(self, sql, params=()):
            if "INSERT" in sql:
                raise _sqlite3.OperationalError("simulated failure")
            return self._real.execute(sql, params)

        def fetchone(self):
            return self._real.fetchone()

        @property
        def rowcount(self):
            return self._real.rowcount

    def patched_connect(path, **kwargs):
        return TrackingConnection(original_connect(path, **kwargs))

    monkeypatch.setattr(
        "kb_server.telemetry.query_logger.sqlite3.connect", patched_connect
    )

    with pytest.raises(_sqlite3.OperationalError):
        logger.log_query(
            query_text="test",
            top_k=5,
            score_threshold=None,
            filters=None,
            version_filter=None,
            result_count=0,
            scores=[],
            latency_ms=1.0,
        )

    # Connection opened during log_query must have been closed (via context manager)
    assert len(connections_opened) >= 1
    assert len(connections_closed) == len(
        connections_opened
    ), "Connection was opened but not closed — connection leak detected"
