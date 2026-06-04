"""
Athena AI Challenge — MCP Server (Python / FastMCP)
Topic TBD — uses mock data until API_BASE is configured.
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
from services.api_client import filter_items, fetch_items


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


# host=0.0.0.0 avoids FastMCP auto-enabling localhost-only DNS rebinding (breaks ngrok POST /mcp).
mcp = FastMCP(
    name="challenge-agent",
    host="0.0.0.0",
    transport_security=_transport_security_settings(),
)

# ── Load widget HTML at startup (not on every request) ───────────────────────
_WIDGET_PATH = Path(__file__).resolve().parent.joinpath("widget.html")
_RAW_WIDGET_HTML = _WIDGET_PATH.read_text(encoding="utf-8")
_TOOL_REFS_JSON = json.dumps(get_direct_tool_names())
WIDGET_HTML = _RAW_WIDGET_HTML.replace("__TOOL_REFS_JSON__", _TOOL_REFS_JSON)

OUTPUT_TEMPLATE = "ui://widget/main.html"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST GET OPTIONS DELETE",
    "Access-Control-Allow-Headers": "content-type mcp-session-id",
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
}


# ── Resource: widget HTML ─────────────────────────────────────────────────────
@mcp.resource(
    OUTPUT_TEMPLATE,
    name="challenge-widget",
    mime_type="text/html+skybridge",
    meta={"openai/widgetPrefersBorder": True},
)
async def widget_resource() -> str:
    """Return raw Skybridge HTML; mime_type must be text/html+skybridge for Athena."""
    return WIDGET_HTML


def _tool_response(items: list[dict], narration: str, **extra) -> CallToolResult:
    """Athena reads structuredContent at the CallToolResult root, not nested in text JSON."""
    return CallToolResult(
        content=[TextContent(type="text", text=narration)],
        structuredContent={"items": items, **extra},
        isError=False,
    )


def _tool_meta(tool_key: str) -> dict:
    tool = TOOLS[tool_key]
    return {
        "openai/outputTemplate": OUTPUT_TEMPLATE,
        "openai/toolInvocation/invoking": tool["invoking"],
        "openai/toolInvocation/invoked": tool["invoked"],
        "openai/widgetAccessible": True,
    }


# ── Tool 1: Primary fetch tool ────────────────────────────────────────────────
@mcp.tool(
    name=TOOLS["fetch"]["name"],
    title=TOOLS["fetch"]["title"],
    description=build_description("fetch"),
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": False,
    },
    meta=_tool_meta("fetch"),
)
async def fetch_data(query: str, limit: int = 20) -> dict:
    """Fetch items from the public API (mock when API_BASE is a placeholder)."""
    items = await fetch_items(query=query, limit=limit)
    return _tool_response(
        items,
        f"Found {len(items)} results for '{query}'.",
        query=query,
        total=len(items),
    )


# ── Tool 2: Filter / detail tool ─────────────────────────────────────────────
@mcp.tool(
    name=TOOLS["filter"]["name"],
    title=TOOLS["filter"]["title"],
    description=build_description("filter"),
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": False,
    },
    meta=_tool_meta("filter"),
)
async def filter_data(
    query: str,
    category: str = "",
    sort_by: str = "name",
) -> dict:
    """Re-fetch with filter params and return updated widget data."""
    items = await filter_items(query=query, category=category, sort_by=sort_by)
    return _tool_response(
        items,
        f"Filtered to {len(items)} results.",
        query=query,
        category=category,
        sort_by=sort_by,
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
