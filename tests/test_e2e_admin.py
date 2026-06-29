"""E2E tests for admin panel: config CRUD, document browse, export."""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kb_server.auth.erasure import ErasureManager
from kb_server.auth.router import router as auth_router
from kb_server.auth.service import AuthService
from kb_server.config.loader import ConfigLoader
from kb_server.config.router import router as config_router


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def config_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def auth_service(db_path):
    return AuthService(db_path=db_path)


@pytest.fixture
def config_loader(config_db_path):
    return ConfigLoader(db_path=config_db_path)


def _build_app(auth_service, config_loader):
    from fastapi import FastAPI

    app = FastAPI()
    app.state.auth_service = auth_service
    app.state.erasure_manager = ErasureManager(auth_service._session)
    app.state.config_loader = config_loader
    app.include_router(auth_router)
    app.include_router(config_router)
    return app


def _setup_admin(auth_service):
    user = auth_service.create_user(username="e2eadmin", role="admin")
    raw_key, _ = auth_service.create_api_key(user.id, "e2e config test")
    return user, raw_key


class TestConfigAdminE2E:
    @pytest.fixture(autouse=True)
    def _patch_auth(self, monkeypatch, db_path):
        monkeypatch.setattr("kb_server.auth.legacy.AUTH_ENABLED", True)
        monkeypatch.setenv("AUTH_DB_PATH", str(db_path))

    @pytest.fixture
    def app(self, auth_service, config_loader):
        return _build_app(auth_service, config_loader)

    @pytest.fixture
    def admin_creds(self, auth_service):
        return _setup_admin(auth_service)

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def _login(self, client, raw_key):
        resp = client.post(
            "/api/v1/auth/session",
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert resp.status_code == 200, f"login failed: {resp.text}"
        return resp.cookies.get("session")

    def test_config_crud_cycle(self, app, client, admin_creds):
        _, raw_key = admin_creds
        session_token = self._login(client, raw_key)

        get_all = client.get("/api/v1/config", cookies={"session": session_token})
        assert get_all.status_code == 200

        put = client.put(
            "/api/v1/config/E2E_TEST_KEY",
            json={"value": "hello", "type": "string"},
            cookies={"session": session_token},
        )
        assert put.status_code == 200
        assert put.json()["key"] == "E2E_TEST_KEY"

        get_one = client.get(
            "/api/v1/config/E2E_TEST_KEY",
            cookies={"session": session_token},
        )
        assert get_one.status_code == 200
        assert get_one.json()["value"] == "hello"

        put2 = client.put(
            "/api/v1/config/E2E_TEST_KEY",
            json={"value": "updated", "type": "string"},
            cookies={"session": session_token},
        )
        assert put2.status_code == 200

        get_updated = client.get(
            "/api/v1/config/E2E_TEST_KEY",
            cookies={"session": session_token},
        )
        assert get_updated.json()["value"] == "updated"

    def test_config_requires_auth(self, client):
        assert client.get("/api/v1/config").status_code == 401
        assert client.get("/api/v1/config/SOME_KEY").status_code == 401
        assert client.put(
            "/api/v1/config/X", json={"value": "x", "type": "string"}
        ).status_code == 401

    def test_config_reset(self, app, client, admin_creds, config_loader):
        _, raw_key = admin_creds
        session_token = self._login(client, raw_key)

        put = client.put(
            "/api/v1/config/RESET_TEST",
            json={"value": "custom_val", "type": "string"},
            cookies={"session": session_token},
        )
        assert put.status_code == 200

        reset = client.post(
            "/api/v1/config/reset",
            cookies={"session": session_token},
        )
        assert reset.status_code == 200
        data = reset.json()
        assert data.get("reset") is True

        get_deleted = client.get(
            "/api/v1/config/RESET_TEST",
            cookies={"session": session_token},
        )
        assert get_deleted.status_code == 404
