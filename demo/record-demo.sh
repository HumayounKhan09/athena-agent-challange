#!/usr/bin/env bash
# Record demo artifacts and build demo/athena-agent-demo.mp4
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/demo"
CAPTURES="$DEMO/captures"
VENV="$ROOT/.venv/bin"

mkdir -p "$CAPTURES"
cd "$ROOT"

if [[ ! -x "$VENV/python3.13" ]]; then
  echo "Missing venv at $ROOT/.venv — run: python3 -m venv .venv && pip install -r requirements.txt" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

echo "==> Capturing pytest output"
"$VENV/pytest" -v 2>&1 | tee "$CAPTURES/01-pytest.txt"

echo "==> Starting MCP server on :8000"
"$VENV/python3.13" server.py &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT
sleep 2

{
  echo "$ $ curl -s http://localhost:8000/"
  curl -s http://localhost:8000/
  echo
  echo
  echo "$ $ curl -s http://localhost:8000/mcp"
  curl -s http://localhost:8000/mcp
  echo
  echo
  echo "$ $ curl -s -X POST http://localhost:8000/mcp (initialize)"
  curl -s -X POST http://localhost:8000/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"demo","version":"1.0"}}}' \
    -D - | head -20
} 2>&1 | tee "$CAPTURES/02-server-mcp.txt"

echo "==> MCP tools/list + fetch_data via HTTP"
"$VENV/python3.13" "$DEMO/mcp-http-demo.py" 2>&1 | tee "$CAPTURES/03-mcp-tools.txt"

{
  echo "Athena agent registration requires ngrok plus a logged-in athenachat.bot account."
  echo "ngrok was not installed in the recording environment."
  echo "Browser reached https://athenachat.bot/chatbot/mybots/create (agent type selection)."
  echo
  echo "Manual steps to finish Athena MCP connector setup:"
  echo "  1. ngrok http 8000"
  echo "  2. Open https://athenachat.bot/chatbot/mybots/create"
  echo "  3. Add MCP URL: https://<ngrok-host>/mcp"
  echo "  4. Refresh connector after metadata changes (Settings → Connectors → Refresh)"
  echo "  5. Prompt: \"fetch data for alpha\""
} | tee "$CAPTURES/04-athena-notes.txt"

if command -v npx >/dev/null 2>&1; then
  echo "==> MCP Inspector (optional — opens browser UI)"
  echo "Run: npx @modelcontextprotocol/inspector@latest --server-url http://localhost:8000/mcp --transport http"
fi

echo "==> Building demo video"
"$VENV/python3.13" "$DEMO/build-demo-video.py"

echo "Done: $DEMO/athena-agent-demo.mp4"
