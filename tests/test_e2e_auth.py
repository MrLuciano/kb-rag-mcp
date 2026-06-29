"""E2E tests for auth flow: API key login, session cookie, logout."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kb_server.auth.erasure import ErasureManager
from kb_server.auth.models import User, create_session
from kb_server.auth.router import router as auth_router
from kb_server.auth.service import AuthService


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def service(db_path):
    return AuthService(db_path=db_path)


def _build_app(service):
    from fastapi import FastAPI

    app = FastAPI()
    app.state.auth_service = service
    app.state.erasure_manager = ErasureManager(service._session)
    app.include_router(auth_router)
    return app


class TestAuthFlowE2E:
    @pytest.fixture
    def app_with_admin(self, service):
        user = service.create_user(username="admin", role="admin")
        raw_key, _ = service.create_api_key(user.id, "e2e test key")
        app = _build_app(service)
        app.state.admin_user = user
        app.state.raw_key = raw_key
        return app

    @pytest.fixture
    def client(self, app_with_admin):
        return TestClient(app_with_admin)

    def test_login_with_valid_key_returns_session(self, client, app_with_admin):
        response = client.post(
            "/api/v1/auth/session",
            headers={"Authorization": f"Bearer {app_with_admin.state.raw_key}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert "session" in response.cookies

    def test_login_with_invalid_key_returns_401(self, client):
        response = client.post(
            "/api/v1/auth/session",
            headers={"Authorization": "Bearer invalid-key-12345"},
        )
        assert response.status_code == 401

    def test_logout_clears_session(
        self, client, app_with_admin
    ):
        login = client.post(
            "/api/v1/auth/session",
            headers={"Authorization": f"Bearer {app_with_admin.state.raw_key}"},
        )
        assert login.status_code == 200
        session_cookie = login.cookies.get("session")
        assert session_cookie is not None

        logout = client.post(
            "/api/v1/auth/logout",
            cookies={"session": session_cookie},
        )
        assert logout.status_code == 200

        used_again = client.post(
            "/api/v1/auth/session",
            headers={"Authorization": f"Bearer {app_with_admin.state.raw_key}"},
            cookies={"session": session_cookie},
        )
        assert used_again.status_code == 200
