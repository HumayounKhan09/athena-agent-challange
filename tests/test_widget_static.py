"""Static contract tests for widget.html."""

from __future__ import annotations

import json
import re

from config.tool_references import get_direct_tool_names


REQUIRED_IDS = [
    "controls",
    "status",
    "results",
    "search-input",
    "category-filter",
    "severity-filter",
    "date-input",
    "sort-select",
    "search-btn",
    "tool-refs",
]


def test_required_dom_ids(widget_html: str):
    for element_id in REQUIRED_IDS:
        assert f'id="{element_id}"' in widget_html


def test_item_card_class_present(widget_html: str):
    assert ".item-card" in widget_html
    assert "item-card" in widget_html


def test_comparison_bar_styles(widget_html: str):
    assert ".bar-track" in widget_html
    assert ".bar-fill" in widget_html


def test_openai_bridge_patterns(widget_html: str):
    assert "toolOutput" in widget_html
    assert "openai:set_globals" in widget_html
    assert "ui/notifications/tool-result" in widget_html
    assert "setWidgetState" in widget_html
    assert "notifyIntrinsicHeight" in widget_html
    assert "callTool" in widget_html
    assert "[dev] callTool" in widget_html


def test_tool_refs_placeholder_in_source(widget_html: str):
    assert "__TOOL_REFS_JSON__" in widget_html
    assert 'id="tool-refs"' in widget_html
    head, _ = widget_html.split("</head>", 1)
    assert 'id="tool-refs"' in head


def test_fetch_uses_config_driven_tool_ref(widget_html_served: str):
    refs = get_direct_tool_names()
    assert json.dumps(refs) in widget_html_served
    assert re.search(
        r"callTool\(\s*TOOL_REFS\.search\s*,",
        widget_html_served,
    )


def test_pollutant_and_severity_call_filter_tool(widget_html_served: str):
    refs = get_direct_tool_names()
    assert "severity-filter" in widget_html_served
    assert re.search(
        r"callTool\(\s*TOOL_REFS\.filter\s*,",
        widget_html_served,
    )
    assert refs["filter"] in widget_html_served


def test_client_side_sort_without_filter_tool_call(widget_html_served: str):
    assert "sortSelect.addEventListener" in widget_html_served
    assert "sortItems()" in widget_html_served
    sort_handler = widget_html_served.split("sortSelect.addEventListener", 1)[1]
    assert "TOOL_REFS.filter" not in sort_handler[:400]


def test_loading_state(widget_html: str):
    assert "isLoading" in widget_html
    assert "Loading…" in widget_html


def test_polish_features(widget_html: str):
    assert "<main>" in widget_html
    assert "detail-panel" in widget_html
    assert "count-badge" in widget_html
    assert 'event.key === "Enter"' in widget_html
    assert "Air Quality Comparison" in widget_html
    assert "No readings found" in widget_html
    assert "--color-surface" in widget_html


def test_no_external_dependencies(widget_html: str):
    assert "<script src=" not in widget_html
    assert '<link rel="stylesheet"' not in widget_html
