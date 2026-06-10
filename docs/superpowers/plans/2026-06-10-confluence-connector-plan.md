# Confluence Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Confluence connector (Cloud + 7.9.3 Server/DC) as a `ConnectorBase` subclass, registered with the factory, with HTTP-based content fetching, HTML→Markdown conversion, incremental sync, and rate limiting.

**Architecture:** Single file `ingest/connectors/confluence.py` implementing `ConfluenceConnector(ConnectorBase)` that detects version from endpoint URL, handles offset (7.9.3) and cursor (Cloud) pagination, converts Storage Format via `html2text`, and tracks sync state via `MetadataStore`.

**Tech Stack:** httpx (existing), html2text (new dependency), existing MultiRateLimiter

---

### Task 1: Add html2text dependency and write Confluence connector tests

**Files:**
- Modify: `requirements.in` (add html2text)
- Create: `tests/test_confluence_connector.py`

- [ ] **Step 1: Add html2text to requirements.in**

```
html2text
```

- [ ] **Step 2: Write the test file with httpx mock fixtures**

```python
"""
Tests for Confluence connector (Cloud + 7.9.3 Server/DC).
"""

import pytest
from unittest.mock import AsyncMock, patch

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
    def test_server_auth_header(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector
        conn = ConfluenceConnector(server_config)
        header = conn._auth_header()
        assert header["Authorization"] is not None

    def test_cloud_auth_header(self, cloud_config):
        from ingest.connectors.confluence import ConfluenceConnector
        conn = ConfluenceConnector(cloud_config)
        header = conn._auth_header()
        assert header["Authorization"] is not None


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
        assert "start=" not in url


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
        assert "label=howto" in cql
        assert "label=reference" in cql


class TestConfluenceVersionDetection:
    def test_server_version_from_custom_url(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector
        conn = ConfluenceConnector(server_config)
        assert conn._detect_version() in ("server", "cloud")

    def test_cloud_version_from_atlassian_url(self, cloud_config):
        from ingest.connectors.confluence import ConfluenceConnector
        conn = ConfluenceConnector(cloud_config)
        assert conn._detect_version() == "cloud"


@pytest.mark.asyncio
class TestConfluenceFetchDocuments:
    async def test_fetch_with_mocked_http(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector
        conn = ConfluenceConnector(server_config)

        # Mock httpx client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "space": {"key": "DEV", "name": "Development"},
                    "version": {"number": 1, "when": "2026-01-01T00:00:00Z"},
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
            "_links": {},
        }

        with patch.object(conn, "_get_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            mock_client_factory.return_value.__aexit__.return_value = None

            result = await conn.fetch_documents()

        assert result.success_count == 1
        assert result.documents[0].remote_id == "123"
        assert result.documents[0].title == "Test Page"
        assert "Hello world" in result.documents[0].content

    async def test_fetch_handles_401(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector
        conn = ConfluenceConnector(server_config)

        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

        with patch.object(conn, "_get_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            mock_client_factory.return_value.__aexit__.return_value = None

            result = await conn.fetch_documents()
            assert result.has_errors()

    async def test_fetch_handles_429(self, server_config):
        from ingest.connectors.confluence import ConfluenceConnector
        conn = ConfluenceConnector(server_config)

        mock_429 = AsyncMock()
        mock_429.status_code = 429

        mock_ok = AsyncMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = {
            "results": [],
            "size": 0,
            "_links": {},
        }

        with patch.object(conn, "_get_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [mock_429, mock_ok]
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            mock_client_factory.return_value.__aexit__.return_value = None

            result = await conn.fetch_documents()
            # Should retry and succeed
            assert not result.has_errors()


class TestConfluenceFactoryRegistration:
    def test_registered_in_factory(self):
        from ingest.connectors.factory import list_supported_types
        assert "confluence" in list_supported_types()

    def test_can_create_via_factory(self, server_config):
        from ingest.connectors.factory import create_connector
        conn = create_connector("confluence", server_config)
        assert conn is not None
        assert conn.connector_type == "confluence"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_confluence_connector.py -v`
Expected: ModuleNotFoundError for ingest.connectors.confluence

---

### Task 2: Implement ConfluenceConnector

**Files:**
- Create: `ingest/connectors/confluence.py`

- [ ] **Step 1: Write the ConfluenceConnector class**

