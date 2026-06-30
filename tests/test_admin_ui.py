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


class TestMonitorLights:
    """Monitor lights bar — 7 components, latency, click-to-expand, ARIA, warning state."""

    def test_monitor_lights_template_exists(self):
        """_monitor_lights.html template exists."""
        assert os.path.exists(
            "kb_server/ui/templates/admin/_monitor_lights.html"
        )

    def test_monitor_lights_has_llm(self):
        """_monitor_lights.html contains LLM as 7th component."""
        with open("kb_server/ui/templates/admin/_monitor_lights.html") as f:
            content = f.read()
        assert "LLM" in content
        # Count the 7 component labels
        for label in ["Qdrant", "Embedding", "Cache", "Database",
                       "Filesystem", "Grafana", "LLM"]:
            assert label in content

    def test_monitor_lights_shows_latency(self):
        """Each component card shows latency in ms."""
        with open("kb_server/ui/templates/admin/_monitor_lights.html") as f:
            content = f.read()
        assert "latency_ms" in content
        assert "ms" in content

    def test_monitor_lights_click_to_expand(self):
        """Component cards have @click toggle for details expansion."""
        with open("kb_server/ui/templates/admin/_monitor_lights.html") as f:
            content = f.read()
        assert "@click" in content
        assert "expanded" in content
        assert "x-show" in content

    def test_monitor_lights_aria_labels(self):
        """Status badges have aria-label with component name and status."""
        with open("kb_server/ui/templates/admin/_monitor_lights.html") as f:
            content = f.read()
        assert "aria-label" in content
        # Should reference status in aria-label
        assert "aria-label=\"{{ label }} status:" in content or \
               'aria-label="{{ label }} status:' in content

    def test_monitor_lights_warning_state(self):
        """Degraded/warning state renders bg-warning."""
        with open("kb_server/ui/templates/admin/_monitor_lights.html") as f:
            content = f.read()
        assert "bg-warning" in content
        assert "degraded" in content

    def test_monitor_lights_route_works(self, client):
        """GET /admin/tabs/monitor-lights returns 200 with monitor lights HTML."""
        from unittest.mock import AsyncMock, MagicMock, patch
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

        mock_components = {
            "vector_store": {"healthy": True, "message": "Connected", "latency_ms": 12},
            "embedding": {"healthy": True, "message": "Ready", "latency_ms": 5},
            "cache": {"healthy": True, "message": "Active", "latency_ms": 1},
            "database": {"healthy": True, "message": "OK", "latency_ms": 3},
            "filesystem": {"healthy": True, "message": "Mounted", "latency_ms": 0},
            "grafana": {"degraded": True, "message": "Degraded", "latency_ms": 200},
            "llm": {"healthy": True, "message": "Available", "latency_ms": 150},
        }

        with patch(
            "kb_server.health.check_all_components",
            new=AsyncMock(return_value=mock_components),
        ):
            resp = client.get("/admin/tabs/monitor-lights")
        assert resp.status_code == 200
        assert "LLM" in resp.text
        assert "12ms" in resp.text or "150ms" in resp.text

    def test_monitor_lights_all_seven_components(self, client):
        """All 7 components render in the monitor lights response."""
        from unittest.mock import AsyncMock, MagicMock, patch
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

        mock_components = {
            "vector_store": {"healthy": True, "message": "Connected"},
            "embedding": {"healthy": True, "message": "Ready"},
            "cache": {"healthy": True, "message": "Active"},
            "database": {"healthy": True, "message": "OK"},
            "filesystem": {"healthy": True, "message": "Mounted"},
            "grafana": {"healthy": True, "message": "Running"},
            "llm": {"healthy": True, "message": "Available"},
        }

        with patch(
            "kb_server.health.check_all_components",
            new=AsyncMock(return_value=mock_components),
        ):
            resp = client.get("/admin/tabs/monitor-lights")
        assert resp.status_code == 200
        for label in ["Qdrant", "Embedding", "Cache", "Database",
                       "Filesystem", "Grafana", "LLM"]:
            assert label in resp.text, f"Missing component: {label}"

    def test_monitor_lights_degraded_shows_warning(self, client):
        """Degraded component renders bg-warning in the response."""
        from unittest.mock import AsyncMock, MagicMock, patch
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

        mock_components = {
            "vector_store": {"healthy": True, "message": "Connected"},
            "embedding": {"healthy": True, "message": "Ready"},
            "cache": {"healthy": True, "message": "Active"},
            "database": {"healthy": True, "message": "OK"},
            "filesystem": {"healthy": True, "message": "Mounted"},
            "grafana": {"degraded": True, "message": "Degraded"},
            "llm": {"healthy": True, "message": "Available"},
        }

        with patch(
            "kb_server.health.check_all_components",
            new=AsyncMock(return_value=mock_components),
        ):
            resp = client.get("/admin/tabs/monitor-lights")
        assert resp.status_code == 200
        assert "bg-warning" in resp.text


