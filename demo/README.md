# Athena MCP Agent Demo

This folder contains a recorded walkthrough of the Athena AI Challenge MCP server.

## Video

**File:** [`athena-agent-demo.mp4`](./athena-agent-demo.mp4)

| Segment | What is shown |
|---------|----------------|
| Intro | Project overview |
| 1 — Tests | Full `pytest -v` run (all tests passing) |
| 2 — Server | `python server.py`, health check (`GET /`), MCP probe (`GET /mcp`), MCP `initialize` |
| 3 — MCP HTTP | `tools/list` → `fetch_data`, `filter_data`; `fetch_data` returns mock widget data |
| 4 — Athena | Screenshot of [athenachat.bot agent creation](https://athenachat.bot/chatbot/mybots/create) + manual ngrok steps |
| Outro | Reproduction commands |

Terminal frames are rendered from captured transcripts in `captures/` and encoded with ffmpeg (via `imageio-ffmpeg`).

## What was captured vs blocked

| Item | Status |
|------|--------|
| pytest suite | **Captured** — all tests pass |
| Local MCP server + health | **Captured** |
| MCP HTTP (`initialize`, `tools/list`, `fetch_data`) | **Captured** |
| MCP Inspector UI | **Not captured headlessly** — run the `npx` command below in a browser |
| ngrok tunnel | **Blocked** — `ngrok` not installed in recording environment |
| Full Athena chat with MCP connector | **Blocked** — requires ngrok HTTPS URL + logged-in Athena account to register connector |

During recording, the Athena create-agent page loaded in the browser (agent type selection). Completing MCP connector registration still requires ngrok and an authenticated Athena session.

## Reproduce

```bash
# From repo root
source .venv/bin/activate
pip install -r requirements.txt
pip install imageio-ffmpeg pillow   # video build only

./demo/record-demo.sh
```

Or step by step:

```bash
source .venv/bin/activate
pytest -v
python server.py          # port 8000
curl http://localhost:8000/
python demo/mcp-http-demo.py

# Optional MCP Inspector (browser UI)
npx @modelcontextprotocol/inspector@latest \
  --server-url http://localhost:8000/mcp \
  --transport http

# Athena (manual)
ngrok http 8000
# Add https://<ngrok-host>/mcp in Athena → Settings → Connectors
```

## Artifacts

| Path | Description |
|------|-------------|
| `record-demo.sh` | End-to-end capture + video build |
| `build-demo-video.py` | Renders terminal frames → MP4 |
| `mcp-http-demo.py` | Headless MCP HTTP client demo |
| `captures/` | Raw terminal transcripts and screenshots |
