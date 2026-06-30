# Phase 40: Configuration Backlog - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 9
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `kb_server/config/loader.py` | service | CRUD + event-driven | `kb_server/config/loader.py` (existing) | exact (self) |
| `kb_server/config/router.py` | controller | request-response | `kb_server/config/router.py` (existing) | exact (self) |
| `kb_server/config/__init__.py` | utility | transform | `kb_server/auth/__init__.py` | role-match |
| `config/bootstrap_env.py` | utility | transform | `config/bootstrap_env.py` (existing) | exact (self) |
| `kb_server/server.py` | controller | event-driven + request-response | `kb_server/server.py` (existing) | exact (self) |
| `kb_server/health_server.py` | controller | request-response | `kb_server/health_server.py` (existing) | exact (self) |
| `tests/test_config_api.py` | test | CRUD | `tests/test_config_api.py` (existing) | exact (self) |
| `tests/test_provider_alias.py` | test | event-driven | `tests/test_provider_alias.py` (existing) | exact (self) |
| `observability/metrics.py` | utility | transform | `observability/metrics.py` (existing) | exact (self) |

## Pattern Assignments

### `kb_server/config/loader.py` (service, CRUD + event-driven)

**Analog:** `kb_server/config/loader.py` (lines 1-231, already implemented in 40-01)

**Imports pattern** (lines 1-15):
```python
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
```

**Core CRUD pattern** (lines 66-118):
```python
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
                    (key, str(value), type_name, group_name, description,
                     time.time(), updated_by),
                )
                bump_config_version(conn)
        except Exception as e:
            log.error("ConfigLoader.set failed for '%s': %s", key, e)
            raise

        self._cache_version = 0
        self._notify_observers(key, value)
        return { ... }
```

**Observer / event bus pattern** (lines 207-231):
```python
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
                        pattern, key,
                    )
            elif pattern.endswith(".*") and key.startswith(pattern[:-2]):
                try:
                    callback(key, value)
                except Exception:
                    log.warning(
                        "ConfigLoader observer hook failed: %s/%s",
                        pattern, key,
                    )
```

**Cache refresh + version detection** (lines 38-55):
```python
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
```

**Silent degradation (CONF-08)** (lines 28-37):
```python
    def _init_db(self) -> None:
        try:
            with get_connection(self._db_path) as conn:
                ensure_config_table(conn)
            log.info("ConfigLoader initialized: %s", self._db_path)
        except Exception:
            log.warning(
                "ConfigLoader: SQLite unavailable, falling through to env"
            )
```

**What to add for 40-02:**
- `reload_if_changed()` method: wraps `_refresh_cache()` + version check, then calls matching observer callbacks synchronously.
- `.env` file layer: read `.env` path from `os.getenv("KB_ENV_FILE")` or `Path(__file__).parent.parent / ".env"`, then use `load_dotenv` (already imported in `bootstrap_env`) to populate the env layer. Since `bootstrap_env` already loads `.env`, ConfigLoader just needs to fall through `os.getenv` (already done). The "layered" aspect is: SQLite → current `os.environ` (populated by dotenv) → hardcoded default.
- Decorator registration: `@loader.on_change("KEY")` should be callable as a decorator. Add `return callback` at end of `on_change`.

---

### `kb_server/config/router.py` (controller, request-response)

**Analog:** `kb_server/config/router.py` (lines 1-122, already implemented in 40-01)

**Imports pattern** (lines 1-7):
```python
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger("kb-mcp.config.router")
```

**Router definition + auth dependency** (lines 32-36):
```python
router = APIRouter(
    prefix="/api/v1/config",
    tags=["config"],
    dependencies=[Depends(_verify_config_auth)],
)
```

**Pydantic request/response models** (lines 39-54):
```python
class ConfigUpdate(BaseModel):
    value: str
    type: str = "string"
    group_name: Optional[str] = None
    description: Optional[str] = None


class ConfigResponse(BaseModel):
    key: str
    value: str
    type: str
    group_name: str
    description: str
    updated_at: float
    updated_by: str
```

