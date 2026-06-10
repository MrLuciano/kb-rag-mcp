"""
JIRA connector (Cloud + Data Center).

Implements ConnectorBase for fetching issues from JIRA via REST API.
Supports:
- JIRA Cloud and Data Center/Server
- Basic auth or Bearer token auth
- JQL-based issue search with project and incremental sync
- ADF (Atlassian Document Format) content extraction
- Pagination via startAt/maxResults
- Rate limiting via MultiRateLimiter
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from ingest.connectors.base import ConnectorBase
from ingest.connectors.factory import register
from ingest.connectors.models import ConnectorConfig, RemoteDocument, SyncResult
from ingest.worker.limiter import MultiRateLimiter

log = logging.getLogger("kb-ingest.connectors.jira")

_JIRA_DEFAULT_RATE = int(os.getenv("JIRA_RATE_LIMIT", "100"))


def _extract_adf_content(adf: Optional[dict]) -> str:
    """Extract plain text from an Atlassian Document Format payload.

    Recursively walks the ADF node tree and joins text content.
    """
    if not adf:
        return ""

    texts: list[str] = []

    def _walk(node: dict[str, Any]) -> None:
        node_type = node.get("type", "")
        if node_type == "text":
            text = node.get("text", "")
            marks = node.get("marks", [])
            for mark in marks:
                mtype = mark.get("type", "")
                if mtype == "link":
                    href = mark.get("attrs", {}).get("href", "")
                    text = f"[{text}]({href})"
                elif mtype == "code":
                    text = f"`{text}`"
                elif mtype == "strong":
                    text = f"**{text}**"
                elif mtype == "em":
                    text = f"*{text}*"
                elif mtype == "strike":
                    text = f"~~{text}~~"
            if text.strip():
                texts.append(text)
        elif node_type == "hardBreak":
            texts.append("\n")
        elif node_type in ("paragraph", "heading"):
            content = node.get("content", [])
            for child in content:
                _walk(child)
            texts.append("\n\n")
        elif node_type == "bulletList":
            for item in node.get("content", []):
                texts.append("- ")
                for child in item.get("content", []):
                    _walk(child)
                texts.append("\n")
        elif node_type == "orderedList":
            for i, item in enumerate(node.get("content", []), 1):
                texts.append(f"{i}. ")
                for child in item.get("content", []):
                    _walk(child)
                texts.append("\n")
        elif node_type == "codeBlock":
            texts.append("\n```\n")
            for child in node.get("content", []):
                _walk(child)
            texts.append("\n```\n")
        elif node_type in ("table", "tableRow"):
            for child in node.get("content", []):
                _walk(child)
        elif node_type == "tableCell":
            content = node.get("content", [])
            for child in content:
                _walk(child)
            texts.append(" | ")
        elif node_type == "tableHeader":
            content = node.get("content", [])
            for child in content:
                _walk(child)
            texts.append(" | ")
        elif node_type in ("blockquote", "extension", "nestedExpand"):
            for child in node.get("content", []):
                _walk(child)
        elif "content" in node:
            for child in node["content"]:
                _walk(child)

    _walk(adf)
    result = "".join(texts)
    return "\n".join(
        line.strip()
        for line in result.splitlines()
        if line.strip()
    )


class JiraConnector(ConnectorBase):
    """Connector for Atlassian JIRA (Cloud + Data Center/Server)."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = MultiRateLimiter()
        self._rate_limiter.add_limiter(
            "jira", requests_per_minute=_JIRA_DEFAULT_RATE
        )

    def _auth_header(self) -> dict[str, str]:
        version = self._detect_version()
        creds = self.config.auth_credentials
        if version == "cloud":
            return {"Authorization": f"Bearer {creds}"}
        username = os.getenv("JIRA_USERNAME", "")
        token = creds or os.getenv("JIRA_TOKEN", "")
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

    def _build_jql(
        self,
        project: Optional[str] = None,
        since: Optional[str] = None,
        jql_filter: Optional[str] = None,
    ) -> str:
        clauses: list[str] = []
        if project:
            clauses.append(f"project={project}")
        if since:
            clauses.append(f'updated>="{since}"')
        if jql_filter:
            clauses.append(f"({jql_filter})")
        if not clauses:
            clauses.append("1=1")
        return " AND ".join(clauses)

    def _build_search_url(
        self,
        project: Optional[str] = None,
        since: Optional[str] = None,
        jql_filter: Optional[str] = None,
        start_at: int = 0,
        max_results: int = 100,
        fields: str = "summary,description,priority,status,assignee,labels,project,updated,created",
    ) -> str:
        jql = self._build_jql(
            project=project, since=since, jql_filter=jql_filter
        )
        import urllib.parse

        encoded = urllib.parse.quote(jql)
        return (
            f"{self.config.endpoint}/search?"
            f"jql={encoded}&"
            f"fields={fields}&"
            f"startAt={start_at}&maxResults={max_results}"
        )

    def _parse_issue(self, issue: dict) -> Optional[RemoteDocument]:
        try:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            summary = fields.get("summary", "Untitled")
            description_adf = fields.get("description")
            content = _extract_adf_content(description_adf)

            priority = fields.get("priority", {})
            status = fields.get("status", {})
            assignee = fields.get("assignee") or {}
            labels = fields.get("labels") or []
            project = fields.get("project", {})
            updated_str = fields.get("updated", "")

            remote_url = (
                f"{self.config.endpoint.rstrip('/api/2').rstrip('/api/3')}"
                f"/browse/{key}"
            )

            remote_mtime = None
            if updated_str:
                try:
                    dt = datetime.fromisoformat(
                        updated_str.replace("Z", "+00:00")
                    )
                    remote_mtime = dt.timestamp()
                except (ValueError, AttributeError):
                    pass

            return RemoteDocument(
                remote_id=key,
                source_key=self.source_key,
                connector_type=self.connector_type,
                title=summary,
                content=content,
                content_type="text/markdown",
                remote_url=remote_url,
                remote_mtime=remote_mtime,
                metadata={
                    "project_key": project.get("key", ""),
                    "project_name": project.get("name", ""),
                    "priority": priority.get("name", ""),
                    "status": status.get("name", ""),
                    "assignee": assignee.get("displayName", ""),
                    "labels": ",".join(labels),
                    "updated": updated_str,
                },
            )
        except Exception as e:
            log.warning("Failed to parse JIRA issue: %s", e)
            return None

    async def connect(self) -> None:
        client = self._get_client()
        headers = self._auth_header()
        try:
            resp = await client.get(
                f"{self.config.endpoint}/myself",
                headers=headers,
            )
            resp.raise_for_status()
            log.info(
                "Connected to JIRA: %s (version=%s)",
                self.config.endpoint,
                self._detect_version(),
            )
        except Exception as e:
            log.error("Failed to connect to JIRA: %s", e)
            raise

    async def fetch_documents(
        self, since: Optional[str] = None
    ) -> SyncResult:
        client = self._get_client()
        headers = self._auth_header()
        documents: list[RemoteDocument] = []
        errors: list[str] = []
        checkpoint: Optional[str] = None

        projects_url = f"{self.config.endpoint}/project"
        try:
            await self._rate_limiter.acquire("jira")
            resp = await client.get(projects_url, headers=headers)
            resp.raise_for_status()
            projects_data = resp.json()
            projects = [
                p["key"] for p in projects_data if isinstance(p, dict)
            ]
        except Exception as e:
            return SyncResult(
                source_key=self.source_key,
                errors=[f"Failed to fetch projects: {e}"],
            )

        if not projects:
            return SyncResult(source_key=self.source_key)

        for project in projects:
            start_at = 0
            max_results = 100
            while True:
                url = self._build_search_url(
                    project=project,
                    since=since,
                    start_at=start_at,
                    max_results=max_results,
                )
                try:
                    await self._rate_limiter.acquire("jira")
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    errors.append(
                        f"Project {project} startAt={start_at}: {e}"
                    )
                    break

                for issue in data.get("issues", []):
                    doc = self._parse_issue(issue)
                    if doc:
                        documents.append(doc)
                        checkpoint = self._update_checkpoint(
                            checkpoint, doc
                        )

                total = data.get("total", 0)
                start_at += data.get("maxResults", max_results)
                if start_at >= total:
                    break

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
        client = self._get_client()
        headers = self._auth_header()
        url = (
            f"{self.config.endpoint}/issue/{remote_id}"
        )

        try:
            await self._rate_limiter.acquire("jira")
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_issue(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            log.error("Failed to fetch issue %s: %s", remote_id, e)
            return None
        except Exception as e:
            log.error("Error fetching issue %s: %s", remote_id, e)
            return None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _update_checkpoint(
        current: Optional[str], doc: RemoteDocument
    ) -> str:
        if doc.remote_mtime is None:
            return current or ""
        dt = datetime.fromtimestamp(doc.remote_mtime, tz=timezone.utc)
        candidate = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        if current is None or candidate > current:
            return candidate
        return current


register("jira", JiraConnector)
