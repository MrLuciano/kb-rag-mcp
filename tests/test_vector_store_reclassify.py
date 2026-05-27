"""
Tests for VectorStore reclassification metadata update method.

RECLASSIFY-01: update_chunk_metadata updates Qdrant payload in-place.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from qdrant_client.models import PointStruct, FieldCondition, Filter, MatchValue

from kb_server.vector_store import VectorStore


@pytest.fixture
def mock_qdrant_client():
    """Create a mock AsyncQdrantClient for testing."""
    client = MagicMock()
    client.scroll = AsyncMock()
    client.set_payload = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_update_chunk_metadata_updates_payload(mock_qdrant_client):
    """RECLASSIFY-01: update_chunk_metadata updates Qdrant payload in-place."""
    store = VectorStore()
    store.client = mock_qdrant_client
    
    # Setup: chunk with old metadata
    mock_qdrant_client.scroll.return_value = (
        [
            PointStruct(
                id="chunk-1",
                vector=[0.1] * 384,
                payload={
                    "source_file": "docs/test.pdf",
                    "vendor": "",
                    "product": "Unknown",
                    "chunk_text": "..."
                }
            )
        ],
        None  # no next offset
    )
    
    # Execute: update vendor field
    updates = {"vendor": "OpenText"}
    count = await store.update_chunk_metadata(
        collection_name="kb-default",
        source_file="docs/test.pdf",
        updates=updates
    )
    
    # Assert: set_payload called with correct args
    assert count == 1
    mock_qdrant_client.set_payload.assert_called_once()
    call_args = mock_qdrant_client.set_payload.call_args
    assert call_args.kwargs["collection_name"] == "kb-default"
    assert call_args.kwargs["payload"] == {"vendor": "OpenText"}
    assert call_args.kwargs["points"] == ["chunk-1"]


@pytest.mark.asyncio
async def test_update_chunk_metadata_multiple_chunks(mock_qdrant_client):
    """RECLASSIFY-01: update_chunk_metadata handles multiple chunks per document."""
    store = VectorStore()
    store.client = mock_qdrant_client
    
    # Setup: document with 3 chunks
    mock_qdrant_client.scroll.return_value = (
        [
            PointStruct(id="chunk-1", vector=[0.1] * 384, payload={"source_file": "docs/test.pdf"}),
            PointStruct(id="chunk-2", vector=[0.2] * 384, payload={"source_file": "docs/test.pdf"}),
            PointStruct(id="chunk-3", vector=[0.3] * 384, payload={"source_file": "docs/test.pdf"}),
        ],
        None
    )
    
    # Execute: update multiple fields
    updates = {"vendor": "OpenText", "product": "WebReports"}
    count = await store.update_chunk_metadata(
        collection_name="kb-default",
        source_file="docs/test.pdf",
        updates=updates
    )
    
    # Assert: all 3 chunks updated
    assert count == 3
    call_args = mock_qdrant_client.set_payload.call_args
    assert call_args.kwargs["points"] == ["chunk-1", "chunk-2", "chunk-3"]
    assert call_args.kwargs["payload"] == {"vendor": "OpenText", "product": "WebReports"}


@pytest.mark.asyncio
async def test_update_chunk_metadata_specific_chunk_index(mock_qdrant_client):
    """RECLASSIFY-01: update_chunk_metadata can target specific chunk_index."""
    store = VectorStore()
    store.client = mock_qdrant_client
    
    # Setup: single chunk with chunk_index=0
    mock_qdrant_client.scroll.return_value = (
        [
            PointStruct(
                id="chunk-1",
                vector=[0.1] * 384,
                payload={"source_file": "docs/test.pdf", "chunk_index": 0}
            )
        ],
        None
    )
    
    # Execute: update only chunk_index=0
    updates = {"subsystem": "Admin"}
    count = await store.update_chunk_metadata(
        collection_name="kb-default",
        source_file="docs/test.pdf",
        updates=updates,
        chunk_index=0
    )
    
    # Assert: only matching chunk updated
    assert count == 1
    call_args = mock_qdrant_client.set_payload.call_args
    assert call_args.kwargs["points"] == ["chunk-1"]


@pytest.mark.asyncio
async def test_update_chunk_metadata_no_chunks_found(mock_qdrant_client):
    """RECLASSIFY-01: update_chunk_metadata returns 0 when no chunks found."""
    store = VectorStore()
    store.client = mock_qdrant_client
    
    # Setup: no chunks found
    mock_qdrant_client.scroll.return_value = ([], None)
    
    # Execute: update non-existent document
    updates = {"vendor": "OpenText"}
    count = await store.update_chunk_metadata(
        collection_name="kb-default",
        source_file="docs/nonexistent.pdf",
        updates=updates
    )
    
    # Assert: no update, count=0
    assert count == 0
    mock_qdrant_client.set_payload.assert_not_called()


@pytest.mark.asyncio
async def test_update_chunk_metadata_filter_built_correctly(mock_qdrant_client):
    """RECLASSIFY-01: update_chunk_metadata builds correct Qdrant filter."""
    store = VectorStore()
    store.client = mock_qdrant_client
    
    # Setup: mock scroll to capture filter
    mock_qdrant_client.scroll.return_value = ([], None)
    
    # Execute: with chunk_index filter
    await store.update_chunk_metadata(
        collection_name="kb-default",
        source_file="docs/test.pdf",
        updates={"vendor": "OpenText"},
        chunk_index=5
    )
    
    # Assert: scroll called with correct filter
    call_args = mock_qdrant_client.scroll.call_args
    scroll_filter = call_args.kwargs["scroll_filter"]
    
    # Check filter has both source_file and chunk_index conditions
    assert isinstance(scroll_filter, Filter)
    assert len(scroll_filter.must) == 2
    
    # Verify source_file condition
    source_file_condition = [c for c in scroll_filter.must if c.key == "source_file"][0]
    assert source_file_condition.match.value == "docs/test.pdf"
    
    # Verify chunk_index condition
    chunk_index_condition = [c for c in scroll_filter.must if c.key == "chunk_index"][0]
    assert chunk_index_condition.match.value == 5
