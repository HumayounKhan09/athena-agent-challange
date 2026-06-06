"""
Athena AI Challenge — Air Quality Comparison MCP Server (Python / FastMCP)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from config.tool_references import TOOLS, build_description, get_direct_tool_names
from services.api_client import (
    _resolve_item_date,
    empty_fetch_date_hint,
    filter_items,
    fetch_items,
    match_cities,
)


def _transport_security_settings() -> TransportSecuritySettings | None:
    """DNS rebinding allowlist. FastMCP defaults host=127.0.0.1 and only allows localhost."""
    extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if extra_hosts:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"] + extra_hosts,
            allowed_origins=[
                "http://127.0.0.1:*",
                "http://localhost:*",
                "http://[::1]:*",
            ],
        )
    return None


mcp = FastMCP(
    name="air-quality-agent",
    host="0.0.0.0",
    transport_security=_transport_security_settings(),
)

_WIDGET_PATH = Path(__file__).resolve().parent.joinpath("widget.html")
_RAW_WIDGET_HTML = _WIDGET_PATH.read_text(encoding="utf-8")
_TOOL_REFS_JSON = json.dumps(get_direct_tool_names())
WIDGET_HTML = _RAW_WIDGET_HTML.replace("__TOOL_REFS_JSON__", _TOOL_REFS_JSON)

OUTPUT_TEMPLATE = "ui://widget/main.html"

WIDGET_RESOURCE_META = {
    "ui": {
        "prefersBorder": True,
        "csp": {
            "connectDomains": [],
            "resourceDomains": [],
        },
    },
    "openai/widgetPrefersBorder": True,
    "openai/widgetDescription": (
        "Interactive air quality comparison card with city search, pollutant filters, "
        "severity bands, and sortable bar charts."
    ),
}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST GET OPTIONS DELETE",
    "Access-Control-Allow-Headers": "content-type mcp-session-id",
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
}


@mcp.resource(
    OUTPUT_TEMPLATE,
    name="air-quality-widget",
    mime_type="text/html+skybridge",
    meta=WIDGET_RESOURCE_META,
)
async def widget_resource() -> str:
    """Return Skybridge HTML; mime_type text/html+skybridge enables window.openai."""
    return WIDGET_HTML


def _tool_response(items: list[dict], narration: str, tool_key: str, **extra) -> CallToolResult:
    """Athena reads structuredContent at the CallToolResult root, not nested in text JSON."""
    tool = TOOLS[tool_key]
    return CallToolResult(
        content=[TextContent(type="text", text=narration)],
        structuredContent={"items": items, **extra},
        _meta={
            "ui": {"resourceUri": OUTPUT_TEMPLATE},
            "openai/outputTemplate": OUTPUT_TEMPLATE,
            "openai/toolInvocation/invoking": tool["invoking"],
            "openai/toolInvocation/invoked": tool["invoked"],
        },
        isError=False,
    )


def _tool_meta(tool_key: str) -> dict:
    tool = TOOLS[tool_key]
    return {
        "ui": {
            "resourceUri": OUTPUT_TEMPLATE,
            "visibility": ["model", "app"],
        },
        "openai/outputTemplate": OUTPUT_TEMPLATE,
        "openai/toolInvocation/invoking": tool["invoking"],
        "openai/toolInvocation/invoked": tool["invoked"],
        "openai/widgetAccessible": True,
    }


@mcp.tool(
    name=TOOLS["fetch"]["name"],
    title=TOOLS["fetch"]["title"],
    description=build_description("fetch"),
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
    meta=_tool_meta("fetch"),
)
async def fetch_data(
    query: str,
    limit: int = 20,
    pollutant: str = "pm2_5",
    date: str = "",
) -> CallToolResult:
    """Fetch air quality readings from Open-Meteo for cities matching the query."""
    requested_date = _resolve_item_date(date)
    items = await fetch_items(query=query, limit=limit, pollutant=pollutant, date_str=date)
    cities = match_cities(query) or []
    pollutant_label = pollutant or "pm2_5"
    used_dates = sorted({str(item.get("date", "")) for item in items if item.get("date")})
    item_date = used_dates[0] if len(used_dates) == 1 else (used_dates[-1] if used_dates else requested_date)
    bands = {}
    for item in items:
        bands[item.get("category", "unknown")] = bands.get(item.get("category", "unknown"), 0) + 1
    summary = ", ".join(f"{count} {band}" for band, count in sorted(bands.items())) or "no readings"
    if not items:
        date_hint = empty_fetch_date_hint(date, requested_date)
        narration = (
            f"No {pollutant_label} readings for {len(cities) or 'default'} cities on {requested_date}. "
        )
        if date_hint:
            narration += date_hint
        else:
            narration += (
                "Open-Meteo may not have hourly data for that date; "
                "try today, yesterday, or another pollutant."
            )
    elif used_dates and (len(used_dates) > 1 or used_dates[0] != requested_date):
        narration = (
            f"Compared {pollutant_label} for {len(items)} cities "
            f"(requested {requested_date}, data from {', '.join(used_dates)}): {summary}."
        )
    else:
        narration = f"Compared {pollutant_label} for {len(items)} cities on {item_date}: {summary}."
    return _tool_response(
        items,
        narration,
        "fetch",
        query=query,
        total=len(items),
        pollutant=pollutant_label,
        date=item_date,
        requested_date=requested_date,
        cities_queried=cities,
    )


@mcp.tool(
    name=TOOLS["filter"]["name"],
    title=TOOLS["filter"]["title"],
    description=build_description("filter"),
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
    meta=_tool_meta("filter"),
)
async def filter_data(
    query: str,
    category: str = "",
    sort_by: str = "value_desc",
    pollutant: str = "pm2_5",
    date: str = "",
    min_severity: str = "",
) -> CallToolResult:
    """Refine comparison by pollutant, date, severity band, and sort order."""
    items = await filter_items(
        query=query,
        category=category,
        sort_by=sort_by,
        pollutant=pollutant,
        date_str=date,
        min_severity=min_severity,
    )
    return _tool_response(
        items,
        f"Filtered to {len(items)} cities.",
        "filter",
        query=query,
        category=category,
        sort_by=sort_by,
        pollutant=pollutant,
        date=date,
        min_severity=min_severity,
    )


async def health(_request: Request) -> PlainTextResponse:
    return PlainTextResponse("MCP server running")


CORS_HEADER_ITEMS = tuple(CORS_HEADERS.items())


class AlwaysCORSMiddleware:
    """Attach required CORS headers to every HTTP response."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_cors(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.decode().lower() for name, _ in headers}
                for key, value in CORS_HEADER_ITEMS:
                    if key.lower() not in existing:
                        headers.append((key.lower().encode(), value.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_cors)


class MCPAppWrapper:
    """Handle OPTIONS preflight and serve MCP transport at /mcp without redirects."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method") == "OPTIONS":
            response = Response(status_code=204, headers=CORS_HEADERS)
            await response(scope, receive, send)
            return

        if scope["type"] == "http" and scope.get("method") == "GET":
            has_session = any(
                name.lower() == b"mcp-session-id" for name, _ in scope.get("headers", [])
            )
            if not has_session:
                response = PlainTextResponse("MCP endpoint ready", headers=CORS_HEADERS)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


MCP_HTTP_APP = mcp.streamable_http_app()
MCP_ENDPOINT = MCPAppWrapper(MCP_HTTP_APP)
MCP_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]


def create_app() -> Starlette:
    """Build the ASGI app with health check, CORS, and MCP transport."""
    routes = [
        Route("/", health, methods=["GET"]),
        Route("/mcp", endpoint=MCP_ENDPOINT, methods=MCP_METHODS),
        Route("/mcp/", endpoint=MCP_ENDPOINT, methods=MCP_METHODS),
    ]

    app = Starlette(
        routes=routes,
        middleware=[Middleware(AlwaysCORSMiddleware)],
        lifespan=MCP_HTTP_APP.router.lifespan_context,
    )

    return app


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"MCP server ready at http://localhost:{port}/mcp")
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
