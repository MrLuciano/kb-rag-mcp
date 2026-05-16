"""
Metadata storage with schema v2 for job management.

Manages SQLite schema for jobs, job_progress, and files tables.
Provides migration from v1 registry.db to v2 kb_metadata.db.
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

log = logging.getLogger("kb-ingest.metadata")

DEFAULT_DB = Path(__file__).parent.parent.parent / "data" / "kb_metadata.db"
SCHEMA_VERSION = 2


class MetadataStore:
    """
    SQLite-backed metadata store for job management and file tracking.

    Schema v2 includes:
    - schema_version: Track schema migrations
    - jobs: Job queue and lifecycle
    - job_progress: Per-file progress tracking within jobs
    - files: File registry (migrated from v1)
    """

    def __init__(self, db_path: Optional[Path] = None):
        resolved_db_path: Path
        if db_path is not None:
            resolved_db_path = db_path
        else:
            meta_env = os.getenv("METADATA_DB")
            resolved_db_path = (
                Path(meta_env) if meta_env is not None else DEFAULT_DB
            )
        self.db_path = resolved_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    # ── Connection Management

    def connect(self) -> None:
        """Open database connection and initialize schema."""
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow multi-threaded access
            timeout=30.0,  # Wait up to 30s for locks
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        self._conn.execute("PRAGMA synchronous=NORMAL")  # Performance
        self._migrate()
        log.info(f"MetadataStore: {self.db_path} (schema v{SCHEMA_VERSION})")

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get active connection, raising if not connected."""
        if self._conn is None:
            raise RuntimeError("Database not connected")
        return self._conn

    # ── Schema Management

    def _migrate(self) -> None:
        """Initialize or migrate database schema."""
        current_version = self._get_schema_version()

        if current_version == 0:
            self._create_schema_v2()
        elif current_version == 1:
            self._migrate_v1_to_v2()
        elif current_version == SCHEMA_VERSION:
            log.debug(f"Schema v{current_version} up to date")
        else:
            raise ValueError(f"Unknown schema version {current_version}")

    def _get_schema_version(self) -> int:
        """Get current schema version from database."""
        try:
            row = self.conn.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()
            return int(row[0]) if row else 0
        except sqlite3.OperationalError:
            # Table doesn't exist
            return 0

    def _set_schema_version(self, version: int) -> None:
        """Update schema version in database."""
        self.conn.execute("DELETE FROM schema_version")
        self.conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)", (version,)
        )
        self.conn.commit()
        log.info(f"Schema version updated to v{version}")

    def _create_schema_v2(self) -> None:
        """Create fresh schema v2."""
        log.info("Creating schema v2...")

        self.conn.executescript("""
            -- Schema version tracking
            CREATE TABLE schema_version (
                version INTEGER NOT NULL
            );

            -- Job queue and lifecycle
            CREATE TABLE jobs (
                job_id          TEXT PRIMARY KEY,
                status          TEXT NOT NULL DEFAULT 'pending',
                priority        INTEGER NOT NULL DEFAULT 50,
                docs_path       TEXT NOT NULL,
                product_override TEXT,
                workers         INTEGER NOT NULL DEFAULT 2,
                clean           INTEGER NOT NULL DEFAULT 0,
                force           INTEGER NOT NULL DEFAULT 0,
                sync            INTEGER NOT NULL DEFAULT 0,
                created_at      REAL NOT NULL,
                started_at      REAL,
                completed_at    REAL,
                error           TEXT,
                total_files     INTEGER DEFAULT 0,
                processed_files INTEGER DEFAULT 0,
                total_chunks    INTEGER DEFAULT 0
            );

            CREATE INDEX idx_jobs_status ON jobs(status);
            CREATE INDEX idx_jobs_priority ON jobs(priority DESC);
            CREATE INDEX idx_jobs_created ON jobs(created_at);

            -- Per-file progress within jobs
            CREATE TABLE job_progress (
                job_id          TEXT NOT NULL,
                file_path       TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                chunks_generated INTEGER DEFAULT 0,
                error           TEXT,
                started_at      REAL,
                completed_at    REAL,
                PRIMARY KEY (job_id, file_path),
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX idx_jp_status ON job_progress(status);

            -- File registry (migrated from v1)
            CREATE TABLE files (
                path        TEXT PRIMARY KEY,
                sha256      TEXT NOT NULL,
                file_type   TEXT,
                product     TEXT,
                doc_type    TEXT DEFAULT 'document',
                chunks      INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'ok',
                error_msg   TEXT,
                indexed_at  REAL NOT NULL,
                file_mtime  REAL,
                file_size   INTEGER
            );

            CREATE INDEX idx_files_status ON files(status);
            CREATE INDEX idx_files_product ON files(product);
            CREATE INDEX idx_files_type ON files(file_type);
            CREATE INDEX idx_files_doc_type ON files(doc_type);
        """)

        self._set_schema_version(SCHEMA_VERSION)

    def _migrate_v1_to_v2(self) -> None:
        """Migrate from v1 (registry.db) to v2 (kb_metadata.db)."""
        log.info("Migrating schema v1 → v2...")

        # Check if v1 registry.db exists
        v1_path = self.db_path.parent / "registry.db"
        if not v1_path.exists():
            log.warning(f"v1 registry not found: {v1_path}")
            self._create_schema_v2()
            return

        # Attach old database
        self.conn.execute(f"ATTACH DATABASE '{v1_path}' AS old")

        # Create new schema
        self._create_schema_v2()

        # Copy files table
        self.conn.execute("""
            INSERT INTO files
            SELECT * FROM old.files
        """)

        self.conn.execute("DETACH DATABASE old")
        self.conn.commit()

        log.info(f"Migrated files from {v1_path}")

    # ── Transaction Helpers

    def begin(self) -> None:
        """Begin explicit transaction."""
        self.conn.execute("BEGIN")

    def commit(self) -> None:
        """Commit current transaction."""
        self.conn.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.conn.rollback()

    # ── Statistics

    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}

        # Job counts
        row = self.conn.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()
        stats["total_jobs"] = row[0] if row else 0

        row = self.conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status IN "
            "('pending', 'running', 'paused')"
        ).fetchone()
        stats["active_jobs"] = row[0] if row else 0

        # File counts
        row = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()
        stats["total_files"] = row[0] if row else 0

        return stats
