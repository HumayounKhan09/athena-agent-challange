"""Tests for services/api_client.py."""

from __future__ import annotations

import httpx
import pytest

import services.api_client as api_client
from services.api_client import (
    fetch_items,
    filter_items,
    match_cities,
    severity_for_value,
    shape_item,
)


@pytest.fixture(autouse=True)
def reset_api_base(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://api.example.com")
    monkeypatch.setattr(api_client, "API_KEY", "")
    monkeypatch.delenv("AQ_USE_MOCK", raising=False)


@pytest.mark.asyncio
async def test_fetch_items_uses_mock_catalog():
    items = await fetch_items(query="london paris", limit=10)
    assert len(items) == 2
    names = {item["name"] for item in items}
    assert "London" in names
    assert "Paris" in names


@pytest.mark.asyncio
async def test_fetch_items_default_cities_without_match():
    items = await fetch_items(query="", limit=10)
    assert len(items) >= 3


@pytest.mark.asyncio
async def test_filter_items_mock_min_severity():
    items = await filter_items(
        query="",
        min_severity="unhealthy",
        sort_by="value_desc",
    )
    assert items
    assert all(
        api_client._severity_rank(item["category"]) >= api_client._severity_rank("unhealthy")
        for item in items
    )


@pytest.mark.asyncio
async def test_filter_items_sort_by_value_desc():
    items = await filter_items(query="", sort_by="value_desc")
    values = [float(item["value"]) for item in items]
    assert values == sorted(values, reverse=True)


def test_match_cities():
    assert "london" in match_cities("Compare London and Delhi")
    assert "delhi" in match_cities("Delhi air quality")


def test_severity_for_pm25():
    assert severity_for_value("pm2_5", 10.0) == "good"
    assert severity_for_value("pm2_5", 25.0) == "moderate"
    assert severity_for_value("pm2_5", 45.0) == "unhealthy"
    assert severity_for_value("pm2_5", 60.0) == "very_unhealthy"


@pytest.mark.asyncio
async def test_shape_item_normalizes_fields():
    shaped = shape_item(
        {
            "city_key": "paris",
            "name": "Paris",
            "pollutant": "pm2_5",
            "value": 22.5,
            "category": "moderate",
            "date": "2026-06-04",
        }
    )
    assert shaped["name"] == "Paris"
    assert shaped["value"] == 22.5
    assert shaped["category"] == "moderate"
    assert "PM2.5" in shaped["description"]


@pytest.mark.asyncio
async def test_fetch_items_open_meteo_success(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://air-quality.api.open-meteo.com")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert "air-quality" in str(request.url)
        return httpx.Response(
            200,
            json={
                "hourly": {
                    "pm2_5": [12.0, 14.0, 16.0],
                }
            },
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)
    items = await fetch_items(query="london", limit=5, pollutant="pm2_5", date_str="2026-06-04")
    assert len(items) == 1
    assert items[0]["name"] == "London"
    assert items[0]["value"] == 14.0


@pytest.mark.asyncio
async def test_fetch_items_real_api_404(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://air-quality.api.open-meteo.com")
    real_async_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)

    items = await fetch_items(query="london", limit=5)
    assert items == []


@pytest.mark.asyncio
async def test_fetch_items_real_api_timeout_returns_empty(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://air-quality.api.open-meteo.com")
    real_async_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)

    items = await fetch_items(query="london", limit=5)
    assert items == []
