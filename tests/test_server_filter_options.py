"""Tests for list_filter_options MCP tool."""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_filter_options_integration():
    """Integration test: filter options return valid data formats."""
    from kb_server.filter_terms_cache import FilterTermsCache

    cache = FilterTermsCache(store=None)
    assert isinstance(cache.terms, dict)
    assert cache.get_formatted("vendor") == ""


@pytest.mark.asyncio
async def test_list_filter_options_registered():
    """list_filter_options should appear in list_tools output."""
    import kb_server.server as srv

    tools = await srv.list_tools()
    names = [t.name for t in tools]
    assert "list_filter_options" in names


@pytest.mark.asyncio
async def test_list_filter_options_tool_structure():
    """Tool should have field and collection params."""
    import kb_server.server as srv

    tools = await srv.list_tools()
    for tool in tools:
        if tool.name == "list_filter_options":
            props = tool.inputSchema.get("properties", {})
            assert "field" in props
            assert "collection" in props
            break
    else:
        pytest.fail("list_filter_options tool not found")


@pytest.mark.asyncio
async def test_list_filter_options_unknown_field():
    """Unknown field should return empty message."""
    import kb_server.server as srv

    result = await srv.call_tool(
        "list_filter_options", {"field": "nonexistent"}
    )
    assert len(result) == 1
    assert "No values" in result[0].text or "No results" in result[0].text


@pytest.mark.asyncio
async def test_list_filter_options_callable():
    """list_filter_options should be callable without errors."""
    import kb_server.server as srv

    result = await srv.call_tool("list_filter_options", {})
    assert len(result) == 1
    assert isinstance(result[0].text, str)
