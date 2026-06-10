"""
Tests for connector base abstraction, models, and factory.
"""

from ingest.connectors.base import ConnectorBase
from ingest.connectors.factory import (
    create_connector,
    list_supported_types,
    register,
)
from ingest.connectors.models import (
    ConnectorConfig,
    RemoteDocument,
    SyncResult,
)


class TestRemoteDocument:
    """Tests for RemoteDocument model."""

    def test_minimal_creation(self):
        """RemoteDocument can be created with minimal fields."""
        doc = RemoteDocument(
            remote_id="page-123",
            source_key="confluence://myspace",
            connector_type="confluence",
            title="Test Page",
            content="Hello world",
        )
        assert doc.remote_id == "page-123"
        assert doc.connector_type == "confluence"
        assert doc.content_type == "text/plain"
        assert doc.remote_url is None
        assert doc.metadata == {}

    def test_full_creation(self):
        """RemoteDocument with all fields."""
        doc = RemoteDocument(
            remote_id="PROJ-42",
            source_key="jira://PROJ",
            connector_type="jira",
            title="Fix login bug",
            content="Steps to reproduce...",
            content_type="text/markdown",
            remote_url="https://jira.example.com/browse/PROJ-42",
            remote_etag='"abc123"',
            remote_mtime=1000.0,
            metadata={"priority": "P1", "status": "open"},
        )
        assert doc.remote_id == "PROJ-42"
        assert doc.remote_url is not None
        assert doc.metadata["priority"] == "P1"


class TestSyncResult:
    """Tests for SyncResult model."""

    def test_empty_result(self):
        """Empty SyncResult has no documents and no errors."""
        result = SyncResult(source_key="confluence://myspace")
        assert result.success_count == 0
        assert result.error_count == 0
        assert not result.has_errors()
        assert result.total_fetched == 0

    def test_with_documents(self):
        """SyncResult tracks successful documents."""
        doc = RemoteDocument(
            remote_id="page-1",
            source_key="confluence://myspace",
            connector_type="confluence",
            title="Page 1",
            content="Content 1",
        )
        result = SyncResult(
            source_key="confluence://myspace",
            documents=[doc],
            total_fetched=1,
        )
        assert result.success_count == 1
        assert not result.has_errors()

    def test_with_errors(self):
        """SyncResult tracks errors."""
        result = SyncResult(
            source_key="jira://PROJ",
            errors=["HTTP 500 fetching PROJ-1"],
        )
        assert result.error_count == 1
        assert result.has_errors()

    def test_checkpoint(self):
        """SyncResult can carry a checkpoint."""
        result = SyncResult(
            source_key="confluence://myspace",
            checkpoint="cursor_next",
        )
        assert result.checkpoint == "cursor_next"


class TestConnectorConfig:
    """Tests for ConnectorConfig model."""

    def test_minimal_config(self):
        """ConnectorConfig with minimal fields."""
        config = ConnectorConfig(
            source_key="confluence://myspace",
            connector_type="confluence",
            endpoint="https://confluence.example.com/rest/api",
        )
        assert config.auth_method == "basic"
        assert config.options == {}

    def test_full_config(self):
        """ConnectorConfig with all fields."""
        config = ConnectorConfig(
            source_key="jira://PROJ",
            connector_type="jira",
            endpoint="https://jira.example.com/rest/api/2",
            auth_method="token",
            auth_credentials="JIRA_TOKEN",
            options={"project": "PROJ", "batch_size": 50},
        )
        assert config.auth_method == "token"
        assert config.options["project"] == "PROJ"


class TestConnectorFactory:
    """Tests for connector factory."""

    def test_register_and_create(self):
        """Register a mock connector and create it via factory."""
        class MockConnector(ConnectorBase):
            async def fetch_documents(self, since=None):
                return SyncResult(source_key=self.source_key)
            async def fetch_document(self, remote_id):
                return None
            async def close(self):
                pass

        register("mock_test", MockConnector)

        types = list_supported_types()
        assert "mock_test" in types

        config = ConnectorConfig(
            source_key="mock://test",
            connector_type="mock_test",
            endpoint="https://mock.example.com",
        )
        connector = create_connector("mock_test", config)
        assert connector is not None
        assert connector.source_key == "mock://test"
        assert connector.connector_type == "mock_test"

    def test_create_unknown_type(self):
        """Creating an unregistered connector returns None."""
        config = ConnectorConfig(
            source_key="unknown://test",
            connector_type="nonexistent",
            endpoint="https://example.com",
        )
        connector = create_connector("nonexistent", config)
        assert connector is None

    def test_list_supported_types(self):
        """List supported types returns sorted list."""
        # Register additional types for listing
        types = list_supported_types()
        assert isinstance(types, list)
        # Should include mock_test from previous test
        assert "mock_test" in types
