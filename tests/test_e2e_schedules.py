"""E2E tests for schedule management: CRUD, enable/disable, cron matching."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ingest.core.metadata import MetadataStore

os.environ["AUTH_ENABLED"] = "true"


@pytest.fixture
def auth_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def auth_service(auth_db_path):
    from kb_server.auth.service import AuthService
    svc = AuthService(db_path=auth_db_path)
    return svc


@pytest.fixture
def admin_api_key(auth_service):
    user = auth_service.create_user(username="schedadmin", role="admin")
    raw_key, _ = auth_service.create_api_key(user.id, "e2e sched test")
    return raw_key


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def store(db_path):
    s = MetadataStore(db_path=db_path)
    s.connect()
    yield s
    s.close()


def _build_schedule_app(store, auth_service, raw_key):
    from fastapi import FastAPI
    from kb_server.auth.erasure import ErasureManager
    from kb_server.auth.router import router as auth_router
    from kb_server.schedules.router import router
    from kb_server.auth.legacy import AUTH_ENABLED

    app = FastAPI()
    app.state.metadata_store = store
    app.state.auth_service = auth_service
    app.state.erasure_manager = ErasureManager(auth_service._session)
    app.state.raw_key = raw_key
    app.state.admin_key = raw_key
    app.include_router(auth_router)
    app.include_router(router)
    return app


def make_schedule_id():
    import uuid
    return str(uuid.uuid4())


class TestScheduleManagementE2E:
    @pytest.fixture
    def app(self, store, auth_service, admin_api_key):
        return _build_schedule_app(store, auth_service, admin_api_key)

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def _auth_header(self, raw_key):
        return {"Authorization": f"Bearer {raw_key}"}

    def _create_schedule_payload(self, **overrides):
        payload = {
            "name": "e2e-test-schedule",
            "cron_expr": "0 3 * * 1",
            "docs_path": "/data/docs",
            "product": "AppServer",
            "workers": 2,
            "priority": "normal",
            "clean": False,
            "force": False,
        }
        payload.update(overrides)
        return payload

    def _create_schedule(self, client, headers, **overrides):
        payload = self._create_schedule_payload(**overrides)
        resp = client.post("/api/v1/schedules", json=payload, headers=headers)
        assert resp.status_code == 201, f"create failed: {resp.text}"
        return resp.json()["id"]

    def test_create_schedule(self, client, admin_api_key):
        headers = self._auth_header(admin_api_key)
        payload = self._create_schedule_payload()
        response = client.post("/api/v1/schedules", json=payload, headers=headers)
        assert response.status_code == 201, f"create failed: {response.text}"
        data = response.json()
        assert data["name"] == "e2e-test-schedule"
        assert data["cron_expr"] == "0 3 * * 1"

    def test_list_schedules(self, client, admin_api_key):
        headers = self._auth_header(admin_api_key)
        sid = self._create_schedule(client, headers, name="list-test")

        response = client.get("/api/v1/schedules", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(s["name"] == "list-test" for s in data)
        assert any(s["id"] == sid for s in data)

    def test_get_schedule(self, client, admin_api_key):
        headers = self._auth_header(admin_api_key)
        sid = self._create_schedule(client, headers)

        response = client.get(f"/api/v1/schedules/{sid}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == sid

    def test_get_nonexistent_schedule_returns_404(self, client, admin_api_key):
        headers = self._auth_header(admin_api_key)
        response = client.get(f"/api/v1/schedules/{make_schedule_id()}", headers=headers)
        assert response.status_code == 404

    def test_update_schedule(self, client, admin_api_key):
        headers = self._auth_header(admin_api_key)
        sid = self._create_schedule(client, headers, name="before-update")

        update = {"name": "after-update", "workers": 4}
        response = client.put(f"/api/v1/schedules/{sid}", json=update, headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "after-update"
        assert response.json()["workers"] == 4

    def test_disable_schedule(self, client, admin_api_key):
        headers = self._auth_header(admin_api_key)
        sid = self._create_schedule(client, headers)

        response = client.put(
            f"/api/v1/schedules/{sid}", json={"enabled": False}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["enabled"] == 0

    def test_enable_disabled_schedule(self, client, admin_api_key):
        headers = self._auth_header(admin_api_key)
        sid = self._create_schedule(client, headers)

        client.put(f"/api/v1/schedules/{sid}", json={"enabled": False}, headers=headers)
        enable = client.put(
            f"/api/v1/schedules/{sid}", json={"enabled": True}, headers=headers
        )
        assert enable.status_code == 200
        assert enable.json()["enabled"] == 1

    def test_delete_schedule(self, client, admin_api_key):
        headers = self._auth_header(admin_api_key)
        sid = self._create_schedule(client, headers)

        delete = client.delete(f"/api/v1/schedules/{sid}", headers=headers)
        assert delete.status_code == 200

        get = client.get(f"/api/v1/schedules/{sid}", headers=headers)
        assert get.status_code == 404
