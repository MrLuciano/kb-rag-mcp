"""Tests for dynamic tool descriptions."""

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_tools_search_kb_has_module_param():
    import kb_server.server as srv

    tools = await srv.list_tools()
    for tool in tools:
        if tool.name == "search_kb":
            props = tool.inputSchema.get("properties", {})
            assert "module" in props
            break
    else:
        pytest.fail("search_kb tool not found")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_tools_list_docs_has_module_param():
    import kb_server.server as srv

    tools = await srv.list_tools()
    for tool in tools:
        if tool.name == "list_documents":
            props = tool.inputSchema.get("properties", {})
            assert "module" in props
            break
    else:
        pytest.fail("list_documents tool not found")
