"""Static contract tests for widget.html."""

from __future__ import annotations

import json
import re

import pytest

from config.tool_references import get_direct_tool_names


REQUIRED_IDS = [
    "controls",
    "status",
    "results",
    "search-input",
    "category-filter",
    "sort-select",
    "search-btn",
    "tool-refs",
]


def test_required_dom_ids(widget_html: str):
    for element_id in REQUIRED_IDS:
        assert f'id="{element_id}"' in widget_html


def test_item_card_class_present(widget_html: str):
    assert ".item-card" in widget_html
    assert 'className = "item-card"' in widget_html or "item-card" in widget_html


def test_openai_bridge_patterns(widget_html: str):
    assert "toolOutput" in widget_html
    assert "openai:set_globals" in widget_html
    assert "setWidgetState" in widget_html
    assert "callTool" in widget_html
    assert "[dev] callTool" in widget_html


def test_tool_refs_placeholder_in_source(widget_html: str):
    assert "__TOOL_REFS_JSON__" in widget_html
    assert 'id="tool-refs"' in widget_html


def test_fetch_uses_config_driven_tool_ref(widget_html_served: str):
    refs = get_direct_tool_names()
    assert json.dumps(refs) in widget_html_served
    assert re.search(
        r"callTool\(\s*TOOL_REFS\.search\s*,\s*\{\s*query\s*,\s*limit:\s*20\s*\}\s*\)",
        widget_html_served,
    )


def test_category_filter_calls_filter_tool(widget_html_served: str):
    refs = get_direct_tool_names()
    assert "category-filter" in widget_html_served
    assert re.search(
        r"callTool\(\s*TOOL_REFS\.filter\s*,",
        widget_html_served,
    )
    assert refs["filter"] in widget_html_served


def test_client_side_sort_without_filter_tool_call(widget_html_served: str):
    assert "sortSelect.addEventListener" in widget_html_served
    assert "sortItems()" in widget_html_served
    sort_handler = widget_html_served.split("sortSelect.addEventListener", 1)[1]
    assert "TOOL_REFS.filter" not in sort_handler.split("sortDirectionSelect.addEventListener", 1)[0]


def test_loading_state(widget_html: str):
    assert "isLoading" in widget_html
    assert "Loading…" in widget_html


def test_polish_features(widget_html: str):
    assert "detail-panel" in widget_html
    assert "count-badge" in widget_html
    assert 'event.key === "Enter"' in widget_html
    assert "sort-direction" in widget_html or "sortDirection" in widget_html
    assert "No results found" in widget_html


def test_no_external_dependencies(widget_html: str):
    assert "<script src=" not in widget_html
    assert '<link rel="stylesheet"' not in widget_html
