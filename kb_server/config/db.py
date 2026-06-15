import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

log = logging.getLogger("kb-mcp.config.db")

DEFAULT_DB_PATH = (
    Path(__file__).parent.parent.parent / "data" / "kb_metadata.db"
)


def get_db_path() -> Path:
    env_path = os.getenv("METADATA_DB")
    return Path(env_path) if env_path else DEFAULT_DB_PATH


@contextmanager
def get_connection(
    db_path: Optional[Path] = None,
) -> Generator[sqlite3.Connection, None, None]:
    if db_path is None:
        db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_config_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key         TEXT PRIMARY KEY,
            value       TEXT,
            type        TEXT NOT NULL DEFAULT 'string',
            group_name  TEXT NOT NULL DEFAULT 'general',
            description TEXT NOT NULL DEFAULT '',
            updated_at  REAL NOT NULL,
            updated_by  TEXT NOT NULL DEFAULT 'system'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config_version (
            id      INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO config_version (id, version) VALUES (1, 1)
    """)


def get_config_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT version FROM config_version WHERE id = 1"
    ).fetchone()
    return row["version"] if row else 1


def bump_config_version(conn: sqlite3.Connection) -> None:
    conn.execute(
        "UPDATE config_version SET version = version + 1 WHERE id = 1"
    )
