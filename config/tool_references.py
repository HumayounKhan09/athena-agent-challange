"""
Single source of truth for MCP tool names, LLM descriptions, and widget direct refs.
"""

from __future__ import annotations

TOPIC_LABEL = "air quality"
TOPIC_KEYWORDS = ["air quality", "AQI", "pollution", "PM2.5", "cities", "compare"]

# Pollutants for widget category-filter (MCP pollutant param).
WIDGET_POLLUTANTS = ["", "pm2_5", "pm10", "ozone"]
WIDGET_SEVERITY_LEVELS = ["", "good", "moderate", "unhealthy", "very_unhealthy"]

TOOLS: dict[str, dict] = {
    "fetch": {
        "name": "fetch_data",
        "title": "Fetch Air Quality",
        "indirect_triggers": [
            "Use this when the user wants to compare air quality across cities "
            f"or asks about {TOPIC_LABEL}, {TOPIC_KEYWORDS[0]}, or pollution levels.",
            "Use this when the user names cities (e.g. London, Paris, Delhi) and wants "
            "a new comparison by pollutant or date.",
        ],
        "negative_cases": [
            "Do not use when the user only changes pollutant, severity, or date on "
            "results already shown in the widget — use filter_data instead.",
            "Do not use for sorting or opening detail on loaded results without new data.",
        ],
        "direct_refs": [
            "For refining pollutant, minimum severity, or date on loaded results, use filter_data instead.",
        ],
        "invoking": "Fetching air quality…",
        "invoked": "Air quality loaded",
    },
    "filter": {
        "name": "filter_data",
        "title": "Filter Air Quality",
        "indirect_triggers": [
            "Use this when the user wants to change pollutant (PM2.5, PM10, ozone), "
            "date, or minimum severity on comparison results already in the widget.",
            "Use this when the user asks to show only unhealthy cities or switch metrics "
            "on an existing comparison.",
        ],
        "negative_cases": [
            "Do not use for a brand-new city comparison with no prior context — use fetch_data.",
            "Do not use when the user only sorts or inspects a city card client-side.",
        ],
        "direct_refs": [
            "Requires context from a previous fetch_data call or loaded widget data.",
            "For a new set of cities from scratch, use fetch_data instead.",
        ],
        "invoking": "Updating comparison…",
        "invoked": "Comparison updated",
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
