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
SCHEMA_VERSION = 6


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
        self._conn.execute("PRAGMA foreign_keys=ON")
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
            self._migrate_v2_to_v3()
            self._migrate_v3_to_v4()
            self._migrate_v4_to_v5()
            self._migrate_v5_to_v6()
        elif current_version == 1:
            self._migrate_v1_to_v2()
            self._migrate_v2_to_v3()
            self._migrate_v3_to_v4()
            self._migrate_v4_to_v5()
            self._migrate_v5_to_v6()
        elif current_version == 2:
            self._migrate_v2_to_v3()
            self._migrate_v3_to_v4()
            self._migrate_v4_to_v5()
            self._migrate_v5_to_v6()
        elif current_version == 3:
            self._migrate_v3_to_v4()
            self._migrate_v4_to_v5()
            self._migrate_v5_to_v6()
        elif current_version == 4:
            self._migrate_v4_to_v5()
            self._migrate_v5_to_v6()
        elif current_version == 5:
            self._migrate_v5_to_v6()
        elif current_version == 6:  # Already up to date
            pass
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
                file_size   INTEGER,
                tags        TEXT DEFAULT '[]'
            );

            CREATE INDEX idx_files_status ON files(status);
            CREATE INDEX idx_files_product ON files(product);
            CREATE INDEX idx_files_type ON files(file_type);
            CREATE INDEX idx_files_doc_type ON files(doc_type);

            -- Reclassification backup for rollback
            CREATE TABLE reclassify_backups (
                session_timestamp TEXT NOT NULL,
                source_file TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                chunk_index INTEGER,
                PRIMARY KEY (session_timestamp, source_file,
                             field_name, chunk_index)
            );

            -- Reclassification audit history
            CREATE TABLE reclassify_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source_file TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                session_timestamp TEXT NOT NULL,
                FOREIGN KEY (session_timestamp)
                    REFERENCES reclassify_backups(session_timestamp)
            );

            CREATE INDEX idx_reclassify_history_session
                ON reclassify_history(session_timestamp);
            CREATE INDEX idx_reclassify_history_timestamp
                ON reclassify_history(timestamp);

            -- Tag management audit history (Phase 51)
            CREATE TABLE tags_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                user_id TEXT,
                source_file TEXT NOT NULL,
                action TEXT NOT NULL,
                tag_values TEXT
            );

            CREATE INDEX idx_tags_history_file
                ON tags_history(source_file);
            CREATE INDEX idx_tags_history_timestamp
                ON tags_history(timestamp);
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
        self.conn.execute("ATTACH DATABASE ? AS old", (str(v1_path),))

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

    def _migrate_v2_to_v3(self) -> None:
        """Migrate from v2 to v3: add connector_state table."""
        log.info("Migrating schema v2 → v3...")

        # Check if connector_state already exists
        tables = [
            r[0]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        if "connector_state" in tables:
            log.debug("connector_state table already exists")
        else:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS connector_state (
                    source_key     TEXT NOT NULL,
                    remote_id      TEXT NOT NULL,
                    connector_type TEXT NOT NULL,
                    sync_checkpoint TEXT,
                    remote_etag    TEXT,
                    remote_mtime   REAL,
                    local_path     TEXT,
                    sha256         TEXT,
                    status         TEXT DEFAULT 'ok',
                    ingested_at    REAL NOT NULL,
                    PRIMARY KEY (source_key, remote_id)
                )
            """)
            self.conn.execute("""
                CREATE INDEX idx_cs_connector_type
                    ON connector_state(connector_type)
            """)
            self.conn.execute("""
                CREATE INDEX idx_cs_status
                    ON connector_state(status)
            """)
            self.conn.execute("""
                CREATE INDEX idx_cs_ingested_at
                    ON connector_state(ingested_at)
            """)
            log.info("Created connector_state table")

        self._set_schema_version(3)

    def _migrate_v3_to_v4(self) -> None:
        """Migrate from v3 to v4: add quota tables."""
        log.info("Migrating schema v3 → v4...")
        tables = [
            r[0]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        if "quota_config" not in tables:
            self.conn.execute("""
                CREATE TABLE quota_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    max_files_per_upload INTEGER,
                    max_bytes_per_upload INTEGER,
                    max_bytes_per_file INTEGER,
                    max_documents_per_index INTEGER,
                    max_chunks_per_index INTEGER,
                    max_chars_per_index INTEGER
                )
            """)
            self.conn.execute("INSERT INTO quota_config (id) VALUES (1)")
            log.info("Created quota_config table")
        else:
            log.debug("quota_config table already exists")

        if "quota_usage" not in tables:
            self.conn.execute("""
                CREATE TABLE quota_usage (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_files INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    total_documents INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    total_chars INTEGER DEFAULT 0,
                    updated_at REAL
                )
            """)
            self.conn.execute(
                "INSERT INTO quota_usage (id, total_files, total_bytes, "
                "total_documents, total_chunks, total_chars, updated_at) "
                "VALUES (1, 0, 0, 0, 0, 0, ?)",
                (time.time(),),
            )
            log.info("Created quota_usage table")
        else:
            log.debug("quota_usage table already exists")

        self._set_schema_version(4)

    def _migrate_v4_to_v5(self) -> None:
        """Migrate from v4 to v5: add tags support."""
        log.info("Migrating schema v4 → v5...")

        # Add tags column to files table
        columns = [
            r[1]
            for r in self.conn.execute(
                "PRAGMA table_info(files)"
            ).fetchall()
        ]
        if "tags" not in columns:
            self.conn.execute(
                "ALTER TABLE files ADD COLUMN tags TEXT DEFAULT '[]'"
            )
            log.info("Added tags column to files table")
        else:
            log.debug("tags column already exists")

        # Create tags_history table
        tables = [
            r[0]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        if "tags_history" not in tables:
            self.conn.execute("""
                CREATE TABLE tags_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    user_id TEXT,
                    source_file TEXT NOT NULL,
                    action TEXT NOT NULL,
                    tag_values TEXT
                )
            """)
            self.conn.execute(
                "CREATE INDEX idx_tags_history_file ON tags_history(source_file)"
            )
            self.conn.execute(
                "CREATE INDEX idx_tags_history_timestamp ON tags_history(timestamp)"
            )
            log.info("Created tags_history table")
        else:
            log.debug("tags_history table already exists")

        self._set_schema_version(5)

    def _migrate_v5_to_v6(self) -> None:
        """Migrate from v5 to v6: add schedules table."""
        log.info("Migrating schema v5 → v6...")
        tables = [
            r[0]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        if "schedules" not in tables:
            self.conn.execute("""
                CREATE TABLE schedules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    cron_expr TEXT NOT NULL,
                    docs_path TEXT NOT NULL,
                    product TEXT,
                    workers INTEGER DEFAULT 2,
                    priority TEXT DEFAULT 'normal',
                    clean INTEGER DEFAULT 0,
                    force INTEGER DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    created_at REAL NOT NULL,
                    updated_at REAL,
                    last_run_at REAL,
                    last_run_status TEXT,
                    next_run_at REAL
                )
            """)
            self.conn.execute(
                "CREATE INDEX idx_schedules_enabled ON schedules(enabled)"
            )
            log.info("Created schedules table")
        else:
            log.debug("schedules table already exists")
        self._set_schema_version(6)

    # ── Quota Helpers

    def set_quotas(
        self,
        max_files_per_upload: int | None = None,
        max_bytes_per_upload: int | None = None,
        max_bytes_per_file: int | None = None,
        max_documents_per_index: int | None = None,
        max_chunks_per_index: int | None = None,
        max_chars_per_index: int | None = None,
    ) -> None:
        """Set upload/index quota limits. ``None`` means unlimited."""
        self.conn.execute(
            """
            UPDATE quota_config SET
                max_files_per_upload = ?,
                max_bytes_per_upload = ?,
                max_bytes_per_file = ?,
                max_documents_per_index = ?,
                max_chunks_per_index = ?,
                max_chars_per_index = ?
            WHERE id = 1
            """,
            (
                max_files_per_upload,
                max_bytes_per_upload,
                max_bytes_per_file,
                max_documents_per_index,
                max_chunks_per_index,
                max_chars_per_index,
            ),
        )
        self.conn.commit()
        log.info("Quotas updated")

    def get_quotas(self) -> dict:
        """Return current quota limits dict. ``None`` = unlimited."""
        row = self.conn.execute(
            "SELECT * FROM quota_config WHERE id = 1"
        ).fetchone()
        if row is None:
            return {}
        return dict(row)

    def get_quota_usage(self) -> dict:
        """Return current usage counters."""
        row = self.conn.execute(
            "SELECT * FROM quota_usage WHERE id = 1"
        ).fetchone()
        if row is None:
            return {
                "total_files": 0,
                "total_bytes": 0,
                "total_documents": 0,
                "total_chunks": 0,
                "total_chars": 0,
            }
        return dict(row)

    def check_quota(
        self,
        files_count: int = 0,
        bytes_total: int = 0,
        file_bytes: int = 0,
    ) -> tuple[bool, str]:
        """Check whether an ingest operation would exceed configured limits.

        Args:
            files_count: Number of files in this ingest call.
            bytes_total: Total bytes across all files.
            file_bytes: Size of the current file (for per-file check).

        Returns:
            (ok, message) — ``(True, "")`` if within limits,
            ``(False, "description")`` if a quota would be exceeded.
        """
        quotas = self.get_quotas()
        usage = self.get_quota_usage()

        mfu = quotas.get("max_files_per_upload")
        if mfu is not None and files_count > mfu:
            return (
                False,
                f"Upload would exceed max files per upload: "
                f"{files_count} > {mfu}",
            )

        mbu = quotas.get("max_bytes_per_upload")
        if mbu is not None and bytes_total > mbu:
            return (
                False,
                f"Upload would exceed max bytes per upload: "
                f"{bytes_total} > {mbu}",
            )

        mbf = quotas.get("max_bytes_per_file")
        if mbf is not None and file_bytes > mbf:
            return (
                False,
                f"File exceeds max bytes per file: " f"{file_bytes} > {mbf}",
            )

        mdi = quotas.get("max_documents_per_index")
        if mdi is not None:
            current_docs = usage.get("total_documents", 0)
            if current_docs >= mdi:
                return (
                    False,
                    f"Index at capacity: {current_docs} >= {mdi} "
                    f"max documents",
                )

        mci = quotas.get("max_chunks_per_index")
        if mci is not None:
            current_chunks = usage.get("total_chunks", 0)
            if current_chunks >= mci:
                return (
                    False,
                    f"Index at capacity: {current_chunks} >= {mci} "
                    f"max chunks",
                )

        mcci = quotas.get("max_chars_per_index")
        if mcci is not None:
            current_chars = usage.get("total_chars", 0)
            if current_chars >= mcci:
                return (
                    False,
                    f"Index at capacity: {current_chars} >= {mcci} "
                    f"max characters",
                )

        return True, ""

    def update_quota_usage(
        self,
        files: int = 0,
        bytes_count: int = 0,
        documents: int = 0,
        chunks: int = 0,
        chars: int = 0,
    ) -> None:
        """Increment usage counters after a successful ingest."""
        self.conn.execute(
            """
            UPDATE quota_usage SET
                total_files   = total_files + ?,
                total_bytes   = total_bytes + ?,
                total_documents = total_documents + ?,
                total_chunks  = total_chunks + ?,
                total_chars   = total_chars + ?,
                updated_at    = ?
            WHERE id = 1
            """,
            (files, bytes_count, documents, chunks, chars, time.time()),
        )
        self.conn.commit()

    def reset_quota_usage(self) -> dict:
        """Zero out all usage counters. Returns the previous usage dict."""
        prev = self.get_quota_usage()
        self.conn.execute(
            """
            UPDATE quota_usage SET
                total_files = 0,
                total_bytes = 0,
                total_documents = 0,
                total_chunks = 0,
                total_chars = 0,
                updated_at = ?
            WHERE id = 1
            """,
            (time.time(),),
        )
        self.conn.commit()
        log.info("Quota usage reset")
        return prev

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
        row = self.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
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

    # ── Connector State Helpers

    def upsert_connector_state(
        self,
        source_key: str,
        remote_id: str,
        connector_type: str,
        sync_checkpoint: str | None = None,
        remote_etag: str | None = None,
        remote_mtime: float | None = None,
        local_path: str | None = None,
        sha256: str | None = None,
        status: str = "ok",
    ) -> None:
        """Persist or update connector sync state for a remote document.

        Args:
            source_key: Stable identifier for the connector source
                (e.g. ``confluence://myspace``, ``jira://PROJ``).
            remote_id: Stable remote document identity
                (e.g. Confluence page ID, JIRA issue key, Git blob hash).
            connector_type: Connector type string
                (``confluence``, ``jira``, ``git``).
            sync_checkpoint: Opaque cursor or checkpoint token for
                incremental sync.
            remote_etag: Remote server ETag or content hash.
            remote_mtime: Last-modified timestamp from remote source.
            local_path: Path to staged local copy of the content.
            sha256: SHA-256 of the content (for dedup).
            status: Current status (``ok``, ``error``, ``pending``).
        """
        import time

        self.conn.execute(
            """
            INSERT INTO connector_state (
                source_key, remote_id, connector_type,
                sync_checkpoint, remote_etag, remote_mtime,
                local_path, sha256, status, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_key, remote_id) DO UPDATE SET
                sync_checkpoint = excluded.sync_checkpoint,
                remote_etag     = excluded.remote_etag,
                remote_mtime    = excluded.remote_mtime,
                local_path      = excluded.local_path,
                sha256          = excluded.sha256,
                status          = excluded.status,
                ingested_at     = excluded.ingested_at
            """,
            (
                source_key,
                remote_id,
                connector_type,
                sync_checkpoint,
                remote_etag,
                remote_mtime,
                local_path,
                sha256,
                status,
                time.time(),
            ),
        )
        self.conn.commit()
        log.debug(
            "Connector state upserted: %s/%s (type=%s)",
            source_key,
            remote_id,
            connector_type,
        )

    def get_connector_state(
        self, source_key: str, remote_id: str
    ) -> dict | None:
        """Retrieve connector sync state for a remote document.

        Args:
            source_key: Connector source key.
            remote_id: Remote document identity.

        Returns:
            Dict with connector state fields, or None if not found.
        """
        row = self.conn.execute(
            "SELECT * FROM connector_state "
            "WHERE source_key = ? AND remote_id = ?",
            (source_key, remote_id),
        ).fetchone()
        return dict(row) if row else None

    def list_connector_state(
        self,
        connector_type: str | None = None,
        source_key: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """List connector state records, with optional filters.

        Args:
            connector_type: Filter by connector type.
            source_key: Filter by source key.
            status: Filter by status.

        Returns:
            List of connector state dicts.
        """
        conditions = []
        params = []
        if connector_type is not None:
            conditions.append("connector_type = ?")
            params.append(connector_type)
        if source_key is not None:
            conditions.append("source_key = ?")
            params.append(source_key)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self.conn.execute(
            f"SELECT * FROM connector_state WHERE {where} "
            "ORDER BY ingested_at DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_connector_state(self, source_key: str, remote_id: str) -> None:
        """Remove a connector state record.

        Args:
            source_key: Connector source key.
            remote_id: Remote document identity.
        """
        self.conn.execute(
            "DELETE FROM connector_state "
            "WHERE source_key = ? AND remote_id = ?",
            (source_key, remote_id),
        )
        self.conn.commit()
        log.debug("Connector state deleted: %s/%s", source_key, remote_id)

    def get_connector_sync_checkpoint(self, source_key: str) -> str | None:
        """Retrieve the latest sync checkpoint for a connector source.

        Uses the most recent ``ingested_at`` record to determine
        the checkpoint value.

        Args:
            source_key: Connector source key.

        Returns:
            Sync checkpoint string, or None if no records exist.
        """
        row = self.conn.execute(
            "SELECT sync_checkpoint FROM connector_state "
            "WHERE source_key = ? AND sync_checkpoint IS NOT NULL "
            "ORDER BY ingested_at DESC LIMIT 1",
            (source_key,),
        ).fetchone()
        return row["sync_checkpoint"] if row else None

    def add_schedule(
        self,
        schedule_id: str,
        name: str,
        cron_expr: str,
        docs_path: str,
        product: Optional[str] = None,
        workers: int = 2,
        priority: str = "normal",
        clean: bool = False,
        force: bool = False,
    ) -> dict:
        now = time.time()
        self.conn.execute(
            """
            INSERT INTO schedules (id, name, cron_expr, docs_path, product,
                                   workers, priority, clean, force,
                                   enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                schedule_id, name, cron_expr, docs_path,
                product, workers, priority,
                1 if clean else 0, 1 if force else 0,
                now, now,
            ),
        )
        self._conn.commit()
        log.info("Added schedule: %s (cron=%s)", name, cron_expr)
        return self.get_schedule(schedule_id)

    def list_schedules(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM schedules ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_schedule(self, schedule_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM schedules WHERE id = ?", (schedule_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_schedule(
        self,
        schedule_id: str,
        name: Optional[str] = None,
        cron_expr: Optional[str] = None,
        docs_path: Optional[str] = None,
        product: Optional[str] = None,
        workers: Optional[int] = None,
        priority: Optional[str] = None,
        clean: Optional[bool] = None,
        force: Optional[bool] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[dict]:
        existing = self.get_schedule(schedule_id)
        if existing is None:
            return None
        updates = {}
        if name is not None:
            updates["name"] = name
        if cron_expr is not None:
            updates["cron_expr"] = cron_expr
        if docs_path is not None:
            updates["docs_path"] = docs_path
        if product is not None:
            updates["product"] = product
        if workers is not None:
            updates["workers"] = workers
        if priority is not None:
            updates["priority"] = priority
        if clean is not None:
            updates["clean"] = 1 if clean else 0
        if force is not None:
            updates["force"] = 1 if force else 0
        if enabled is not None:
            updates["enabled"] = 1 if enabled else 0
        updates["updated_at"] = time.time()
        set_clause = ", ".join(
            f"{k} = ?" for k in updates
        )
        values = list(updates.values()) + [schedule_id]
        self.conn.execute(
            f"UPDATE schedules SET {set_clause} WHERE id = ?", values
        )
        self._conn.commit()
        return self.get_schedule(schedule_id)

    def delete_schedule(self, schedule_id: str) -> bool:
        row = self.conn.execute(
            "SELECT id FROM schedules WHERE id = ?", (schedule_id,)
        ).fetchone()
        if row is None:
            return False
        self.conn.execute(
            "DELETE FROM schedules WHERE id = ?", (schedule_id,)
        )
        self._conn.commit()
        log.info("Deleted schedule: %s", schedule_id)
        return True

    def update_schedule_run(
        self,
        schedule_id: str,
        last_run_at: float,
        last_run_status: str,
        next_run_at: Optional[float] = None,
    ) -> None:
        if next_run_at is not None:
            self.conn.execute(
                """UPDATE schedules
                   SET last_run_at = ?, last_run_status = ?,
                       next_run_at = ?, updated_at = ?
                   WHERE id = ?""",
                (last_run_at, last_run_status, next_run_at, time.time(), schedule_id),
            )
        else:
            self.conn.execute(
                """UPDATE schedules
                   SET last_run_at = ?, last_run_status = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (last_run_at, last_run_status, time.time(), schedule_id),
            )
        self._conn.commit()

    def get_enabled_schedules_due(self) -> list[dict]:
        now = time.time()
        rows = self.conn.execute(
            """SELECT * FROM schedules
               WHERE enabled = 1
                 AND (next_run_at IS NULL OR next_run_at <= ?)
               ORDER BY created_at""",
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Legacy registry (migrated from ingest/registry.py) ──────────────────────

_REGISTRY_DEFAULT_DB = (
    Path(__file__).parent.parent.parent / "data" / "registry.db"
)

log_reg = logging.getLogger("kb-ingest.registry")


class IngestRegistry:
    """SQLite-backed registry tracking ingested file state and deduplication.

    Maintains a files table with SHA-256 hashes for change detection.
    Tracks per-file status (ok/error/deleted), chunk counts, and timestamps.
    Used by the ingest pipeline to determine which files need processing.

    Attributes:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: Path | None = None):
        resolved_db_path: Path
        if db_path is not None:
            resolved_db_path = db_path
        else:
            reg_env = os.getenv("REGISTRY_DB")
            resolved_db_path = (
                Path(reg_env) if reg_env is not None else _REGISTRY_DEFAULT_DB
            )
        self.db_path = resolved_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        log_reg.debug("IngestRegistry initialized: db=%s", self.db_path)

    def connect(self) -> None:
        """Open database connection and initialize schema.

        Creates the files table and indexes if they do not exist.
        """
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()
        log_reg.info(f"Registry: {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            log_reg.debug("Registry connection closed")

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
                file_size   INTEGER,
                tags        TEXT DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS idx_status   ON files(status);
            CREATE INDEX IF NOT EXISTS idx_product  ON files(product);
            CREATE INDEX IF NOT EXISTS idx_type     ON files(file_type);
            CREATE INDEX IF NOT EXISTS idx_doc_type ON files(doc_type);
        """)
        cols = [
            r[1]
            for r in self._conn.execute("PRAGMA table_info(files)").fetchall()
        ]
        if "doc_type" not in cols:
            self._conn.execute(
                "ALTER TABLE files ADD COLUMN "
                "doc_type TEXT DEFAULT 'document'"
            )
        if "tags" not in cols:
            self._conn.execute(
                "ALTER TABLE files ADD COLUMN "
                "tags TEXT DEFAULT '[]'"
            )
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tags_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                user_id TEXT,
                source_file TEXT NOT NULL,
                action TEXT NOT NULL,
                tag_values TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tags_history_file
                ON tags_history(source_file);
            CREATE INDEX IF NOT EXISTS idx_tags_history_timestamp
                ON tags_history(timestamp);
        """)
        self._conn.commit()

    @staticmethod
    def sha256(path: Path) -> str:
        """Compute SHA-256 hex digest of a file.

        Reads the file in 64 KB blocks for memory efficiency.

        Args:
            path: Path to the file.

        Returns:
            SHA-256 hex digest string.
        """
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    def needs_ingest(self, path: Path, rel_path: str) -> tuple[bool, str]:
        """Check if a file needs to be ingested.

        Returns True if the file is new, has a changed SHA-256 hash, or
        was previously in error status.

        Args:
            path: Full path to the file on disk.
            rel_path: Relative path used as the registry key.

        Returns:
            Tuple of (needs_ingest: bool, reason: str).
        """
        assert self._conn is not None, "Database connection not established."
        row = self._conn.execute(
            "SELECT sha256, status FROM files WHERE path = ?", (rel_path,)
        ).fetchone()
        if row is None:
            log_reg.debug("needs_ingest '%s': new", rel_path)
            return True, "new"
        if row["status"] == "error":
            log_reg.debug("needs_ingest '%s': retry", rel_path)
            return True, "previous error — retrying"
        current_hash = self.sha256(path)
        if current_hash != row["sha256"]:
            log_reg.debug("needs_ingest '%s': modified", rel_path)
            return True, "content modified"
        log_reg.debug("needs_ingest '%s': no changes", rel_path)
        return False, "no changes"

    def get_record(self, rel_path: str) -> dict | None:
        """Retrieve a single file record by relative path.

        Args:
            rel_path: Relative path of the file.

        Returns:
            Dict with file fields, or None if not found.
        """
        assert self._conn is not None, "Database connection not established."
        row = self._conn.execute(
            "SELECT * FROM files WHERE path = ?", (rel_path,)
        ).fetchone()
        log_reg.debug(
            "get_record '%s': %s", rel_path, "found" if row else "not found"
        )
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
        """Mark a file as successfully ingested.

        Inserts or updates the file record with status 'ok', recording
        the SHA-256 hash, chunk count, and file metadata.

        Args:
            path: Full path to the file on disk.
            rel_path: Relative path for the registry key.
            chunks: Number of chunks generated.
            file_type: File type identifier (pdf, docx, etc.).
            product: Product name.
            doc_type: Document type classification.
        """
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
        log_reg.info("Marked ok: '%s' chunks=%d", rel_path, chunks)

    def mark_error(
        self,
        path: Path,
        rel_path: str,
        error: str,
        file_type: str,
        product: str,
        doc_type: str = "document",
    ) -> None:
        """Mark a file as failed during ingestion.

        Sets status to 'error' with the error message for debugging.

        Args:
            path: Full path to the file on disk.
            rel_path: Relative path for the registry key.
            error: Error message describing the failure.
            file_type: File type identifier.
            product: Product name.
            doc_type: Document type classification.
        """
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
        log_reg.warning("Marked error: '%s' error='%s'", rel_path, error[:100])

    def mark_deleted(self, rel_path: str) -> None:
        """Mark a file as deleted from disk.

        Sets the file status to 'deleted' without removing the record,
        allowing recovery or audit of removed files.

        Args:
            rel_path: Relative path of the file to mark.
        """
        assert self._conn is not None, "Database connection not established."
        self._conn.execute(
            "UPDATE files SET status = 'deleted' WHERE path = ?",
            (rel_path,),
        )
        self._conn.commit()
        log_reg.info("Marked deleted: '%s'", rel_path)

    def summary(self) -> dict:
        """Return aggregate statistics about all files in the registry.

        Returns:
            Dict with total, ok, errors, deleted, total_chunks,
            first_indexed, and last_indexed.
        """
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
        result = dict(rows)
        log_reg.info("Registry summary: %s", result)
        return result

    def per_source_summary(self) -> list[dict]:
        """
        Return per-source directory summary from the files table.

        Source directory is the first path component before ``/`` in the
        ``path`` column. Files at root (no ``/`` in path) are grouped
        under ``"(root)"``.

        Returns a list of dicts, each with keys: ``source`` (str),
        ``files`` (int), ``ok`` (int), ``errors`` (int), ``chunks`` (int),
        ``last_indexed`` (float | None).
        """
        assert self._conn is not None, "Database connection not established."
        rows = self._conn.execute("""
            SELECT
                CASE
                    WHEN INSTR(path, '/') > 0
                    THEN SUBSTR(path, 1, INSTR(path, '/') - 1)
                    ELSE '(root)'
                END AS source,
                COUNT(*)                                          AS files,
                SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END)    AS ok,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errors,
                COALESCE(SUM(chunks), 0)                          AS chunks,
                MAX(indexed_at) AS last_indexed
            FROM files
            GROUP BY source
            ORDER BY source
        """).fetchall()
        results = [dict(r) for r in rows]
        log_reg.debug("Per-source summary: %d sources", len(results))
        return results

    def list_errors(self) -> list[dict]:
        """List all files with error status.

        Returns:
            List of dicts with path, error_msg, and indexed_at.
        """
        assert self._conn is not None, "Database connection not established."
        rows = self._conn.execute(
            "SELECT path, error_msg, indexed_at FROM files "
            "WHERE status = 'error'"
        ).fetchall()
        log_reg.debug("Listed %d errors", len(rows))
        return [dict(r) for r in rows]

    def list_all(self, status: str | None = None) -> list[dict]:
        """List all file records, optionally filtered by status.

        Args:
            status: Optional status filter ('ok', 'error', 'deleted').

        Returns:
            List of file record dicts sorted by indexed_at descending.
        """
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
        log_reg.debug(
            "Listed %d files (status=%s)", len(rows), status or "all"
        )
        return [dict(r) for r in rows]

    # ── Phase 51: Tag management ────────────────────────────────────────

    def update_file_tags(
        self, rel_path: str, tags: list[str]
    ) -> None:
        """Update tags for a file in the registry.

        Args:
            rel_path: Relative file path (primary key).
            tags: List of tag strings (will be JSON-serialized).
        """
        assert self._conn is not None, "Database connection not established."
        import json

        self._conn.execute(
            "UPDATE files SET tags = ? WHERE path = ?",
            (json.dumps(tags), rel_path),
        )
        self._conn.commit()
        log_reg.info("Updated tags for '%s': %s", rel_path, tags)

    def get_file_tags(self, rel_path: str) -> list[str]:
        """Get tags for a file from the registry.

        Args:
            rel_path: Relative file path.

        Returns:
            List of tag strings.
        """
        assert self._conn is not None, "Database connection not established."
        import json

        row = self._conn.execute(
            "SELECT tags FROM files WHERE path = ?", (rel_path,)
        ).fetchone()
        if row and row[0]:
            return json.loads(row[0])
        return []

    def log_tag_history(
        self,
        user_id: str | None,
        source_file: str,
        action: str,
        tag_values: list[str],
    ) -> None:
        """Log a tag mutation to the audit history.

        Args:
            user_id: User who performed the action.
            source_file: Document path affected.
            action: Action type (add, remove, replace, delete-tag).
            tag_values: List of tag values involved.
        """
        assert self._conn is not None, "Database connection not established."
        import json

        self._conn.execute(
            """
            INSERT INTO tags_history (timestamp, user_id, source_file,
                                      action, tag_values)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                user_id,
                source_file,
                action,
                json.dumps(tag_values),
            ),
        )
        self._conn.commit()

    def get_tags_history(
        self, source_file: str | None = None
    ) -> list[dict]:
        """Get tag audit history, optionally filtered by file.

        Args:
            source_file: Optional file path filter.

        Returns:
            List of history record dicts.
        """
        assert self._conn is not None, "Database connection not established."
        if source_file:
            rows = self._conn.execute(
                "SELECT * FROM tags_history WHERE source_file = ? "
                "ORDER BY timestamp DESC",
                (source_file,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM tags_history ORDER BY timestamp DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def purge_deleted(self) -> None:
        """Permanently delete all records with status 'deleted'."""
        assert self._conn is not None, "Database connection not established."
        self._conn.execute("DELETE FROM files WHERE status = 'deleted'")
        self._conn.commit()
        log_reg.info("Purged deleted records")

    def reset(self):
        """Delete all file records from the registry.

        Warning: This is destructive and cannot be undone. Does not
        affect the vector store — only the tracking registry.
        """
        self._conn.execute("DELETE FROM files")
        self._conn.commit()
        log_reg.info("Registry reset.")

    def is_indexed(self, rel_path: str, checksum: str | None = None) -> bool:
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
            indexed = row is not None
            log_reg.debug("is_indexed '%s': %s", rel_path, indexed)
            return indexed
        row = self._conn.execute(
            "SELECT 1 FROM files WHERE path = ? AND sha256 = ? "
            "AND status = 'ok'",
            (rel_path, checksum),
        ).fetchone()
        indexed = row is not None
        log_reg.debug("is_indexed '%s' (checksum): %s", rel_path, indexed)
        return indexed

    def mark_indexed(self, rel_path: str, checksum: str, chunks: int) -> None:
        """
        Mark a file as successfully indexed with a pre-computed checksum.
        """
        assert self._conn is not None, "Database connection not established."
        self._conn.execute(
            """
            INSERT INTO files (path, sha256, file_type, product, doc_type,
                               chunks, status, error_msg, indexed_at,
                               file_mtime, file_size, tags)
            VALUES (?, ?, '', '', 'document', ?, 'ok', NULL, ?, 0, 0, '[]')
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

