"""Shared pytest fixtures for Athena MCP challenge tests."""

from pathlib import Path

import httpx
import pytest

import services.api_client as api_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def mock_air_quality_api(monkeypatch):
    """Keep tests offline with fixture air-quality readings."""
    monkeypatch.setattr(api_client, "API_BASE", "https://api.example.com")
    monkeypatch.setattr(api_client, "API_KEY", "")
    monkeypatch.delenv("AQ_USE_MOCK", raising=False)


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def widget_html(project_root: Path) -> str:
    return (project_root / "widget.html").read_text(encoding="utf-8")


@pytest.fixture
def widget_html_served() -> str:
    """Widget HTML after server injects direct tool refs (production shape)."""
    from server import WIDGET_HTML

    return WIDGET_HTML


@pytest.fixture
async def app_client():
    """Async httpx client bound to the Starlette app (no live server)."""
    from server import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
