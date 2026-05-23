"""Query logger for RAG observability."""
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)


class QueryLogger:
    """
    Logs search queries with results and performance metrics.
    
    Stores queries in SQLite with auto-rotation to keep last 90 days.
    """
    
    def __init__(self, db_path: Path):
        """Initialize query logger with database path."""
        self.db_path = db_path
        self._ensure_schema()
        log.info("QueryLogger initialized: db=%s", db_path)
    
    def _ensure_schema(self) -> None:
        """Create query_log table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    top_k INTEGER,
                    score_threshold REAL,
                    filters TEXT,
                    version_filter TEXT,
                    result_count INTEGER,
                    max_score REAL,
                    min_score REAL,
                    avg_score REAL,
                    latency_ms REAL
                )
            """)
    
    def log_query(
        self,
        query_text: str,
        top_k: int,
        score_threshold: Optional[float],
        filters: Optional[Dict[str, Any]],
        version_filter: Optional[str],
        result_count: int,
        scores: list[float],
        latency_ms: float
    ) -> None:
        """
        Log a search query with results and metrics.
        
        Args:
            query_text: The search query
            top_k: Number of results requested
            score_threshold: Minimum score threshold
            filters: Metadata filters applied
            version_filter: Version filter applied
            result_count: Number of results returned
            scores: List of result scores
            latency_ms: Query latency in milliseconds
        """
        # Calculate score statistics
        max_score = max(scores) if scores else None
        min_score = min(scores) if scores else None
        avg_score = sum(scores) / len(scores) if scores else None
        
        # Serialize filters to JSON
        filters_json = json.dumps(filters) if filters else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO query_log (
                    timestamp, query_text, top_k, score_threshold,
                    filters, version_filter, result_count,
                    max_score, min_score, avg_score, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                query_text,
                top_k,
                score_threshold,
                filters_json,
                version_filter,
                result_count,
                max_score,
                min_score,
                avg_score,
                latency_ms
            ))
        log.debug(
            "Query logged: text='%s...' results=%d latency=%.0fms",
            query_text[:50], result_count, latency_ms,
        )
    
    def cleanup_old_queries(self, retention_days: int = 90) -> int:
        """
        Remove queries older than retention_days.
        
        Args:
            retention_days: Number of days to retain (default 90)
            
        Returns:
            Number of queries deleted
        """
        cutoff_date = (
            datetime.utcnow() - timedelta(days=retention_days)
        ).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM query_log WHERE timestamp < ?",
                (cutoff_date,)
            )
            deleted_count = cursor.rowcount
        
        log.info("Cleaned up %d old queries (retention=%d days)", deleted_count, retention_days)
        return deleted_count
    
    def get_query_stats(self) -> Dict[str, float]:
        """
        Get aggregate statistics from query log.
        
        Returns:
            Dictionary with query statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(latency_ms) as avg_latency_ms,
                    AVG(result_count) as avg_results,
                    AVG(max_score) as avg_max_score,
                    AVG(min_score) as avg_min_score
                FROM query_log
            """)
            row = cursor.fetchone()
        
        stats = {
            'total_queries': row[0] or 0,
            'avg_latency_ms': row[1] or 0.0,
            'avg_results': row[2] or 0.0,
            'avg_max_score': row[3] or 0.0,
            'avg_min_score': row[4] or 0.0
        }
        log.debug("Query stats: %s", stats)
        return stats
