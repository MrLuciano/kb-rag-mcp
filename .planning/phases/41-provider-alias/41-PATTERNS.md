# Phase 41: Provider Alias - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 3 (2 modified, 1 new)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `kb_server/config/loader.py` | config/utility | request-response | Self (existing ConfigLoader methods like `get_all`, `get_item`) | exact |
| `kb_server/embed_client.py` | utility | request-response | `_try_provider()` / `_dispatch_with_resilience()` | role-match |
| `tests/test_provider_alias.py` | test | N/A | `test_config_api.py` + `test_embed_client_unit.py` | role-match |

## Pattern Assignments

### `kb_server/config/loader.py` — Add alias lookup methods

**Role:** config/utility — **Data flow:** request-response (lookup from SQLite config table)

**Analog:** Self — existing `ConfigLoader` methods (`get_all`, `get_item`, `get`)

All ConfigLoader read methods follow the same pattern: `_refresh_cache()` + SQLite query + try/except with graceful degradation (log warning, return safe default). The new `resolve_alias()` and `get_aliases()` methods must follow identical conventions.

---

**Imports pattern** (loader.py lines 1-16):
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

**`get_all(group_name=...)` — closest analog for `get_aliases()`** (lines 151-167):
```python
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
```

**Key pattern:** `get_all` with `group_name` filter is the primary mechanism to discover `provider_alias.*` entries. The new `get_aliases()` method should call `get_all(group_name='provider_alias')` and convert to `dict[str, str]`.

**`get_item(key)` — closest analog for `resolve_alias()`** (lines 120-131):
```python
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
```

**Key pattern:** `_refresh_cache()` + SQLite query + `try`/`except Exception` returning `None` on failure. The new `resolve_alias(alias)` method should follow this: construct the full key as `provider_alias.{alias}`, query the `value` column, return it if found, return `None` if missing.

**Error handling pattern** (all ConfigLoader methods share this):
```python
# Graceful degradation on SQLite failures
try:
    with get_connection(self._db_path) as conn:
        # ... operation ...
except Exception:
    log.warning("ConfigLoader: ... ")
    return []           # or None, or default
```

**Module logger pattern** (line 16):
```python
log = logging.getLogger("kb-mcp.config.loader")
```

---

### `kb_server/embed_client.py` — Add alias resolution at provider-selection time

**Role:** utility — **Data flow:** request-response

**Analog:** `_try_provider()` lines 321-390 — the function where provider names are first used against `_BACKENDS`. Alias resolution should inject before the `_BACKENDS.get(provider)` lookup.

---

**Imports pattern** (lines 24-37) — note no config import currently exists:
```python
import asyncio
import logging
import os
import re
import time
from typing import Optional

import httpx

from observability.metrics import MetricsCollector, record_batch_embedding
from kb_server.cache.manager import CacheManager
from kb_server.circuit_breaker import CircuitBreaker, CircuitState
from kb_server.provider_budget import ProviderBudget

log = logging.getLogger("kb-mcp.embed")
```

**New import to add** (follows existing local import pattern):
```python
from kb_server.config.loader import ConfigLoader
```

**Provider chain pattern** — current module-level parsing (lines 51-54) — this is where alias resolution should integrate (lazy, per-call, not at import time per D-02):
```python
PROVIDER_CHAIN = [
    p.strip() for p in BACKEND.split(";") if p.strip()
]
PRIMARY_BACKEND = PROVIDER_CHAIN[0] if PROVIDER_CHAIN else BACKEND
```

**`_try_provider()` — the key integration point** (lines 321-390) — alias resolution should happen right before the `_BACKENDS.get(provider)` lookup at line 337:
```python
async def _try_provider(
    provider: str, text: str
) -> Optional[list[float]]:
    """..."""
    fn = _BACKENDS.get(provider)
    if fn is None:
        log.warning("Unknown provider '%s' — not in _BACKENDS", provider)
        return None
    # ... circuit breaker, budget, call ...
```

**Integration approach:** At the start of `_try_provider` (before line 337), resolve the alias:
```python
# Resolve alias if provider not directly in _BACKENDS
if provider not in _BACKENDS:
    resolved = _resolve_alias(provider)  # function/module-level helper
    if resolved:
        log.debug("Provider alias resolved: %s → %s", provider, resolved)
        provider = resolved
```

**"Log once per key" pattern** — follows existing `log.warning` convention in `_try_provider`:
```python
log.warning("Unknown provider '%s' — not in _BACKENDS", provider)
```

**`validate_providers()` — validation pattern** (lines 435-448) — alias resolution should also apply here so that `validate_providers` accepts aliased names:
```python
def validate_providers() -> None:
    for provider in PROVIDER_CHAIN:
        if provider not in _BACKENDS:
            raise ValueError(
                f"Invalid provider: '{provider}'. "
                f"Options: {list(_BACKENDS)}"
            )
```

