import sqlite3
import tempfile
from pathlib import Path
import pytest
from server.analytics.query_analyzer import QueryAnalyzer


@pytest.fixture
def temp_query_db():
    """Temporary database with sample query logs."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create query_log table
    cursor.execute("""
        CREATE TABLE query_log (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            query_text TEXT NOT NULL,
            result_count INTEGER,
            max_score REAL,
            latency_ms REAL
        )
    """)
    
    # Insert sample queries
    cursor.executemany("""
        INSERT INTO query_log (
            timestamp, query_text, result_count, max_score, latency_ms
        ) VALUES (?, ?, ?, ?, ?)
    """, [
        ('2024-01-01T10:00:00', 'How to install?', 5, 0.95, 45.0),
        ('2024-01-01T10:05:00', 'How to install?', 5, 0.94, 43.0),
        ('2024-01-01T10:10:00', 'SSL configuration', 3, 0.88, 50.0),
        ('2024-01-01T10:15:00', 'API documentation', 0, 0.0, 35.0),
        ('2024-01-01T10:20:00', 'upgrade guide', 4, 0.72, 48.0),
    ])
    
    conn.commit()
    conn.close()
    
    yield db_path
    db_path.unlink(missing_ok=True)


def test_load_queries(temp_query_db):
    """Test loading queries from database."""
    analyzer = QueryAnalyzer(db_path=temp_query_db)
    queries = analyzer.load_queries()
    
    assert len(queries) == 5
    # Queries are ordered by timestamp DESC
    assert queries[0]['query_text'] == 'upgrade guide'
    assert queries[0]['result_count'] == 4


def test_most_common_queries(temp_query_db):
    """Test identifying most common queries."""
    analyzer = QueryAnalyzer(db_path=temp_query_db)
    common = analyzer.get_most_common_queries(limit=3)
    
    assert len(common) == 1
    assert common[0]['query_text'] == 'How to install?'
    assert common[0]['frequency'] == 2


def test_low_score_queries(temp_query_db):
    """Test identifying low-score queries."""
    analyzer = QueryAnalyzer(db_path=temp_query_db)
    low_scores = analyzer.get_low_score_queries(threshold=0.75)
    
    assert len(low_scores) == 1
    assert all(q['max_score'] < 0.75 for q in low_scores)
    assert low_scores[0]['query_text'] == 'upgrade guide'


def test_zero_result_queries(temp_query_db):
    """Test identifying zero-result queries."""
    analyzer = QueryAnalyzer(db_path=temp_query_db)
    zero_results = analyzer.get_zero_result_queries()
    
    assert len(zero_results) == 1
    assert zero_results[0]['query_text'] == 'API documentation'
    assert zero_results[0]['frequency'] == 1



