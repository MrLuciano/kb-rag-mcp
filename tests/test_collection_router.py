"""Tests for CollectionRouter."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kb_server.collections.router import CollectionNotFoundError, CollectionRouter


@pytest.fixture
def manager():
    m = AsyncMock()
    return m


@pytest.fixture
def router(manager):
    return CollectionRouter(manager, default_collection="kb_docs")


# ------------------------------------------------------------------
# resolve
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_none_returns_default(manager, router):
    manager.collection_exists.return_value = True
    result = await router.resolve(None)
    assert result == "kb_docs"
    manager.collection_exists.assert_awaited_once_with("kb_docs")


@pytest.mark.asyncio
async def test_resolve_existing_returns_name(manager, router):
    manager.collection_exists.return_value = True
    result = await router.resolve("custom")
    assert result == "custom"


@pytest.mark.asyncio
async def test_resolve_missing_raises_error(manager, router):
    manager.collection_exists.return_value = False
    with pytest.raises(CollectionNotFoundError, match="custom"):
        await router.resolve("custom")


@pytest.mark.asyncio
async def test_resolve_missing_default_raises_error(manager, router):
    manager.collection_exists.return_value = False
    with pytest.raises(CollectionNotFoundError, match="kb_docs"):
        await router.resolve(None)


# ------------------------------------------------------------------
# ensure
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_none_uses_default(manager, router):
    manager.create_collection.return_value = False  # already existed
    result = await router.ensure(None)
    assert result == "kb_docs"
    manager.create_collection.assert_awaited_once_with("kb_docs")


@pytest.mark.asyncio
async def test_ensure_creates_if_missing(manager, router):
    manager.create_collection.return_value = True  # was created
    result = await router.ensure("new_col")
    assert result == "new_col"
    manager.create_collection.assert_awaited_once_with("new_col")


@pytest.mark.asyncio
async def test_ensure_returns_existing(manager, router):
    manager.create_collection.return_value = False  # already existed
    result = await router.ensure("existing")
    assert result == "existing"


# ------------------------------------------------------------------
# resolve_multi
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_multi_all_existing(manager, router):
    manager.collection_exists.return_value = True
    result = await router.resolve_multi(["kb_hr", "kb_eng"])
    assert result == ["kb_hr", "kb_eng"]
    assert manager.collection_exists.await_count == 2


@pytest.mark.asyncio
async def test_resolve_multi_empty_returns_empty(manager, router):
    result = await router.resolve_multi([])
    assert result == []


@pytest.mark.asyncio
async def test_resolve_multi_missing_raises_error(manager, router):
    manager.collection_exists.side_effect = lambda name: name != "missing"

    with pytest.raises(CollectionNotFoundError, match="missing"):
        await router.resolve_multi(["kb_docs", "missing", "kb_hr"])


@pytest.mark.asyncio
async def test_resolve_multi_single_element(manager, router):
    manager.collection_exists.return_value = True
    result = await router.resolve_multi(["single_kb"])
    assert result == ["single_kb"]


@pytest.mark.asyncio
async def test_resolve_multi_with_none_uses_default(manager, router):
    """None entries are replaced by the default collection."""
    manager.collection_exists.side_effect = (
        lambda n: n in ("kb_eng", "kb_docs")
    )
    result = await router.resolve_multi(["kb_eng", None])
    assert result == ["kb_eng", "kb_docs"]
