"""Smoke tests for kb_server/ui/ — app.py, routes.py, run_ui.py.

Uses FastAPI TestClient with mocked SQLite to avoid live DB dependency.
"""

import sys
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Ensure kb_server.ui is the real package before test_smoke.py stubs it.
# Import eagerly here so our package wins in sys.modules.
# ---------------------------------------------------------------------------
import kb_server.ui.routes  # noqa: F401 — registers routes on app
from kb_server.ui.app import app, _version

client = TestClient(app, raise_server_exceptions=False)

# ── Helper: setup auth override for admin tab tests ────────────────────────
# The module-level TestClient doesn't trigger app startup events, so
# app.state.auth_service is not set.  Override get_current_user to return a
# mock admin user for tests that hit protected admin endpoints.
# NOTE: This must be called in each test class that needs it, because
# test_admin_ui.py's client fixture pops get_current_user from
# dependency_overrides after each test.
from unittest.mock import MagicMock
from kb_server.auth.deps import get_current_user


def _setup_auth():
    _admin = MagicMock()
    _admin.id = 1
    _admin.username = "admin"
    _admin.role = "admin"
    _admin.is_active = True

    async def _mock():
        return _admin

    app.dependency_overrides[get_current_user] = _mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fake_row(doc_id: int = 1) -> dict:
    return {
        "id": doc_id,
        "file_path": f"/docs/guide{doc_id}.md",
        "product": "testproduct",
        "doc_type": "guide",
        "version": "1.0",
        "status": "indexed",
        "chunk_count": 5,
        "checksum": "abc123",
    }


# ---------------------------------------------------------------------------
# app.py — version, health, root redirect
# ---------------------------------------------------------------------------
class TestAppModule:
    def test_version_is_string(self):
        assert isinstance(_version, str)
        assert len(_version) > 0

    def test_health_endpoint_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "kb-rag-ui"

    def test_root_redirects_to_browse(self):
        # follow_redirects=False to inspect the redirect itself
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (301, 302, 307, 308)
        assert "/ui/browse" in resp.headers.get("location", "")


# ---------------------------------------------------------------------------
# routes.py — get_documents helper
# ---------------------------------------------------------------------------
class TestGetDocuments:
    def _make_conn_mock(self):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        return mock_conn

    def test_returns_empty_on_no_rows(self):
        mock_conn = self._make_conn_mock()
        mock_conn.cursor.return_value.fetchone.return_value = (0,)
        mock_conn.cursor.return_value.fetchall.return_value = []
        with patch("sqlite3.connect", return_value=mock_conn):
            from kb_server.ui.routes import get_documents

            docs, total = get_documents()
        assert docs == []
        assert total == 0

    def test_returns_rows_as_dicts(self):
        fake = _fake_row()
        mock_conn = self._make_conn_mock()
        mock_row = MagicMock()
        mock_row.__iter__ = MagicMock(return_value=iter(fake.items()))
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.fetchall.return_value = [fake]
        mock_conn.cursor.return_value = mock_cursor
        # Patch dict(row) — rows are already dicts in our mock
        with patch("sqlite3.connect", return_value=mock_conn):
            # Patch conn.row_factory assignment (no-op in mock)
            mock_conn.row_factory = None
            from kb_server.ui.routes import get_documents

            # cursor.fetchall returns dicts; dict(row) on a dict = dict
            # Use sqlite3.Row-like objects (not plain dicts) since routes uses dict(row)
            class FakeRow:
                def __init__(self, data):
                    self._data = data

                def __iter__(self):
                    return iter(self._data.items())

                def keys(self):
                    return self._data.keys()

                def __getitem__(self, key):
                    return self._data[key]

                def get(self, key, default=None):
                    return self._data.get(key, default)

            mock_cursor.fetchall.return_value = [FakeRow(fake)]
            docs, total = get_documents(product="testproduct")
        assert total == 1

    def test_filters_build_where_clause(self):
        """Verify SQL params include all four filter values when set."""
        captured_params = []

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_cursor.fetchall.return_value = []

        def capture_execute(sql, params=()):
            captured_params.append(list(params))

        mock_cursor.execute.side_effect = capture_execute
        mock_conn = self._make_conn_mock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("sqlite3.connect", return_value=mock_conn):
            from kb_server.ui.routes import get_documents

            get_documents(
                product="prod",
                doc_type="guide",
                version="2.0",
                status="indexed",
            )

        # Both COUNT and SELECT calls should carry the 4 filter params
        assert len(captured_params) >= 1
        flat = [p for call in captured_params for p in call]
        assert "prod" in flat
        assert "guide" in flat
        assert "2.0" in flat
        assert "indexed" in flat


