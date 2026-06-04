# Athena Platform Quick Reference

Primary knowledge source: [`.cursor/skills/athena-knowledge/SKILL.md`](../.cursor/skills/athena-knowledge/SKILL.md) — read that skill for full checklists and project mapping.

Official docs: https://athenachat.bot/docs

## Essential URLs

| URL | Use |
|-----|-----|
| https://athenachat.bot/docs | Agent SDK documentation (single page) |
| https://athenachat.bot/chatbot/mybots/create | Create agent + add MCP connector |
| https://athenachat.bot/chatbot/mybots | List agents |
| `https://athenachat.bot/chatbot/mcp/oauth/callback` | OAuth callback (auth integrations) |

## Tool `_meta` keys

| Key | Value |
|-----|-------|
| `openai/outputTemplate` | `ui://widget/...` resource URI |
| `openai/widgetAccessible` | `true` for widget `callTool` |
| `openai/visibility` | `"public"` \| `"private"` |
| `openai/toolInvocation/invoking` | In-progress label |
| `openai/toolInvocation/invoked` | Done label |

## Required annotations

`readOnlyHint`, `destructiveHint`, `openWorldHint` — all required on tool descriptors.

## Connector refresh

After tool/resource/metadata changes: restart server → MCP Inspector → **Settings → Connectors → Refresh**.

## This repo map

| File | Athena role |
|------|-------------|
| `server.py` | FastMCP server, Skybridge resource, tools, CORS |
| `widget.html` | Skybridge UI, `window.openai`, `callTool` loop |
| `config/tool_references.py` | Tool names, LLM descriptions, widget `TOOL_REFS` |
