import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kb_server.auth.erasure import ErasureManager
from kb_server.auth.models import (
    ApiKey,
    AuditLog,
    ErasureRequest,
    User,
    create_session,
)
from kb_server.auth.router import router
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
    svc = AuthService(db_path=db_path)
    return svc


@pytest.fixture
def session(db_path):
    return create_session(db_path)


@pytest.fixture
def app(service):
    app = FastAPI()
    app.state.auth_service = service
    app.state.erasure_manager = ErasureManager(service._session)
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def admin_user(service):
    return service.create_user(username="admin", role="admin")


@pytest.fixture
def regular_user(service):
    return service.create_user(username="user1", role="user")


@pytest.fixture
def admin_api_key(service, admin_user):
    raw, key = service.create_api_key(admin_user.id, "admin key")
    return raw, key


# ── Model Tests ─────────────────────────────────────────────────


class TestUserModel:
    def test_create_user(self, session):
        user = User(username="testuser", role="user")
        session.add(user)
        session.commit()
        assert user.id is not None
        assert len(user.id) == 36
        assert user.username == "testuser"
        assert user.role == "user"
        assert user.is_active is True
        assert user.erasure_status == "active"

    def test_user_unique_username(self, session):
        user1 = User(username="unique", role="user")
        session.add(user1)
        session.commit()
        user2 = User(username="unique", role="user")
        session.add(user2)
        with pytest.raises(Exception):
            session.commit()


class TestApiKeyModel:
    def test_create_api_key(self, session):
        user = User(username="keyuser", role="user")
        session.add(user)
        session.commit()

        key = ApiKey(
            user_id=user.id,
            key_hash="a" * 64,
            prefix="abc123",
        )
        session.add(key)
        session.commit()
        assert key.id is not None
        assert key.key_hash == "a" * 64
        assert key.prefix == "abc123"

    def test_cascade_delete(self, session):
        user = User(username="cascade_test", role="user")
        session.add(user)
        session.commit()

        key = ApiKey(
            user_id=user.id,
            key_hash="b" * 64,
            prefix="test1234",
        )
        session.add(key)
        session.commit()

        session.delete(user)
        session.commit()

        remaining = (
            session.query(ApiKey).filter(ApiKey.user_id == user.id).all()
        )
        assert len(remaining) == 0


class TestAuditLogModel:
    def test_create_audit_log(self, session):
        entry = AuditLog(
            actor_id="actor-1",
            action="test.action",
            resource_type="test",
            resource_id="res-1",
        )
        session.add(entry)
        session.commit()
        assert entry.id is not None
        assert entry.action == "test.action"


class TestErasureRequestModel:
    def test_create_erasure_request(self, session):
        user = User(username="erasure_user", role="user")
        session.add(user)
        session.commit()

        er = ErasureRequest(
            user_id=user.id,
            status="erasure_requested",
            requested_by=user.id,
        )
        session.add(er)
        session.commit()
        assert er.id is not None
        assert er.status == "erasure_requested"


# ── Service Tests ───────────────────────────────────────────────