```python
"""
Confluence connector (Cloud + 7.9.3 Server/Data Center).

Implements ConnectorBase for fetching pages from Confluence via REST API.
Supports:
- Confluence 7.9.3 (Server/DC): basic auth, offset pagination, Storage Format
- Confluence Cloud: token auth, cursor pagination, ADF/Storage Format
- Incremental sync via CQL lastModified checkpoint
- HTML→Markdown conversion via html2text
- Rate limiting via MultiRateLimiter
"""

import html
import logging
import os
import re
from typing import Optional

import httpx

from ingest.connectors.base import ConnectorBase
from ingest.connectors.factory import register
from ingest.connectors.models import ConnectorConfig, RemoteDocument, SyncResult
from ingest.worker.limiter import MultiRateLimiter

log = logging.getLogger("kb-ingest.connectors.confluence")

_CONFLUENCE_DEFAULT_RATE = int(os.getenv("CONFLUENCE_RATE_LIMIT", "100"))


def _storage_to_markdown(html_content: str) -> str:
    """Convert Confluence Storage Format (XHTML) to Markdown.

    Uses ``html2text`` if available, falls back to HTML tag stripping
    with basic structure preservation.

    Args:
        html_content: XHTML content from Confluence Storage Format.

    Returns:
        Markdown-formatted text.
    """
    if not html_content:
        return ""

    try:
        import html2text

        converter = html2text.HTML2Text()
        converter.body_width = 0  # No line wrapping
        converter.ignore_links = False
        converter.ignore_images = False
        converter.ignore_emphasis = False
        return converter.handle(html_content).strip()
    except ImportError:
        pass

    # Fallback: strip HTML tags, preserve basic structure
    text = re.sub(r"<br\s*/?>", "\n", html_content)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


class ConfluenceConnector(ConnectorBase):
    """Connector for Atlassian Confluence (Cloud + Server/Data Center).

    Attributes:
        config: Connector configuration.
        _client: Optional shared httpx client for connection reuse.
        _rate_limiter: Rate limiter for API call throttling.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = MultiRateLimiter(
            default_requests_per_minute=_CONFLUENCE_DEFAULT_RATE
        )

    # ── Auth

    def _auth_header(self) -> dict[str, str]:
        """Build the Authorization header based on version and config.

        Returns:
            Dict with ``Authorization`` key.
        """
        version = self._detect_version()
        creds = self.config.auth_credentials
        if version == "cloud":
            return {"Authorization": f"Bearer {creds}"}
        # Server/DC: basic auth with personal access token
        username = os.getenv("CONFLUENCE_USERNAME", "")
        token = creds or os.getenv("CONFLUENCE_TOKEN", "")
        if username:
            import base64

            auth_str = f"{username}:{token}"
            encoded = base64.b64encode(auth_str.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {"Authorization": f"Bearer {token}"}

    # ── Version Detection

    def _detect_version(self) -> str:
        """Detect Confluence version from endpoint URL.

        Returns:
            ``"cloud"`` if endpoint contains ``atlassian.net``,
            ``"server"`` otherwise.
        """
        endpoint = self.config.endpoint.lower()
        if "atlassian.net" in endpoint:
            return "cloud"
        return "server"

    # ── HTTP Client

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create an httpx async client.

        Returns:
            An ``httpx.AsyncClient`` instance.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    # ── CQL Builder

    def _build_cql(
        self,
        space: str,
        since: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> str:
        """Build a CQL query string for fetching Confluence content.

        Args:
            space: Confluence space key.
            since: ISO 8601 timestamp for incremental sync checkpoint.
            labels: Optional list of document type labels to filter.

        Returns:
            CQL query string.
        """
        clauses = [f"space={space}", "type=page"]
        if since:
            clauses.append(f"lastModified>=\"{since}\"")
        if labels:
            for label in labels:
                clauses.append(f"label=\"{label}\"")
        return " AND ".join(clauses)

    # ── URL Builder

    def _build_content_url(
        self,
        space: str,
        start: int = 0,
        limit: int = 200,
        cursor: Optional[str] = None,
        expand: str = "body.storage,version,space",
    ) -> str:
        """Build the content API URL with pagination.

        Args:
            space: Confluence space key (used for CQL filtering).
            start: Offset for server pagination.
            limit: Max results per page (max 200 for server).
            cursor: Cursor for Cloud pagination.
            expand: API expand parameter.

        Returns:
            Full URL string.
        """
        base = f"{self.config.endpoint}/content"
        if cursor:
            return f"{base}?cursor={cursor}&expand={expand}"
        return (
            f"{base}?"
            f"cql={self._build_cql(space)}&"
            f"expand={expand}&"
            f"start={start}&limit={limit}"
        )

    # ── Content Parser

    def _parse_result(self, item: dict) -> Optional[RemoteDocument]:
        """Parse a Confluence API result item into a RemoteDocument.

        Args:
            item: Raw API result dict from Confluence REST API.

        Returns:
            A ``RemoteDocument``, or ``None`` if parsing fails.
        """
        try:
            page_id = str(item.get("id", ""))
            title = item.get("title", "Untitled")
            space_key = item.get("space", {}).get("key", "")
            space_name = item.get("space", {}).get("name", "")
            version = item.get("version", {})
            version_number = version.get("number", 1)
            modified = version.get("when", "")

            # Extract content from body.storage
            body = item.get("body", {})
            storage = body.get("storage", {})
            raw_html = storage.get("value", "")

            content = _storage_to_markdown(raw_html)

            webui = item.get("_links", {}).get("webui", "")
            remote_url = None
            if webui:
                remote_url = f"{self.config.endpoint}{webui}"

            remote_mtime = None
            if modified:
                from datetime import datetime

                try:
                    dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                    remote_mtime = dt.timestamp()
                except (ValueError, AttributeError):
                    pass

            return RemoteDocument(
                remote_id=page_id,
                source_key=self.source_key,
                connector_type=self.connector_type,
                title=title,
                content=content,
                content_type="text/markdown",
                remote_url=remote_url,
                remote_mtime=remote_mtime,
                metadata={
                    "space_key": space_key,
                    "space_name": space_name,
                    "version": str(version_number),
                    "modified": modified,
                },
            )
        except Exception as e:
            log.warning("Failed to parse Confluence item: %s", e)
            return None

    # ── ConnectorBase Implementation

    async def connect(self) -> None:
        """Validate connectivity by testing the API endpoint."""
        client = self._get_client()
        headers = self._auth_header()
        test_url = f"{self.config.endpoint}/space?limit=1"
        try:
            resp = await client.get(test_url, headers=headers)
            resp.raise_for_status()
            log.info(
                "Connected to Confluence: %s (version=%s)",
                self.config.endpoint,
                self._detect_version(),
            )
        except Exception as e:
            log.error("Failed to connect to Confluence: %s", e)
            raise

    async def fetch_documents(
        self, since: Optional[str] = None
    ) -> SyncResult:
        """Fetch Confluence pages, optionally since a checkpoint.

        Iterates over all spaces, then for each space fetches pages
        using CQL and pagination.

        Args:
            since: ISO 8601 timestamp checkpoint for incremental sync.

        Returns:
            A ``SyncResult`` with fetched documents.
        """
        client = self._get_client()
        headers = self._auth_header()
        documents: list[RemoteDocument] = []
        errors: list[str] = []
        checkpoint: Optional[str] = None

        # Fetch list of spaces
        spaces_url = f"{self.config.endpoint}/space?limit=200"
        try:
            await self._rate_limiter.acquire("confluence")
            resp = await client.get(spaces_url, headers=headers)
            resp.raise_for_status()
            spaces_data = resp.json()
            spaces = [
                s["key"]
                for s in spaces_data.get("results", [])
            ]
        except Exception as e:
            log.error("Failed to fetch spaces: %s", e)
            return SyncResult(
                source_key=self.source_key,
                errors=[f"Failed to fetch spaces: {e}"],
            )

        if not spaces:
            log.info("No spaces found in Confluence")
            return SyncResult(source_key=self.source_key)

        log.info("Found %d Confluence spaces", len(spaces))

        version = self._detect_version()

        for space in spaces:
            if version == "cloud":
                # Cloud: cursor-based pagination
                cursor: Optional[str] = None
                while True:
                    url = self._build_content_url(
                        space=space,
                        cursor=cursor,
                        since_checkpoint=since,
                    )
                    # Override URL with CQL and cursor if present
                    cql = self._build_cql(space, since=since)
                    params = f"cql={cql}&expand=body.storage,version,space"
                    if cursor:
                        params += f"&cursor={cursor}"
                    url = f"{self.config.endpoint}/content?{params}"

                    try:
                        await self._rate_limiter.acquire("confluence")
                        resp = await client.get(url, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()
                    except Exception as e:
                        errors.append(
                            f"Space {space} cursor={cursor}: {e}"
                        )
                        break

                    for item in data.get("results", []):
                        doc = self._parse_result(item)
                        if doc:
                            documents.append(doc)
                            # Use latest modified as checkpoint
                            if doc.remote_mtime is not None:
                                from datetime import datetime, timezone

                                dt = datetime.fromtimestamp(
                                    doc.remote_mtime, tz=timezone.utc
                                )
                                candidate = dt.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ"
                                )
                                if (
                                    checkpoint is None
                                    or candidate > checkpoint
                                ):
                                    checkpoint = candidate

                    links = data.get("_links", {})
                    next_cursor = links.get("next")
                    if not next_cursor:
                        break
                    cursor = next_cursor
            else:
                # Server/DC: offset pagination
                start = 0
                limit = 200
                while True:
                    cql = self._build_cql(space, since=since)
                    url = (
                        f"{self.config.endpoint}/content?"
                        f"cql={cql}&"
                        f"expand=body.storage,version,space&"
                        f"start={start}&limit={limit}"
                    )

                    try:
                        await self._rate_limiter.acquire("confluence")
                        resp = await client.get(url, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()
                    except Exception as e:
                        errors.append(
                            f"Space {space} start={start}: {e}"
                        )
                        break

                    for item in data.get("results", []):
                        doc = self._parse_result(item)
                        if doc:
                            documents.append(doc)
                            if doc.remote_mtime is not None:
                                from datetime import datetime, timezone

                                dt = datetime.fromtimestamp(
                                    doc.remote_mtime, tz=timezone.utc
                                )
                                candidate = dt.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ"
                                )
                                if (
                                    checkpoint is None
                                    or candidate > checkpoint
                                ):
                                    checkpoint = candidate

                    size = data.get("size", 0)
                    if start + size >= data.get("totalSize", start + size):
                        break
                    start += size

        return SyncResult(
            source_key=self.source_key,
            documents=documents,
            checkpoint=checkpoint,
            total_fetched=len(documents),
            errors=errors,
        )

    async def fetch_document(
        self, remote_id: str
    ) -> Optional[RemoteDocument]:
        """Fetch a single Confluence page by ID.

        Args:
            remote_id: Confluence page ID.

        Returns:
            A ``RemoteDocument``, or ``None`` if not found.
        """
        client = self._get_client()
        headers = self._auth_header()
        url = (
            f"{self.config.endpoint}/content/{remote_id}?"
            f"expand=body.storage,version,space"
        )

        try:
            await self._rate_limiter.acquire("confluence")
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_result(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log.warning(
                    "Confluence page not found: %s", remote_id
                )
                return None
            log.error(
                "Failed to fetch Confluence page %s: %s",
                remote_id, e,
            )
            return None
        except Exception as e:
            log.error(
                "Error fetching Confluence page %s: %s",
                remote_id, e,
            )
            return None

    async def close(self) -> None:
        """Close the httpx client session."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Register with factory on import
register("confluence", ConfluenceConnector)
```

