#!/usr/bin/env python3
"""Exercise MCP HTTP endpoints (initialize, tools/list, fetch_data)."""

from __future__ import annotations

import json
import sys

import httpx

BASE = "http://localhost:8000/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def parse_sse(text: str) -> list[dict]:
    events: list[dict] = []
    for block in text.strip().split("\n\n"):
        data_lines = [line[5:] for line in block.splitlines() if line.startswith("data: ")]
        if data_lines:
            events.append(json.loads("\n".join(data_lines)))
    return events


def rpc(client: httpx.Client, method: str, params: dict | None, session_id: str | None, req_id: int):
    headers = dict(HEADERS)
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        payload["params"] = params
    print(f"$ curl -X POST {BASE}  # {method}")
    response = client.post(BASE, headers=headers, json=payload)
    print(f"HTTP {response.status_code}")
    events = parse_sse(response.text) if response.text else []
    for event in events:
        print(json.dumps(event, indent=2)[:1200])
    print()
    new_session = response.headers.get("mcp-session-id", session_id)
    return events, new_session


def main() -> int:
    with httpx.Client(timeout=30.0) as client:
        init_events, session = rpc(
            client,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "demo", "version": "1.0"},
            },
            None,
            1,
        )
        if not session:
            print("No session id returned", file=sys.stderr)
            return 1

        rpc(
            client,
            "notifications/initialized",
            {},
            session,
            2,
        )
        tools_events, session = rpc(client, "tools/list", {}, session, 3)
        tool_names = []
        for event in tools_events:
            tools = event.get("result", {}).get("tools", [])
            tool_names = [t.get("name") for t in tools]
        print(f"Tools: {', '.join(tool_names)}")
        print()

        fetch_events, _ = rpc(
            client,
            "tools/call",
            {"name": "fetch_data", "arguments": {"query": "alpha", "limit": 3}},
            session,
            4,
        )
        for event in fetch_events:
            result = event.get("result", {})
            structured = result.get("structuredContent") or {}
            items = structured.get("items") or []
            if not items:
                text_blob = ""
                for block in result.get("content") or []:
                    if block.get("type") == "text":
                        text_blob = block.get("text") or ""
                if text_blob.strip().startswith("{"):
                    print(
                        "FAIL: structuredContent nested inside content.text JSON. "
                        "Restart server with CallToolResult-based server.py.",
                        file=sys.stderr,
                    )
                    return 1
            print(
                f"fetch_data returned {len(items)} item(s); "
                f"first: {items[0]['name'] if items else 'n/a'}"
            )
            if not structured:
                print("FAIL: missing root structuredContent on tools/call", file=sys.stderr)
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
