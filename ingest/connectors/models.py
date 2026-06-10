"""
Typed models for enterprise connector documents and sync results.

Provides data classes for remote documents, connector configuration,
and sync results that feed into the staging layer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RemoteDocument:
    """Represents a document fetched from a remote connector source.

    Attributes:
        remote_id: Stable identity from the remote source
            (Confluence page ID, JIRA issue key, Git blob hash).
        source_key: Connector source identifier
            (e.g. ``confluence://myspace``, ``jira://PROJ``).
        connector_type: Connector type (``confluence``, ``jira``, ``git``).
        title: Document title from the remote source.
        content: Raw text content extracted from the remote source.
        content_type: MIME type or format hint for the content
            (``text/plain``, ``text/markdown``, ``text/html``).
        remote_url: URL to the original remote document.
        remote_etag: ETag or content hash from the remote server.
        remote_mtime: Last-modified timestamp from the remote source.
        metadata: Additional source-specific metadata
            (Confluence space key, JIRA project, Git repository).
    """

    remote_id: str
    source_key: str
    connector_type: str
    title: str
    content: str
    content_type: str = "text/plain"
    remote_url: Optional[str] = None
    remote_etag: Optional[str] = None
    remote_mtime: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ConnectorConfig:
    """Configuration for a connector source.

    Attributes:
        source_key: Unique identifier for this connector source
            (e.g. ``confluence://myspace``, ``jira://PROJ``).
        connector_type: Connector type (``confluence``, ``jira``, ``git``).
        endpoint: Base URL for the remote API.
        auth_method: Authentication method
            (``basic``, ``token``, ``oauth``, ``ssh``).
        auth_credentials: Authentication credentials reference
            (e.g. environment variable name or keychain entry).
        options: Additional source-specific configuration.
    """

    source_key: str
    connector_type: str
    endpoint: str
    auth_method: str = "basic"
    auth_credentials: str = ""
    options: dict = field(default_factory=dict)


@dataclass
class SyncResult:
    """Result of a connector sync operation.

    Attributes:
        source_key: Connector source key.
        documents: List of remote documents fetched during sync.
        checkpoint: Opaque cursor for incremental sync.
        total_fetched: Total documents fetched in this sync.
        errors: List of error messages for failed fetches.
    """

    source_key: str
    documents: list[RemoteDocument] = field(default_factory=list)
    checkpoint: Optional[str] = None
    total_fetched: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        """Number of successfully fetched documents."""
        return len(self.documents)

    @property
    def error_count(self) -> int:
        """Number of errors encountered."""
        return len(self.errors)

    def has_errors(self) -> bool:
        """Check if any errors occurred during sync."""
        return len(self.errors) > 0
