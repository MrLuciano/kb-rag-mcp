import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from kb_server.ui.app import app


@pytest.fixture
def client():
    return TestClient(app)


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
    def test_build_grafana_embed_url_empty_without_env(self):
        from kb_server.ui.routes_admin import build_grafana_embed_url

        url = build_grafana_embed_url()
        assert url == ""

    def test_build_grafana_embed_url_with_range_empty_without_env(self):
        from kb_server.ui.routes_admin import (
            build_grafana_embed_url_with_range,
        )

        url = build_grafana_embed_url_with_range("6h")
        assert url == ""

    def test_grafana_globals_registered(self):
        from kb_server.ui.app import templates

        assert "build_grafana_embed_url" in templates.env.globals
        assert "build_grafana_embed_url_with_range" in templates.env.globals


class TestAdminTemplates:
    def test_all_tab_templates_exist(self):
        tabs = [
            "documents",
            "monitoring",
            "ingestion",
            "ragas",
            "admin",
            "profile",
        ]
        for tab in tabs:
            path = f"kb_server/ui/templates/admin/tab_{tab}.html"
            assert os.path.exists(path), f"Missing template: {path}"

    def test_shell_template_exists(self):
        assert os.path.exists("kb_server/ui/templates/admin/shell.html")
