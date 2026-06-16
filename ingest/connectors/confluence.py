"""
Confluence connector (Cloud + 7.9.3 Server/Data Center).

Implements ConnectorBase for fetching pages from Confluence via REST API.
Supports:
- Confluence 7.9.3 (Server/DC): basic auth, offset pagination
- Confluence Cloud: token auth, cursor pagination
- Incremental sync via CQL lastModified checkpoint
- HTML->Markdown conversion via html2text with stdlib fallback
- Rate limiting via MultiRateLimiter
"""

import html
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional, cast

import httpx

from ingest.connectors.base import ConnectorBase
from ingest.connectors.factory import register
from ingest.connectors.models import (
    ConnectorConfig,
    RemoteDocument,
    SyncResult,
)
from ingest.worker.limiter import MultiRateLimiter

log = logging.getLogger("kb-ingest.connectors.confluence")

_CONFLUENCE_DEFAULT_RATE = int(os.getenv("CONFLUENCE_RATE_LIMIT", "100"))


def _storage_to_markdown(html_content: str) -> str:
    """Convert Confluence Storage Format (XHTML) to Markdown.

    Uses ``html2text`` if available, falls back to HTML tag stripping
    with basic structure preservation.
    """
    if not html_content:
        return ""

    try:
        import html2text

        converter = html2text.HTML2Text()
        converter.body_width = 0
        converter.ignore_links = False
        converter.ignore_images = False
        converter.ignore_emphasis = False
        return cast(str, converter.handle(html_content).strip())
    except ImportError:
        pass

    text = re.sub(r"<br\s*/?>", "\n", html_content)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return "\n".join(
        line.strip() for line in text.splitlines() if line.strip()
    )


class ConfluenceConnector(ConnectorBase):
    """Connector for Atlassian Confluence (Cloud + Server/DC)."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = MultiRateLimiter()
        self._rate_limiter.add_limiter(
            "confluence",
            requests_per_minute=_CONFLUENCE_DEFAULT_RATE,
        )

    def _auth_header(self) -> dict[str, str]:
        version = self._detect_version()
        creds = self.config.auth_credentials
        if version == "cloud":
            return {"Authorization": f"Bearer {creds}"}
        username = os.getenv("CONFLUENCE_USERNAME", "")
        token = creds or os.getenv("CONFLUENCE_TOKEN", "")
        if username:
            import base64

            auth_str = f"{username}:{token}"
            encoded = base64.b64encode(auth_str.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {"Authorization": f"Bearer {token}"}

    def _detect_version(self) -> str:
        endpoint = self.config.endpoint.lower()
        if "atlassian.net" in endpoint:
            return "cloud"
        return "server"

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    def _build_cql(
        self,
        space: str,
        since: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> str:
        clauses = [f"space={space}", "type=page"]
        if since:
            clauses.append(f'lastModified>="{since}"')
        if labels:
            for label in labels:
                clauses.append(f'label="{label}"')
        return " AND ".join(clauses)

    def _build_content_url(
        self,
        space: str,
        start: int = 0,
        limit: int = 200,
        cursor: Optional[str] = None,
        since_checkpoint: Optional[str] = None,
        expand: str = "body.storage,version,space",
    ) -> str:
        base = f"{self.config.endpoint}/content"
        cql = self._build_cql(space, since=since_checkpoint)
        if cursor:
            return f"{base}?cql={cql}&expand={expand}&cursor={cursor}"
        return (
            f"{base}?cql={cql}&"
            f"expand={expand}&"
            f"start={start}&limit={limit}"
        )

    def _parse_result(self, item: dict) -> Optional[RemoteDocument]:
        try:
            page_id = str(item.get("id", ""))
            title = item.get("title", "Untitled")
            space_key = item.get("space", {}).get("key", "")
            space_name = item.get("space", {}).get("name", "")
            version = item.get("version", {})
            modified = version.get("when", "")

            body = item.get("body", {})
            storage = body.get("storage", {})
            raw_html = storage.get("value", "")
            content = _storage_to_markdown(raw_html)

            webui = item.get("_links", {}).get("webui", "")
            remote_url = f"{self.config.endpoint}{webui}" if webui else None

            remote_mtime = None
            if modified:
                m = modified.replace("Z", "+00:00")
                try:
                    dt = datetime.fromisoformat(m)
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
                    "version": str(version.get("number", 1)),
                    "modified": modified,
                },
            )
        except Exception as e:
            log.warning("Failed to parse Confluence item: %s", e)
            return None

    async def connect(self) -> None:
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

    async def fetch_documents(self, since: Optional[str] = None) -> SyncResult:
        client = self._get_client()
        headers = self._auth_header()
        documents: list[RemoteDocument] = []
        errors: list[str] = []
        checkpoint: Optional[str] = None
        version = self._detect_version()

        spaces_url = f"{self.config.endpoint}/space?limit=200"
        try:
            await self._rate_limiter.acquire("confluence")
            resp = await client.get(spaces_url, headers=headers)
            resp.raise_for_status()
            spaces_data = resp.json()
            spaces = [s["key"] for s in spaces_data.get("results", [])]
        except Exception as e:
            return SyncResult(
                source_key=self.source_key,
                errors=[f"Failed to fetch spaces: {e}"],
            )

        if not spaces:
            return SyncResult(source_key=self.source_key)

        for space in spaces:
            if version == "cloud":
                cursor: Optional[str] = None
                while True:
                    url = self._build_content_url(
                        space=space,
                        cursor=cursor,
                        since_checkpoint=since,
                    )
                    try:
                        await self._rate_limiter.acquire("confluence")
                        resp = await client.get(url, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()
                    except Exception as e:
                        errors.append(f"Space {space} cursor={cursor}: {e}")
                        break

                    for item in data.get("results", []):
                        doc = self._parse_result(item)
                        if doc:
                            documents.append(doc)
                            checkpoint = self._update_checkpoint(
                                checkpoint, doc
                            )

                    links = data.get("_links", {})
                    next_val = links.get("next")
                    if not next_val:
                        break
                    cursor = next_val
            else:
                start = 0
                limit = 200
                while True:
                    url = self._build_content_url(
                        space=space,
                        start=start,
                        limit=limit,
                        since_checkpoint=since,
                    )
                    try:
                        await self._rate_limiter.acquire("confluence")
                        resp = await client.get(url, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()
                    except Exception as e:
                        errors.append(f"Space {space} start={start}: {e}")
                        break

                    for item in data.get("results", []):
                        doc = self._parse_result(item)
                        if doc:
                            documents.append(doc)
                            checkpoint = self._update_checkpoint(
                                checkpoint, doc
                            )

                    size = data.get("size", 0)
                    total = data.get("totalSize", start + size)
                    if start + size >= total:
                        break
                    start += size

        return SyncResult(
            source_key=self.source_key,
            documents=documents,
            checkpoint=checkpoint,
            total_fetched=len(documents),
            errors=errors,
        )

    async def fetch_document(self, remote_id: str) -> Optional[RemoteDocument]:
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
                return None
            log.error("Failed to fetch page %s: %s", remote_id, e)
            return None
        except Exception as e:
            log.error("Error fetching page %s: %s", remote_id, e)
            return None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _update_checkpoint(current: Optional[str], doc: RemoteDocument) -> str:
        if doc.remote_mtime is None:
            return current or ""
        dt = datetime.fromtimestamp(doc.remote_mtime, tz=timezone.utc)
        candidate = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        if current is None or candidate > current:
            return candidate
        return current


register("confluence", ConfluenceConnector)
