"""Query pattern analyzer for RAG optimization."""

import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

log = logging.getLogger(__name__)


class QueryAnalyzer:
    """
    Analyzes query logs to identify patterns and optimization opportunities.

    Loads queries from PHASE 14 query_log table and provides methods to:
    - Identify most common queries
    - Find low-score queries (quality issues)
    - Detect zero-result queries (content gaps)
    - Cluster similar queries
    """

    def __init__(self, db_path: Path):
        """Initialize analyzer with database path."""
        self.db_path = db_path
        log.info("QueryAnalyzer initialized: db=%s", db_path)

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

        log.debug("Loaded %d queries from log", len(rows))
        return [dict(row) for row in rows]

    def get_most_common_queries(
        self, limit: int = 10, time_range_days: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently asked queries.

        Args:
            limit: Maximum number of queries to return
            time_range_days: Only include queries from last N days
                (0 = no time filter)

        Returns:
            List of {query_text, frequency} dicts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if time_range_days > 0:
            from datetime import datetime, timezone, timedelta

            cutoff = (
                datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=time_range_days)
            ).isoformat()
            cursor.execute(
                """
                SELECT query_text, COUNT(*) as frequency
                FROM query_log
                WHERE timestamp >= ?
                GROUP BY query_text
                HAVING frequency > 1
                ORDER BY frequency DESC
                LIMIT ?
            """,
                (cutoff, limit),
            )
        else:
            cursor.execute(
                """
                SELECT query_text, COUNT(*) as frequency
                FROM query_log
                GROUP BY query_text
                HAVING frequency > 1
                ORDER BY frequency DESC
                LIMIT ?
            """,
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        log.debug(
            "Most common queries: %d results above threshold",
            len(rows),
        )
        return [{"query_text": row[0], "frequency": row[1]} for row in rows]

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

        cursor.execute(
            """
            SELECT * FROM query_log
            WHERE max_score < ? AND result_count > 0
            ORDER BY max_score ASC
        """,
            (threshold,),
        )

        rows = cursor.fetchall()
        conn.close()

        log.debug(
            "Low score queries (<%.1f): %d results", threshold, len(rows)
        )
        return [dict(row) for row in rows]

    def get_zero_result_queries(
        self, time_range_days: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get queries that returned zero results (content gaps).

        Args:
            time_range_days: Only include queries from last N days
                (0 = no time filter)

        Returns:
            List of query dictionaries with frequency counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if time_range_days > 0:
            from datetime import datetime, timezone, timedelta

            cutoff = (
                datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=time_range_days)
            ).isoformat()
            cursor.execute(
                """
                SELECT query_text, COUNT(*) as frequency
                FROM query_log
                WHERE timestamp >= ? AND result_count = 0
                GROUP BY query_text
                ORDER BY frequency DESC
            """,
                (cutoff,),
            )
        else:
            cursor.execute("""
                SELECT query_text, COUNT(*) as frequency
                FROM query_log
                WHERE result_count = 0
                GROUP BY query_text
                ORDER BY frequency DESC
            """)

        rows = cursor.fetchall()
        conn.close()

        log.debug("Zero-result queries: %d unique queries", len(rows))
        return [{"query_text": row[0], "frequency": row[1]} for row in rows]

    def get_latency_stats(
        self, time_range_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Compute p50/p95/p99 latency statistics.

        Args:
            time_range_days: Number of days of data to analyze.

        Returns:
            List with a single dict: ``{'operation': 'All queries',
            'count': N, 'p50_ms': float, 'p95_ms': float,
            'p99_ms': float}``.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        from datetime import datetime, timezone, timedelta

        cutoff = (
            datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=time_range_days)
        ).isoformat()
        cursor.execute(
            "SELECT latency_ms FROM query_log WHERE timestamp >= ?",
            (cutoff,),
        )
        rows = cursor.fetchall()
        conn.close()

        sorted_vals = sorted([r[0] for r in rows if r[0] is not None])
        n = len(sorted_vals)
        if n == 0:
            log.debug("No latency data for last %d days", time_range_days)
            return [
                {
                    "operation": "All queries",
                    "count": 0,
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                }
            ]

        def _p(p: int) -> float:
            idx = (n - 1) * p / 100.0
            f = int(idx)
            c = min(f + 1, n - 1)
            frac = idx - f
            return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * frac

        result = {
            "operation": "All queries",
            "count": n,
            "p50_ms": round(_p(50), 1),
            "p95_ms": round(_p(95), 1),
            "p99_ms": round(_p(99), 1),
        }
        log.debug("Latency stats (last %d days): %s", time_range_days, result)
        return [result]
