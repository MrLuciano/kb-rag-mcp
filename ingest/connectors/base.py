"""
Connector base abstraction for enterprise data source ingestion.

Defines ``ConnectorBase`` — the interface all enterprise connectors
(Confluence, JIRA, Git) must implement. Each connector handles
authentication, remote document discovery, content fetching, and
incremental sync checkpointing.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ingest.connectors.models import (
    ConnectorConfig,
    RemoteDocument,
    SyncResult,
)


class ConnectorBase(ABC):
    """Abstract base class for all enterprise data source connectors.

    Subclasses must implement ``fetch_documents``, ``fetch_document``,
    and ``close``. The ``connect`` method is optional for sources that
    need persistent sessions or authentication handshakes.

    Attributes:
        config: Connector configuration.
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config

    @abstractmethod
    async def fetch_documents(self, since: Optional[str] = None) -> SyncResult:
        """Fetch documents from the remote source, optionally since a
        checkpoint.

        Args:
            since: Opaque checkpoint cursor from a previous sync.
                ``None`` means fetch all documents.

        Returns:
            A ``SyncResult`` with fetched documents and next checkpoint.
        """
        ...

    @abstractmethod
    async def fetch_document(self, remote_id: str) -> Optional[RemoteDocument]:
        """Fetch a single document by its remote identity.

        Args:
            remote_id: Stable remote document identity.

        Returns:
            A ``RemoteDocument``, or ``None`` if not found.
        """
        ...

    async def connect(self) -> None:
        """Establish connection or authenticate with the remote source.

        Default implementation is a no-op. Override for sources that
        require persistent sessions (e.g. OAuth token refresh, SSH
        connection).
        """

    @abstractmethod
    async def close(self) -> None:
        """Release resources and close any persistent connections."""
        ...

    @property
    def source_key(self) -> str:
        """Shortcut to the connector's source key from config."""
        return self.config.source_key

    @property
    def connector_type(self) -> str:
        """Shortcut to the connector type string."""
        return self.config.connector_type
