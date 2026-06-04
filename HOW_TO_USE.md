# How to Use — Air Quality Comparison Dashboard

Step-by-step guide to run, test, expose, and connect this air quality MCP server to [Athena](https://athenachat.bot). For stack details and file layout, see [README.md](README.md).

**Video walkthrough:** [demo/athena-agent-demo.mp4](demo/athena-agent-demo.mp4) · **Re-record:** `./demo/record-demo.sh` (see [demo/README.md](demo/README.md))

---

## Quick start

**Use the project venv** — run `source .venv/bin/activate` or `./run.sh`; using conda `(base)` Python without the venv will fail with `ModuleNotFoundError: No module named 'mcp'`.

From the repository root:

```bash
# 1. Virtual environment (Python 3.10+, 3.13 recommended)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Dependencies
pip install -r requirements.txt

# 3. Verify everything works
pytest -v

# 4. Start the MCP server (default port 8000)
python server.py
```

You should see:

```text
MCP server ready at http://localhost:8000/mcp
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `8000` | HTTP port |
| `API_BASE` | `https://air-quality.api.open-meteo.com` | Open-Meteo Air Quality API |
| `API_KEY` | _(empty)_ | Optional bearer token (not required) |
| `AQ_USE_MOCK` | _(unset)_ | Set to `1` for offline fixture data |

While `API_BASE` contains `example.com` or `AQ_USE_MOCK=1`, the server returns **fixture readings** — no external API calls.

---

## Local testing

### Health check

With the server running:

```bash
curl http://localhost:8000/
# MCP server running
```

### MCP Inspector

Requires Node.js/npm for `npx` only:

```bash
npx @modelcontextprotocol/inspector@latest \
  --server-url http://localhost:8000/mcp \
  --transport http
```

Confirm in the Inspector:

1. **Tools:** `fetch_data`, `filter_data`
2. **Resource:** `ui://widget/main.html` with mime type `text/html+skybridge`
3. **`fetch_data`** returns `structuredContent.items` (array of records)

---

## Expose with ngrok

Athena requires **HTTPS** and the MCP path **`/mcp`**.

### Install ngrok

**Option A — Homebrew (macOS):**

```bash
brew install ngrok/ngrok/ngrok
```

**Option B — Binary in this repo (no Homebrew):**

```bash
mkdir -p .local/bin
curl -fsSL -o /tmp/ngrok.zip https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip
unzip -o /tmp/ngrok.zip -d .local/bin
export PATH="$(pwd)/.local/bin:$PATH"
```

Add that `export PATH=...` line to your shell profile if you use the repo-local binary often. `.local/` is gitignored.

### One-time authentication

1. Sign up at [ngrok.com](https://ngrok.com/)
2. Run: `ngrok config add-authtoken <your-token>`

### Start the tunnel

In a **second terminal** (server still running on 8000):

```bash
ngrok http 8000
```

Copy the **HTTPS** forwarding URL and append **`/mcp`**. Example:

```text
https://abcd-12-34-56.ngrok-free.app/mcp
```

Do **not** use the bare ngrok root URL — Athena expects the Streamable HTTP MCP endpoint.

---

## Connect to Athena

1. Open [Create agent](https://athenachat.bot/chatbot/mybots/create)
2. Fill name, description, and system prompt
3. Under **Connectors**, paste your ngrok MCP URL (must end with `/mcp`)
4. Save, then open the agent from [My bots](https://athenachat.bot/chatbot/mybots) → **Go to Agent**

### Suggested system prompt

> You help users compare air quality across cities. Use fetch_data for new comparisons; use filter_data when refining pollutant, date, or severity. Always render results in the widget.

### Test prompts (should trigger `fetch_data`)

- “Compare PM2.5 in London and Delhi today”
- “Show air quality for Paris and Berlin”
- “How polluted is Beijing compared to Los Angeles?”

After data loads, prompts like “show only unhealthy cities” or “switch to ozone” may route to `filter_data`. The widget can also change pollutant and severity via direct `callTool` without the model.

---

## Using the widget

When `fetch_data` runs, Athena loads the Skybridge widget (`widget.html`).

| Control | Behavior |
|---------|----------|
| **Compare** | Calls `fetch_data` with cities, pollutant, and date |
| **Pollutant** | Calls `filter_data` (PM2.5, PM10, ozone) |
| **Minimum severity** | Calls `filter_data` |
| **Date** | Calls `filter_data` when results exist |
| **Sort** | Client-side by pollution level or city name |
| **City cards** | Comparison bars; click for **detail panel** |
| **Empty state** | Shown when no readings match filters |

Widget state (last query, sort keys) persists via `setWidgetState` for the session.

---

## Indirect vs direct tool references

All routing configuration lives in **`config/tool_references.py`**.

### Indirect (LLM / Athena model)

The model reads each tool’s **description**, built from:

- `indirect_triggers` — phrases starting with “Use this when…”
- `negative_cases` — “Do not use for…”
- `direct_refs` — cross-tool hints (e.g. use `filter_data` instead)

Edit `TOPIC_LABEL`, `TOPIC_KEYWORDS`, and per-tool triggers/negatives in `config/tool_references.py` if you extend the domain.

### Direct (widget UI)

`get_direct_tool_names()` maps UI actions to MCP tool names (injected into the widget as `TOOL_REFS`):

| UI action | MCP tool |
|-----------|----------|
| Compare button | `fetch_data` |
| Pollutant / severity / date | `filter_data` |

If you **rename tools**, update `TOOLS[*]["name"]`, server handlers, **and** this map together.

**Sort** never uses a tool — only JavaScript in the widget.

---

## Connector refresh after metadata changes

After changing tool names, descriptions, `_meta`, resource URI, or widget HTML injection:

1. Save files and **restart** `python server.py`
2. Restart **ngrok** if the tunnel died
3. In Athena: **Settings → Connectors → Refresh**
4. Re-check in MCP Inspector before testing in chat

Skipping refresh often causes missing tools, old descriptions, or a broken widget template.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Wrong Python / import errors | Use `.venv`: `source .venv/bin/activate` and `which python` → should point inside `.venv` |
| `pytest` not found or wrong version | Run `.venv/bin/pytest -v` or activate venv first |
| Athena shows no tools | Connector URL must end with `/mcp`; refresh connector after server restart |
| Stale tool list or widget | Settings → Connectors → **Refresh** |
| ngrok command not found | `export PATH="$(pwd)/.local/bin:$PATH"` or install via Homebrew |
| CORS / MCP session errors | Confirm server logs show port 8000; use HTTPS ngrok URL, not `http://localhost` in Athena |
| `POST /mcp` **421**, `Invalid Host header: …ngrok…` | Restart server after pulling latest `server.py` (FastMCP must use `host="0.0.0.0"`). Or set `MCP_ALLOWED_HOSTS=your-subdomain.ngrok-free.dev` before `python server.py` |
| Widget missing in Athena | In MCP Inspector: `resources/list` must show `text/html+skybridge`; `tools/call` must return top-level `structuredContent.items`. Restart server, then **Connectors → Refresh** |
| Always fixture data | Unset `AQ_USE_MOCK` and use default `API_BASE` (Open-Meteo) |
| Real API errors | Check network; verify city names match the built-in catalog in `services/api_client.py` |

Platform-specific behavior: `.cursor/skills/athena-knowledge/SKILL.md` and [Athena docs](https://athenachat.bot/docs).

---

## Demo video and scripts

| Artifact | Description |
|----------|-------------|
| [demo/athena-agent-demo.mp4](demo/athena-agent-demo.mp4) | Recorded pytest, server, MCP HTTP, and Athena setup notes |
| [demo/record-demo.sh](demo/record-demo.sh) | Re-capture terminal output and rebuild the MP4 |
| [demo/mcp-http-demo.py](demo/mcp-http-demo.py) | Headless MCP client (no browser) |

Full segment breakdown: [demo/README.md](demo/README.md).