Fix the `_build_content_url` method — the cursor version should also accept `since_checkpoint` for the Cloud variant:

```python
    def _build_content_url(
        self,
        space: str,
        start: int = 0,
        limit: int = 200,
        cursor: Optional[str] = None,
        since_checkpoint: Optional[str] = None,
        expand: str = "body.storage,version,space",
    ) -> str:
        """Build the content API URL with pagination.

        Args:
            space: Confluence space key.
            start: Offset for server pagination.
            limit: Max results per page (max 200 for server).
            cursor: Cursor for Cloud pagination.
            since_checkpoint: ISO 8601 timestamp for incremental sync.
            expand: API expand parameter.

        Returns:
            Full URL string.
        """
        base = f"{self.config.endpoint}/content"
        cql = self._build_cql(space, since=since_checkpoint)
        if cursor:
            return f"{base}?cql={cql}&expand={expand}&cursor={cursor}"
        return (
            f"{base}?cql={cql}&"
            f"expand={expand}&"
            f"start={start}&limit={limit}"
        )
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_confluence_connector.py -v`
Expected: Tests pass (some may need adjustment for quote encoding in URLs)

- [ ] **Step 3: Run full test suite**

Run: `pytest -q`
Expected: All existing tests green, new tests green

- [ ] **Step 4: Update requirements.in**

