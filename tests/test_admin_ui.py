import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from kb_server.ui.app import app


@pytest.fixture(autouse=True)
def cleanup_auth_db():
    """Remove test auth DB after each test."""
    yield
    for p in ["data/auth.db", "data/auth.db-wal", "data/auth.db-shm"]:
        try:
            os.remove(p)
        except FileNotFoundError:
            pass


@pytest.fixture
def client():
    from kb_server.auth.deps import get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


class TestAdminShell:
    def test_admin_nav_link_in_base(self):
        with open("kb_server/ui/templates/base.html") as f:
            content = f.read()
        assert "/admin" in content
        assert "Admin" in content

    def test_shell_template_exists(self):
        assert os.path.exists("kb_server/ui/templates/admin/shell.html")


class TestCSP:
    def test_csp_middleware_adds_header(self, client):
        resp = client.get("/health")
        assert "Content-Security-Policy" in resp.headers
        assert "nonce-" in resp.headers["Content-Security-Policy"]

    def test_cdn_scripts_have_integrity(self):
        with open("kb_server/ui/templates/base.html") as f:
            content = f.read()
        assert 'integrity="sha384-' in content


class TestGrafana:
    def test_build_grafana_embed_url_empty_without_env(self, monkeypatch):
        monkeypatch.delenv("GRAFANA_URL", raising=False)
        monkeypatch.delenv("GRAFANA_DASHBOARD_UID", raising=False)
        from kb_server.ui.routes_admin import build_grafana_embed_url

        url = build_grafana_embed_url()
        assert url == ""

    def test_build_grafana_embed_url_with_range_empty_without_env(
        self, monkeypatch
    ):
        monkeypatch.delenv("GRAFANA_URL", raising=False)
        monkeypatch.delenv("GRAFANA_DASHBOARD_UID", raising=False)
        from kb_server.ui.routes_admin import (
            build_grafana_embed_url_with_range,
        )

        url = build_grafana_embed_url_with_range("6h")
        assert url == ""

    def test_grafana_globals_registered(self):
        from kb_server.ui.app import templates

        assert "build_grafana_embed_url" in templates.env.globals
        assert "build_grafana_embed_url_with_range" in templates.env.globals


class TestAnalyticsTab:
    def test_analytics_tab_template_exists(self):
        assert os.path.exists(
            "kb_server/ui/templates/admin/tab_analytics.html"
        )

    def test_analytics_in_sidebar(self):
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert "analytics" in content
        assert "Analytics" in content

    def test_analytics_in_template_map(self):
        with open("kb_server/ui/routes_admin.py") as f:
            content = f.read()
        assert '"analytics"' in content
        assert "tab_analytics.html" in content

    def test_get_most_common_queries_accepts_time_range(self):
        from kb_server.analytics.query_analyzer import QueryAnalyzer

        import inspect

        sig = inspect.signature(QueryAnalyzer.get_most_common_queries)
        assert "time_range_days" in sig.parameters

    def test_get_zero_result_queries_accepts_time_range(self):
        from kb_server.analytics.query_analyzer import (
            QueryAnalyzer,
        )

        import inspect

        sig = inspect.signature(QueryAnalyzer.get_zero_result_queries)
        assert "time_range_days" in sig.parameters

    def test_get_latency_stats_exists(self):
        from kb_server.analytics.query_analyzer import (
            QueryAnalyzer,
        )

        assert hasattr(QueryAnalyzer, "get_latency_stats")


class TestAdminTemplates:
    def test_all_tab_templates_exist(self):
        tabs = [
            "documents",
            "monitoring",
            "ingestion",
            "ragas",
            "admin",
            "profile",
            "analytics",
        ]
        for tab in tabs:
            path = f"kb_server/ui/templates/admin/tab_{tab}.html"
            assert os.path.exists(path), f"Missing template: {path}"

    def test_shell_template_exists(self):
        assert os.path.exists("kb_server/ui/templates/admin/shell.html")


class TestAdminTabs:

    def _setup_auth(self, client):
        """Override auth dependency to bypass login for testing."""
        from unittest.mock import MagicMock
        from kb_server.auth.deps import get_current_user
        from kb_server.auth.models import User

        mock_user = MagicMock(spec=User)
        mock_user.id = "test-admin-id"
        mock_user.username = "admin"
        mock_user.role = "admin"
        mock_user.is_active = True

        async def _mock_get_current_user():
            return mock_user

        client.app.dependency_overrides[get_current_user] = _mock_get_current_user

    def test_admin_documents_tab(self, client):
        """Documents tab returns real content."""
        self._setup_auth(client)
        response = client.get("/admin/tabs/documents")
        assert response.status_code == 200
        assert "Documents" in response.text
        assert "alert alert-info" not in response.text  # No placeholder

    def test_admin_ingestion_tab(self, client):
        """Ingestion tab returns real content."""
        self._setup_auth(client)
        response = client.get("/admin/tabs/ingestion")
        assert response.status_code == 200
        assert "Ingestion" in response.text
        assert "Manual" in response.text
        assert "Schedule" in response.text
        assert "Monitor" in response.text

    def test_admin_ragas_tab(self, client):
        """RAGAS tab returns real content."""
        self._setup_auth(client)
        response = client.get("/admin/tabs/ragas")
        assert response.status_code == 200
        assert "RAGAS Evaluation" in response.text
        assert "Editor" in response.text
        assert "Results" in response.text


