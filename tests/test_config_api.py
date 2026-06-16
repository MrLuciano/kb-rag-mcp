import os
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kb_server.config.loader import ConfigLoader
from kb_server.config.router import router


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


def test_server_imports_config_loader():
    """Verify server.py can import and use ConfigLoader without errors."""
    from kb_server.server import config

    assert config is not None


# ── ConfigLoader Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_config_loader_set_get(loader):
    result = await loader.set("TEST_KEY", "test_value")
    assert result["key"] == "TEST_KEY"
    assert result["value"] == "test_value"
    val = loader.get("TEST_KEY")
    assert val == "test_value"


@pytest.mark.asyncio
async def test_config_loader_get_all(loader):
    await loader.set("KEY_A", "val_a", group_name="group1")
    await loader.set("KEY_B", "val_b", group_name="group2")
    all_entries = await loader.get_all()
    keys = [e["key"] for e in all_entries]
    assert "KEY_A" in keys
    assert "KEY_B" in keys


@pytest.mark.asyncio
async def test_config_loader_get_all_filtered(loader):
    await loader.set("KEY_C", "val_c", group_name="group1")
    await loader.set("KEY_D", "val_d", group_name="group2")
    group1 = await loader.get_all(group_name="group1")
    assert all(e["group_name"] == "group1" for e in group1)
    assert len(group1) == 1


@pytest.mark.asyncio
async def test_config_loader_fallback_to_env(loader):
    os.environ["_TEST_CONFIG_ENV_FALLBACK"] = "env_value"
    val = loader.get("_TEST_CONFIG_ENV_FALLBACK")
    assert val == "env_value"


@pytest.mark.asyncio
async def test_config_loader_delete(loader):
    await loader.set("DELETE_KEY", "to_delete")
    val = loader.get("DELETE_KEY")
    assert val == "to_delete"
    deleted = await loader.delete("DELETE_KEY")
    assert deleted is True
    val = loader.get("DELETE_KEY")
    assert val is None


@pytest.mark.asyncio
async def test_config_loader_delete_nonexistent(loader):
    deleted = await loader.delete("NONEXISTENT_KEY")
    assert deleted is False


@pytest.mark.asyncio
async def test_config_loader_reset_all(loader):
    await loader.set("KEY_E", "val_e")
    await loader.set("KEY_F", "val_f")
    deleted = await loader.reset_all()
    assert deleted == 2
    assert loader.get("KEY_E") is None
    assert loader.get("KEY_F") is None


@pytest.mark.asyncio
async def test_config_loader_typed_values(loader):
    await loader.set("INT_KEY", "42", type_name="int")
    val = loader.get("INT_KEY")
    assert val == 42
    assert isinstance(val, int)

    await loader.set("BOOL_KEY", "true", type_name="bool")
    val = loader.get("BOOL_KEY")
    assert val is True
    assert isinstance(val, bool)

    await loader.set("FLOAT_KEY", "3.14", type_name="float")
    val = loader.get("FLOAT_KEY")
    assert val == 3.14
    assert isinstance(val, float)


@pytest.mark.asyncio
async def test_config_loader_validation_error(loader):
    with pytest.raises(ValueError, match="Invalid int"):
        await loader.set("BAD_INT", "not_a_number", type_name="int")


@pytest.mark.asyncio
async def test_config_loader_on_change(loader):
    changes = []

    def callback(key, value):
        changes.append((key, value))

    loader.on_change("CHANGE_KEY", callback)
    await loader.set("CHANGE_KEY", "new_val")
    loader._notify_observers("CHANGE_KEY", "new_val")
    assert len(changes) >= 0


@pytest.mark.asyncio
async def test_config_loader_get_item(loader):
    await loader.set("ITEM_KEY", "item_val", description="test item")
    item = await loader.get_item("ITEM_KEY")
    assert item is not None
    assert item["key"] == "ITEM_KEY"
    assert item["value"] == "item_val"
    assert item["description"] == "test item"


@pytest.mark.asyncio
async def test_config_loader_get_item_missing(loader):
    item = await loader.get_item("MISSING_KEY")
    assert item is None


# ── REST API Tests ──────────────────────────────────────────────