```
html2text
```

- [ ] **Step 5: Compile requirements**

```bash
pip-compile requirements.in
```

- [ ] **Step 6: Commit**

```bash
git add ingest/connectors/confluence.py tests/test_confluence_connector.py requirements.in
git commit -m "feat(phase-29): Confluence connector (Cloud + 7.9.3 Server/DC)

- ConfluenceConnector with auth for Server (basic) and Cloud (bearer)
- Offset pagination for 7.9.3, cursor pagination for Cloud
- CQL-based queries with space, lastModified, and label filters
- HTML→Markdown via html2text with stdlib fallback
- Rate limiting via MultiRateLimiter (100 req/min default)
- Factory-registered on import for CLI discoverability
- 12 tests covering auth, pagination, CQL, content extraction, fetch
```

---

### Task 3: Wire Confluence connector into CLI stage command

**Files:**
- Modify: `ingest/cli/connectors.py`

- [ ] **Step 1: Add Confluence-specific --space flag to stage command**

```python
@connectors_group.command(name="confluence-stage")
@click.option("--space", required=True, help="Confluence space key")
@click.option("--since", default=None, help="ISO 8601 checkpoint timestamp")
@click.option("--labels", default=None, help="Comma-separated label filter")
def stage_confluence(space, since, labels):
    """Stage Confluence space content for ingestion."""
    # Implementation calls ConfluenceConnector.fetch_documents()
    # then stage_documents() and run_ingest(staged_paths=...)
    ...
```

