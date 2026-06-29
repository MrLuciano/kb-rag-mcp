import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Optional

from kb_server.config.db import (
    bump_config_version,
    ensure_config_table,
    get_config_version,
    get_connection,
    get_db_path,
)
from kb_server.config.models import convert_value, validate_type

log = logging.getLogger("kb-mcp.config.loader")


class ConfigLoader:
    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or get_db_path()
        self._cache: dict[str, tuple[str, str, float]] = {}
        self._old_cache: dict[str, tuple[str, str, float]] = {}
        self._cache_version: int = 0
        self._observers: list[tuple[str, Callable[[str, Any], None]]] = []

        self._init_db()
        self.load_from_env()

    def _init_db(self) -> None:
        try:
            with get_connection(self._db_path) as conn:
                ensure_config_table(conn)
            log.info("ConfigLoader initialized: %s", self._db_path)
        except Exception:
            log.warning(
                "ConfigLoader: SQLite unavailable, falling through to env"
            )

    def load_from_env(self) -> None:
        """Seed known env keys into SQLite config table if not present.

        Iterates over a curated list of known environment keys and inserts
        them into the config table with group_name="env_default" when the
        key does not already exist in the database.

        Seeds both kb_metadata.db (MCP server) and config.db (UI server)
        to make all env keys visible in the admin settings UI. Skips
        temporary test databases.
        """
        # Skip seeding for test databases
        if self._db_path.name not in ("kb_metadata.db", "config.db"):
            return

        seed_keys = [
            # ── Embedding ──────────────────────────────────────────────────
            "EMBED_BACKEND",
            "EMBED_MODEL",
            "EMBED_BATCH_SIZE",
            "LMS_BASE_URL",
            "LMS_HOST",
            "LMS_PORT",
            "OLLAMA_HOST",
            # ── Qdrant ─────────────────────────────────────────────────────
            "QDRANT_HOST",
            "QDRANT_PORT",
            "QDRANT_GRPC_PORT",
            "QDRANT_COLLECTION",
            "QDRANT_DATA_PATH",
            "QDRANT_URL",
            "QDRANT_TIMEOUT",
            "QDRANT_BATCH_SIZE",
            # ── Search / Retrieval ─────────────────────────────────────────
            "SCORE_THRESHOLD",
            "DEFAULT_TOP_K",
            "HYBRID_ENABLED",
            "HYBRID_DENSE_WEIGHT",
            "HYBRID_SPARSE_WEIGHT",
            "HYBRID_RRF_K",
            "HYBRID_SPARSE_MODEL",
            "RERANK_ENABLED",
            "RERANKER_MODEL",
            "RERANKER_BATCH_SIZE",
            "RERANKER_CACHE_TTL",
            # ── MCP Server ─────────────────────────────────────────────────
            "MCP_TRANSPORT",
            "SSE_HOST",
            "SSE_PORT",
            "DATA_DIR",
            "KB_METADATA_DB",
            "METADATA_DB",
            "CONFIG_DB_PATH",
            "REGISTRY_DB_PATH",
            "REGISTRY_DB",
            # ── UI Server ──────────────────────────────────────────────────
            "UI_HOST",
            "UI_PORT",
            # ── Logs ───────────────────────────────────────────────────────
            "LOG_PATH",
            "LOGS_DIR",
            "MCP_LOG",
            # ── Docs / Ingestion ───────────────────────────────────────────
            "DOCS_PATH",
            "WATCH_PATH",
            "WATCH_DEBOUNCE_SECONDS",
            "WATCH_RECURSIVE",
            "WATCH_IGNORE_PATTERNS",
            "INGEST_CHUNK_SIZE_DEFAULT",
            "INGEST_CHUNK_OVERLAP_DEFAULT",
            "PDF_EXTRACTOR",
            # ── Auth ───────────────────────────────────────────────────────
            "AUTH_DASHBOARD_ENABLED",
            "AUTH_ENABLED",
            "AUTH_DB_PATH",
            "JWT_SECURE",
            "SESSION_TIMEOUT",
            # ── Grafana ────────────────────────────────────────────────────
            "GRAFANA_URL",
            "GRAFANA_DASHBOARD_UID",
            # ── Rate Limiting ──────────────────────────────────────────────
            "RATE_LIMIT_ENABLED",
            "RATE_LIMIT_REQUESTS",
            "RATE_LIMIT_WINDOW",
            # ── Cache ──────────────────────────────────────────────────────
            "RLCACHE_ENABLED",
            "RLCACHE_TTL",
            "RLCACHE_MAX_ENTRIES",
            # ── Query Logging ──────────────────────────────────────────────
            "QUERY_LOG_ENABLED",
            "QUERY_LOG_PATH",
            "QUERY_LOG_RETENTION_DAYS",
            "QUERY_LOG_CLEANUP_INTERVAL_HOURS",
            # ── Health ─────────────────────────────────────────────────────
            "HEALTH_HOST",
            "HEALTH_PORT",
            # ── Tags ───────────────────────────────────────────────────────
            "TAGS_SEARCH_ENABLED",
            # ── Embedding Infrastructure ───────────────────────────────────
            "HTTP_POOL_CONNECTIONS",
            "HTTP_POOL_MAXSIZE",
            "HTTP_TIMEOUT",
            "CIRCUIT_BREAKER_THRESHOLD",
            "CIRCUIT_BREAKER_COOLDOWN",
            "CIRCUIT_BREAKER_COOLDOWN_MAX",
            "PROVIDER_BUDGET_WINDOW_SECONDS",
            "PROVIDER_BUDGET_MAX_REQUESTS",
            # ── LLM / Evaluation ───────────────────────────────────────────
            "OPENAI_BASE_URL",
            "LLM_MODEL",
            "EVAL_LLM_MODEL",
            # ── Optimization ───────────────────────────────────────────────
            "OPT_CHUNK_SIZE",
            "OPT_CHUNK_OVERLAP",
            "OPT_TOP_K",
            "OPT_DENSE_WEIGHT",
            "OPT_SPARSE_WEIGHT",
            "OPT_RRF_K",
            "OPT_DISTANCE_METRIC",
            "OPT_EVAL_BACKEND",
            # ── Reclassification ───────────────────────────────────────────
            "RECLASSIFY_BACKUP_RETENTION_DAYS",
        ]
        try:
            with get_connection(self._db_path) as conn:
                ensure_config_table(conn)
                for key in seed_keys:
                    row = conn.execute(
                        "SELECT 1 FROM config WHERE key = ?", (key,)
                    ).fetchone()
                    if row is None:
                        value = os.getenv(key)
                        if value is not None:
                            conn.execute(
                                """
                                INSERT INTO config (key, value, type,
                                                    group_name, description,
                                                    updated_at, updated_by)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    key,
                                    value,
                                    "string",
                                    "env_default",
                                    "Seeded from .env on startup",
                                    time.time(),
                                    "system",
                                ),
                            )
                bump_config_version(conn)
            self._cache_version = 0
        except Exception:
            log.warning(
                "ConfigLoader.load_from_env: SQLite unavailable, "
                "skipping env seed"
            )

    def _refresh_cache(self) -> None:
        try:
            with get_connection(self._db_path) as conn:
                current_version = get_config_version(conn)
                if current_version == self._cache_version:
                    return
                rows = conn.execute(
                    "SELECT key, value, type FROM config"
                ).fetchall()
                self._old_cache = dict(self._cache)
                self._cache = {
                    r["key"]: (r["value"], r["type"], time.time())
                    for r in rows
                }
                self._cache_version = current_version
        except Exception:
            log.warning(
                "ConfigLoader: cache refresh failed, using stale cache"
            )

    def get(self, key: str, default: Any = None) -> Any:
        self._refresh_cache()
        if key in self._cache:
            value, type_name, _ = self._cache[key]
            if value is None:
                return default
            return convert_value(value, type_name)
        return os.getenv(key, default)

    async def set(
        self,
        key: str,
        value: str,
        type_name: str = "string",
        group_name: str = "general",
        description: str = "",
        updated_by: str = "system",
    ) -> dict:
        validation_error = validate_type(value, type_name)
        if validation_error:
            raise ValueError(validation_error)

        try:
            with get_connection(self._db_path) as conn:
                ensure_config_table(conn)
                conn.execute(
                    """
                    INSERT INTO config (key, value, type, group_name,
                                        description, updated_at, updated_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value       = excluded.value,
                        type        = excluded.type,
                        group_name  = excluded.group_name,
                        description = excluded.description,
                        updated_at  = excluded.updated_at,
                        updated_by  = excluded.updated_by
                    """,
                    (
                        key,
                        str(value),
                        type_name,
                        group_name,
                        description,
                        time.time(),
                        updated_by,
                    ),
                )
                bump_config_version(conn)
        except Exception as e:
            log.error("ConfigLoader.set failed for '%s': %s", key, e)
            raise

        self._cache_version = 0
        self._notify_observers(key, value)
        return {
            "key": key,
            "value": value,
            "type": type_name,
            "group_name": group_name,
            "description": description,
        }

    async def get_item(self, key: str) -> Optional[dict]:
        self._refresh_cache()
        try:
            with get_connection(self._db_path) as conn:
                row = conn.execute(
                    "SELECT * FROM config WHERE key = ?", (key,)
                ).fetchone()
                if row is None:
                    return None
                return dict(row)
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        try:
            with get_connection(self._db_path) as conn:
                ensure_config_table(conn)
                cursor = conn.execute(
                    "DELETE FROM config WHERE key = ?", (key,)
                )
                if cursor.rowcount == 0:
                    return False
                bump_config_version(conn)
        except Exception as e:
            log.error("ConfigLoader.delete failed for '%s': %s", key, e)
            raise

        self._cache_version = 0
        self._notify_observers(key, None)
        return True

    async def get_all(self, group_name: Optional[str] = None) -> list[dict]:
        self._refresh_cache()
        try:
            with get_connection(self._db_path) as conn:
                if group_name:
                    rows = conn.execute(
                        "SELECT * FROM config WHERE group_name = ? "
                        "ORDER BY group_name, key",
                        (group_name,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM config ORDER BY group_name, key"
                    ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    async def reset_all(self) -> int:
        try:
            with get_connection(self._db_path) as conn:
                ensure_config_table(conn)
                cursor = conn.execute("DELETE FROM config")
                deleted = cursor.rowcount
                bump_config_version(conn)
        except Exception as e:
            log.error("ConfigLoader.reset_all failed: %s", e)
            raise

        self._cache_version = 0
        self._notify_observers("*", None)
        return deleted

    async def get_aliases(self) -> dict[str, str]:
        self._refresh_cache()
        try:
            entries = await self.get_all(group_name="provider_alias")
            aliases: dict[str, str] = {}
            prefix = "provider_alias."
            for entry in entries:
                key: str = entry["key"]
                if key.startswith(prefix):
                    alias_name = key[len(prefix) :]
                    aliases[alias_name] = str(entry["value"])
            return aliases
        except Exception:
            log.warning("ConfigLoader.get_aliases failed")
            return {}

    async def resolve_alias(self, alias_name: str) -> Optional[str]:
        full_key = f"provider_alias.{alias_name}"
        entry = await self.get_item(full_key)
        if entry is None:
            return None
        return str(entry["value"])

    def on_change(
        self,
        key_or_pattern: str,
        callback: Optional[Callable[[str, Any], None]] = None,
    ) -> Any:
        """Register an observer callback for config changes.

        Supports both direct registration and decorator syntax:

            loader.on_change("KEY", callback)
            @loader.on_change("KEY")
            def my_callback(key, value):
                ...
        """
        if callback is None:

            def decorator(
                cb: Callable[[str, Any], None],
            ) -> Callable[[str, Any], None]:
                self._observers.append((key_or_pattern, cb))
                return cb

            return decorator

        self._observers.append((key_or_pattern, callback))
        return callback

    def reload_if_changed(self) -> bool:
        """Check for config changes and notify observers synchronously.

        Returns True if any changes were detected and observers were
        notified, False otherwise.
        """
        self._old_cache = dict(self._cache)
        self._refresh_cache()
        changed = False
        # Detect new or changed keys
        for key, (new_val, new_type, _) in self._cache.items():
            old = self._old_cache.get(key)
            if old is None or old[0] != new_val or old[1] != new_type:
                self._notify_observers(key, convert_value(new_val, new_type))
                changed = True
        # Detect deleted keys
        for key, (old_val, old_type, _) in self._old_cache.items():
            if key not in self._cache:
                self._notify_observers(key, None)
                changed = True
        return changed

    def _notify_observers(self, key: str, value: Any) -> None:
        for pattern, callback in self._observers:
            if pattern == "*" or pattern == key:
                try:
                    callback(key, value)
                except Exception:
                    log.warning(
                        "ConfigLoader observer hook failed: %s/%s",
                        pattern,
                        key,
                    )
            elif pattern.endswith(".*") and key.startswith(pattern[:-2]):
                try:
                    callback(key, value)
                except Exception:
                    log.warning(
                        "ConfigLoader observer hook failed: %s/%s",
                        pattern,
                        key,
                    )

    def is_tag_search_enabled(self) -> bool:
        """Check if tag search integration is enabled.

        Phase 51: Tags are stored in Qdrant payload but not indexed
        for search by default. Set TAGS_SEARCH_ENABLED=true to enable.

        Returns:
            True if tag search is enabled, False otherwise.
        """
        val = self.get("TAGS_SEARCH_ENABLED", "false")
        return str(val).lower() in ("true", "1", "yes", "on")