class TestAuthService:
    def test_create_user(self, service):
        user = service.create_user("newuser", role="user")
        assert user.username == "newuser"
        assert user.role == "user"

    def test_create_duplicate_user(self, service):
        service.create_user("dupuser")
        with pytest.raises(ValueError, match="already exists"):
            service.create_user("dupuser")

    def test_list_users(self, service):
        service.create_user("user_a")
        service.create_user("user_b")
        users = service.list_users()
        assert len(users) >= 2

    def test_get_user(self, service):
        created = service.create_user("getme")
        found = service.get_user(created.id)
        assert found is not None
        assert found.username == "getme"

    def test_get_user_by_username(self, service):
        service.create_user("byusername")
        found = service.get_user_by_username("byusername")
        assert found is not None

    def test_create_api_key(self, service):
        user = service.create_user("key_user")
        raw_key, api_key = service.create_api_key(user.id, "test description")
        assert len(raw_key) > 20
        assert api_key.prefix == raw_key[:8]
        assert api_key.description == "test description"

    def test_list_api_keys(self, service):
        user = service.create_user("list_keys_user")
        service.create_api_key(user.id, "key1")
        service.create_api_key(user.id, "key2")
        keys = service.list_api_keys(user.id)
        assert len(keys) == 2

    def test_revoke_api_key(self, service):
        user = service.create_user("revoke_user")
        raw, api_key = service.create_api_key(user.id)
        revoked = service.revoke_api_key(api_key.id)
        assert revoked is True
        # Verify key no longer works
        verified = service.verify_key(raw)
        assert verified is None

    def test_verify_key_valid(self, service):
        user = service.create_user("verify_user")
        raw, _ = service.create_api_key(user.id)
        verified = service.verify_key(raw)
        assert verified is not None
        assert verified.id == user.id

    def test_verify_key_invalid(self, service):
        assert service.verify_key("invalid_key") is None

    def test_verify_key_revoked(self, service):
        user = service.create_user("verify_revoked")
        raw, api_key = service.create_api_key(user.id)
        service.revoke_api_key(api_key.id)
        assert service.verify_key(raw) is None

    def test_delete_user(self, service):
        user = service.create_user("delete_me")
        deleted = service.delete_user(user.id)
        assert deleted is True
        found = service.get_user(user.id)
        assert found is not None
        assert found.is_active is False
        assert "deleted-user-" in found.username


# ── Dependency Tests ────────────────────────────────────────────


class TestDeps:
    def test_get_current_user_valid(self, service, admin_user, admin_api_key):
        test_app = FastAPI()
        test_app.state.auth_service = service

        from kb_server.auth.deps import get_current_user

        raw_key, _ = admin_api_key

        class MockRequest:
            headers = {"X-API-Key": raw_key}
            app = test_app

        import asyncio

        user = asyncio.run(get_current_user(MockRequest(), api_key=raw_key))
        assert user is not None
        assert user.id == admin_user.id

    def test_get_current_user_missing_key(self, service):
        test_app = FastAPI()
        test_app.state.auth_service = service

        from kb_server.auth.deps import get_current_user

        class MockRequest:
            headers = {}
            app = test_app

        import asyncio

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_user(MockRequest(), api_key=None))
        assert exc.value.status_code == 401

    def test_require_admin_passes(self, service, admin_user):
        import asyncio

        from kb_server.auth.deps import require_admin

        result = asyncio.run(require_admin(admin_user))
        assert result.id == admin_user.id

    def test_require_admin_fails(self, service, regular_user):
        import asyncio

        from fastapi import HTTPException

        from kb_server.auth.deps import require_admin

        with pytest.raises(HTTPException) as exc:
            asyncio.run(require_admin(regular_user))
        assert exc.value.status_code == 403


# ── Erasure Tests ───────────────────────────────────────────────


class TestErasure:
    def test_erasure_workflow(self, service, session):
        user = service.create_user("erasure_test")
        mgr = ErasureManager(service._session)

        er = mgr.request_erasure(
            user_id=user.id,
            requested_by=user.id,
            reason="GDPR request",
        )
        assert er.status == "erasure_requested"

        approved = mgr.approve_erasure(er.id, approved_by=user.id)
        assert approved is True

        executed = mgr.execute_erasure(er.id)
        assert executed is True

        # Verify user is anonymized
        updated = service.get_user(user.id)
        assert updated.is_active is False
        assert "deleted-user-" in updated.username

        # Verify keys are hard-deleted
        keys = service.list_api_keys(user.id)
        assert len(keys) == 0

    def test_invalid_state_transition(self, service):
        user = service.create_user("invalid_state")
        mgr = ErasureManager(service._session)

        er = mgr.request_erasure(user_id=user.id, requested_by=user.id)
        assert er.status == "erasure_requested"

        executed = mgr.execute_erasure(er.id)
        assert executed is False

    def test_export_user_data(self, service):
        user = service.create_user("export_me")
        raw, key = service.create_api_key(user.id)
        mgr = ErasureManager(service._session)
        data = mgr.export_user_data(user.id)
        assert data is not None
        assert data["username"] == "export_me"
        assert len(data["api_keys"]) == 1
        assert "key_hash" not in str(data["api_keys"][0])


