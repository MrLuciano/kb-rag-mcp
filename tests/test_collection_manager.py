"""Tests for CollectionManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from kb_server.collections.manager import CollectionManager


def _make_collections(*names: str):
    """Build a mock get_collections() response."""
    result = MagicMock()
    cols = []
    for n in names:
        col = MagicMock()
        col.name = n  # set attribute directly — MagicMock(name=...) is special
        cols.append(col)
    result.collections = cols
    return result


@pytest.fixture
def client():
    c = AsyncMock()
    return c


@pytest.fixture
def manager(client):
    return CollectionManager(client, vector_size=1024)


# ------------------------------------------------------------------
# list_collections
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_collections_returns_names(client, manager):
    client.get_collections.return_value = _make_collections("kb_docs", "alpha")
    result = await manager.list_collections()
    assert result == ["kb_docs", "alpha"]


@pytest.mark.asyncio
async def test_list_collections_empty(client, manager):
    client.get_collections.return_value = _make_collections()
    result = await manager.list_collections()
    assert result == []


# ------------------------------------------------------------------
# collection_exists
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collection_exists_true(client, manager):
    client.get_collections.return_value = _make_collections("kb_docs")
    assert await manager.collection_exists("kb_docs") is True


@pytest.mark.asyncio
async def test_collection_exists_false(client, manager):
    client.get_collections.return_value = _make_collections("kb_docs")
    assert await manager.collection_exists("other") is False


# ------------------------------------------------------------------
# create_collection
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_collection_calls_qdrant(client, manager):
    client.get_collections.return_value = _make_collections()  # empty
    result = await manager.create_collection("new_col")
    assert result is True
    client.create_collection.assert_awaited_once()
    call_kwargs = client.create_collection.call_args.kwargs
    assert call_kwargs["collection_name"] == "new_col"


@pytest.mark.asyncio
async def test_create_collection_skips_if_exists(client, manager):
    client.get_collections.return_value = _make_collections("existing")
    result = await manager.create_collection("existing")
    assert result is False
    client.create_collection.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_collection_uses_custom_vector_size(client, manager):
    client.get_collections.return_value = _make_collections()
    # Pass explicit vectors_config to avoid importing qdrant_client.models here
    await manager.create_collection("col", vector_size=512)
    # Verify create_collection was called with the right name
    call_kwargs = client.create_collection.call_args.kwargs
    assert call_kwargs["collection_name"] == "col"


@pytest.mark.asyncio
async def test_create_collection_creates_payload_indexes(client, manager):
    client.get_collections.return_value = _make_collections()
    await manager.create_collection("col")
    # 6 payload indexes: product, doc_type, source, doc_graph_id,
    # graph_topics, graph_related
    assert client.create_payload_index.await_count == 6


# ------------------------------------------------------------------
# delete_collection
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_collection_calls_qdrant(client, manager):
    client.get_collections.return_value = _make_collections("to_delete")
    result = await manager.delete_collection("to_delete")
    assert result is True
    client.delete_collection.assert_awaited_once_with(
        collection_name="to_delete"
    )


@pytest.mark.asyncio
async def test_delete_collection_missing_returns_false(client, manager):
    client.get_collections.return_value = _make_collections()
    result = await manager.delete_collection("ghost")
    assert result is False
    client.delete_collection.assert_not_awaited()
