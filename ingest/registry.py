"""
Registry de ingestão — controla quais arquivos foram indexados e se mudaram.

Usa SQLite local (data/registry.db) para persistir entre execuções:
  - SHA256 do arquivo → detecta mudanças de conteúdo
  - timestamp de ingestão
  - número de chunks gerados
  - status: ok | error | skipped

Fluxo:
  needs_ingest(path) → True/False
  mark_ok(path, chunks)
  mark_error(path, error)
  mark_deleted(path)   ← quando arquivo some do disco
"""

import hashlib
import logging
import os
import sqlite3
import time
from pathlib import Path

log = logging.getLogger("kb-ingest.registry")

DEFAULT_DB = Path(__file__).parent.parent / "data" / "registry.db"


class IngestRegistry:
    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or os.getenv("REGISTRY_DB", DEFAULT_DB))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ── Conexão ───────────────────────────────────────────────────────────────

    def connect(self):
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._migrate()
        log.info(f"Registry: {self.db_path}")

    def close(self):
        if self._conn:
            self._conn.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    def _migrate(self):
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
        # Migração: adiciona doc_type se tabela já existia sem ela
        cols = [r[1] for r in self._conn.execute("PRAGMA table_info(files)").fetchall()]
        if "doc_type" not in cols:
            self._conn.execute("ALTER TABLE files ADD COLUMN doc_type TEXT DEFAULT 'document'")
        self._conn.commit()

    # ── Hash ──────────────────────────────────────────────────────────────────

    @staticmethod
    def sha256(path: Path) -> str:
        """Calcula SHA256 do arquivo em blocos (eficiente para arquivos grandes)."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    # ── Consultas ─────────────────────────────────────────────────────────────

    def needs_ingest(self, path: Path, rel_path: str) -> tuple[bool, str]:
        """
        Verifica se o arquivo precisa ser (re)ingerido.
        Retorna (precisa_ingerir, motivo).
        """
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
        row = self._conn.execute(
            "SELECT * FROM files WHERE path = ?", (rel_path,)
        ).fetchone()
        return dict(row) if row else None

    # ── Atualizações ──────────────────────────────────────────────────────────

    def mark_ok(self, path: Path, rel_path: str, chunks: int, file_type: str, product: str, doc_type: str = "document"):
        stat = path.stat()
        self._conn.execute("""
            INSERT INTO files (path, sha256, file_type, product, doc_type, chunks, status,
                               error_msg, indexed_at, file_mtime, file_size)
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
        """, (
            rel_path, self.sha256(path), file_type, product, doc_type,
            chunks, time.time(), stat.st_mtime, stat.st_size,
        ))
        self._conn.commit()

    def mark_error(self, path: Path, rel_path: str, error: str, file_type: str, product: str, doc_type: str = "document"):
        self._conn.execute("""
            INSERT INTO files (path, sha256, file_type, product, doc_type, chunks, status,
                               error_msg, indexed_at, file_mtime, file_size)
            VALUES (?, ?, ?, ?, ?, 0, 'error', ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                status    = 'error',
                error_msg = excluded.error_msg,
                indexed_at = excluded.indexed_at
        """, (
            rel_path,
            self.sha256(path) if path.exists() else "",
            file_type, product, doc_type,
            error[:500], time.time(),
            path.stat().st_mtime if path.exists() else 0,
            path.stat().st_size if path.exists() else 0,
        ))
        self._conn.commit()

    def mark_deleted(self, rel_path: str):
        """Marca arquivo que não existe mais no disco."""
        self._conn.execute(
            "UPDATE files SET status = 'deleted' WHERE path = ?", (rel_path,)
        )
        self._conn.commit()

    # ── Relatórios ────────────────────────────────────────────────────────────

    def summary(self) -> dict:
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
        rows = self._conn.execute(
            "SELECT path, error_msg, indexed_at FROM files WHERE status = 'error'"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_all(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM files WHERE status = ? ORDER BY indexed_at DESC", (status,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM files ORDER BY indexed_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def purge_deleted(self):
        """Remove registros de arquivos deletados do banco."""
        n = self._conn.execute("DELETE FROM files WHERE status = 'deleted'").rowcount
        self._conn.commit()
        return n

    def reset(self):
        """Apaga todo o registry (use junto com --clean)."""
        self._conn.execute("DELETE FROM files")
        self._conn.commit()
        log.info("Registry resetado.")