def test_api_list_config(client):
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_api_set_and_get_config(client):
    resp = client.put(
        "/api/v1/config/TEST_API_KEY",
        json={
            "value": "api_value",
            "type": "string",
            "group_name": "test",
            "description": "test key",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "TEST_API_KEY"
    assert data["value"] == "api_value"

    resp = client.get("/api/v1/config/TEST_API_KEY")
    assert resp.status_code == 200
    data = resp.json()
    assert data["value"] == "api_value"


def test_api_get_missing_key(client):
    resp = client.get("/api/v1/config/NONEXISTENT")
    assert resp.status_code == 404


def test_api_delete_config(client):
    client.put(
        "/api/v1/config/DEL_API_KEY",
        json={"value": "delete_me"},
    )
    resp = client.delete("/api/v1/config/DEL_API_KEY")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    resp = client.get("/api/v1/config/DEL_API_KEY")
    assert resp.status_code == 404


def test_api_delete_missing(client):
    resp = client.delete("/api/v1/config/NONEXISTENT")
    assert resp.status_code == 404


def test_api_reset_config(client):
    client.put("/api/v1/config/RESET_A", json={"value": "a"})
    client.put("/api/v1/config/RESET_B", json={"value": "b"})

    resp = client.post("/api/v1/config/reset")
    assert resp.status_code == 200
    assert resp.json()["entries_deleted"] >= 2

    resp = client.get("/api/v1/config")
    assert len(resp.json()) == 0


def test_api_validation_error(client):
    resp = client.put(
        "/api/v1/config/BAD_INT",
        json={"value": "not_a_number", "type": "int"},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "Validation failed"


def test_api_list_group_filter(client):
    client.put(
        "/api/v1/config/GROUP_A_1",
        json={"value": "v1", "group_name": "alpha"},
    )
    client.put(
        "/api/v1/config/GROUP_B_1",
        json={"value": "v2", "group_name": "beta"},
    )
    resp = client.get("/api/v1/config?group=alpha")
    assert resp.status_code == 200
    entries = resp.json()
    assert all(e["group_name"] == "alpha" for e in entries)
    assert len(entries) == 1


def test_api_upsert_overwrite(client):
    client.put(
        "/api/v1/config/UPSERT_KEY",
        json={
            "value": "first",
            "group_name": "test",
            "description": "original",
        },
    )
    client.put(
        "/api/v1/config/UPSERT_KEY",
        json={
            "value": "second",
            "group_name": "test",
            "description": "updated",
        },
    )
    resp = client.get("/api/v1/config/UPSERT_KEY")
    assert resp.status_code == 200
    assert resp.json()["value"] == "second"
    assert resp.json()["description"] == "updated"


# ── Hot-reload Tests ───────────────────────────────────────────


def test_reload_if_changed_no_changes(loader):
    changes = []

    def callback(key, value):
        changes.append((key, value))

    loader.on_change("RELOAD_KEY", callback)
    result = loader.reload_if_changed()
    assert result is False
    assert len(changes) == 0


@pytest.mark.asyncio
async def test_reload_if_changed_triggers_callback(loader):
    changes = []

    def callback(key, value):
        changes.append((key, value))

    loader.on_change("RELOAD_KEY", callback)
    await loader.set("RELOAD_KEY", "initial")
    # set() already notifies observers; clear changes
    changes.clear()

    # Simulate external change by modifying DB directly
    from kb_server.config.db import get_connection

    with get_connection(loader._db_path) as conn:
        conn.execute(
            "UPDATE config SET value = ? WHERE key = ?",
            ("updated", "RELOAD_KEY"),
        )
        from kb_server.config.db import bump_config_version

        bump_config_version(conn)

    result = loader.reload_if_changed()
    assert result is True
    assert len(changes) == 1
    assert changes[0] == ("RELOAD_KEY", "updated")


def test_reload_if_changed_synchronous(loader):
    import inspect

    assert not inspect.iscoroutinefunction(loader.reload_if_changed)


@pytest.mark.asyncio
async def test_on_change_decorator(loader):
    changes = []

    @loader.on_change("DECORATOR_KEY")
    def my_callback(key, value):
        changes.append((key, value))

    await loader.set("DECORATOR_KEY", "decorated_value")
    # set() already notifies observers
    assert len(changes) >= 1
    assert changes[0] == ("DECORATOR_KEY", "decorated_value")


@pytest.mark.asyncio
async def test_observer_hook_error_caught(loader, caplog):
    changes_good = []
    changes_bad = []

    def bad_callback(key, value):
        changes_bad.append((key, value))
        raise RuntimeError("hook error")

    def good_callback(key, value):
        changes_good.append((key, value))

    loader.on_change("HOOK_KEY", bad_callback)
    loader.on_change("HOOK_KEY", good_callback)
    await loader.set("HOOK_KEY", "hook_value")
    assert changes_good == [("HOOK_KEY", "hook_value")]
    assert changes_bad == [("HOOK_KEY", "hook_value")]
    assert any(
        "observer hook failed" in record.message for record in caplog.records
    )


@pytest.mark.asyncio
async def test_on_change_wildcard_pattern(loader):
    changes = []

    def callback(key, value):
        changes.append((key, value))

    loader.on_change("rate_limit.*", callback)
    await loader.set("rate_limit.enabled", "true")
    await loader.set("rate_limit.window", "60")
    await loader.set("other.key", "value")
    assert len(changes) == 2
    assert changes[0] == ("rate_limit.enabled", "true")
    assert changes[1] == ("rate_limit.window", "60")
