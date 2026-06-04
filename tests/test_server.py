"""Tests for MCP server routes, CORS, tools, and resource."""

from __future__ import annotations

import json

import pytest

from server import OUTPUT_TEMPLATE, WIDGET_HTML, fetch_data, filter_data, mcp, widget_resource


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


@pytest.mark.asyncio
async def test_widget_resource_metadata():
    payload = await widget_resource()
    content = payload["contents"][0]
    assert content["uri"] == OUTPUT_TEMPLATE
    assert content["mimeType"] == "text/html+skybridge"
    assert content["text"] == WIDGET_HTML
    assert content["_meta"]["openai/widgetPrefersBorder"] is True


@pytest.mark.asyncio
async def test_tools_registered_with_metadata():
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    assert names == {"fetch_data", "filter_data"}

    for tool in tools:
        assert tool.description.startswith("Use this when")
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.openWorldHint is False
        assert tool.meta["openai/outputTemplate"] == OUTPUT_TEMPLATE
        assert tool.meta["openai/widgetAccessible"] is True
        assert tool.meta["openai/toolInvocation/invoking"]
        assert tool.meta["openai/toolInvocation/invoked"]


@pytest.mark.asyncio
async def test_fetch_data_returns_structured_content():
    result = await fetch_data(query="alpha", limit=5)
    assert isinstance(result["structuredContent"]["items"], list)
    assert result["content"][0]["type"] == "text"
    assert "alpha" in result["content"][0]["text"].lower()


@pytest.mark.asyncio
async def test_filter_data_returns_structured_content():
    result = await filter_data(query="", category="general", sort_by="name")
    assert isinstance(result["structuredContent"]["items"], list)
    assert result["content"][0]["type"] == "text"
    assert all(item["category"] == "general" for item in result["structuredContent"]["items"])


@pytest.mark.asyncio
async def test_call_tool_wrapper_returns_json_payload():
    contents = await mcp.call_tool("fetch_data", {"query": "beta", "limit": 5})
    assert contents
    payload = json.loads(contents[0].text)
    assert payload["structuredContent"]["items"]
    assert payload["content"][0]["type"] == "text"
