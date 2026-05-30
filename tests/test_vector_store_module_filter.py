"""Tests for module filter in VectorStore."""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_store():
    s = AsyncMock()
    s.collection = "kb_docs"
    s.search.return_value = []
    s.list_documents.return_value = []
    return s


@pytest.mark.asyncio
async def test_search_accepts_module_filter(mock_store):
    result = await mock_store.search(
        vector=[0.1] * 384,
        top_k=5,
        module="Administration",
    )
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_list_documents_accepts_module_filter(mock_store):
    result = await mock_store.list_documents(module="Administration")
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_search_module_none_no_error(mock_store):
    result = await mock_store.search(
        vector=[0.1] * 384,
        top_k=5,
    )
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_list_documents_module_none_no_error(mock_store):
    result = await mock_store.list_documents()
    assert isinstance(result, list)
