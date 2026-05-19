"""
Metadata storage with schema v2 for job management.

Manages SQLite schema for jobs, job_progress, and files tables.
Provides migration from v1 registry.db to v2 kb_metadata.db.
"""

import hashlib
import logging
import os
import sqlite3
import time
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


# ── Legacy registry (migrated from ingest/registry.py) ──────────────────────

_REGISTRY_DEFAULT_DB = (
    Path(__file__).parent.parent.parent / "data" / "registry.db"
)

log_reg = logging.getLogger("kb-ingest.registry")


class IngestRegistry:
    def __init__(self, db_path: Path | None = None):
        resolved_db_path: Path
        if db_path is not None:
            resolved_db_path = db_path
        else:
            reg_env = os.getenv("REGISTRY_DB")
            resolved_db_path = (
                Path(reg_env)
                if reg_env is not None
                else _REGISTRY_DEFAULT_DB
            )
        self.db_path = resolved_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._migrate()
        log_reg.info(f"Registry: {self.db_path}")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    def _migrate(self) -> None:
        assert self._conn is not None, "Database connection not established."
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS files (
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
            CREATE INDEX IF NOT EXISTS idx_status   ON files(status);
            CREATE INDEX IF NOT EXISTS idx_product  ON files(product);
            CREATE INDEX IF NOT EXISTS idx_type     ON files(file_type);
            CREATE INDEX IF NOT EXISTS idx_doc_type ON files(doc_type);
        """)
        cols = [
            r[1]
            for r in self._conn.execute(
                "PRAGMA table_info(files)"
            ).fetchall()
        ]
        if "doc_type" not in cols:
            self._conn.execute(
                "ALTER TABLE files ADD COLUMN "
                "doc_type TEXT DEFAULT 'document'"
            )
        self._conn.commit()

    @staticmethod
    def sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    def needs_ingest(self, path: Path, rel_path: str) -> tuple[bool, str]:
        assert self._conn is not None, "Database connection not established."
        row = self._conn.execute(
            "SELECT sha256, status FROM files WHERE path = ?", (rel_path,)
        ).fetchone()
        if row is None:
            return True, "novo"
        if row["status"] == "error":
            return True, "erro anterior — tentando novamente"
        current_hash = self.sha256(path)
        if current_hash != row["sha256"]:
            return True, "conteúdo modificado"
        return False, "sem alterações"

    def get_record(self, rel_path: str) -> dict | None:
        assert self._conn is not None, "Database connection not established."
        row = self._conn.execute(
            "SELECT * FROM files WHERE path = ?", (rel_path,)
        ).fetchone()
        return dict(row) if row else None

    def mark_ok(
        self,
        path: Path,
        rel_path: str,
        chunks: int,
        file_type: str,
        product: str,
        doc_type: str = "document",
    ) -> None:
        assert self._conn is not None, "Database connection not established."
        stat = path.stat()
        self._conn.execute(
            """
            INSERT INTO files (path, sha256, file_type, product, doc_type,
                               chunks, status, error_msg, indexed_at,
                               file_mtime, file_size)
            VALUES (?, ?, ?, ?, ?, ?, 'ok', NULL, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                sha256     = excluded.sha256,
                file_type  = excluded.file_type,
                product    = excluded.product,
                doc_type   = excluded.doc_type,
                chunks     = excluded.chunks,
                status     = 'ok',
                error_msg  = NULL,
                indexed_at = excluded.indexed_at,
                file_mtime = excluded.file_mtime,
                file_size  = excluded.file_size
            """,
            (
                rel_path,
                self.sha256(path),
                file_type,
                product,
                doc_type,
                chunks,
                time.time(),
                stat.st_mtime,
                stat.st_size,
            ),
        )
        self._conn.commit()

    def mark_error(
        self,
        path: Path,
        rel_path: str,
        error: str,
        file_type: str,
        product: str,
        doc_type: str = "document",
    ) -> None:
        assert self._conn is not None, "Database connection not established."
        self._conn.execute(
            """
            INSERT INTO files (path, sha256, file_type, product, doc_type,
                               chunks, status, error_msg, indexed_at,
                               file_mtime, file_size)
            VALUES (?, ?, ?, ?, ?, 0, 'error', ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                status    = 'error',
                error_msg = excluded.error_msg,
                indexed_at = excluded.indexed_at
            """,
            (
                rel_path,
                self.sha256(path) if path.exists() else "",
                file_type,
                product,
                doc_type,
                error[:500],
                time.time(),
                path.stat().st_mtime if path.exists() else 0,
                path.stat().st_size if path.exists() else 0,
            ),
        )
        self._conn.commit()

    def mark_deleted(self, rel_path: str) -> None:
        assert self._conn is not None, "Database connection not established."
        self._conn.execute(
            "UPDATE files SET status = 'deleted' WHERE path = ?",
            (rel_path,),
        )
        self._conn.commit()

    def summary(self) -> dict:
        assert self._conn is not None, "Database connection not established."
        rows = self._conn.execute("""
            SELECT
                COUNT(*)                              AS total,
                SUM(status = 'ok')                    AS ok,
                SUM(status = 'error')                 AS errors,
                SUM(status = 'deleted')               AS deleted,
                SUM(chunks)                           AS total_chunks,
                MIN(indexed_at)                       AS first_indexed,
                MAX(indexed_at)                       AS last_indexed
            FROM files
        """).fetchone()
        return dict(rows)

    def list_errors(self) -> list[dict]:
        assert self._conn is not None, "Database connection not established."
        rows = self._conn.execute(
            "SELECT path, error_msg, indexed_at FROM files "
            "WHERE status = 'error'"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_all(self, status: str | None = None) -> list[dict]:
        assert self._conn is not None, "Database connection not established."
        if status:
            rows = self._conn.execute(
                "SELECT * FROM files WHERE status = ? "
                "ORDER BY indexed_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM files ORDER BY indexed_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def purge_deleted(self) -> None:
        assert self._conn is not None, "Database connection not established."
        self._conn.execute("DELETE FROM files WHERE status = 'deleted'")
        self._conn.commit()

    def reset(self):
        self._conn.execute("DELETE FROM files")
        self._conn.commit()
        log_reg.info("Registry resetado.")

    def is_indexed(
        self, rel_path: str, checksum: str | None = None
    ) -> bool:
        """
        Return True if the file is already indexed with the given checksum.

        If ``checksum`` is None, returns True if the file has any 'ok' record.
        """
        assert self._conn is not None, "Database connection not established."
        if checksum is None:
            row = self._conn.execute(
                "SELECT 1 FROM files WHERE path = ? AND status = 'ok'",
                (rel_path,),
            ).fetchone()
            return row is not None
        row = self._conn.execute(
            "SELECT 1 FROM files WHERE path = ? AND sha256 = ? "
            "AND status = 'ok'",
            (rel_path, checksum),
        ).fetchone()
        return row is not None

    def mark_indexed(
        self, rel_path: str, checksum: str, chunks: int
    ) -> None:
        """
        Mark a file as successfully indexed with a pre-computed checksum.
        """
        assert self._conn is not None, "Database connection not established."
        self._conn.execute(
            """
            INSERT INTO files (path, sha256, file_type, product, doc_type,
                               chunks, status, error_msg, indexed_at,
                               file_mtime, file_size)
            VALUES (?, ?, '', '', 'document', ?, 'ok', NULL, ?, 0, 0)
            ON CONFLICT(path) DO UPDATE SET
                sha256     = excluded.sha256,
                chunks     = excluded.chunks,
                status     = 'ok',
                error_msg  = NULL,
                indexed_at = excluded.indexed_at
            """,
            (rel_path, checksum, chunks, time.time()),
        )
        self._conn.commit()
