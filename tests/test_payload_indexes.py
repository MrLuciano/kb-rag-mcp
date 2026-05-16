"""
Tests for payload indexing feature (FASE 12).

Tests index creation, idempotency, query performance, and correctness.
"""

import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.models import PayloadSchemaType

# Add paths for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPayloadIndexCreation:
    """Test payload index creation logic."""

    @pytest.mark.asyncio
    async def test_create_index_on_new_collection(self):
        """Test that indexes are created when new collection is created."""
        from server.vector_store import VectorStore

        store = VectorStore()
        
        # Mock client
        mock_client = AsyncMock()
        mock_client.get_collections.return_value = MagicMock(
            collections=[]
        )
        mock_client.create_collection = AsyncMock()
        mock_client.create_payload_index = AsyncMock()
        store.client = mock_client
        
        # Trigger collection creation
        await store._ensure_collection()
        
        # Verify collection created
        assert mock_client.create_collection.called
        
        # Verify indexes created for both fields
        assert mock_client.create_payload_index.call_count == 2
        
        # Check that both 'product' and 'doc_type' were indexed
        calls = mock_client.create_payload_index.call_args_list
        indexed_fields = [
            call.kwargs["field_name"] for call in calls
        ]
        assert "product" in indexed_fields
        assert "doc_type" in indexed_fields
        
        # Verify keyword schema used
        for call in calls:
            assert (
                call.kwargs["field_schema"] == PayloadSchemaType.KEYWORD
            )

    @pytest.mark.asyncio
    async def test_index_creation_is_non_fatal(self):
        """Test that index creation failures don't prevent collection use."""
        from server.vector_store import VectorStore

        store = VectorStore()
        
        # Mock client that fails on index creation
        mock_client = AsyncMock()
        mock_client.get_collections.return_value = MagicMock(
            collections=[]
        )
        mock_client.create_collection = AsyncMock()
        mock_client.create_payload_index = AsyncMock(
            side_effect=Exception("Index creation failed")
        )
        store.client = mock_client
        
        # Should not raise, only warn
        await store._ensure_collection()
        
        # Collection still created
        assert mock_client.create_collection.called

    @pytest.mark.asyncio
    async def test_no_duplicate_index_on_existing_collection(self):
        """Test that indexes aren't recreated for existing collections."""
        from server.vector_store import VectorStore

        store = VectorStore()
        
        # Mock client with existing collection
        mock_collection = MagicMock()
        mock_collection.name = "kb_docs"
        mock_client = AsyncMock()
        mock_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )
        mock_client.create_payload_index = AsyncMock()
        store.client = mock_client
        
        # Trigger collection check
        await store._ensure_collection()
        
        # Verify NO index creation (collection already existed)
        assert not mock_client.create_payload_index.called


class TestMigrationScript:
    """Test the create_payload_indexes.py migration script."""

    @pytest.mark.asyncio
    async def test_migration_script_dry_run(self, tmp_path):
        """Test migration script in dry-run mode."""
        # This test would require setting up a real Qdrant instance
        # or extensive mocking. For now, test that script imports correctly.
        from scripts.migrations.create_payload_indexes import (
            check_existing_indexes,
            create_index,
        )
        
        # Verify functions exist and are callable
        assert callable(check_existing_indexes)
        assert callable(create_index)

    @pytest.mark.asyncio
    async def test_check_existing_indexes(self):
        """Test checking which indexes already exist."""
        from scripts.migrations.create_payload_indexes import (
            check_existing_indexes,
        )
        
        # Mock client
        mock_client = AsyncMock()
        
        # Mock collection with one index
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.payload_schema = {
            "product": MagicMock()
        }
        mock_client.get_collection.return_value = mock_collection_info
        
        # Check indexes
        result = await check_existing_indexes(mock_client, "kb_docs")
        
        # Should detect product index exists, doc_type doesn't
        assert result["product"] is True
        assert result["doc_type"] is False


@pytest.mark.integration
class TestPayloadIndexPerformance:
    """
    Integration tests for payload index performance.
    
    Requires a running Qdrant instance.
    Set QDRANT_HOST and QDRANT_PORT env vars or skip with:
        pytest -m "not integration"
    """

    @pytest.fixture
    async def vector_store(self):
        """Create a vector store connected to test Qdrant."""
        if not os.getenv("QDRANT_HOST"):
            pytest.skip("Integration test requires QDRANT_HOST")
        
        from server.vector_store import VectorStore

        store = VectorStore()
        store.collection = "test_payload_indexes"
        await store.connect()
        
        # Cleanup test collection if exists
        try:
            await store.client.delete_collection(store.collection)
        except Exception:
            pass
        
        yield store
        
        # Cleanup
        try:
            await store.client.delete_collection(store.collection)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_filtered_query_speed_with_indexes(self, vector_store):
        """
        Benchmark filtered queries with and without indexes.
        
        Should show >10x improvement with indexes on large collections.
        """
        # This test would require:
        # 1. Insert 10k+ points with varied product/doc_type
        # 2. Query with filters before index creation
        # 3. Create indexes
        # 4. Query with filters after index creation
        # 5. Compare latencies
        
        # For now, just verify the test structure is correct
        pytest.skip("Requires large test dataset and timing infrastructure")

    @pytest.mark.asyncio
    async def test_query_correctness_with_indexes(self, vector_store):
        """Verify query results are identical with/without indexes."""
        # Insert test data
        test_points = [
            {
                "id": "1",
                "vector": [0.1] * vector_store.dim,
                "payload": {
                    "product": "TestProduct",
                    "doc_type": "admin_guide",
                },
            },
            {
                "id": "2",
                "vector": [0.2] * vector_store.dim,
                "payload": {
                    "product": "TestProduct",
                    "doc_type": "install_guide",
                },
            },
            {
                "id": "3",
                "vector": [0.3] * vector_store.dim,
                "payload": {
                    "product": "OtherProduct",
                    "doc_type": "admin_guide",
                },
            },
        ]
        
        # Would insert points, query, create indexes, query again,
        # and compare results. Skipped for unit test.
        pytest.skip("Requires full integration test setup")


@pytest.mark.cli
class TestCLICommands:
    """Test CLI commands for payload indexing."""

    def test_db_create_indexes_command_exists(self):
        """Test that db create-indexes command exists."""
        from ingest.cli.db import db_group
        
        # Verify command group exists
        assert db_group is not None
        
        # Verify create-indexes subcommand exists
        assert "create-indexes" in [
            cmd.name for cmd in db_group.commands.values()
        ]

    def test_db_command_integrated_in_main_cli(self):
        """Test that db command group is registered in main CLI."""
        from ingest.cli.main import cli
        
        # Verify db group registered
        assert "db" in [cmd.name for cmd in cli.commands.values()]


# Mark all tests in this module
pytestmark = pytest.mark.fase12
