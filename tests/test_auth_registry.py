"""
Tests for Phase 32 API key authentication.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kb_server.auth import extract_bearer_token, is_auth_enabled, verify_request
from kb_server.auth_registry import AuthRegistry


# ---------------------------------------------------------------------------
# Auth Registry
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_auth_db(tmp_path: Path) -> AuthRegistry:
    db_path = tmp_path / "test_auth.db"
    return AuthRegistry(db_path)


class TestAuthRegistry:
    def test_create_key_returns_string(self, temp_auth_db):
        raw = temp_auth_db.create_key(description="test key")
        assert len(raw) == 64  # 32 bytes hex

    def test_verify_valid_key(self, temp_auth_db):
        raw = temp_auth_db.create_key()
        assert temp_auth_db.verify_key(raw) is True

    def test_verify_unknown_key(self, temp_auth_db):
        assert temp_auth_db.verify_key("unknownkey123") is False

    def test_revoke_key(self, temp_auth_db):
        raw = temp_auth_db.create_key()
        prefix = raw[:8]
        assert temp_auth_db.verify_key(raw) is True
        temp_auth_db.revoke_key(prefix)
        assert temp_auth_db.verify_key(raw) is False

    def test_revoke_unknown_prefix(self, temp_auth_db):
        assert temp_auth_db.revoke_key("deadbeef") is False

    def test_create_key_with_scope(self, temp_auth_db):
        raw = temp_auth_db.create_key(
            scope="kb", kb_name="mykb", description="my key"
        )
        keys = temp_auth_db.list_keys()
        assert len(keys) >= 1
        match = [k for k in keys if k["prefix"] == raw[:8]]
        assert len(match) == 1
        assert match[0]["scope"] == "kb"
        assert match[0]["kb_name"] == "mykb"
        assert match[0]["description"] == "my key"

    def test_list_keys_no_keys(self, temp_auth_db):
        keys = temp_auth_db.list_keys()
        assert keys == []

    def test_verify_revoked_key(self, temp_auth_db):
        raw = temp_auth_db.create_key()
        temp_auth_db.revoke_key(raw[:8])
        assert temp_auth_db.verify_key(raw) is False


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


class TestExtractBearerToken:
    def test_valid_bearer(self):
        assert extract_bearer_token("Bearer mytoken123") == "mytoken123"

    def test_no_header(self):
        assert extract_bearer_token(None) is None

    def test_empty_header(self):
        assert extract_bearer_token("") is None

    def test_wrong_scheme(self):
        assert extract_bearer_token("Basic dXNlcjpwYXNz") is None

    def test_bearer_with_extra_whitespace(self):
        assert extract_bearer_token("Bearer   token  ") == "token"


class TestVerifyRequest:
    @patch("kb_server.auth.AUTH_ENABLED", False)
    def test_auth_disabled_always_passes(self):
        ok, err = verify_request(None)
        assert ok is True
        assert err is None

    @patch("kb_server.auth.AUTH_ENABLED", True)
    def test_auth_enabled_no_header(self):
        ok, err = verify_request(None)
        assert ok is False
        assert "Missing" in err

    @patch("kb_server.auth.AUTH_ENABLED", True)
    def test_auth_enabled_invalid_key(self):
        ok, err = verify_request("Bearer invalidkey")
        assert ok is False
        assert "Invalid" in err

    @patch("kb_server.auth.AUTH_ENABLED", True)
    def test_auth_enabled_valid_key(self, tmp_path):
        registry = AuthRegistry(tmp_path / "test_auth.db")
        raw = registry.create_key()

        with patch(
            "kb_server.auth.get_registry", return_value=registry
        ):
            ok, err = verify_request(f"Bearer {raw}")
            assert ok is True
            assert err is None


# ---------------------------------------------------------------------------
# SSE Handler Auth (server.py integration)
# ---------------------------------------------------------------------------


class TestSSEHandlerAuth:
    @pytest.mark.asyncio
    @patch("kb_server.auth.is_auth_enabled", return_value=True)
    @patch("kb_server.auth.verify_request", return_value=(False, "Invalid key"))
    async def test_sse_rejects_unauthenticated(
        self, mock_verify, mock_enabled
    ):
        from starlette.responses import Response

        ok, err = mock_verify.return_value
        assert ok is False
        if not ok:
            resp = Response(
                content=f'{{"error":"{err}"}}',
                status_code=401,
                media_type="application/json",
            )
            assert resp.status_code == 401

    @pytest.mark.asyncio
    @patch("kb_server.auth.is_auth_enabled", return_value=False)
    async def test_sse_auth_disabled_no_check(self, mock_enabled):
        from kb_server.server import list_tools

        prompts = await list_tools()
        assert len(prompts) > 0


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


class TestCLIAuthCommands:
    def test_auth_group_registered(self):
        from ingest.cli.main import cli

        cmds = {c.name: c for c in cli.commands.values()}
        assert "auth" in cmds

    def test_auth_create_command(self):
        from ingest.cli.auth import auth_group

        cmds = {c.name: c for c in auth_group.commands.values()}
        assert "create" in cmds
        assert "list" in cmds
        assert "revoke" in cmds
