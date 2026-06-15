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
    def test_returns_empty_on_no_rows(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchone.return_value = (0,)
        mock_conn.cursor.return_value.fetchall.return_value = []
        with patch("sqlite3.connect", return_value=mock_conn):
            from kb_server.ui.routes import get_documents

            docs, total = get_documents()
        assert docs == []
        assert total == 0

    def test_returns_rows_as_dicts(self):
        fake = _fake_row()
        # sqlite3.Row-like: fetchone returns count, fetchall returns row-like objects
        mock_row = MagicMock()
        mock_row.__iter__ = MagicMock(return_value=iter(fake.items()))
        # Make dict(row) work by having the mock support it
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.fetchall.return_value = [fake]
        mock_conn = MagicMock()
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
        mock_conn = MagicMock()
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

    def test_document_detail_not_found_returns_404(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
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