**Service retrieval from app.state** (lines 56-62):
```python
def _get_loader(request: Request):
    loader = getattr(request.app.state, "config_loader", None)
    if loader is None:
        raise HTTPException(
            status_code=503, detail="Config loader not available"
        )
    return loader
```

**Handler pattern: GET /{key}** (lines 72-80):
```python
@router.get("/{key}")
async def get_config(request: Request, key: str):
    loader = _get_loader(request)
    entry = await loader.get_item(key)
    if entry is None:
        raise HTTPException(
            status_code=404, detail=f"Config key not found: {key}"
        )
    return entry
```

**Handler pattern: PUT /{key} with validation** (lines 83-104):
```python
@router.put("/{key}")
async def set_config(request: Request, key: str, body: ConfigUpdate):
    loader = _get_loader(request)
    try:
        result = await loader.set(
            key=key,
            value=body.value,
            type_name=body.type,
            group_name=body.group_name or "general",
            description=body.description or "",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation failed",
                "field": "value",
                "type": body.type,
                "reason": str(e),
            },
        )
    return result
```

**What to add for 40-02:**
- All endpoints already exist. No changes needed for 40-02 unless the planner wants to add a `reload` endpoint or change the 422 format.

---

### `kb_server/config/__init__.py` (utility, transform)

**Analog:** `kb_server/auth/__init__.py`

**Pattern:** Typical package `__init__.py` with exports. Read to confirm exact pattern.

```bash
# Read analog
$ cat kb_server/auth/__init__.py
```

**Pattern to copy** (lines 1-8, typical style):
```python
"""Config package — database-backed configuration loader."""

from kb_server.config.loader import ConfigLoader
from kb_server.config.router import router

__all__ = ["ConfigLoader", "router"]
```

**What to add for 40-02:**
- Export `ConfigLoader` and `router` so other modules can do `from kb_server.config import ConfigLoader`.

---

### `config/bootstrap_env.py` (utility, transform)

**Analog:** `config/bootstrap_env.py` (lines 1-45, already implemented)

**Core pattern** (lines 15-45):
```python
def bootstrap_env(env_file: str | None = None) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        log.debug("python-dotenv not installed; skipping .env load")
        return

    if env_file is None:
        env_file = os.environ.get("KB_ENV_FILE")
    if env_file is None:
        env_file = str(Path(__file__).parent.parent / ".env")

    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path, override=True)
        log.debug(f"Loaded env from {env_path}")
    else:
        log.debug(f"No .env file found at {env_path}; skipping")
```

**What to add for 40-02:**
- After `load_dotenv()` returns, initialize `ConfigLoader`, create tables, and seed known keys. Then store the loader instance globally or return it so `server.py` and `health_server.py` can access it.
- Example addition:
```python
    # After load_dotenv succeeds:
    from kb_server.config.loader import ConfigLoader
    global _config_loader
    _config_loader = ConfigLoader()
    _config_loader.seed_from_env()   # new method
    return _config_loader
```

---

### `kb_server/server.py` (controller, event-driven + request-response)

**Analog:** `kb_server/server.py` (lines 1-1813, already implemented)

**Bootstrap import pattern** (lines 21-25):
```python
# ── Load .env before any os.getenv reads
from config.bootstrap_env import bootstrap_env

bootstrap_env()
```

**Module-level config read pattern** (lines 75-116):
```python
# ── Config ────────────────────────────────────────────────────────
TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")  # stdio | sse
SSE_HOST = os.getenv("SSE_HOST", "127.0.0.1")
SSE_PORT = int(os.getenv("SSE_PORT", "8765"))
TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))

# PHASE 33: Rate limiting config
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() in (
    "true", "1", "yes",
)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
```

