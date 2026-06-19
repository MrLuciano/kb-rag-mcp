"""
API key registry — SQLite-backed hash storage for MCP auth.

Stores SHA-256 hashed API keys with scope, revocation state, and
optional KB binding. Raw keys are never persisted or logged.
"""

import hashlib
import logging
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("kb-mcp.auth_registry")

_DEFAULT_DB_PATH = Path(os.getenv("AUTH_DB_PATH", "data/auth.db"))


def _resolve_db_path(path: Path) -> Path:
    """Return writable path, falling back to /tmp if file is read-only."""
    if path.exists() and not os.access(path, os.W_OK):
        fallback = Path("/tmp") / path.name
        log.warning(
            "Auth DB %s is read-only (Docker root mount?). "
            "Using fallback: %s",
            path,
            fallback,
        )
        return fallback
    return path


class AuthRegistry:
    """SQLite-backed registry for API key hashes and metadata.

    Thread-safe via ``threading.Lock``. Supports global and per-KB
    scoped keys with revocation tracking.
    """

    _TABLE = "auth_api_keys"

    def __init__(self, db_path: Path = _DEFAULT_DB_PATH):
        self._db_path = _resolve_db_path(db_path)
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._conn()
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._TABLE} (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash    TEXT NOT NULL UNIQUE,
                    prefix      TEXT NOT NULL,
                    scope       TEXT NOT NULL DEFAULT 'global',
                    kb_name     TEXT,
                    revoked     INTEGER NOT NULL DEFAULT 0,
                    description TEXT DEFAULT '',
                    created_at  TEXT NOT NULL,
                    revoked_at  TEXT
                )
                """
            )
            try:
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{self._TABLE}_prefix "
                    f"ON {self._TABLE}(prefix)"
                )
                conn.commit()
            except sqlite3.OperationalError as e:
                if "readonly" in str(e).lower():
                    log.warning(
                        "Auth DB is read-only (%s). "
                        "Using existing schema without modifications.",
                        self._db_path,
                    )
                else:
                    raise
            finally:
                conn.close()

    def _get_columns(self) -> set[str]:
        conn = self._conn()
        cursor = conn.execute(f"PRAGMA table_info({self._TABLE})")
        cols = {row[1] for row in cursor.fetchall()}
        conn.close()
        return cols

    def create_key(
        self,
        scope: str = "global",
        kb_name: Optional[str] = None,
        description: str = "",
    ) -> str:
        """Generate and store a new API key.

        Returns the plaintext key (shown once to the operator).
        Only the SHA-256 hash is persisted.

        Args:
            scope: ``"global"`` or ``"kb"``.
            kb_name: Required if scope is ``"kb"``.
            description: Optional human-readable label.

        Returns:
            The plaintext API key (hex string, 64 chars).
        """
        raw_key = secrets.token_hex(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:8]
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._conn()
            conn.execute(
                f"""
                INSERT INTO {self._TABLE}
                    (key_hash, prefix, scope, kb_name, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key_hash, prefix, scope, kb_name, description, now),
            )
            conn.commit()
            conn.close()

        return raw_key

    def verify_key(self, raw_key: str) -> bool:
        """Check if a raw key is valid (exists and not revoked).

        Args:
            raw_key: The plaintext API key to verify.

        Returns:
            True if the key exists and is not revoked.
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        with self._lock:
            conn = self._conn()
            row = conn.execute(
                f"SELECT revoked FROM {self._TABLE} WHERE key_hash = ?",
                (key_hash,),
            ).fetchone()
            conn.close()
        return row is not None and row["revoked"] == 0

    def revoke_key(self, prefix: str) -> bool:
        """Revoke a key by its 8-character prefix.

        Args:
            prefix: First 8 characters of the raw key.

        Returns:
            True if a matching key was revoked, False if not found.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._conn()
            cursor = conn.execute(
                f"""
                UPDATE {self._TABLE} SET revoked = 1, revoked_at = ?
                WHERE prefix = ? AND revoked = 0
                """,
                (now, prefix),
            )
            conn.commit()
            affected = cursor.rowcount
            conn.close()
        return affected > 0

    def list_keys(self) -> list[dict]:
        """List all API keys with metadata (never the raw key).

        Returns:
            List of dicts with prefix, scope, kb_name, description,
            revoked, created_at, revoked_at.
        """
        with self._lock:
            conn = self._conn()
            cursor = conn.execute(f"PRAGMA table_info({self._TABLE})")
            columns = {row[1] for row in cursor.fetchall()}

            select_cols = []
            if "prefix" in columns:
                select_cols.append("prefix")
            if "scope" in columns:
                select_cols.append("scope")
            else:
                select_cols.append("'global' AS scope")
            if "kb_name" in columns:
                select_cols.append("kb_name")
            else:
                select_cols.append("NULL AS kb_name")
            if "description" in columns:
                select_cols.append("description")
            if "revoked" in columns:
                select_cols.append("revoked")
            if "created_at" in columns:
                select_cols.append("created_at")
            if "revoked_at" in columns:
                select_cols.append("revoked_at")

            if not select_cols:
                conn.close()
                return []

            query = (
                f"SELECT {', '.join(select_cols)} "
                f"FROM {self._TABLE} ORDER BY created_at DESC"
            )
            rows = conn.execute(query).fetchall()
            conn.close()
        return [dict(r) for r in rows]

    def close(self) -> None:
        """Close any resources (no-op for sqlite3)."""


# Module-level singleton for server use
_registry: Optional[AuthRegistry] = None


def get_registry() -> AuthRegistry:
    global _registry
    if _registry is None:
        _registry = AuthRegistry()
    return _registry