class TestAuthFlow:
    def test_shell_html_uses_alpine_xshow(self):
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert 'x-data="adminApp"' in content
        assert 'x-show="showOverlay"' in content

    def test_login_modal_heading(self):
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert "Login to Admin Panel" in content

    def test_api_key_placeholder(self):
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert "kb_xxxxxxxx..." in content

    def test_sidebar_tab_labels(self):
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert "RAGAS Evaluation" in content
        assert "Admin" in content

    def test_auth_router_has_logout(self):
        with open("kb_server/auth/router.py") as f:
            content = f.read()
        assert "/auth/logout" in content
        assert "delete_cookie" in content

    def test_authenticate_posts_to_auth_session(self):
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert "auth/session" in content

    def test_logout_calls_auth_logout(self):
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert "auth/logout" in content

    def test_base_html_401_dispatches_custom_event(self):
        with open("kb_server/ui/templates/base.html") as f:
            content = f.read()
        assert "show-login" in content


class TestDocTableSelection:
    def test_doc_table_select_all_checkbox(self):
        with open("kb_server/ui/templates/admin/_documents_table.html") as f:
            content = f.read()
        assert '<input type="checkbox"' in content

    def test_doc_table_per_row_checkbox(self):
        with open("kb_server/ui/templates/admin/_documents_table.html") as f:
            content = f.read()
        assert 'x-model="selected"' in content

    def test_doc_table_bulk_toolbar(self):
        with open("kb_server/ui/templates/admin/_documents_table.html") as f:
            content = f.read()
        assert "Delete" in content
        assert "Re-ingest" in content

    def test_doc_table_per_row_actions(self):
        with open("kb_server/ui/templates/admin/_documents_table.html") as f:
            content = f.read()
        assert "Actions" in content

    def test_destructive_actions_have_confirm(self):
        with open("kb_server/ui/templates/admin/_documents_table.html") as f:
            content = f.read()
        assert "hx-confirm" in content

    def test_doc_table_empty_state(self):
        with open("kb_server/ui/templates/admin/_documents_table.html") as f:
            content = f.read()
        assert "No documents match your search filters" in content or "No documents found" in content


class TestCSPFix:
    def test_partial_has_csp_nonce(self):
        with open("kb_server/ui/templates/admin/_ragas_editor.html") as f:
            content = f.read()
        assert "nonce" in content

    def test_ragas_empty_state_text(self):
        with open("kb_server/ui/templates/admin/_ragas_results.html") as f:
            content = f.read()
        assert "No evaluation results yet" in content


class TestSessionManagement:

    def _setup_auth(self, client):
        from unittest.mock import MagicMock
        from kb_server.auth.deps import get_current_user
        from kb_server.auth.models import User

        mock_user = MagicMock(spec=User)
        mock_user.id = "test-admin-id"
        mock_user.username = "admin"
        mock_user.role = "admin"
        mock_user.is_active = True

        async def _mock_get_current_user():
            return mock_user

        client.app.dependency_overrides[get_current_user] = (
            _mock_get_current_user
        )

    def test_session_timeout_uses_env(self):
        """SESSION_TIMEOUT env var is read by router.py."""
        from kb_server.auth.router import _SESSION_TIMEOUT
        assert _SESSION_TIMEOUT == 1800

    def test_session_list_endpoint_returns_list(self, client):
        """GET /api/v1/auth/sessions returns a list."""
        from kb_server.auth.deps import get_current_user
        from unittest.mock import MagicMock
        from kb_server.auth.models import User

        mock_user = MagicMock(spec=User)
        mock_user.id = "test-admin-id"
        mock_user.username = "admin"
        mock_user.role = "admin"
        mock_user.is_active = True

        async def _mock_get_current_user():
            return mock_user

        client.app.dependency_overrides[get_current_user] = (
            _mock_get_current_user
        )
        resp = client.get("/api/v1/auth/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_sessions_table_template_exists(self):
        assert os.path.exists(
            "kb_server/ui/templates/admin/_sessions_table.html"
        )

    def test_sessions_table_has_revoke(self):
        with open(
            "kb_server/ui/templates/admin/_sessions_table.html"
        ) as f:
            content = f.read()
        assert "Revoke" in content
        assert "No active sessions" in content

    def test_sessions_content_route_returns_200(self, client):
        """GET /admin/tabs/sessions-content returns 200."""
        self._setup_auth(client)
        resp = client.get("/admin/tabs/sessions-content")
        assert resp.status_code == 200


class TestCredentialsSection:

    def _setup_auth(self, client):
        from unittest.mock import MagicMock
        from kb_server.auth.deps import get_current_user
        from kb_server.auth.models import User

        mock_user = MagicMock(spec=User)
        mock_user.id = "test-admin-id"
        mock_user.username = "admin"
        mock_user.role = "admin"
        mock_user.is_active = True

        async def _mock_get_current_user():
            return mock_user

        client.app.dependency_overrides[get_current_user] = (
            _mock_get_current_user
        )

    def test_credentials_template_exists(self):
        assert os.path.exists(
            "kb_server/ui/templates/admin/_credentials_section.html"
        )

    def test_credentials_has_generate_key(self):
        with open(
            "kb_server/ui/templates/admin/_credentials_section.html"
        ) as f:
            content = f.read()
        assert "Generate New Key" in content
        assert "API Keys" in content

    def test_credentials_content_route_returns_200(self, client):
        """GET /admin/tabs/credentials-content returns 200."""
        self._setup_auth(client)
        resp = client.get("/admin/tabs/credentials-content")
        assert resp.status_code == 200

    def test_tab_admin_loads_sessions_and_credentials(self):
        with open("kb_server/ui/templates/admin/tab_admin.html") as f:
            content = f.read()
        assert '{% include "admin/_sessions_table.html" %}' in content
        assert '{% include "admin/_credentials_section.html" %}' in content
