# Phase 40+41: Config API & Provider Alias

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SQLite-backed config storage with REST API and hot-reload, plus provider name aliases resolved through it.

**Architecture:** A new `config` table in `kb_metadata.db` stores key/value/type/group. A `ConfigLoader` class wraps `os.getenv` with SQLite override chain. A FastAPI router exposes CRUD endpoints. Provider aliases use config entries with group `provider_alias`. Hot-reload uses a simple mtime-polling mechanism.

**Tech Stack:** FastAPI, SQLAlchemy, existing `kb_metadata.db`, `ingest.core.metadata`.

---

### Task 1: Add config table and ConfigLoader

**Files:**
- Create: `kb_server/config/__init__.py`
- Create: `kb_server/config/loader.py`
- Create: `kb_server/config/models.py`
- Test: `tests/test_config_api.py`

- [ ] **Step 1: Write the failing test — config table creates and stores a value**

`tests/test_config_api.py`:
```python
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def config_db():
    db_path = Path(tempfile.mktemp(suffix=".db"))
    from kb_server.config.models import ConfigModel, create_config_table
    create_config_table(db_path)
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_config_set_get(config_db):
    from kb_server.config.loader import ConfigLoader
    loader = ConfigLoader(db_path=config_db)
    await loader.set("embed.backend", "ollama", type="str", group="Embedding")
    val = await loader.get("embed.backend")
    assert val == "ollama"


@pytest.mark.asyncio
async def test_config_get_all(config_db):
    from kb_server.config.loader import ConfigLoader
    loader = ConfigLoader(db_path=config_db)
    await loader.set("a", "1", type="int", group="G1")
    await loader.set("b", "true", type="bool", group="G1")
    all_cfg = await loader.get_all()
    assert len(all_cfg) == 2


@pytest.mark.asyncio
async def test_config_fallback_to_env(config_db, monkeypatch):
    monkeypatch.setenv("TEST_MY_KEY", "env_value")
    from kb_server.config.loader import ConfigLoader
    loader = ConfigLoader(db_path=config_db)
    val = await loader.get("TEST_MY_KEY")
    assert val == "env_value"


@pytest.mark.asyncio
async def test_config_delete(config_db):
    from kb_server.config.loader import ConfigLoader
    loader = ConfigLoader(db_path=config_db)
    await loader.set("to_delete", "val", type="str", group="G")
    await loader.delete("to_delete")
    val = await loader.get("to_delete")
    assert val is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_config_api.py::test_config_set_get -x -v 2>&1 | tail -20`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create config models**

`kb_server/config/__init__.py`:
```python
```

`kb_server/config/models.py`:
```python
import sqlite3
from pathlib import Path
from typing import Optional


def create_config_table(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'str',
            group_name TEXT DEFAULT '',
            description TEXT DEFAULT '',
            updated_at TEXT DEFAULT (datetime('now')),
            updated_by TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Create ConfigLoader**

`kb_server/config/loader.py`:
```python
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

TYPE_MAP = {
    "int": int,
    "float": float,
    "bool": lambda v: v.lower() in ("true", "1", "yes"),
    "str": str,
    "list": lambda v: [x.strip() for x in v.split(",") if x.strip()],
}