**Periodic task scheduling pattern** (lines 1309-1335):
```python
async def _schedule_log_cleanup() -> None:
    interval_seconds = QUERY_LOG_CLEANUP_INTERVAL_HOURS * 3600
    while True:
        await asyncio.sleep(interval_seconds)
        if query_logger:
            try:
                deleted = query_logger.cleanup_old_queries(
                    QUERY_LOG_RETENTION_DAYS
                )
                log.info(...)
            except Exception as e:
                log.error(f"Query log cleanup failed: {e}", exc_info=True)
```

**Mounting sub-app on Starlette** (lines 1608-1615):
```python
        starlette_app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/health", endpoint=handle_health),
                Mount("/messages/", app=sse.handle_post_message),
                Mount("/api/v1", app=_build_auth_app()),
            ]
        )
```

**What to add for 40-02:**
- Replace `os.getenv()` calls with `config_loader.get()` calls. Pattern: `TRANSPORT = config_loader.get("MCP_TRANSPORT", "stdio")`.
- Register `on_change` hooks for hot-reloadable values (e.g., `RATE_LIMIT_ENABLED`, `TOP_K`).
- Inject `config_loader` into `app.state` (or global) so `embed_client.py` can call `init_alias_resolution()`.
- Schedule a periodic `reload_if_changed()` task every 5-10 seconds if the planner chooses polling fallback.

---

### `kb_server/health_server.py` (controller, request-response)

**Analog:** `kb_server/health_server.py` (lines 1-140, already implemented)

**App creation pattern** (lines 48-53):
```python
app = FastAPI(
    title="KB-RAG Health Check",
    description="Health check endpoints for KB-RAG services",
    version="1.0.0",
)
```

**What to add for 40-02:**
- Mount config router: `app.include_router(config_router)` after creating the FastAPI app.
- Inject `ConfigLoader` into `app.state`: `app.state.config_loader = config_loader`.
- Pattern copied from `test_config_api.py` (line 31-32):
```python
    app.state.config_loader = loader
    app.include_router(router)
```

---

### `tests/test_config_api.py` (test, CRUD)

**Analog:** `tests/test_config_api.py` (lines 1-270, already implemented)

**Fixture pattern** (lines 13-38):
```python
@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def loader(db_path):
    ldr = ConfigLoader(db_path=db_path)
    return ldr


@pytest.fixture
def app(loader):
    app = FastAPI()
    app.state.config_loader = loader
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)
```

**Test pattern: async ConfigLoader test** (lines 44-50):
```python
@pytest.mark.asyncio
async def test_config_loader_set_get(loader):
    result = await loader.set("TEST_KEY", "test_value")
    assert result["key"] == "TEST_KEY"
    assert result["value"] == "test_value"
    val = loader.get("TEST_KEY")
    assert val == "test_value"
```