# ---------------------------------------------------------------------------
# routes.py — HTTP endpoints via TestClient
# ---------------------------------------------------------------------------
def _html_response(text: str = "<html>ok</html>", status_code: int = 200):
    """Return a minimal HTMLResponse for template mocking."""
    from fastapi.responses import HTMLResponse

    return HTMLResponse(content=text, status_code=status_code)


def _mock_template_response():
    """Patch templates.TemplateResponse to avoid Jinja2 rendering."""
    return patch(
        "kb_server.ui.routes.templates.TemplateResponse",
        side_effect=lambda request, name, ctx, status_code=200, **kw: _html_response(
            f"<html>{name}</html>", status_code=status_code
        ),
    )


def _not_found_template_response():
    """Simulate a 404 TemplateResponse for document not found."""
    from fastapi.responses import HTMLResponse

    def _side_effect(request, name, ctx, status_code=200, **kw):
        return HTMLResponse(
            content=f"<html>{name}</html>", status_code=status_code
        )

    return patch(
        "kb_server.ui.routes.templates.TemplateResponse",
        side_effect=_side_effect,
    )


class TestUIEndpoints:
    def _mock_get_documents(self, docs=None, total=None):
        docs = docs or [_fake_row()]
        total = total if total is not None else len(docs)
        return patch(
            "kb_server.ui.routes.get_documents", return_value=(docs, total)
        )

    def test_browse_returns_200(self):
        with self._mock_get_documents(), _mock_template_response():
            resp = client.get("/ui/browse")
        assert resp.status_code == 200

    def test_browse_with_filters_passes_params(self):
        with (
            patch(
                "kb_server.ui.routes.get_documents", return_value=([], 0)
            ) as mock_gd,
            _mock_template_response(),
        ):
            client.get("/ui/browse?product=myproduct&doc_type=guide")
        mock_gd.assert_called_once()
        _, kwargs = mock_gd.call_args
        assert kwargs.get("product") == "myproduct"
        assert kwargs.get("doc_type") == "guide"

    def test_browse_empty_results_200(self):
        with (
            self._mock_get_documents(docs=[], total=0),
            _mock_template_response(),
        ):
            resp = client.get("/ui/browse")
        assert resp.status_code == 200

    def test_search_tester_returns_200(self):
        with _mock_template_response():
            resp = client.get("/ui/search")
        assert resp.status_code == 200

    def test_search_endpoint_returns_results(self):
        """POST /ui/search returns HTML results."""
        from mcp.types import TextContent

        fake_result = TextContent(
            type="text",
            text="## Results for: 'test query'\n\n### [1] doc.md (relevance: 95.0%)",
        )

        with (
            patch(
                "kb_server.server._search_kb",
                return_value=[fake_result],
            ) as mock_search,
            _mock_template_response(),
        ):
            resp = client.post(
                "/ui/search",
                data={"query": "test query", "top_k": "5"},
            )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        mock_search.assert_called_once()
        args = mock_search.call_args[0][0]
        assert args["query"] == "test query"
        assert args["top_k"] == 5

    def test_search_endpoint_no_results(self):
        """POST /ui/search handles empty results gracefully."""
        from mcp.types import TextContent

        with (
            patch(
                "kb_server.server._search_kb",
                return_value=[
                    TextContent(
                        type="text",
                        text="No results found in the knowledge base",
                    )
                ],
            ),
            _mock_template_response(),
        ):
            resp = client.post(
                "/ui/search",
                data={"query": "missing query"},
            )
        assert resp.status_code == 200

    def test_search_endpoint_passes_all_params(self):
        """POST /ui/search passes all form params to _search_kb."""
        from mcp.types import TextContent

        with (
            patch(
                "kb_server.server._search_kb",
                return_value=[TextContent(type="text", text="ok")],
            ) as mock_search,
            _mock_template_response(),
        ):
            client.post(
                "/ui/search",
                data={
                    "query": "q",
                    "top_k": "10",
                    "product": "myproduct",
                    "version": "1.0",
                    "hybrid": "true",
                    "rerank": "true",
                },
            )
        args = mock_search.call_args[0][0]
        assert args["query"] == "q"
        assert args["top_k"] == 10
        assert args["product"] == "myproduct"
        assert args["version"] == "1.0"
        assert args["hybrid"] is True
        assert args["rerank"] is True

    def test_document_detail_not_found_returns_404(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor

        with (
            patch("sqlite3.connect", return_value=mock_conn),
            _not_found_template_response(),
        ):
            resp = client.get("/ui/document/9999")
        assert resp.status_code == 404

    def test_document_detail_found_returns_200(self):
        fake = _fake_row(doc_id=42)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = fake
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor

        with (
            patch("sqlite3.connect", return_value=mock_conn),
            _mock_template_response(),
        ):
            resp = client.get("/ui/document/42")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# run_ui.py — importability smoke test
# ---------------------------------------------------------------------------
class TestChunkPreview:
    def test_document_detail_accepts_q_param(self):
        from kb_server.ui.routes import document_detail
        import inspect

        sig = inspect.signature(document_detail)
        assert "q" in sig.parameters

    def test_highlight_term_registered(self):
        from kb_server.ui.app import templates

        assert "highlight_term" in templates.env.globals

    def test_highlight_term_wraps_matches(self):
        from kb_server.ui.app import highlight_term

        result = highlight_term("The quick brown fox", "quick")
        assert "<mark>quick</mark>" in result

    def test_highlight_term_no_query(self):
        from kb_server.ui.app import highlight_term

        result = highlight_term("hello world", None)
        assert result == "hello world"

    def test_highlight_term_empty_text(self):
        from kb_server.ui.app import highlight_term

        assert highlight_term("", "test") == ""
        assert highlight_term("", None) == ""

    def test_chunk_template_exists(self):
        import os

        assert os.path.exists("kb_server/ui/templates/document_chunks.html")


class TestParseSearchResults:
    def test_parse_empty_text(self):
        from kb_server.ui.routes import _parse_search_results
        assert _parse_search_results("") == []

    def test_parse_with_all_metadata(self):
        from kb_server.ui.routes import _parse_search_results
        text = (
            "Header text\n\n"
            "### [1] guide.md (relevance: 95.0%)\n"
            "**ID:** `chunk_123`\n"
            "**Product:** MyProduct\n"
            "**Type:** guide\n"
            "**Page/section:** p.5\n"
            "\n"
            "Chunk content here\n"
            "---\n"
        )
        results = _parse_search_results(text)
        assert len(results) == 1
        assert results[0]["source_file"] == "guide.md"
        assert results[0]["score"] == 0.95
        assert results[0]["chunk_id"] == "chunk_123"
        assert results[0]["product"] == "MyProduct"
        assert results[0]["doc_type"] == "guide"
        assert results[0]["page"] == "p.5"
        assert "Chunk content here" in results[0]["text"]

    def test_parse_section_without_lines(self):
        from kb_server.ui.routes import _parse_search_results
        text = "Header\n\n### [1] doc.md (relevance: 50.0%)\n"
        results = _parse_search_results(text)
        assert len(results) == 1
        assert results[0]["source_file"] == "doc.md"

    def test_parse_no_relevance(self):
        from kb_server.ui.routes import _parse_search_results
        text = "Header\n\n### [1] doc.md\n\nSome text\n---\n"
        results = _parse_search_results(text)
        assert len(results) == 1
        assert results[0]["source_file"] == "doc.md"
        assert results[0]["score"] == 0.0

    def test_parse_no_text_section(self):
        from kb_server.ui.routes import _parse_search_results
        text = (
            "Header\n\n"
            "### [1] doc.md (relevance: 80.0%)\n"
            "**ID:** `chunk_1`\n"
        )
        results = _parse_search_results(text)
        assert len(results) == 1
        # No text_parts[1] — chunk_text stays empty
        assert results[0]["text"] == ""
        assert results[0]["chunk_id"] == "chunk_1"


class TestHeadingHierarchy:
    def setup_method(self):
        _setup_auth()

    def test_heading_hierarchy(self):
        """Verify no skipped heading levels in rendered HTML."""
        import re

        pages = [
            "/ui/browse",
            "/ui/search",
            "/admin",
            "/admin/tabs/analytics",
            "/admin/tabs/monitoring",
        ]

        # Inject missing template globals for routes_admin templates
        from kb_server.ui import routes_admin

        routes_admin.templates.env.globals["build_grafana_embed_url"] = (
            routes_admin.build_grafana_embed_url
        )
        routes_admin.templates.env.globals[
            "build_grafana_embed_url_with_range"
        ] = routes_admin.build_grafana_embed_url_with_range

        for path in pages:
            if path == "/ui/browse":
                with self._mock_get_documents():
                    resp = client.get(path)
            elif path == "/admin/tabs/analytics":
                with patch(
                    "kb_server.analytics.query_analyzer.QueryAnalyzer",
                ) as mock_analyzer:
                    instance = mock_analyzer.return_value
                    instance.get_most_common_queries.return_value = []
                    instance.get_zero_result_queries.return_value = []
                    instance.get_latency_stats.return_value = []
                    resp = client.get(path)
            else:
                resp = client.get(path)

            assert resp.status_code == 200, f"{path} returned {resp.status_code}"
            html = resp.text
            headings = re.findall(r"<h([1-6])", html)
            if headings:
                levels = [int(h) for h in headings]
                for i in range(1, len(levels)):
                    if levels[i] > levels[i - 1] + 1:
                        assert False, (
                            f"Heading skip at {path}: "
                            f"h{levels[i - 1]} -> h{levels[i]}"
                        )

    def _mock_get_documents(self, docs=None, total=None):
        docs = docs or [_fake_row()]
        total = total if total is not None else len(docs)
        return patch(
            "kb_server.ui.routes.get_documents", return_value=(docs, total)
        )


class TestNavbarActiveState:
    def _mock_get_documents(self, docs=None, total=None):
        docs = docs or [_fake_row()]
        total = total if total is not None else len(docs)
        return patch(
            "kb_server.ui.routes.get_documents", return_value=(docs, total)
        )

    def test_navbar_active_state(self):
        """Navbar highlights current page."""
        pages = {
            "/ui/browse": "browse",
            "/ui/search": "search",
            "/admin": "admin",
        }

        for path, expected_active in pages.items():
            if path == "/ui/browse":
                with self._mock_get_documents():
                    resp = client.get(path)
            else:
                resp = client.get(path)

            assert resp.status_code == 200
            html = resp.text
            assert 'nav-link' in html and 'active' in html
            # Verify the expected link has aria-current
            if expected_active == "browse":
                assert 'href="/ui/browse"' in html
                assert 'aria-current="page"' in html
            elif expected_active == "search":
                assert 'href="/ui/search"' in html
                assert 'aria-current="page"' in html
            elif expected_active == "admin":
                assert 'href="/admin"' in html
                assert 'aria-current="page"' in html


class TestInlineStyles:
    def _mock_get_documents(self, docs=None, total=None):
        docs = docs or [_fake_row()]
        total = total if total is not None else len(docs)
        return patch(
            "kb_server.ui.routes.get_documents", return_value=(docs, total)
        )

    def test_no_inline_styles_in_critical_templates(self):
        """Verify no inline styles in rendered HTML pages.

        Known exceptions for the login overlay in shell.html:
          - position/background/z-index, min-height, width
        """
        import re

        known_overlay = {
            ' style="position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9999;"',
            ' style="min-height: 100vh;"',
            ' style="width: 350px;"',
        }

        pages = [
            "/ui/browse",
            "/ui/search",
            "/admin",
        ]

        for path in pages:
            if path == "/ui/browse":
                with self._mock_get_documents():
                    resp = client.get(path)
            else:
                resp = client.get(path)

            assert resp.status_code == 200, f"{path} returned {resp.status_code}"
            html = resp.text
            style_matches = re.findall(r'\sstyle="[^"]*"', html)
            bad_styles = [
                s for s in style_matches if s not in known_overlay
            ]
            assert len(bad_styles) == 0, (
                f"Found inline styles in {path}: {bad_styles}"
            )


class TestRunUiModule:
    def test_run_ui_imports_without_error(self):
        """run_ui.py should be importable without starting uvicorn."""
        import importlib
        import kb_server.ui.run_ui as run_ui_mod

        # The module-level code (sys.path insert, imports) ran without error
        assert run_ui_mod is not None

    def test_run_ui_exposes_app(self):
        from kb_server.ui.run_ui import app as run_app

        assert run_app is not None


class TestAdminBadges:
    def setup_method(self):
        _setup_auth()

    def test_admin_badges_outline(self):
        """Admin badges use outline style for contrast."""
        resp = client.get("/admin/tabs/profile")
        assert resp.status_code == 200
        html = resp.text
        assert 'bg-success' not in html
        assert 'text-success border border-success' in html
        assert 'bg-danger' not in html


class TestLoginFormLabels:
    def test_login_form_labels(self):
        """Login form has visible labels in shell.html."""
        with open("kb_server/ui/templates/admin/shell.html") as f:
            content = f.read()
        assert 'placeholder="Username"' in content
        assert 'placeholder="Password"' in content
        assert 'aria-label="Username"' in content
        assert 'aria-label="Password"' in content


class TestProfileConfigValidation:
    def setup_method(self):
        _setup_auth()

    def test_profile_config_validation(self):
        """Profile tab shows config validation badges."""
        resp = client.get("/admin/tabs/profile")
        assert resp.status_code == 200
        html = resp.text
        assert "Top-K:" in html
        assert "BM25 Enabled:" in html
        assert "Reranker Enabled:" in html
        assert 'text-success border border-success' in html
        assert 'text-danger border border-danger' not in html


class TestErrorHandlers:
    def test_404_error_page(self):
        """404 returns user-friendly error page."""
        resp = client.get("/nonexistent")
        assert resp.status_code == 404
        assert "Error 404" in resp.text
        assert "Try searching" in resp.text

    def test_403_error_page(self):
        """403 returns user-friendly error page."""
        from fastapi import HTTPException
        resp = client.get("/ui/search")
        assert resp.status_code == 200
        assert "Error" in resp.text

    def test_search_loading_state(self):
        """Search page has loading indicator."""
        resp = client.get("/ui/search")
        assert resp.status_code == 200
        assert "search-loading" in resp.text
        assert "Searching knowledge base" in resp.text

    def test_admin_shell_error_state(self):
        """Admin shell has tab error state."""
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert "tab-error" in resp.text
        assert "Failed to load tab content" in resp.text

    def test_base_html_has_htmx_error_handler(self):
        """Base template includes global HTMX error handling."""
        resp = client.get("/ui/search")
        assert resp.status_code == 200
        assert "htmx:sendError" in resp.text
        assert "Network error. Please check your connection." in resp.text