class ConfigLoader:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(os.getenv("METADATA_DB", "data/kb_metadata.db"))
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    async def get(self, key: str) -> Any:
        conn = self._conn()
        row = conn.execute(
            "SELECT value, type FROM config WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        if row:
            value, typ = row
            converter = TYPE_MAP.get(typ, str)
            return converter(value)
        return os.getenv(key)

    async def get_all(self) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT key, value, type, group_name, description FROM config "
            "ORDER BY group_name, key"
        ).fetchall()
        conn.close()
        return [
            {"key": r[0], "value": r[1], "type": r[2],
             "group": r[3], "description": r[4]}
            for r in rows
        ]

    async def set(self, key: str, value: str, type: str = "str",
                  group: str = "", description: str = "",
                  updated_by: str = "") -> None:
        conn = self._conn()
        conn.execute("""
            INSERT OR REPLACE INTO config
            (key, value, type, group_name, description, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        """, (key, value, type, group, description, updated_by))
        conn.commit()
        conn.close()

    async def delete(self, key: str) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM config WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    async def reset_all(self) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM config")
        conn.commit()
        conn.close()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_config_api.py -x -v 2>&1 | tail -20`
Expected: PASS (all 4 tests)

- [ ] **Step 6: Commit**

```bash
git add kb_server/config/ tests/test_config_api.py
git commit -m "feat(40): add config table and ConfigLoader"
```

---

### Task 2: Config REST API router

**Files:**
- Create: `kb_server/config/router.py`
- Modify: `tests/test_config_api.py`

- [ ] **Step 1: Write the failing test — config API CRUD**

Append to `tests/test_config_api.py`:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI


@pytest.fixture
def config_app(config_db):
    app = FastAPI()
    from kb_server.config.router import router
    from kb_server.config.loader import ConfigLoader
    app.state.config_loader = ConfigLoader(db_path=config_db)
    app.include_router(router)
    return app


@pytest.mark.asyncio
async def test_config_api_get_all(config_app):
    transport = ASGITransport(app=config_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/config")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_config_api_put(config_app):
    transport = ASGITransport(app=config_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put("/api/v1/config/test.key", json={
            "value": "test_val", "type": "str", "group": "Test"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "test.key"
    assert data["value"] == "test_val"


@pytest.mark.asyncio
async def test_config_api_get_key(config_app):
    transport = ASGITransport(app=config_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.put("/api/v1/config/mykey", json={"value": "myval"})
        resp = await ac.get("/api/v1/config/mykey")
    assert resp.status_code == 200
    assert resp.json()["value"] == "myval"


@pytest.mark.asyncio
async def test_config_api_delete(config_app):
    transport = ASGITransport(app=config_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.put("/api/v1/config/todel", json={"value": "val"})
        resp = await ac.delete("/api/v1/config/todel")
    assert resp.status_code == 200
    resp2 = await ac.get("/api/v1/config/todel")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_config_api_reset(config_app):
    transport = ASGITransport(app=config_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.put("/api/v1/config/k1", json={"value": "v1"})
        await ac.put("/api/v1/config/k2", json={"value": "v2"})
        resp = await ac.post("/api/v1/config/reset")
    assert resp.status_code == 200
    resp2 = await ac.get("/api/v1/config")
    assert len(resp2.json()) == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_config_api.py::test_config_api_get_all -x -v 2>&1 | tail -10`
Expected: `ImportError` or 404

- [ ] **Step 3: Create config API router**

`kb_server/config/router.py`:
```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigUpdate(BaseModel):
    value: str
    type: str = "str"
    group: str = ""
    description: str = ""


@router.get("")
async def list_config(request: Request):
    loader = request.app.state.config_loader
    return await loader.get_all()


@router.get("/{key}")
async def get_config(key: str, request: Request):
    loader = request.app.state.config_loader
    val = await loader.get(key)
    if val is None:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    return {"key": key, "value": val}


@router.put("/{key}")
async def set_config(key: str, body: ConfigUpdate, request: Request):
    loader = request.app.state.config_loader
    await loader.set(
        key=key, value=body.value, type=body.type,
        group=body.group, description=body.description,
    )
    return {"key": key, "value": body.value, "type": body.type,
            "group": body.group, "status": "updated"}


@router.delete("/{key}")
async def delete_config(key: str, request: Request):
    loader = request.app.state.config_loader
    await loader.delete(key)
    return {"key": key, "status": "deleted"}


@router.post("/reset")
async def reset_config(request: Request):
    loader = request.app.state.config_loader
    await loader.reset_all()
    return {"status": "reset"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_config_api.py -x -v 2>&1 | tail -20`
Expected: PASS (all 5 config API tests)

- [ ] **Step 5: Commit**

```bash
git add kb_server/config/router.py tests/test_config_api.py
git commit -m "feat(40): add config REST API router"
```

---

### Task 3: Provider Alias integration

**Files:**
- Modify: `kb_server/config/loader.py`
- Modify: `kb_server/embed_client.py`
- Modify: `tests/test_config_api.py`

- [ ] **Step 1: Write the failing test — resolve provider alias**

