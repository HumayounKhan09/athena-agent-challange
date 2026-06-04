"""Static contract tests for widget.html."""

from __future__ import annotations

import re

import pytest


REQUIRED_IDS = ["controls", "status", "results", "search-input", "sort-select", "search-btn"]


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


def test_fetch_data_call_payload(widget_html: str):
    assert re.search(
        r'callTool\(\s*"fetch_data"\s*,\s*\{\s*query\s*,\s*limit:\s*20\s*\}\s*\)',
        widget_html,
    )


def test_client_side_sort_without_tool_call(widget_html: str):
    assert "sortSelect.addEventListener" in widget_html
    assert "sortItems()" in widget_html
    assert 'callTool("filter_data"' not in widget_html


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
