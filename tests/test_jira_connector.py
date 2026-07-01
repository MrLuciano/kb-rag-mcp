"""
Tests for JIRA connector (Cloud + Data Center).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingest.connectors.models import ConnectorConfig


@pytest.fixture
def server_config():
    return ConnectorConfig(
        source_key="jira://PROJ",
        connector_type="jira",
        endpoint="https://jira.example.com/rest/api/2",
        auth_method="basic",
        auth_credentials="JIRA_TOKEN",
    )


@pytest.fixture
def cloud_config():
    return ConnectorConfig(
        source_key="jira://PROJ",
        connector_type="jira",
        endpoint="https://example.atlassian.net/rest/api/3",
        auth_method="token",
        auth_credentials="JIRA_TOKEN",
    )


class TestJiraAuth:
    def test_server_auth_header(self, server_config, monkeypatch):
        from ingest.connectors.jira import JiraConnector

        monkeypatch.setenv("JIRA_USERNAME", "admin")
        monkeypatch.setenv("JIRA_TOKEN", "mytoken")
        conn = JiraConnector(server_config)
        header = conn._auth_header()
        assert "Authorization" in header
        assert header["Authorization"].startswith("Basic ")

    def test_cloud_auth_header(self, cloud_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(cloud_config)
        header = conn._auth_header()
        assert header["Authorization"] == "Bearer JIRA_TOKEN"


class TestJiraJQL:
    def test_jql_without_checkpoint(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)
        jql = conn._build_jql(project="PROJ")
        assert "project=PROJ" in jql

    def test_jql_with_checkpoint(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)
        jql = conn._build_jql(project="PROJ", since="2026-01-01T00:00:00Z")
        assert "updated" in jql

    def test_jql_with_jql_filter(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)
        jql = conn._build_jql(
            project="PROJ",
            jql_filter='status in (Open, "In Progress")',
        )
        assert "project=PROJ" in jql
        assert "status in" in jql


class TestJiraPagination:
    def test_search_url_with_offset(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)
        url = conn._build_search_url(project="PROJ", start_at=50)
        assert "startAt=50" in url
        assert "maxResults=100" in url


class TestJiraVersionDetection:
    def test_server_version(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)
        assert conn._detect_version() == "server"

    def test_cloud_version(self, cloud_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(cloud_config)
        assert conn._detect_version() == "cloud"


class TestParseIssue:
    def test_parse_issue_success(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)
        issue = {
            "id": "10001",
            "key": "PROJ-42",
            "fields": {
                "summary": "Fix login bug",
                "description": {
                    "content": [
                        {
                            "content": [
                                {"text": "Steps to reproduce", "type": "text"}
                            ],
                            "type": "paragraph",
                        }
                    ],
                    "type": "doc",
                    "version": 1,
                },
                "priority": {"name": "High"},
                "status": {"name": "In Progress"},
                "assignee": {
                    "displayName": "John Doe",
                    "emailAddress": "john@example.com",
                },
                "labels": ["bug", "security"],
                "project": {"key": "PROJ", "name": "My Project"},
                "updated": "2026-01-15T10:30:00.000+0000",
                "created": "2026-01-01T08:00:00.000+0000",
            },
        }

        doc = conn._parse_issue(issue)
        assert doc is not None
        assert doc.remote_id == "PROJ-42"
        assert doc.title == "Fix login bug"
        assert "Steps to reproduce" in doc.content
        assert doc.metadata["priority"] == "High"
        assert doc.metadata["status"] == "In Progress"
        assert doc.metadata["labels"] == "bug,security"

    def test_parse_issue_no_description(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)
        issue = {
            "id": "10002",
            "key": "PROJ-43",
            "fields": {
                "summary": "No description",
                "project": {"key": "PROJ", "name": "Test"},
                "updated": "2026-01-10T00:00:00.000+0000",
            },
        }

        doc = conn._parse_issue(issue)
        assert doc is not None
        assert doc.content == ""


@pytest.mark.asyncio
class TestJiraFetchDocuments:
    async def test_fetch_with_mocked_http(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)

        projects_response = MagicMock()
        projects_response.status_code = 200
        projects_response.json.return_value = [
            {"key": "PROJ", "name": "My Project"}
        ]

        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "startAt": 0,
            "maxResults": 100,
            "total": 1,
            "issues": [
                {
                    "id": "10001",
                    "key": "PROJ-42",
                    "fields": {
                        "summary": "Fix login bug",
                        "description": {
                            "content": [
                                {
                                    "content": [
                                        {
                                            "text": "Details here",
                                            "type": "text",
                                        }
                                    ],
                                    "type": "paragraph",
                                }
                            ],
                            "type": "doc",
                            "version": 1,
                        },
                        "priority": {"name": "High"},
                        "status": {"name": "Open"},
                        "project": {
                            "key": "PROJ",
                            "name": "My Project",
                        },
                        "updated": "2026-01-15T10:30:00.000+0000",
                    },
                }
            ],
        }

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock()
            mc.get.side_effect = [projects_response, search_response]
            mf.return_value = mc
            result = await conn.fetch_documents()

        assert result.success_count == 1
        assert result.documents[0].remote_id == "PROJ-42"
        assert result.documents[0].title == "Fix login bug"

    async def test_fetch_handles_failure(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)

        projects_response = MagicMock()
        projects_response.status_code = 200
        projects_response.json.return_value = [
            {"key": "PROJ", "name": "My Project"}
        ]

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = Exception("JIRA error")

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock()
            mc.get.side_effect = [projects_response, error_response]
            mf.return_value = mc
            result = await conn.fetch_documents()
            assert result.has_errors()

    async def test_fetch_document_by_key(self, server_config):
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)

        issue_response = MagicMock()
        issue_response.status_code = 200
        issue_response.json.return_value = {
            "id": "10003",
            "key": "PROJ-99",
            "fields": {
                "summary": "Single issue",
                "project": {"key": "PROJ", "name": "Test"},
                "updated": "2026-02-01T00:00:00.000+0000",
            },
        }

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock(return_value=issue_response)
            mf.return_value = mc
            doc = await conn.fetch_document("PROJ-99")

        assert doc is not None
        assert doc.remote_id == "PROJ-99"
        assert doc.title == "Single issue"

    async def test_fetch_document_404(self, server_config):
        import httpx

        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            req = httpx.Request("GET", "https://example.com")
            resp = httpx.Response(404, request=req)
            exc = httpx.HTTPStatusError("404", request=req, response=resp)
            mc.get = AsyncMock(side_effect=exc)
            mf.return_value = mc
            doc = await conn.fetch_document("PROJ-999")
            assert doc is None

    async def test_fetch_applies_rate_limiting(self, server_config):
        """MultiRateLimiter.acquire is called before each HTTP request."""
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)

        projects_response = MagicMock()
        projects_response.status_code = 200
        projects_response.json.return_value = [
            {"key": "PROJ", "name": "My Project"}
        ]

        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "startAt": 0, "maxResults": 100, "total": 0, "issues": [],
        }

        # Mock the rate limiter's acquire method
        conn._rate_limiter.acquire = AsyncMock(return_value=None)

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock()
            mc.get.side_effect = [projects_response, search_response]
            mf.return_value = mc
            await conn.fetch_documents()

        # Verify rate limiter was acquired for projects and search requests
        assert conn._rate_limiter.acquire.call_count >= 2
        conn._rate_limiter.acquire.assert_any_call("jira")

    async def test_fetch_incremental_uses_checkpoint(self, server_config):
        """When since is provided, it is passed as checkpoint in JQL query."""
        from ingest.connectors.jira import JiraConnector

        conn = JiraConnector(server_config)

        projects_response = MagicMock()
        projects_response.status_code = 200
        projects_response.json.return_value = [
            {"key": "PROJ", "name": "My Project"}
        ]

        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "startAt": 0, "maxResults": 100, "total": 0, "issues": [],
        }

        with patch.object(conn, "_get_client") as mf:
            mc = AsyncMock()
            mc.get = AsyncMock()
            mc.get.side_effect = [projects_response, search_response]
            mf.return_value = mc

            # Fetch with a checkpoint
            since = "2026-06-01T00:00:00Z"
            await conn.fetch_documents(since=since)

        # The search URL should contain updated filter
        # Check the second call (search URL)
        search_url = mc.get.call_args_list[1][0][0]  # First positional arg
        assert "updated" in search_url

        # Verify the since checkpoint appears in the encoded JQL
        import urllib.parse
        decoded = urllib.parse.unquote(search_url)
        assert 'updated>="2026-06-01T00:00:00Z"' in decoded


class TestFactoryRegistration:
    def test_registered_in_factory(self):
        from ingest.connectors.factory import list_supported_types

        assert "jira" in list_supported_types()

    def test_can_create_via_factory(self, server_config):
        from ingest.connectors.factory import create_connector

        conn = create_connector("jira", server_config)
        assert conn is not None
        assert conn.connector_type == "jira"