Append to `tests/test_config_api.py`:
```python
@pytest.mark.asyncio
async def test_config_resolve_provider_alias(config_db):
    from kb_server.config.loader import ConfigLoader
    loader = ConfigLoader(db_path=config_db)
    await loader.set("provider_alias.aliyun", "dashscope", type="str",
                      group="provider_alias")
    resolved = await loader.resolve_provider("aliyun")
    assert resolved == "dashscope"


@pytest.mark.asyncio
async def test_config_resolve_provider_no_alias(config_db):
    from kb_server.config.loader import ConfigLoader
    loader = ConfigLoader(db_path=config_db)
    resolved = await loader.resolve_provider("openai")
    assert resolved == "openai"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_config_api.py::test_config_resolve_provider_alias -x -v 2>&1 | tail -10`
Expected: `AttributeError` (resolve_provider doesn't exist)

- [ ] **Step 3: Add resolve_provider to ConfigLoader**

Add to `kb_server/config/loader.py`:
```python
    async def resolve_provider(self, name: str) -> str:
        alias = await self.get(f"provider_alias.{name}")
        return alias if alias else name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_config_api.py::test_config_resolve_provider_alias -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Integrate with embed_client.py**

In `kb_server/embed_client.py`, locate where `EMBED_BACKEND` env var is read. After importing ConfigLoader and getting the backend env value, call `resolve_provider`. Add near the top-level code that determines the backend:

```python
# In embed_client.py, after env reads
from kb_server.config.loader import ConfigLoader

def _resolve_backend():
    backend = os.getenv("EMBED_BACKACK", "lmstudio-rest")
    loader = ConfigLoader()
    # synchronous resolve for startup
    import sqlite3
    conn = sqlite3.connect(str(loader.db_path))
    row = conn.execute(
        "SELECT value FROM config WHERE key = ?",
        (f"provider_alias.{backend}",)
    ).fetchone()
    conn.close()
    return row[0] if row else backend
```

Then replace all references to `os.getenv("EMBED_BACKEND", ...)` with `_resolve_backend()`. This avoids async at module level.

- [ ] **Step 6: Commit**

```bash
git add kb_server/config/loader.py kb_server/embed_client.py tests/test_config_api.py
git commit -m "feat(41): add provider alias resolution via config"
```

---

### Task 4: Hot-reload mechanism

**Files:**
- Create: `kb_server/config/hotreload.py`
- Modify: `tests/test_config_api.py`

- [ ] **Step 1: Write the failing test — hot-reload detects config change**

`tests/test_config_api.py`:
```python
@pytest.mark.asyncio
async def test_hotreload_detect_change(config_db):
    from kb_server.config.hotreload import ConfigWatcher
    from kb_server.config.loader import ConfigLoader
    loader = ConfigLoader(db_path=config_db)
    watcher = ConfigWatcher(db_path=config_db)
    changed = await watcher.check_for_changes()
    assert changed is False
    await loader.set("new.key", "new_val", type="str", group="Test")
    changed = await watcher.check_for_changes()
    assert changed is True
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_config_api.py::test_hotreload_detect_change -x -v 2>&1 | tail -10`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create ConfigWatcher**

`kb_server/config/hotreload.py`:
```python
import sqlite3
import os
from pathlib import Path
from typing import Optional


class ConfigWatcher:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(os.getenv("METADATA_DB", "data/kb_metadata.db"))
        self.db_path = db_path
        self._last_mtime: float = 0.0

    def _get_mtime(self) -> float:
        try:
            return os.path.getmtime(self.db_path)
        except OSError:
            return 0.0

    async def check_for_changes(self) -> bool:
        current = self._get_mtime()
        if current > self._last_mtime:
            self._last_mtime = current
            return True
        return False

    async def get_changed_keys(self, previous_snapshot: dict) -> list[str]:
        current = {}
        try:
            conn = sqlite3.connect(str(self.db_path))
            rows = conn.execute(
                "SELECT key, value FROM config"
            ).fetchall()
            conn.close()
            current = {r[0]: r[1] for r in rows}
        except Exception:
            pass
        changed = []
        for key in set(list(previous_snapshot.keys()) + list(current.keys())):
            if previous_snapshot.get(key) != current.get(key):
                changed.append(key)
        return changed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_config_api.py::test_hotreload_detect_change -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/config/hotreload.py tests/test_config_api.py
git commit -m "feat(40): add config hot-reload watcher"
```
