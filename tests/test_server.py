"""Tests for MCP server routes, CORS, tools, and resource."""

from __future__ import annotations

import json

import pytest

import services.api_client as api_client
from config.tool_references import TOOLS, get_direct_tool_names, get_tool_names
from server import OUTPUT_TEMPLATE, WIDGET_HTML, WIDGET_RESOURCE_META, fetch_data, filter_data, mcp, widget_resource


@pytest.mark.asyncio
async def test_health_endpoint(app_client):
    response = await app_client.get("/")
    assert response.status_code == 200
    assert response.text == "MCP server running"


@pytest.mark.asyncio
async def test_options_mcp_returns_204_with_cors(app_client):
    response = await app_client.options("/mcp")
    assert response.status_code == 204
    assert response.headers.get("access-control-allow-origin") == "*"
    assert "POST" in response.headers.get("access-control-allow-methods", "")
    assert "GET" in response.headers.get("access-control-allow-methods", "")
    assert "OPTIONS" in response.headers.get("access-control-allow-methods", "")
    assert "DELETE" in response.headers.get("access-control-allow-methods", "")
    assert "content-type" in response.headers.get("access-control-allow-headers", "").lower()
    assert "mcp-session-id" in response.headers.get("access-control-allow-headers", "").lower()
    assert response.headers.get("access-control-expose-headers", "").lower() == "mcp-session-id"


@pytest.mark.asyncio
async def test_mcp_get_includes_cors_headers(app_client):
    response = await app_client.get("/mcp")
    assert response.headers.get("access-control-allow-origin") == "*"


@pytest.mark.asyncio
async def test_widget_loaded_at_startup():
    assert WIDGET_HTML
    assert "<!DOCTYPE html>" in WIDGET_HTML
    assert "window.openai" in WIDGET_HTML or "openai" in WIDGET_HTML
    assert "__TOOL_REFS_JSON__" not in WIDGET_HTML
    assert TOOLS["fetch"]["name"] in WIDGET_HTML


@pytest.mark.asyncio
async def test_widget_resource_metadata():
    html = await widget_resource()
    assert html == WIDGET_HTML
    resources = await mcp.list_resources()
    assert len(resources) == 1
    assert str(resources[0].uri) == OUTPUT_TEMPLATE
    assert resources[0].mimeType == "text/html+skybridge"
    assert resources[0].meta["ui"]["prefersBorder"] is True
    assert resources[0].meta["openai/widgetDescription"]
    assert resources[0].meta == WIDGET_RESOURCE_META


@pytest.mark.asyncio
async def test_widget_injects_tool_refs_json():
    import json

    refs = get_direct_tool_names()
    assert json.dumps(refs) in WIDGET_HTML
    assert 'id="tool-refs"' in WIDGET_HTML


@pytest.mark.asyncio
async def test_tools_registered_with_metadata():
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    assert names == get_tool_names()

    for tool in tools:
        assert tool.description.startswith("Use this when")
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.openWorldHint is True
        assert tool.meta["ui"]["resourceUri"] == OUTPUT_TEMPLATE
        assert tool.meta["openai/outputTemplate"] == OUTPUT_TEMPLATE
        assert tool.meta["openai/widgetAccessible"] is True
        assert tool.meta["openai/toolInvocation/invoking"]
        assert tool.meta["openai/toolInvocation/invoked"]


@pytest.mark.asyncio
async def test_fetch_data_returns_structured_content():
    result = await fetch_data(query="london paris", limit=5)
    assert isinstance(result.structuredContent["items"], list)
    assert result.content[0].type == "text"
    assert result.structuredContent["pollutant"] == "pm2_5"


@pytest.mark.asyncio
async def test_filter_data_returns_structured_content():
    result = await filter_data(query="", min_severity="moderate", sort_by="value_desc")
    assert isinstance(result.structuredContent["items"], list)
    assert result.content[0].type == "text"
    for item in result.structuredContent["items"]:
        assert api_client._severity_rank(item["category"]) >= api_client._severity_rank("moderate")


@pytest.mark.asyncio
async def test_call_tool_wrapper_returns_call_tool_result():
    result = await mcp.call_tool(TOOLS["fetch"]["name"], {"query": "london", "limit": 5})
    assert result.structuredContent["items"]
    assert result.content[0].type == "text"


@pytest.mark.asyncio
async def test_tool_content_is_narration_not_nested_json():
    """Athena needs structuredContent at result root; dict returns embed it in content.text."""
    result = await fetch_data(query="london", limit=3)
    narration = result.content[0].text
    assert not narration.strip().startswith("{")
    assert "structuredContent" not in narration
    assert result.structuredContent["items"]


@pytest.mark.asyncio
async def test_read_resource_returns_skybridge_html():
    contents = await mcp.read_resource(OUTPUT_TEMPLATE)
    assert len(contents) == 1
    assert contents[0].mime_type == "text/html+skybridge"
    assert contents[0].content.startswith("<!DOCTYPE html>")
    assert "fetch_data" in contents[0].content


@pytest.mark.asyncio
async def test_tool_response_includes_invocation_meta():
    result = await fetch_data(query="london", limit=3)
    assert result.meta["ui"]["resourceUri"] == OUTPUT_TEMPLATE
    assert result.meta["openai/outputTemplate"] == OUTPUT_TEMPLATE
    assert result.meta["openai/toolInvocation/invoking"] == TOOLS["fetch"]["invoking"]
    assert result.meta["openai/toolInvocation/invoked"] == TOOLS["fetch"]["invoked"]
