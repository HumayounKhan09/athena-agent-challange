"""Shared pytest fixtures for Athena MCP challenge tests."""

from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def widget_html(project_root: Path) -> str:
    return (project_root / "widget.html").read_text(encoding="utf-8")


@pytest.fixture
async def app_client():
    """Async httpx client bound to the Starlette app (no live server)."""
    from server import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
