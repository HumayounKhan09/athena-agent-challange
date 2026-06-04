"""
Single source of truth for MCP tool names, LLM descriptions, and widget direct refs.

Adjusting when the topic is assigned (Phase 6)
-----------------------------------------------
1. Set TOPIC_LABEL and TOPIC_KEYWORDS to match the domain (e.g. "clinical trials").
2. For each tool key in TOOLS, update:
   - indirect_triggers: natural-language phrases the model should match (each must start
     with "Use this when…"); these become the LLM routing hints via build_description().
   - negative_cases: when the model should *not* pick this tool.
   - direct_refs: explicit cross-tool guidance (e.g. "use filter_data instead").
3. Rename tool ``name`` only if you also update server handlers and get_direct_tool_names()
   so the widget's direct callTool keys stay in sync.
4. Update WIDGET_FILTER_CATEGORIES when the API exposes new category values.
5. Restart the server and refresh the Athena connector so descriptions and widget injection
   reload.

Indirect vs direct triggers
---------------------------
- **Indirect** (LLM): composed into tool ``description`` from indirect_triggers,
  negative_cases, and direct_refs — the model reads these when choosing tools.
- **Direct** (widget): get_direct_tool_names() maps UI actions to MCP tool names; the widget
  calls callTool with those names (search button → fetch tool, category dropdown → filter tool).
  Client-side sort stays in the widget and does not call a tool.
"""

from __future__ import annotations

# ── Topic placeholders (swap in Phase 6) ─────────────────────────────────────
TOPIC_LABEL = "data"
TOPIC_KEYWORDS = ["data", "items", "records", "search"]

# Categories shown in the widget category filter (server-side filter tool).
WIDGET_FILTER_CATEGORIES = ["", "general", "research", "reports"]

# ── Per-tool configuration ───────────────────────────────────────────────────
TOOLS: dict[str, dict] = {
    "fetch": {
        "name": "fetch_data",
        "title": "Fetch Data",
        "indirect_triggers": [
            "Use this when the user asks about "
            f"{TOPIC_LABEL} or wants to search for {TOPIC_KEYWORDS[0]}.",
            "Use this when the user wants to look up or load items into the widget.",
        ],
        "negative_cases": [
            "Do not use for filtering, sorting, or narrowing results already shown in the widget.",
            "Do not use when the user only wants to change category or sort on loaded results.",
        ],
        "direct_refs": [
            'For filtering already-loaded results, use filter_data instead.',
        ],
        "invoking": "Fetching data…",
        "invoked": "Data loaded",
    },
    "filter": {
        "name": "filter_data",
        "title": "Filter Data",
        "indirect_triggers": [
            "Use this when the user wants to filter, sort, or narrow down results "
            "already shown in the widget.",
            "Use this when the user asks to restrict results by category or refine a list.",
        ],
        "negative_cases": [
            "Do not use for an initial search or when no results have been loaded yet.",
            "Do not use when the user is starting a new query from scratch — use fetch_data.",
        ],
        "direct_refs": [
            "Requires a previous fetch_data call so the widget has context.",
            "For a new search term, use fetch_data instead.",
        ],
        "invoking": "Filtering…",
        "invoked": "Filtered",
    },
}


def build_description(tool_key: str) -> str:
    """Compose MCP tool description from indirect triggers, negatives, and cross-refs."""
    tool = TOOLS[tool_key]
    parts: list[str] = []
    parts.extend(tool["indirect_triggers"])
    parts.extend(tool["negative_cases"])
    parts.extend(tool["direct_refs"])
    return " ".join(parts)


def get_direct_tool_names() -> dict[str, str]:
    """Map widget UI action keys to MCP tool names for callTool."""
    return {
        "search": TOOLS["fetch"]["name"],
        "filter": TOOLS["filter"]["name"],
    }


def get_tool_names() -> set[str]:
    """All registered MCP tool names."""
    return {TOOLS[key]["name"] for key in TOOLS}
