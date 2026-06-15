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
        self._cache_version: int = 0
        self._observers: list[tuple[str, Callable[[str, Any], None]]] = []

        self._init_db()

    def _init_db(self) -> None:
        try:
            with get_connection(self._db_path) as conn:
                ensure_config_table(conn)
            log.info("ConfigLoader initialized: %s", self._db_path)
        except Exception:
            log.warning(
                "ConfigLoader: SQLite unavailable, falling through to env"
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
        self, key_or_pattern: str, callback: Callable[[str, Any], None]
    ) -> None:
        self._observers.append((key_or_pattern, callback))

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
