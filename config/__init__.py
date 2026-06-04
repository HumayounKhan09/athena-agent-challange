"""Configuration package for MCP tool references and air quality topic metadata."""

from config.tool_references import (
    TOPIC_KEYWORDS,
    TOPIC_LABEL,
    TOOLS,
    build_description,
    get_direct_tool_names,
)

__all__ = [
    "TOPIC_KEYWORDS",
    "TOPIC_LABEL",
    "TOOLS",
    "build_description",
    "get_direct_tool_names",
]