**Error handling pattern** — `try`/`except Exception` with log + None return:
```python
except Exception as e:
    log.warning(
        "Provider '%s' failed (%s: %s)",
        provider,
        type(e).__name__,
        e,
    )
```

---

### `tests/test_provider_alias.py` — Unit tests for alias resolution

**Role:** test — **Data flow:** N/A

**Analogs:** Two separate analogs since testing covers both ConfigLoader and EmbedClient integration.

**Test file structure** — follows `test_config_api.py` pattern for loader tests:
```python
import os
import tempfile
from pathlib import Path

import pytest

from kb_server.config.loader import ConfigLoader
```

**ConfigLoader fixture pattern** (`test_config_api.py` lines 13-25):
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
```

**Async test pattern** for ConfigLoader methods (`test_config_api.py` lines 44-50):
```python
@pytest.mark.asyncio
async def test_config_loader_set_get(loader):
    result = await loader.set("TEST_KEY", "test_value")
    assert result["key"] == "TEST_KEY"
    assert result["value"] == "test_value"
    val = loader.get("TEST_KEY")
    assert val == "test_value"
```

**`get_all(group_name=...)` test pattern** (`test_config_api.py` lines 63-69):
```python
@pytest.mark.asyncio
async def test_config_loader_get_all_filtered(loader):
    await loader.set("KEY_C", "val_c", group_name="group1")
    await loader.set("KEY_D", "val_d", group_name="group2")
    group1 = await loader.get_all(group_name="group1")
    assert all(e["group_name"] == "group1" for e in group1)
    assert len(group1) == 1
```

**EmbedClient mock pattern** (`test_embed_client_unit.py` lines 22-39):
```python
def _fake_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp
```

**Provider chain test pattern** (`test_embed_client_unit.py` lines 78-93):
```python
@pytest.mark.asyncio
async def test_openai_compat_returns_embedding(monkeypatch):
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.PRIMARY_BACKEND = "openai-compat"

    mock_client = AsyncMock()
    mock_client.post.return_value = _fake_response(OPENAI_RESPONSE)
    ec._http_client = mock_client

    result = await ec.get_embedding("test text", use_cache=False)
    assert isinstance(result, list)
    assert len(result) == DIM
```

**`reset_provider_chain` fixture pattern** (`test_embed_client_unit.py` lines 68-76):
```python
@pytest.fixture(autouse=True)
def reset_provider_chain():
    """Reset PROVIDER_CHAIN between tests to match initial state."""
    yield
    # Restore to single-provider openai-compat default
    ec.PROVIDER_CHAIN.clear()
    ec.PROVIDER_CHAIN.append("openai-compat")
    ec.PRIMARY_BACKEND = "openai-compat"
```

**Alias-specific test plans:**
1. **ConfigLoader tests:** Set alias entries via `loader.set()` with `group_name='provider_alias'`, then call `get_aliases()` and verify dict mapping. Test `resolve_alias()` returns canonical name when found, None when missing.
2. **EmbedClient integration tests:** Mock the bundle or monkeypatch the alias resolution so that `_try_provider` with an aliased name resolves to a canonical backend. Verify the correct backend function is called.

---

## Shared Patterns

### Module Logger Pattern
**Source:** `kb_server/config/loader.py:16`, `kb_server/embed_client.py:38`
**Apply to:** All modified/new files
```python
log = logging.getLogger("kb-mcp.<module>")
```

### Graceful Degradation on SQLite Failure
**Source:** `kb_server/config/loader.py:28-36`, `kb_server/config/loader.py:52-55`, lines 166-167
**Apply to:** All new ConfigLoader methods
```python
try:
    with get_connection(self._db_path) as conn:
        # ... database operation ...
except Exception:
    log.warning("ConfigLoader: <description>")
    return None  # or [], or default
```

### Async Method Signature Convention
**Source:** `kb_server/config/loader.py` (all public DB methods are async)
**Apply to:** `resolve_alias()` and `get_aliases()` methods
```python
async def method_name(self, param: type) -> return_type:
    self._refresh_cache()
    try:
        ...
    except Exception:
        ...
```

### Monkeypatch Pattern for EmbedClient Tests
**Source:** `test_embed_client_unit.py` lines 80-84, 103-108, etc.
**Apply to:** EmbedClient alias integration tests
```python
monkeypatch.setenv("EMBED_BACKEND", "aliyun;ollama")  # alias in chain
ec.BACKEND = "aliyun;ollama"
ec.PROVIDER_CHAIN[:] = ["aliyun", "ollama"]
ec.PRIMARY_BACKEND = "aliyun"
```

### Observer / on_change Pattern
**Source:** `kb_server/config/loader.py:184-198`
**Apply to:** Hot-reload hook registration (D-03)
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
```

## No Analog Found

All files have strong analogs. No new files without patterns exist.

## Metadata

**Analog search scope:** `kb_server/config/`, `kb_server/embed_client.py`, `tests/`
**Files scanned:** 10+
**Pattern extraction date:** 2026-06-15
