# Athena AI Challenge — Air Quality Comparison Dashboard

**→ [How to Use](HOW_TO_USE.md)** — setup, ngrok, Athena connector, widget, and troubleshooting (start here).

Python MCP server with an interactive Skybridge widget that compares **air quality across cities** by pollutant, date, and severity. Data comes from the free [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api).

For Athena platform questions, use the **athena-knowledge** skill (`.cursor/skills/athena-knowledge/SKILL.md`).

## Stack

- **Python 3.10+** (3.13 recommended)
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (`mcp[cli]`)
- [httpx](https://www.python-httpx.org/) for API calls
- [uvicorn](https://www.uvicorn.org/) ASGI server
- Vanilla JS widget (`widget.html`) served as `text/html+skybridge`

## Prerequisites

| Tool | Required | Notes |
|------|----------|-------|
| **Python 3.10+** | Yes | 3.13 recommended; use a virtualenv (see Setup) |
| **ngrok** | Yes (for Athena tunnel) | Expose port `8000` to the public internet |
| **Node.js / npm** | Optional | For MCP Inspector via `npx` only |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | HTTP port for the MCP server |
| `API_BASE` | `https://air-quality.api.open-meteo.com` | Open-Meteo Air Quality API base |
| `API_KEY` | _(empty)_ | Optional bearer token (not required for Open-Meteo) |
| `AQ_USE_MOCK` | _(unset)_ | Set to `1` to use offline fixture data |

When `API_BASE` contains `example.com` or `AQ_USE_MOCK=1`, the server uses fixture readings (used by `pytest`).

## Run locally

```bash
source .venv/bin/activate
python server.py
```

```bash
curl http://localhost:8000/
# MCP server running
```

## Test

```bash
pytest -v
```

## Supported cities

London, Paris, Berlin, Delhi, Beijing, Los Angeles (hardcoded coordinates — no geocoding API).

## Example Athena prompts

- “Compare PM2.5 in London and Delhi today”
- “Show air quality for Paris and Berlin”
- “Switch to ozone for London and Los Angeles”
- “Show only unhealthy cities”

## Widget interactions

1. **Compare** — `fetch_data` with cities, pollutant, date
2. **Pollutant dropdown** — `filter_data` (PM2.5, PM10, ozone)
3. **Minimum severity** — `filter_data`
4. **Date** — `filter_data` when results exist
5. **Click a city card** — detail panel (client-side)
6. **Sort** — client-side by pollution level or city name

## Connect to Athena

1. `ngrok http 8000` → use `https://<host>/mcp`
2. [Create agent](https://athenachat.bot/chatbot/mybots/create) with suggested system prompt:

   > You help users compare air quality across cities. Use fetch_data for new comparisons; use filter_data when refining pollutant, date, or severity. Always render results in the widget.

3. After code changes: **Settings → Connectors → Refresh**

## Project layout

```text
server.py                  # FastMCP server, tools, resource, HTTP/CORS
widget.html                # Air quality comparison widget (Skybridge)
config/tool_references.py  # Tool names, LLM descriptions, widget direct refs
services/api_client.py     # Open-Meteo client + severity mapping
tests/
```
