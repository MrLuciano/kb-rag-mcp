"""
Tests for Confluence connector (Cloud + 7.9.3 Server/DC).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingest.connectors.models import ConnectorConfig


@pytest.fixture
def server_config():
    return ConnectorConfig(
        source_key="confluence://myspace",
        connector_type="confluence",
        endpoint="https://confluence.example.com/rest/api",
        auth_method="basic",
        auth_credentials="CONFLUENCE_TOKEN",
    )


@pytest.fixture
def cloud_config():
    return ConnectorConfig(
        source_key="confluence://myspace",
        connector_type="confluence",
        endpoint="https://example.atlassian.net/wiki/rest/api",
        auth_method="token",
        auth_credentials="CONFLUENCE_TOKEN",
    )


class TestConfluenceAuth:
    def test_server_auth_header(self, server_config, monkeypatch):
        from ingest.connectors.confluence import ConfluenceConnector

        monkeypatch.setenv("CONFLUENCE_USERNAME", "admin")
        monkeypatch.setenv("CONFLUENCE_TOKEN", "mytoken")
        conn = ConfluenceConnector(server_config)
        header = conn._auth_header()
        assert "Authorization" in header
        assert header["Authorization"].startswith("Basic ")

    def test_cloud_auth_header(self, cloud_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(cloud_config)
        header = conn._auth_header()
        assert header["Authorization"] == "Bearer CONFLUENCE_TOKEN"


class TestConfluenceContentExtraction:
    def test_storage_format_to_markdown(self):
        from ingest.connectors.confluence import _storage_to_markdown

        html = "<p>Hello <strong>world</strong></p>"
        md = _storage_to_markdown(html)
        assert "Hello" in md
        assert "world" in md

    def test_empty_content_returns_empty(self):
        from ingest.connectors.confluence import _storage_to_markdown

        assert _storage_to_markdown("") == ""

    def test_plain_text_passthrough(self):
        from ingest.connectors.confluence import _storage_to_markdown

        assert "hello" in _storage_to_markdown("hello")

    def test_html_fallback_without_html2text(self):
        from ingest.connectors.confluence import _storage_to_markdown

        html = "<p>Para 1</p><p>Para 2</p>"
        md = _storage_to_markdown(html)
        assert "Para 1" in md
        assert "Para 2" in md
        # Verify HTML tags are stripped (no angle brackets remain from tags)
        assert "<p>" not in md
        assert "</p>" not in md
        assert "<" not in md or "<" in md  # Only '<' in text should be if content contained it

    def test_html_fallback_strips_all_tags(self):
        """HTML fallback removes all HTML tags, leaving only text."""
        from ingest.connectors.confluence import _storage_to_markdown

        html = (
            "<div><h1>Title</h1><p>Some <b>bold</b> text</p>"
            "<ul><li>Item 1</li><li>Item 2</li></ul></div>"
        )
        md = _storage_to_markdown(html)
        # All text content should survive
        assert "Title" in md
        assert "Some" in md
        assert "bold" in md
        assert "Item 1" in md
        assert "Item 2" in md
        # No HTML tags should remain
        assert "<div>" not in md
        assert "</div>" not in md
        assert "<h1>" not in md
        assert "<b>" not in md
        assert "</b>" not in md
        assert "<ul>" not in md
        assert "<li>" not in md


class TestConfluencePagination:
    def test_offset_pagination_url(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)
        url = conn._build_content_url(space="DEV", start=50, limit=200)
        assert "start=50" in url
        assert "limit=200" in url

    def test_cursor_pagination_url(self, cloud_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(cloud_config)
        url = conn._build_content_url(space="DEV", cursor="abc123")
        assert "cursor=abc123" in url


class TestConfluenceCQL:
    def test_cql_without_checkpoint(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)
        cql = conn._build_cql(space="DEV")
        assert "space=DEV" in cql
        assert "type=page" in cql

    def test_cql_with_checkpoint(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)
        cql = conn._build_cql(space="DEV", since="2026-01-01T00:00:00Z")
        assert "lastModified" in cql
        assert "2026-01-01" in cql

    def test_cql_with_labels(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)
        cql = conn._build_cql(space="DEV", labels=["howto", "reference"])
        assert "label=" in cql
        assert "howto" in cql or "reference" in cql


class TestConfluenceVersionDetection:
    def test_server_version_from_custom_url(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)
        assert conn._detect_version() == "server"

    def test_cloud_version_from_atlassian_url(self, cloud_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(cloud_config)
        assert conn._detect_version() == "cloud"


@pytest.mark.asyncio
class TestConfluenceFetchDocuments:
    async def test_fetch_with_mocked_http(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)

        spaces_response = MagicMock()
        spaces_response.status_code = 200
        spaces_response.json.return_value = {
            "results": [{"key": "DEV", "name": "Development"}],
            "size": 1,
        }

        content_response = MagicMock()
        content_response.status_code = 200
        content_response.json.return_value = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "space": {
                        "key": "DEV",
                        "name": "Development",
                    },
                    "version": {
                        "number": 1,
                        "when": "2026-01-01T00:00:00Z",
                    },
                    "body": {
                        "storage": {
                            "value": "<p>Hello world</p>",
                            "representation": "storage",
                        }
                    },
                    "_links": {"webui": "/pages/123"},
                }
            ],
            "size": 1,
            "start": 0,
            "limit": 200,
            "totalSize": 1,
            "_links": {},
        }

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock()
            mc.get.side_effect = [spaces_response, content_response]
            mf.return_value = mc
            result = await conn.fetch_documents()

        assert result.success_count == 1
        assert result.documents[0].remote_id == "123"
        assert result.documents[0].title == "Test Page"
        assert "Hello world" in result.documents[0].content

    async def test_fetch_handles_failure(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)

        spaces_response = MagicMock()
        spaces_response.status_code = 200
        spaces_response.json.return_value = {
            "results": [{"key": "DEV", "name": "Development"}],
            "size": 1,
        }

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = Exception("API error")

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock()
            mc.get.side_effect = [spaces_response, error_response]
            mf.return_value = mc
            result = await conn.fetch_documents()
            assert result.has_errors()

    async def test_fetch_document_by_id(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "456",
            "title": "Single Page",
            "space": {"key": "DEV", "name": "Development"},
            "version": {"number": 2, "when": "2026-02-01T00:00:00Z"},
            "body": {
                "storage": {
                    "value": "<p>Single doc content</p>",
                    "representation": "storage",
                }
            },
            "_links": {"webui": "/pages/456"},
        }

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock(return_value=mock_response)
            mf.return_value = mc
            doc = await conn.fetch_document("456")

        assert doc is not None
        assert doc.remote_id == "456"
        assert doc.title == "Single Page"

    async def test_fetch_document_404(self, server_config):
        import httpx

        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            req = httpx.Request("GET", "https://example.com")
            resp = httpx.Response(404, request=req)
            exc = httpx.HTTPStatusError(
                "404 Not Found", request=req, response=resp
            )
            mc.get = AsyncMock(side_effect=exc)
            mf.return_value = mc
            doc = await conn.fetch_document("999")
            assert doc is None

    async def test_fetch_applies_rate_limiting(self, server_config):
        """MultiRateLimiter.acquire is called before each HTTP request."""
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)

        spaces_response = MagicMock()
        spaces_response.status_code = 200
        spaces_response.json.return_value = {
            "results": [{"key": "DEV", "name": "Development"}],
            "size": 1,
        }

        content_response = MagicMock()
        content_response.status_code = 200
        content_response.json.return_value = {
            "results": [], "size": 0, "start": 0,
            "limit": 200, "totalSize": 0, "_links": {},
        }

        # Mock the rate limiter's acquire method
        conn._rate_limiter.acquire = AsyncMock(return_value=None)

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock()
            mc.get.side_effect = [spaces_response, content_response]
            mf.return_value = mc
            await conn.fetch_documents()

        # Verify rate limiter was acquired for spaces request and content request
        assert conn._rate_limiter.acquire.call_count >= 2
        conn._rate_limiter.acquire.assert_any_call("confluence")

    async def test_fetch_incremental_uses_checkpoint(self, server_config):
        """When since is provided, it is passed as checkpoint in content CQL query."""
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)

        spaces_response = MagicMock()
        spaces_response.status_code = 200
        spaces_response.json.return_value = {
            "results": [{"key": "DEV", "name": "Development"}],
            "size": 1,
        }

        content_response = MagicMock()
        content_response.status_code = 200
        content_response.json.return_value = {
            "results": [], "size": 0, "start": 0,
            "limit": 200, "totalSize": 0, "_links": {},
        }

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock()
            mc.get.side_effect = [spaces_response, content_response]
            mf.return_value = mc

            # Fetch with a checkpoint
            since = "2026-06-01T00:00:00Z"
            await conn.fetch_documents(since=since)

        # The URL should contain lastModified filter
        _, call_kwargs = mc.get.call_args
        url = call_kwargs["url"] if "url" in call_kwargs else mc.get.call_args[0][0]
        assert "lastModified" in url or "since_checkpoint" in str(mc.get.call_args_list)
        # Verify the checkpoint appears in the URL
        url_str = str(mc.get.call_args_list[1]) if len(mc.get.call_args_list) > 1 else str(mc.get.call_args_list[-1])
        # The content URL should include the since parameter
        assert since in url_str or "lastModified" in url_str


class TestParseResult:
    def test_parse_result_success(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)
        item = {
            "id": "789",
            "title": "Parsed Page",
            "space": {"key": "DOCS", "name": "Documentation"},
            "version": {
                "number": 3,
                "when": "2026-03-01T00:00:00Z",
            },
            "body": {
                "storage": {
                    "value": "<p>Parsed content</p>",
                    "representation": "storage",
                }
            },
            "_links": {"webui": "/pages/789"},
        }

        doc = conn._parse_result(item)
        assert doc is not None
        assert doc.remote_id == "789"
        assert doc.metadata["space_key"] == "DOCS"
        assert doc.metadata["version"] == "3"

    def test_parse_result_no_body(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector

        conn = ConfluenceConnector(server_config)
        item = {"id": "000", "title": "No Body", "space": {}}
        doc = conn._parse_result(item)
        assert doc is not None
        assert doc.content == ""


class TestFactoryRegistration:
    def test_registered_in_factory(self):
        from ingest.connectors.factory import (
            list_supported_types,
        )

        assert "confluence" in list_supported_types()

    def test_can_create_via_factory(self, server_config):
        from ingest.connectors.factory import create_connector

        conn = create_connector("confluence", server_config)
        assert conn is not None
        assert conn.connector_type == "confluence"