# ── Audit Log Tests ─────────────────────────────────────────────


class TestAuditLog:
    def test_audit_log_created_on_user_create(self, service):
        service.create_user("audit_test")
        logs = service.get_audit_logs()
        actions = [entry.action for entry in logs]
        assert "user.created" in actions

    def test_prune_audit_logs(self, service):
        service.create_user("prune_test")
        logs_before = service.get_audit_logs()
        assert len(logs_before) > 0

        deleted = service.prune_audit_logs(days=0)
        assert deleted > 0

        logs_after = service.get_audit_logs()
        assert len(logs_after) == 0


# ── API Tests ───────────────────────────────────────────────────


class TestAPI:
    def _auth_headers(self, raw_key):
        return {"X-API-Key": raw_key}

    def test_create_user(self, service, client, admin_user, admin_api_key):
        raw_key, _ = admin_api_key
        resp = client.post(
            "/api/v1/users",
            json={"username": "new_api_user", "role": "user"},
            headers=self._auth_headers(raw_key),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "new_api_user"

    def test_create_duplicate_user(
        self, service, client, admin_user, admin_api_key
    ):
        raw_key, _ = admin_api_key
        client.post(
            "/api/v1/users",
            json={"username": "dup_api"},
            headers=self._auth_headers(raw_key),
        )
        resp = client.post(
            "/api/v1/users",
            json={"username": "dup_api"},
            headers=self._auth_headers(raw_key),
        )
        assert resp.status_code == 409

    def test_list_users(self, service, client, admin_api_key):
        raw_key, _ = admin_api_key
        resp = client.get(
            "/api/v1/users",
            headers=self._auth_headers(raw_key),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_current_user(
        self, service, client, admin_user, admin_api_key
    ):
        raw_key, _ = admin_api_key
        resp = client.get(
            "/api/v1/users/me",
            headers=self._auth_headers(raw_key),
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

    def test_create_api_key(
        self, service, client, regular_user, admin_api_key
    ):
        raw_key, _ = admin_api_key
        resp = client.post(
            "/api/v1/api-keys",
            json={
                "user_id": regular_user.id,
                "description": "test key",
            },
            headers=self._auth_headers(raw_key),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "raw_key" in data
        assert data["prefix"] == data["raw_key"][:8]
        assert "key_hash" not in data

    def test_list_api_keys(self, service, client, regular_user, admin_api_key):
        raw_key, _ = admin_api_key
        service.create_api_key(regular_user.id, "k1")
        service.create_api_key(regular_user.id, "k2")
        resp = client.get(
            f"/api/v1/api-keys?user_id={regular_user.id}",
            headers=self._auth_headers(raw_key),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    def test_revoke_api_key(self, service, client, admin_user, admin_api_key):
        raw_key, _ = admin_api_key
        _, key = service.create_api_key(admin_user.id)
        resp = client.delete(
            f"/api/v1/api-keys/{key.id}",
            headers=self._auth_headers(raw_key),
        )
        assert resp.status_code == 200
        assert resp.json()["revoked"] is True

    def test_erasure_endpoint(
        self, service, client, regular_user, admin_api_key
    ):
        raw_key, _ = admin_api_key
        resp = client.post(
            f"/api/v1/users/{regular_user.id}/erasure-request",
            headers=self._auth_headers(raw_key),
        )
        assert resp.status_code == 200

    def test_unauthorized_access(self, client, regular_user):
        resp = client.get(
            "/api/v1/users",
            headers={"X-API-Key": "invalid_key"},
        )
        assert resp.status_code == 401

    def test_non_admin_cannot_create_user(self, service, client, regular_user):
        raw, _ = service.create_api_key(regular_user.id)
        resp = client.post(
            "/api/v1/users",
            json={"username": "should_fail"},
            headers=self._auth_headers(raw),
        )
        assert resp.status_code == 403