**Test pattern: REST API test** (lines 162-166):
```python
def test_api_list_config(client):
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

**Test pattern: validation error** (lines 224-232):
```python
def test_api_validation_error(client):
    resp = client.put(
        "/api/v1/config/BAD_INT",
        json={"value": "not_a_number", "type": "int"},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "Validation failed"
```

**What to add for 40-02:**
- Tests for `reload_if_changed()` returning True/False based on version bump.
- Tests for `on_change` decorator syntax.
- Tests for `.env` fallback layer (set env var, delete DB key, assert `loader.get()` returns env value).
- Tests for `ConfigLoader` silent degradation when DB file is missing.

---

### `tests/test_provider_alias.py` (test, event-driven)

**Analog:** `tests/test_provider_alias.py` (lines 91-105)

**Observer test pattern** (lines 91-105):
```python
    @pytest.mark.asyncio
    async def test_wildcard_observer(self, loader):
        changes = []

        def callback(key, value):
            changes.append((key, value))

        loader.on_change("provider_alias.*", callback)
        await loader.set(
            "provider_alias.test_alias",
            "test_val",
            group_name="provider_alias",
        )
        assert len(changes) == 1
        assert changes[0] == ("provider_alias.test_alias", "test_val")
```

**What to add for 40-02:**
- Test decorator registration: `@loader.on_change("KEY")`.
- Test `reload_if_changed()` triggers callbacks only when version changes.
- Test multiple observers, one failing observer does not block others.

---

### `observability/metrics.py` (utility, transform)

**Analog:** `observability/metrics.py` (search for `Gauge` / `Counter` definitions)

**Pattern to extract** (from `observability/metrics.py`):
```python
from prometheus_client import Counter, Gauge, Histogram

# Example gauge
config_version_gauge = Gauge(
    "kb_rag_config_version",
    "Current version of the runtime configuration",
)
```

**What to add for 40-02:**
- Add `kb_rag_config_version` Gauge. Update it in `ConfigLoader._notify_observers()` or in the router after PUT/reset.

---

## Shared Patterns

### Authentication Middleware
**Source:** `kb_server/config/router.py` (lines 10-30)
**Apply to:** `kb_server/config/router.py` (no change needed for 40-02)
```python
def _verify_config_auth(request: Request):
    auth_header = request.headers.get("Authorization", "")
    api_key = None
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:].strip()
    if not api_key:
        api_key = request.headers.get("X-API-Key")
    if not api_key:
        from kb_server.auth import is_auth_enabled
        if not is_auth_enabled():
            return
        raise HTTPException(status_code=401, detail="API key required")
    from kb_server.auth_registry import get_registry
    registry = get_registry()
    if not registry.verify_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
```

### Error Handling
**Source:** `kb_server/config/router.py` (lines 94-103)
**Apply to:** All PUT handlers in `kb_server/config/router.py`
```python
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation failed",
                "field": "value",
                "type": body.type,
                "reason": str(e),
            },
        )
```

### SQLite Connection Context Manager
**Source:** `kb_server/config/db.py` (lines 20-38)
**Apply to:** `kb_server/config/loader.py`, any new SQLite consumers
```python
@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
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
```

### Graceful Degradation
**Source:** `kb_server/config/loader.py` (lines 28-37)
**Apply to:** All ConfigLoader DB operations
```python
    def _init_db(self) -> None:
        try:
            with get_connection(self._db_path) as conn:
                ensure_config_table(conn)
            log.info("ConfigLoader initialized: %s", self._db_path)
        except Exception:
            log.warning("ConfigLoader: SQLite unavailable, falling through to env")
```

### Periodic Background Task
**Source:** `kb_server/server.py` (lines 1316-1335)
**Apply to:** `kb_server/server.py` if planner adds a periodic `reload_if_changed()` task
```python
async def _schedule_log_cleanup() -> None:
    interval_seconds = QUERY_LOG_CLEANUP_INTERVAL_HOURS * 3600
    while True:
        await asyncio.sleep(interval_seconds)
        if query_logger:
            try:
                deleted = query_logger.cleanup_old_queries(...)
                log.info(...)
            except Exception as e:
                log.error(f"Query log cleanup failed: {e}", exc_info=True)
```

### FastAPI Router Mounting
**Source:** `test_config_api.py` (lines 28-32)
**Apply to:** `kb_server/health_server.py`
```python
app = FastAPI()
app.state.config_loader = loader
app.include_router(router)
```

### Starlette Sub-app Mounting
**Source:** `kb_server/server.py` (lines 1608-1615)
**Apply to:** `kb_server/server.py` if SSE transport needs config router
```python
starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/api/v1", app=_build_auth_app()),
    ]
)
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| None | — | — | All files for 40-02 have direct analogs in the existing config module or related patterns in the codebase. |

## Metadata

**Analog search scope:** `kb_server/`, `config/`, `tests/`, `observability/`
**Files scanned:** 18
**Pattern extraction date:** 2026-06-16
