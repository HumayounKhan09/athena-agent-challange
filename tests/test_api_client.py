"""Tests for services/api_client.py."""

from __future__ import annotations

import httpx
import pytest

import services.api_client as api_client
from services.api_client import fetch_items, filter_items, shape_item


@pytest.fixture(autouse=True)
def reset_api_base(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://api.example.com")
    monkeypatch.setattr(api_client, "API_KEY", "")


@pytest.mark.asyncio
async def test_fetch_items_uses_mock_catalog():
    items = await fetch_items(query="alpha", limit=10)
    assert len(items) == 1
    assert items[0]["name"] == "Alpha Project"


@pytest.mark.asyncio
async def test_filter_items_mock_category_and_sort():
    items = await filter_items(query="", category="general", sort_by="name_desc")
    assert items
    assert all(item["category"] == "general" for item in items)
    names = [item["name"] for item in items]
    assert names == sorted(names, reverse=True)


@pytest.mark.asyncio
async def test_shape_item_normalizes_fields():
    shaped = shape_item(
        {
            "id": 42,
            "title": "Example",
            "summary": "Summary text",
            "published_at": "2025-01-01",
        }
    )
    assert shaped["id"] == "42"
    assert shaped["name"] == "Example"
    assert shaped["description"] == "Summary text"
    assert shaped["date"] == "2025-01-01"


@pytest.mark.asyncio
async def test_fetch_items_real_api_success(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://real.api.test")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") is None
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "9", "name": "Live Item", "description": "From API"},
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)
    items = await fetch_items(query="live", limit=5)
    assert items[0]["name"] == "Live Item"


@pytest.mark.asyncio
async def test_fetch_items_real_api_404(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://real.api.test")
    real_async_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_items(query="missing", limit=5)


@pytest.mark.asyncio
async def test_fetch_items_real_api_timeout(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://real.api.test")
    real_async_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)

    with pytest.raises(httpx.ReadTimeout):
        await fetch_items(query="slow", limit=5)


@pytest.mark.asyncio
async def test_fetch_items_sends_api_key_header(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://real.api.test")
    monkeypatch.setattr(api_client, "API_KEY", "secret-token")
    real_async_client = httpx.AsyncClient
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"results": []})

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)
    await fetch_items(query="secure", limit=5)
    assert seen["authorization"] == "Bearer secret-token"