class TestConfigEditor:
    """Config inline editor — Reset All, Group badges, HTMX PUT, aria-live, placeholder."""

    def test_config_has_reset_all(self):
        """_config_table.html contains a Reset All button with hx-confirm."""
        with open("kb_server/ui/templates/admin/_config_table.html") as f:
            content = f.read()
        assert "Reset All" in content
        assert "hx-confirm" in content

    def test_config_group_badges(self):
        """Group column renders badge bg-info instead of plain text."""
        with open("kb_server/ui/templates/admin/_config_table.html") as f:
            content = f.read()
        assert "badge bg-info" in content
        assert "entry.group_name" in content

    def test_config_save_uses_alpine_fetch(self):
        """Save mechanism uses Alpine.js fetch() on @keydown.enter."""
        with open("kb_server/ui/templates/admin/_config_table.html") as f:
            content = f.read()
        assert "@keydown.enter.prevent" in content
        assert "fetch('/api/v1/config/'" in content
        assert "method: 'PUT'" in content
        assert "JSON.stringify({value: editValue})" in content

    def test_config_error_aria_live(self):
        """Error container has aria-live='assertive' and role='alert'."""
        with open("kb_server/ui/templates/admin/_config_table.html") as f:
            content = f.read()
        assert 'aria-live="assertive"' in content
        assert 'role="alert"' in content

    def test_config_search_placeholder(self):
        """Search placeholder is 'Search config keys...'."""
        with open("kb_server/ui/templates/admin/_config_table.html") as f:
            content = f.read()
        assert 'placeholder="Search config keys..."' in content

    def test_config_table_route_works(self, client):
        """GET /admin/tabs/config-table returns 200."""
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
        resp = client.get("/admin/tabs/config-table")
        assert resp.status_code == 200
        assert "Search config keys" in resp.text


class TestRouteOrdering:
    """Specific /tabs/ paths resolve correctly (not shadowed by generic /tabs/{tab_name})."""

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

    def test_specific_routes_not_shadowed(self, client):
        """GET /admin/tabs/documents-content returns 200 (not 'Unknown tab')."""
        self._setup_auth(client)
        resp = client.get("/admin/tabs/documents-content")
        assert resp.status_code == 200
        assert "Unknown tab" not in resp.text

    def test_config_table_route_works(self, client):
        """GET /admin/tabs/config-table returns 200."""
        self._setup_auth(client)
        resp = client.get("/admin/tabs/config-table")
        assert resp.status_code == 200
        assert "Unknown tab" not in resp.text

    def test_profile_content_route_works(self, client):
        """GET /admin/tabs/profile-content returns 200."""
        self._setup_auth(client)
        resp = client.get("/admin/tabs/profile-content")
        assert resp.status_code == 200
        assert "Unknown tab" not in resp.text

    def test_generic_tab_route_still_works(self, client):
        """GET /admin/tabs/documents still resolves to generic handler."""
        self._setup_auth(client)
        resp = client.get("/admin/tabs/documents")
        assert resp.status_code == 200
        assert "Unknown tab" not in resp.text


class TestSidebarLayout:
    """Sidebar responsive breakpoints — 280px, icon-only 60px at md, hamburger at sm, ARIA."""

    def test_sidebar_width_280px(self):
        """styles.css sets .admin-sidebar width: 280px."""
        with open("kb_server/ui/static/styles.css") as f:
            content = f.read()
        assert "width: 280px" in content

    def test_sidebar_md_breakpoint(self):
        """styles.css has @media (min-width: 768px) for icon-only 60px."""
        with open("kb_server/ui/static/styles.css") as f:
            content = f.read()
        assert "@media (min-width: 768px) and (max-width: 991px)" in content
        assert "width: 60px" in content

    def test_sidebar_sm_breakpoint(self):
        """styles.css has @media (max-width: 767px) for hamburger-hidden."""
        with open("kb_server/ui/static/styles.css") as f:
            content = f.read()
        assert "@media (max-width: 767px)" in content
        assert ".admin-sidebar" in content

    def test_sidebar_text_light(self):
        """shell.html uses text-light classes on sidebar."""
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert 'text-light' in content

    def test_sidebar_aria_roles(self):
        """shell.html has role='navigation' and role='tablist' on sidebar nav."""
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert 'role="navigation"' in content
        assert 'role="tablist"' in content

    def test_sidebar_hamburger_button(self):
        """shell.html has hamburger toggle button for mobile."""
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert "d-md-none" in content
        assert "toggle-sidebar" in content
        assert "aria-label" in content


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
