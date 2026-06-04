"""Tests for services/api_client.py."""

from __future__ import annotations

import httpx
import pytest

import services.api_client as api_client
from services.api_client import (
    _daily_averages_by_date,
    _date_range_unavailable_reason,
    _open_meteo_fetch_params,
    _pick_daily_average,
    _resolve_item_date,
    _uses_explicit_date_range,
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
    assert "delhi" in match_cities("Compare PM2.5 in London and Delhi today")
    assert "delhi" in match_cities("Delhi air quality")


def test_resolve_item_date_today():
    assert _resolve_item_date("today") == api_client._today_iso()
    assert _resolve_item_date("  2026-06-04  ") == "2026-06-04"
    assert _resolve_item_date("not-a-date") == api_client._today_iso()


def test_uses_explicit_date_range():
    assert _uses_explicit_date_range("2026-05-01") is True
    assert _uses_explicit_date_range("today") is False
    assert _uses_explicit_date_range("") is False


def test_open_meteo_params_explicit_date():
    meta = {"latitude": 51.5, "longitude": -0.1}
    params = _open_meteo_fetch_params(
        meta, "pm2_5", target_date="2026-05-01", use_date_range=True
    )
    assert params["start_date"] == "2026-05-01"
    assert params["end_date"] == "2026-05-01"
    assert "past_days" not in params


def test_open_meteo_params_rolling_window():
    meta = {"latitude": 51.5, "longitude": -0.1}
    params = _open_meteo_fetch_params(
        meta, "pm2_5", target_date="2026-06-04", use_date_range=False
    )
    assert params["past_days"] == 2
    assert params["forecast_days"] == 5
    assert "start_date" not in params


def test_date_range_unavailable_reason_future():
    reason = _date_range_unavailable_reason("2099-01-01")
    assert reason is not None
    assert "forecast" in reason.lower()


def test_date_range_unavailable_reason_too_old():
    reason = _date_range_unavailable_reason("2020-01-01")
    assert reason is not None
    assert "2022" in reason


def test_pick_daily_average_fallback():
    averages = {"2026-06-02": 10.0, "2026-06-03": 12.0}
    avg, used, fallback = _pick_daily_average(averages, "2026-06-04")
    assert fallback is True
    assert used == "2026-06-03"
    assert avg == 12.0


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
        assert "start_date=2026-06-04" in str(request.url)
        assert "end_date=2026-06-04" in str(request.url)
        return httpx.Response(
            200,
            json={
                "hourly": {
                    "time": [
                        "2026-06-04T00:00",
                        "2026-06-04T01:00",
                        "2026-06-04T02:00",
                    ],
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


@pytest.mark.asyncio
async def test_fetch_items_open_meteo_date_today(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://air-quality.api.open-meteo.com")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "hourly": {
                    "time": ["2026-06-04T10:00", "2026-06-04T11:00"],
                    "pm2_5": [20.0, 22.0],
                }
            },
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)
    items = await fetch_items(query="london delhi", limit=5, date_str="today")
    assert len(items) == 2


@pytest.mark.asyncio
async def test_fetch_items_open_meteo_fallback_previous_day(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://air-quality.api.open-meteo.com")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert "past_days" in str(request.url)
        return httpx.Response(
            200,
            json={
                "hourly": {
                    "time": ["2026-06-03T12:00", "2026-06-03T13:00"],
                    "pm2_5": [8.0, 10.0],
                }
            },
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)
    items = await fetch_items(query="london", limit=5, date_str="today")
    assert len(items) == 1
    assert items[0]["date"] == "2026-06-03"
    assert "No data for" in items[0]["description"]


@pytest.mark.asyncio
async def test_fetch_items_open_meteo_historical_date_strict(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://air-quality.api.open-meteo.com")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert "start_date=2026-05-01" in str(request.url)
        return httpx.Response(
            200,
            json={
                "hourly": {
                    "time": ["2026-05-01T08:00", "2026-05-01T09:00"],
                    "pm2_5": [11.0, 13.0],
                }
            },
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)
    items = await fetch_items(query="london", limit=5, date_str="2026-05-01")
    assert len(items) == 1
    assert items[0]["date"] == "2026-05-01"
    assert items[0]["value"] == 12.0


@pytest.mark.asyncio
async def test_fetch_items_open_meteo_explicit_date_no_fallback(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE", "https://air-quality.api.open-meteo.com")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert "start_date=2026-06-04" in str(request.url)
        return httpx.Response(
            200,
            json={
                "hourly": {
                    "time": ["2026-06-03T12:00", "2026-06-03T13:00"],
                    "pm2_5": [8.0, 10.0],
                }
            },
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(api_client.httpx, "AsyncClient", client_factory)
    items = await fetch_items(query="london", limit=5, date_str="2026-06-04")
    assert items == []


def test_daily_averages_by_date_groups_hours():
    hourly = {
        "time": ["2026-06-04T00:00", "2026-06-04T01:00", "2026-06-03T23:00"],
        "pm2_5": [10.0, 14.0, 30.0],
    }
    assert _daily_averages_by_date(hourly, "pm2_5") == {
        "2026-06-04": 12.0,
        "2026-06-03": 30.0,
    }
