"""Tests for config/tool_references.py — single source of truth for tool metadata."""

from __future__ import annotations

from config.tool_references import (
    TOOLS,
    build_description,
    get_direct_tool_names,
    get_tool_names,
)


def test_indirect_triggers_start_with_use_this_when():
    for tool_key, tool in TOOLS.items():
        for trigger in tool["indirect_triggers"]:
            assert trigger.startswith("Use this when"), (
                f"{tool_key} indirect trigger must start with 'Use this when': {trigger!r}"
            )


def test_each_tool_has_indirect_triggers():
    for tool_key, tool in TOOLS.items():
        assert tool["indirect_triggers"], f"{tool_key} must have indirect_triggers"


def test_direct_refs_mention_other_tool_names():
    fetch_name = TOOLS["fetch"]["name"]
    filter_name = TOOLS["filter"]["name"]
    fetch_desc = build_description("fetch")
    filter_desc = build_description("filter")
    assert filter_name in fetch_desc
    assert fetch_name in filter_desc


def test_build_description_composes_all_sections():
    desc = build_description("fetch")
    tool = TOOLS["fetch"]
    for phrase in tool["indirect_triggers"]:
        assert phrase in desc
    for phrase in tool["negative_cases"]:
        assert phrase in desc
    for phrase in tool["direct_refs"]:
        assert phrase in desc


def test_build_description_starts_with_use_this_when():
    for tool_key in TOOLS:
        assert build_description(tool_key).startswith("Use this when")


def test_get_direct_tool_names_maps_widget_actions():
    refs = get_direct_tool_names()
    assert refs == {"search": TOOLS["fetch"]["name"], "filter": TOOLS["filter"]["name"]}


def test_get_tool_names_matches_config():
    assert get_tool_names() == {TOOLS["fetch"]["name"], TOOLS["filter"]["name"]}


def test_tool_metadata_fields_present():
    for tool_key, tool in TOOLS.items():
        assert tool["name"]
        assert tool["title"]
        assert tool["invoking"]
        assert tool["invoked"]
        assert tool["negative_cases"]
        assert tool["direct_refs"]
