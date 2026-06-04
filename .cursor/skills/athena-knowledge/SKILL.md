---
name: athena-knowledge
description: >-
  Answers questions about the Athena AI Agent SDK, MCP connectors, Skybridge widgets,
  tool metadata, deployment, and connector refresh using official athenachat.bot docs.
  Use when the user or another agent asks about Athena platform behavior, says "ask athena
  knowledge", "athena docs", "how does athena work", "connector refresh", "skybridge widget",
  "window.openai", "tool metadata", "outputTemplate", "widgetAccessible", "callTool loop",
  "ngrok deployment", "MCP Inspector", "FastMCP", or needs help wiring this repo's server/widget.
---

# Athena Knowledge Agent

Authoritative summary of [Athena Agent SDK docs](https://athenachat.bot/docs). When answering, cite official URLs and map answers to this repo where relevant.

**Official docs:** https://athenachat.bot/docs (single-page; section anchors only — no separate `/docs/*` subpages as of 2026-06)

**Agent creation:** https://athenachat.bot/chatbot/mybots/create  
**My agents:** https://athenachat.bot/chatbot/mybots  
**OAuth callback (if implementing auth):** `https://athenachat.bot/chatbot/mcp/oauth/callback`

---

## How Athena Apps Work

An Athena app = **MCP server** + **Skybridge widget** + **model routing**.

| Layer | Role |
|-------|------|
| MCP server | Defines tools, returns `structuredContent` + optional `_meta`, registers HTML resource |
| Widget (iframe) | Reads `window.openai.toolOutput`, calls tools via `window.openai.callTool`, persists UI via `setWidgetState` |
| Athena model | Chooses tools from metadata/descriptions; narrates from `structuredContent` |

**Architecture flow:** user prompt → model calls tool → server returns data + template URI → Athena loads `text/html+skybridge` resource → injects payload into `window.openai` → widget renders; widget may call tools again.

**Transport:** Streamable HTTP recommended (`/mcp` endpoint). HTTPS required in production (use ngrok locally).

---

## MCP Setup Checklist

- [ ] MCP server exposes `/mcp` over Streamable HTTP (GET/POST/DELETE + OPTIONS preflight)
- [ ] CORS headers: `Access-Control-Allow-Origin: *`, allow `content-type` and `mcp-session-id`, expose `Mcp-Session-Id`
- [ ] Health route at `/` for sanity checks
- [ ] Register at least one resource with `mimeType: "text/html+skybridge"`
- [ ] Each UI tool sets `_meta["openai/outputTemplate"]` to that resource URI
- [ ] Tool responses include `structuredContent` (model + widget) and optional `content` (narration)
- [ ] Test locally with MCP Inspector before connecting Athena
- [ ] Expose via HTTPS (`ngrok http <port>`) — connector URL must end in `/mcp`
- [ ] Create agent at https://athenachat.bot/chatbot/mybots/create with ngrok MCP URL

**MCP Inspector:**

```bash
npx @modelcontextprotocol/inspector@latest \
  --server-url http://localhost:8000/mcp \
  --transport http
```

Verify: tools listed, resource loads as `text/html+skybridge`, `structuredContent` shape matches widget expectations.

---

## Agent Creation Checklist

1. Sign up / sign in at https://athenachat.bot/chatbot/mybots/create
2. Fill name, description, system prompt
3. Add MCP connector URL: `https://<tunnel-host>/mcp` (not bare root)
4. Save and open agent from https://athenachat.bot/chatbot/mybots → "Go to Agent"
5. Test prompts that should trigger your primary tool
6. After any server/metadata change → **Settings → Connectors → Refresh** (see Connector Refresh)

---

## Widget / Skybridge

Skybridge = Athena's sandboxed iframe runtime for MCP-served HTML.

**Resource registration requirements:**

- URI pattern: `ui://widget/<name>.html`
- `mimeType`: **`text/html+skybridge`** (required — without it, `window.openai` is undefined)
- Optional resource `_meta`:
  - `openai/widgetPrefersBorder`: boolean — bordered card
  - `openai/widgetCSP`: `{ connect_domains, resource_domains, frame_domains }` for fetch/CSP allowlists
  - `openai/widgetDescription`: summary for the model when component loads

**Display modes:** inline (default), inline card, carousel, fullscreen, picture-in-picture — request via `window.openai.requestDisplayMode(...)`.

**Widget design rules (high level):** extract atomic actions (don't port full website); optimize for conversation; max ~2 primary CTAs per card; no nested scrolling; responsive iframe layouts.

---

## `window.openai` Bridge

Injected by Athena only for `text/html+skybridge` templates.

| API | Purpose |
|-----|---------|
| `toolOutput` | Initial render data from tool `structuredContent` |
| `toolInput` | Args passed to the tool that produced this widget |
| `widgetState` / `setWidgetState(state)` | Persist UI state for this widget instance (keep <4k tokens; sent to model) |
| `callTool(name, args)` | Widget-initiated MCP tool call; returns fresh structured content |
| `sendFollowUpMessage(text)` | Post user-authored follow-up into chat |
| `requestDisplayMode`, `requestModal`, `notifyIntrinsicHeight`, `openExternal` | Layout / navigation |
| `theme`, `displayMode`, `maxHeight`, `safeArea`, `locale`, `userAgent`, `view` | Host context |

**Events:** listen for `openai:set_globals` — `event.detail.globals` updates `toolOutput`, `widgetState`, etc.

**callTool loop pattern:**

1. Widget reads `window.openai.toolOutput` on load
2. User action → `await window.openai.callTool(toolName, payload)`
3. Update UI from `response.structuredContent`
4. Call `setWidgetState` after meaningful interactions
5. Server must set `_meta["openai/widgetAccessible"]: true` on tools the widget may call

**CSP / sandbox:** no `alert`/`prompt`/`confirm`/`clipboard`; fetch only to allowed domains; subframes blocked unless `frame_domains` set.

---

## Tool Metadata

Discovery is **metadata-driven** — the model picks tools from names, descriptions, and annotations.

### Required tool fields

- **name** — action-oriented, unique in connector
- **title** — human label
- **description** — start with **"Use this when…"**; include **negative cases** ("Do not use for…")
- **inputSchema** — explicit types, enums, defaults
- **annotations (required):**
  - `readOnlyHint` — true if no mutations
  - `destructiveHint` — true if deletes/overwrites data
  - `openWorldHint` — true if publishes or reaches outside user account

### `_meta` on tool descriptor

| Key | Purpose |
|-----|---------|
| `openai/outputTemplate` | URI of Skybridge HTML resource |
| `openai/widgetAccessible` | `true` to allow widget `callTool` (default false) |
| `openai/visibility` | `"public"` (default) or `"private"` (hide from model, widget-only) |
| `openai/toolInvocation/invoking` | Short in-progress status |
| `openai/toolInvocation/invoked` | Short completed status |
| `openai/fileParams` | Input fields that are file uploads |

### Tool response shape

```json
{
  "content": [{ "type": "text", "text": "narration for model" }],
  "structuredContent": { "items": [] },
  "_meta": { }
}
```

- **`structuredContent`** — concise JSON for model + widget (keep tight; model reads verbatim)
- **`content`** — optional narration
- **`_meta` on result** — widget-only; never reaches model

### PDF attachments (`_athenaAttachments`)

For chat agents with MCP URL in agent settings, Athena may inject `_athenaAttachments` (base64 PDFs, current turn only) into tool calls. Declare as optional input if your validator rejects unknown fields. Oversized PDFs omitted server-side.

### Metadata optimization workflow

1. Build golden prompt set: direct, indirect, and **negative** prompts
2. Tune one metadata field at a time
3. Test in developer mode; track precision/recall
4. Use "Use this when…" / "Do not use for…" phrasing (matches this repo's `config/tool_references.py` pattern)

---

## Deployment / ngrok

```bash
python server.py          # default PORT=8000
ngrok http 8000           # → https://xxxx.ngrok.app
# Connector URL: https://xxxx.ngrok.app/mcp
```

- Athena requires **HTTPS**
- Restart ngrok if tunnel times out; confirm local server up first
- Production: stable host with health checks; ensure proxies allow streaming HTTP/SSE

---

## Connector Refresh

**When:** after changing tool names, descriptions, `_meta`, annotations, resource HTML, or CORS.

**Steps:**

1. Save code changes
2. Restart MCP server (and ngrok if URL changed)
3. Re-verify in MCP Inspector
4. In Athena: **Settings → Connectors → Refresh** on your connector
5. Re-test in chat

**Stale connector metadata** is the #1 cause of missing tools, wrong descriptions, and broken widget rendering.

---

## Common Pitfalls

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `window.openai` undefined | Wrong MIME type | Use `text/html+skybridge` on resource |
| Widget blank / no render | Missing or wrong `outputTemplate` | Point tool `_meta` to registered resource URI |
| Widget can't call tools | `widgetAccessible` false/missing | Set `openai/widgetAccessible: true` on callable tools |
| Tool never triggers | Weak descriptions | "Use this when…" + negative cases; refresh connector |
| Wrong tool selected | Overlapping tools | Split tools; add "Do not use for…" |
| CSP / fetch failures | Blocked domain | Add `openai/widgetCSP.connect_domains` |
| No tools in Athena | Stale connector or wrong URL | Refresh connector; URL must be `…/mcp` |
| Structured content only, no UI | No template link | Add `outputTemplate` + skybridge resource |
| OAuth loop | Bad token / missing WWW-Authenticate | Verify OAuth 2.1 + PKCE; callback URL above |

---

## This Project ↔ Athena Concepts

| Athena concept | This repo |
|----------------|-----------|
| MCP server (Streamable HTTP) | `server.py` — FastMCP + Starlette, `/mcp` via `mcp.streamable_http_app()` |
| Skybridge widget resource | `@mcp.resource("ui://widget/main.html")` → `text/html+skybridge`, HTML from `widget.html` |
| Tool metadata | `config/tool_references.py` — `build_description()`, `_tool_meta()`, annotations |
| LLM routing (indirect) | `indirect_triggers`, `negative_cases`, `direct_refs` in `TOOLS` |
| Widget direct `callTool` | `get_direct_tool_names()` → injected as `__TOOL_REFS_JSON__` in widget |
| `outputTemplate` | `ui://widget/main.html` (`OUTPUT_TEMPLATE` constant) |
| `widgetAccessible` | `True` in `_tool_meta()` for `fetch_data` and `filter_data` |
| `structuredContent` | `_tool_response()` returns `{ items, query, … }` |
| CORS + OPTIONS | `AlwaysCORSMiddleware`, `MCPAppWrapper`, `CORS_HEADERS` |
| Indirect vs direct tools | **Indirect:** model chooses via descriptions. **Direct:** search → `fetch_data`, category filter → `filter_data`. Client sort stays in widget (no tool). |

**Local run:** `python server.py` → http://localhost:8000/mcp  
**Tests:** `pytest -v` (server, widget, tool_references)

When topic/API changes (Phase 6): edit `config/tool_references.py` + `services/api_client.py`, restart server, refresh connector.

---

## State Management (Official Guidance)

| State type | Where | Examples |
|------------|-------|----------|
| Business (authoritative) | MCP server / backend | Items, tickets, records |
| UI (ephemeral) | Widget via `setWidgetState` | Selected row, sort, panel open |
| Cross-session | Your backend + OAuth | Saved prefs, workspaces |

Widgets are **message-scoped** — new tool response = new widget instance. Don't use `localStorage` for core state.

---

## Authentication (When Needed)

Private data → OAuth 2.1 per MCP auth spec. Callback: `https://athenachat.bot/chatbot/mcp/oauth/callback`. Verify tokens on every tool call; 401 + `WWW-Authenticate` to re-trigger flow.

---

## UX / Publishing Checklist (Abbreviated)

Before publishing, confirm: conversational value, atomic model-friendly tools, in-chat task completion, fast responses, discoverable prompts. Avoid long-form static content, multi-tab navigation inside cards, duplicating Athena UI.

---

## Quick Answer Template

When another agent asks an Athena question:

1. State the relevant docs section (link https://athenachat.bot/docs)
2. Give the concrete requirement (MIME type, metadata key, refresh step, etc.)
3. Map to this repo file if applicable
4. Include actionable checklist item if they're debugging

For extended lookup tables, see [docs/athena-reference.md](../../../docs/athena-reference.md).
