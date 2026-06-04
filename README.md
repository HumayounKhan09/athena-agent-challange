# Athena AI Challenge — MCP Agent

Python MCP server with an interactive Skybridge widget for the Athena AI Challenge. Topic is **TBD** — the server uses mock data until a real public API is assigned (Phase 6).

## Stack

- **Python 3.10+** (3.13 recommended)
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (`mcp[cli]`)
- [httpx](https://www.python-httpx.org/) for API calls
- [uvicorn](https://www.uvicorn.org/) ASGI server
- Vanilla JS widget (`widget.html`) served as `text/html+skybridge`

## Setup

Create and activate a virtual environment with **Python 3.10+**, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | HTTP port for the MCP server |
| `API_BASE` | `https://api.example.com` | Public API base URL (placeholder uses mock data) |
| `API_KEY` | _(empty)_ | Optional bearer token for authenticated APIs |

When `API_BASE` contains `example.com`, the service layer returns mock items instead of making HTTP requests.

## Run locally

```bash
source .venv/bin/activate
python server.py
```

Expected startup log:

```text
MCP server ready at http://localhost:8000/mcp
```

Health check:

```bash
curl http://localhost:8000/
# MCP server running
```

## Test

```bash
source .venv/bin/activate
pytest -v
```

Test modules:

- `tests/test_server.py` — health, CORS, tools, widget resource
- `tests/test_api_client.py` — mock + mocked HTTP paths
- `tests/test_tool_references.py` — config descriptions and direct-ref map
- `tests/test_widget_static.py` — widget bridge and DOM contracts

## Expose with ngrok

```bash
ngrok http 8000
```

Use the HTTPS forwarding URL with the `/mcp` path when connecting to Athena, for example:

```text
https://xxxx.ngrok.app/mcp
```

## MCP Inspector

With the server running locally:

```bash
npx @modelcontextprotocol/inspector@latest \
  --server-url http://localhost:8000/mcp \
  --transport http
```

Verify:

1. Two tools: `fetch_data`, `filter_data`
2. One resource: `ui://widget/main.html` (`text/html+skybridge`)
3. `fetch_data` returns `structuredContent.items`

## Connect to Athena

1. Open [Athena agent creation](https://athenachat.bot/chatbot/mybots/create)
2. Add your ngrok MCP URL ending in `/mcp`
3. Test prompts that trigger `fetch_data`

### Refresh connector after metadata changes

Whenever you change tool names, descriptions, `_meta`, or resource metadata:

1. Save your code changes
2. Restart the server (and ngrok if needed)
3. In Athena: **Settings → Connectors → Refresh**
4. Re-test in MCP Inspector before trying in Athena

Stale connector metadata is a common cause of missing tools or broken widget rendering.

## Project layout

```text
server.py                  # FastMCP server, tools, resource, HTTP/CORS
widget.html                # Interactive widget (Skybridge)
config/tool_references.py  # Tool names, LLM descriptions, widget direct refs
services/api_client.py     # API abstraction (mock or real HTTP)
tests/                     # pytest suite
requirements.txt
```

## Tool references (`config/tool_references.py`)

All MCP tool names, LLM descriptions, and widget **direct** tool mappings live in one file:

| Mechanism | Where | Purpose |
|-----------|--------|---------|
| **Indirect** (LLM) | `indirect_triggers`, `negative_cases`, `direct_refs` → `build_description()` | Athena chooses tools from natural-language routing hints |
| **Direct** (widget) | `get_direct_tool_names()` → injected into `widget.html` as `TOOL_REFS` | Search button and category dropdown call `callTool` with configured names |

When the topic is assigned, edit `TOPIC_LABEL`, `TOPIC_KEYWORDS`, per-tool triggers/negatives, and `WIDGET_FILTER_CATEGORIES` as needed. Restart the server so descriptions and injected JSON reload, then refresh the Athena connector.

Client-side **sort** stays in the widget (no tool call). **Category filter** uses the direct `filter` tool mapping; **search** uses the `search` mapping.

## Phase 6 — Topic assignment (later)

When the topic and public API are assigned:

1. Set `API_BASE` (and `API_KEY` if required)
2. Update endpoints and response shaping in `services/api_client.py`
3. Adjust `config/tool_references.py` (topic placeholders, indirect/direct triggers, categories)
4. Refresh the Athena connector and re-run the full test suite
