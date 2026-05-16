"""Query pattern analyzer for RAG optimization."""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any


class QueryAnalyzer:
    """
    Analyzes query logs to identify patterns and optimization opportunities.
    
    Loads queries from FASE 14 query_log table and provides methods to:
    - Identify most common queries
    - Find low-score queries (quality issues)
    - Detect zero-result queries (content gaps)
    - Cluster similar queries
    """
    
    def __init__(self, db_path: Path):
        """Initialize analyzer with database path."""
        self.db_path = db_path
    
    def load_queries(self) -> List[Dict[str, Any]]:
        """
        Load all queries from query_log.
        
        Returns:
            List of query dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM query_log
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def get_most_common_queries(
        self, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently asked queries.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of {query_text, frequency} dicts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT query_text, COUNT(*) as frequency
            FROM query_log
            GROUP BY query_text
            HAVING frequency > 1
            ORDER BY frequency DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {'query_text': row[0], 'frequency': row[1]}
            for row in rows
        ]

    def get_low_score_queries(
        self, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get queries with low max scores (quality issues).
        
        Args:
            threshold: Score threshold (queries below this)
            
        Returns:
            List of query dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM query_log
            WHERE max_score < ? AND result_count > 0
            ORDER BY max_score ASC
        """, (threshold,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def get_zero_result_queries(self) -> List[Dict[str, Any]]:
        """
        Get queries that returned zero results (content gaps).
        
        Returns:
            List of query dictionaries with frequency counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT query_text, COUNT(*) as frequency
            FROM query_log
            WHERE result_count = 0
            GROUP BY query_text
            ORDER BY frequency DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {'query_text': row[0], 'frequency': row[1]}
            for row in rows
        ]



