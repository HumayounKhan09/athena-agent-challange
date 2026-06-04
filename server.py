"""
Athena AI Challenge — MCP Server (Python / FastMCP)
Topic TBD — uses mock data until API_BASE is configured.
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from services.api_client import filter_items, fetch_items

# ── Server init ──────────────────────────────────────────────────────────────
mcp = FastMCP(name="challenge-agent")

# ── Load widget HTML at startup (not on every request) ───────────────────────
WIDGET_HTML = Path(__file__).resolve().parent.joinpath("widget.html").read_text(
    encoding="utf-8"
)

OUTPUT_TEMPLATE = "ui://widget/main.html"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST GET OPTIONS DELETE",
    "Access-Control-Allow-Headers": "content-type mcp-session-id",
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
}


# ── Resource: widget HTML ─────────────────────────────────────────────────────
@mcp.resource("ui://widget/main.html")
async def widget_resource() -> dict:
    return {
        "contents": [
            {
                "uri": OUTPUT_TEMPLATE,
                "mimeType": "text/html+skybridge",
                "text": WIDGET_HTML,
                "_meta": {
                    "openai/widgetPrefersBorder": True,
                },
            }
        ]
    }


def _tool_response(items: list[dict], narration: str, **extra) -> dict:
    structured = {"items": items, **extra}
    return {
        "content": [{"type": "text", "text": narration}],
        "structuredContent": structured,
    }


# ── Tool 1: Primary fetch tool ────────────────────────────────────────────────
@mcp.tool(
    name="fetch_data",
    title="Fetch Data",
    description=(
        "Use this when the user asks about data or wants to search for items. "
        "Returns matching records as an interactive widget. "
        "Do not use for filtering already-loaded results — use filter_data instead."
    ),
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": False,
    },
    meta={
        "openai/outputTemplate": OUTPUT_TEMPLATE,
        "openai/toolInvocation/invoking": "Fetching data…",
        "openai/toolInvocation/invoked": "Data loaded",
        "openai/widgetAccessible": True,
    },
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
    name="filter_data",
    title="Filter Data",
    description=(
        "Use this when the user wants to filter, sort, or narrow down "
        "results already shown in the widget. Requires a previous fetch_data call first."
    ),
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": False,
    },
    meta={
        "openai/outputTemplate": OUTPUT_TEMPLATE,
        "openai/toolInvocation/invoking": "Filtering…",
        "openai/toolInvocation/invoked": "Filtered",
        "openai/widgetAccessible": True,
    },
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

        inner_scope = dict(scope)
        path = scope.get("path", "")
        if path.startswith("/mcp"):
            remainder = path[4:] or "/"
            inner_scope["path"] = remainder
            inner_scope["root_path"] = scope.get("root_path", "") + "/mcp"
        await self.app(inner_scope, receive, send)


MCP_ENDPOINT = MCPAppWrapper(mcp.streamable_http_app())
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
    )

    return app


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"MCP server ready at http://localhost:{port}/mcp")
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
