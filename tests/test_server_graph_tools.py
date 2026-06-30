"""
Tests for Phase 30 graph MCP tools (get_related_documents, explore_topic).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import kb_server.server as srv
from kb_server.collections.router import CollectionNotFoundError


@pytest.fixture(autouse=True)
def reset_server_globals():
    """Restore module-level globals after each test."""
    original_store = srv.store
    original_router = srv.collection_router
    yield
    srv.store = original_store
    srv.collection_router = original_router


@pytest.fixture
def mock_store():
    s = AsyncMock()
    s.collection = "kb_docs"
    return s


@pytest.fixture
def mock_router():
    r = AsyncMock()
    r.resolve.return_value = "kb_docs"
    return r


# ---------------------------------------------------------------------------
# _get_related_documents
# ---------------------------------------------------------------------------


class TestGetRelatedDocuments:
    @pytest.mark.asyncio
    async def test_returns_chunks_for_graph_id(self, mock_store, mock_router):
        mock_store.list_documents_by_graph_id.return_value = [
            {
                "source_file": "docs/guide.md",
                "chunk_index": 0,
                "product": "AppServer",
                "text": "Content here.",
            },
            {
                "source_file": "docs/guide.md",
                "chunk_index": 1,
                "product": "AppServer",
                "text": "More content.",
            },
        ]
        srv.store = mock_store
        srv.collection_router = mock_router

        out = await srv._get_related_documents({"doc_graph_id": "abc123"})

        assert len(out) == 1
        assert "abc123" in out[0].text
        assert "2 chunks" in out[0].text
        assert "docs/guide.md" in out[0].text
        assert "Content here" in out[0].text
        mock_store.list_documents_by_graph_id.assert_called_once_with(
            doc_graph_id="abc123",
            limit=20,
            collection_name="kb_docs",
        )

    @pytest.mark.asyncio
    async def test_no_results_returns_message(self, mock_store, mock_router):
        mock_store.list_documents_by_graph_id.return_value = []
        srv.store = mock_store
        srv.collection_router = mock_router

        out = await srv._get_related_documents({"doc_graph_id": "missing"})

        assert len(out) == 1
        assert "No documents found" in out[0].text

    @pytest.mark.asyncio
    async def test_respects_limit(self, mock_store, mock_router):
        mock_store.list_documents_by_graph_id.return_value = []
        srv.store = mock_store
        srv.collection_router = mock_router

        await srv._get_related_documents({"doc_graph_id": "abc", "limit": 5})

        mock_store.list_documents_by_graph_id.assert_called_once_with(
            doc_graph_id="abc",
            limit=5,
            collection_name="kb_docs",
        )

    @pytest.mark.asyncio
    async def test_respects_collection_param(self, mock_store, mock_router):
        mock_store.list_documents_by_graph_id.return_value = []
        srv.store = mock_store
        srv.collection_router = mock_router
        mock_router.resolve.return_value = "custom_col"

        await srv._get_related_documents(
            {"doc_graph_id": "abc", "collection": "custom"}
        )

        mock_store.list_documents_by_graph_id.assert_called_once_with(
            doc_graph_id="abc",
            limit=20,
            collection_name="custom_col",
        )

    @pytest.mark.asyncio
    async def test_handles_collection_not_found(self, mock_store, mock_router):
        srv.store = mock_store
        srv.collection_router = mock_router
        mock_router.resolve.side_effect = CollectionNotFoundError(
            "Unknown collection"
        )

        out = await srv._get_related_documents(
            {"doc_graph_id": "abc", "collection": "unknown"}
        )

        assert len(out) == 1
        assert "Unknown collection" in out[0].text


# ---------------------------------------------------------------------------
# _explore_topic
# ---------------------------------------------------------------------------


class TestExploreTopic:
    @pytest.mark.asyncio
    async def test_returns_documents_for_topic(self, mock_store, mock_router):
        payload_1 = MagicMock()
        payload_1.payload = {
            "source_file": "docs/install.md",
            "product": "AppServer",
            "doc_type": "install_guide",
        }
        payload_2 = MagicMock()
        payload_2.payload = {
            "source_file": "docs/admin.md",
            "product": "AppServer",
            "doc_type": "admin_guide",
        }

        mock_store.client.scroll.return_value = ([payload_1, payload_2], None)
        srv.store = mock_store
        srv.collection_router = mock_router

        out = await srv._explore_topic({"topic": "AppServer"})

        assert len(out) == 1
        assert "AppServer" in out[0].text
        assert "docs/install.md" in out[0].text
        assert "docs/admin.md" in out[0].text
        mock_store.client.scroll.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_results_returns_message(self, mock_store, mock_router):
        mock_store.client.scroll.return_value = ([], None)
        srv.store = mock_store
        srv.collection_router = mock_router

        out = await srv._explore_topic({"topic": "Unknown"})

        assert len(out) == 1
        assert "No documents found" in out[0].text

    @pytest.mark.asyncio
    async def test_deduplicates_by_source_file(self, mock_store, mock_router):
        payload = MagicMock()
        payload.payload = {
            "source_file": "docs/guide.md",
            "product": "AppServer",
            "doc_type": "guide",
        }
        # Two chunks from same file
        mock_store.client.scroll.return_value = ([payload, payload], None)
        srv.store = mock_store
        srv.collection_router = mock_router

        out = await srv._explore_topic({"topic": "AppServer"})

        # Only one entry despite 2 chunks
        assert "Total: 1 unique documents" in out[0].text

    @pytest.mark.asyncio
    async def test_respects_collection_param(self, mock_store, mock_router):
        mock_store.client.scroll.return_value = ([], None)
        srv.store = mock_store
        srv.collection_router = mock_router
        mock_router.resolve.return_value = "custom_col"

        await srv._explore_topic(
            {"topic": "AppServer", "collection": "custom"}
        )

        call_kwargs = mock_store.client.scroll.call_args.kwargs
        assert call_kwargs["collection_name"] == "custom_col"

    @pytest.mark.asyncio
    async def test_handles_collection_not_found(self, mock_store, mock_router):
        srv.store = mock_store
        srv.collection_router = mock_router
        mock_router.resolve.side_effect = CollectionNotFoundError(
            "Unknown collection"
        )

        out = await srv._explore_topic(
            {"topic": "AppServer", "collection": "unknown"}
        )

        assert len(out) == 1
        assert "Unknown collection" in out[0].text
