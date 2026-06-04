"""Shared pytest fixtures for Athena MCP challenge tests."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def widget_html(project_root: Path) -> str:
    return (project_root / "widget.html").read_text(encoding="utf-8")