But wait, we need to actually instantiate the connector from env vars, not CLI flags. Let me think about this.

The user said "Env-based auth config". So the CLI command should be:

```
kb-rag connectors stage --type confluence --source-key confluence://myspace
```

And the actual auth config comes from env vars. The Confluence connector reads CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_TOKEN from the environment.

But actually, looking at the existing `stage` command, it already accepts `--type`, `--source-key`, `--endpoint`, `--auth-method`, `--auth-credentials` flags. The issue is that `--endpoint` is required, but for Confluence we might want to derive it from env or have a more targeted command.

Let me add a `confluence configure` and `confluence stage` subcommand to the connectors group, or just make the generic `stage` command work well with Confluence and add helper commands.

- [ ] **Step 2: Add confluence sub-group**

```python
@connectors_group.group(name="confluence")
def confluence_group() -> None:
    """Confluence-specific connector commands."""


@confluence_group.command(name="stage")
@click.option(
    "--space", required=True, help="Confluence space key to stage"
)
@click.option(
    "--since", default=None, help="ISO 8601 checkpoint for incremental sync"
)
@click.option(
    "--labels", default=None, help="Comma-separated document type labels"
)
@click.option(
    "--staging-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Override staging directory",
)
@click.pass_context
def stage_confluence(ctx, space, since, labels, staging_dir):
    """Stage Confluence space content for ingestion.

    Uses env vars for auth:
      CONFLUENCE_URL   - Base URL (e.g. https://confluence.example.com/rest/api)
      CONFLUENCE_USERNAME - Username for basic auth (7.9.3 Server)
      CONFLUENCE_TOKEN    - API token or PAT
    """
    import asyncio

    confluence_url = os.getenv("CONFLUENCE_URL")
    if not confluence_url:
        click.echo(
            "Error: CONFLUENCE_URL environment variable not set"
        )
        raise click.Abort()

    config = ConnectorConfig(
        source_key=f"confluence://{space}",
        connector_type="confluence",
        endpoint=confluence_url,
        auth_method="basic",
        auth_credentials=os.getenv("CONFLUENCE_TOKEN", ""),
    )

    conn = create_connector("confluence", config)
    if conn is None:
        click.echo("Error: Confluence connector not registered")
        raise click.Abort()

    click.echo(f"Connecting to {confluence_url}...")
    try:
        result = asyncio.run(conn.fetch_documents(since=since))
    finally:
        asyncio.run(conn.close())

    if result.has_errors():
        for err in result.errors:
            click.echo(f"  Warning: {err}")

    click.echo(
        f"Fetched {result.success_count} documents"
    )
    if not result.documents:
        click.echo("No documents to stage.")
        return

    staging_root = staging_dir or get_staging_root()
    staged = stage_documents(result.documents, staging_root=staging_root)
    click.echo(f"Staged {len(staged)} files to {staging_root}")
    click.echo(f"Checkpoint: {result.checkpoint}")
    click.echo("\nRun ingestion: kb-rag ingest --staged-dir <dir>")
```

- [ ] **Step 3: Add staged-dir option to ingest**

Make the ingest pipeline accept `--staged-dir` as an alternative to `--docs`:

```python
# In ingest.py run_ingest():
if staged_paths:
    # Already handled
    pass
elif staged_dir:
    staged_paths = list(staged_dir.glob("*.md"))
    docs_root = staged_dir
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_cli.py -v`
Expected: CLI tests pass including new confluence commands

- [ ] **Step 5: Commit**

```bash
git add ingest/cli/connectors.py ingest/ingest.py
git commit -m "feat(phase-29): Confluence CLI commands and staged-dir ingest

- Add connectors confluence stage command for space-level staging
- Add --staged-dir option to ingest command for connector flow
"
```

---

### Verification

```bash
# Run all tests
.venv/bin/python -m pytest tests/test_confluence_connector.py -v
.venv/bin/python -m pytest tests/test_cli.py -v
.venv/bin/python -m pytest -q
```
