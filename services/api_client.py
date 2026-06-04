"""HTTP client for Open-Meteo Air Quality API."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import httpx

API_BASE = os.environ.get("API_BASE", "https://air-quality.api.open-meteo.com")
API_KEY = os.environ.get("API_KEY", "")

POLLUTANTS = ("pm2_5", "pm10", "ozone")
POLLUTANT_LABELS = {
    "pm2_5": "PM2.5",
    "pm10": "PM10",
    "ozone": "Ozone",
}
POLLUTANT_UNITS = {
    "pm2_5": "µg/m³",
    "pm10": "µg/m³",
    "ozone": "µg/m³",
}

SEVERITY_ORDER = ("good", "moderate", "unhealthy", "very_unhealthy")
SEVERITY_LABELS = {
    "good": "Good",
    "moderate": "Moderate",
    "unhealthy": "Unhealthy",
    "very_unhealthy": "Very Unhealthy",
}

# PM2.5 breakpoints (µg/m³, 24h-style bands for display)
PM25_BREAKPOINTS = (
    (12.0, "good"),
    (35.4, "moderate"),
    (55.4, "unhealthy"),
    (float("inf"), "very_unhealthy"),
)
PM10_BREAKPOINTS = (
    (54.0, "good"),
    (154.0, "moderate"),
    (254.0, "unhealthy"),
    (float("inf"), "very_unhealthy"),
)
OZONE_BREAKPOINTS = (
    (54.0, "good"),
    (70.0, "moderate"),
    (85.0, "unhealthy"),
    (float("inf"), "very_unhealthy"),
)

CITIES: dict[str, dict[str, Any]] = {
    "london": {"name": "London", "latitude": 51.5074, "longitude": -0.1278},
    "paris": {"name": "Paris", "latitude": 48.8566, "longitude": 2.3522},
    "berlin": {"name": "Berlin", "latitude": 52.52, "longitude": 13.41},
    "delhi": {"name": "Delhi", "latitude": 28.61, "longitude": 77.23},
    "beijing": {"name": "Beijing", "latitude": 39.90, "longitude": 116.40},
    "los_angeles": {"name": "Los Angeles", "latitude": 34.05, "longitude": -118.24},
}

DEFAULT_CITY_KEYS = ("london", "paris", "berlin", "delhi")

MOCK_ITEMS: list[dict[str, Any]] = [
    {
        "id": "london-2026-06-04-pm2_5",
        "name": "London",
        "description": "PM2.5: 14.2 µg/m³ — Good. Air quality is satisfactory.",
        "category": "good",
        "date": "2026-06-04",
        "pollutant": "pm2_5",
        "value": 14.2,
        "unit": "µg/m³",
    },
    {
        "id": "paris-2026-06-04-pm2_5",
        "name": "Paris",
        "description": "PM2.5: 22.5 µg/m³ — Moderate. Sensitive groups may be affected.",
        "category": "moderate",
        "date": "2026-06-04",
        "pollutant": "pm2_5",
        "value": 22.5,
        "unit": "µg/m³",
    },
    {
        "id": "delhi-2026-06-04-pm2_5",
        "name": "Delhi",
        "description": "PM2.5: 78.0 µg/m³ — Unhealthy. Everyone may experience effects.",
        "category": "unhealthy",
        "date": "2026-06-04",
        "pollutant": "pm2_5",
        "value": 78.0,
        "unit": "µg/m³",
    },
    {
        "id": "beijing-2026-06-04-pm2_5",
        "name": "Beijing",
        "description": "PM2.5: 95.0 µg/m³ — Very Unhealthy. Avoid prolonged outdoor exertion.",
        "category": "very_unhealthy",
        "date": "2026-06-04",
        "pollutant": "pm2_5",
        "value": 95.0,
        "unit": "µg/m³",
    },
]

SEVERITY_HEALTH = {
    "good": "Air quality is satisfactory.",
    "moderate": "Sensitive groups may be affected.",
    "unhealthy": "Everyone may experience health effects.",
    "very_unhealthy": "Avoid prolonged outdoor exertion.",
}


def _uses_mock_api() -> bool:
    if os.environ.get("AQ_USE_MOCK", "").lower() in ("1", "true", "yes"):
        return True
    return "example.com" in API_BASE


def _auth_headers() -> dict[str, str]:
    if API_KEY:
        return {"Authorization": f"Bearer {API_KEY}"}
    return {}


def _today_iso() -> str:
    return date.today().isoformat()


def _normalize_pollutant(pollutant: str) -> str:
    key = pollutant.strip().lower().replace(".", "").replace(" ", "_")
    aliases = {
        "pm25": "pm2_5",
        "pm2.5": "pm2_5",
        "pm10": "pm10",
        "o3": "ozone",
    }
    key = aliases.get(key, key)
    if key not in POLLUTANTS:
        return "pm2_5"
    return key


def severity_for_value(pollutant: str, value: float) -> str:
    """Map concentration to severity band using inclusive upper limits."""
    if pollutant == "pm10":
        thresholds = PM10_BREAKPOINTS
    elif pollutant == "ozone":
        thresholds = OZONE_BREAKPOINTS
    else:
        thresholds = PM25_BREAKPOINTS
    for upper, band in thresholds:
        if value <= upper:
            return band
    return "very_unhealthy"


def _severity_rank(band: str) -> int:
    try:
        return SEVERITY_ORDER.index(band)
    except ValueError:
        return -1


def _meets_min_severity(band: str, min_severity: str) -> bool:
    if not min_severity:
        return True
    return _severity_rank(band) >= _severity_rank(min_severity)


def match_cities(query: str) -> list[str]:
    """Return city keys mentioned in query (substring match on key and display name)."""
    query_lower = query.lower().strip()
    if not query_lower:
        return []
    matched: list[str] = []
    for key, meta in CITIES.items():
        name = meta["name"].lower()
        if key in query_lower or name in query_lower:
            matched.append(key)
    return matched


def _resolve_city_keys(query: str, limit: int) -> list[str]:
    matched = match_cities(query)
    if matched:
        return matched[:limit]
    return list(DEFAULT_CITY_KEYS)[:limit]


def _build_description(pollutant: str, value: float, band: str) -> str:
    label = POLLUTANT_LABELS.get(pollutant, pollutant)
    unit = POLLUTANT_UNITS.get(pollutant, "")
    severity = SEVERITY_LABELS.get(band, band)
    health = SEVERITY_HEALTH.get(band, "")
    return f"{label}: {value:.1f} {unit} — {severity}. {health}"


def shape_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize API or internal records into the widget's expected shape."""
    pollutant = _normalize_pollutant(str(raw.get("pollutant", "pm2_5")))
    value = float(raw.get("value", 0))
    band = raw.get("category") or severity_for_value(pollutant, value)
    city_name = raw.get("name", "")
    item_date = raw.get("date", _today_iso())
    city_key = raw.get("city_key", city_name.lower().replace(" ", "_"))
    item_id = raw.get("id") or f"{city_key}-{item_date}-{pollutant}"
    return {
        "id": str(item_id),
        "name": city_name,
        "description": raw.get("description") or _build_description(pollutant, value, band),
        "category": band,
        "date": item_date,
        "pollutant": pollutant,
        "value": value,
        "unit": raw.get("unit", POLLUTANT_UNITS.get(pollutant, "")),
    }


def _average_hourly(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


async def _fetch_city_reading(
    client: httpx.AsyncClient,
    city_key: str,
    pollutant: str,
    item_date: str,
) -> dict[str, Any] | None:
    meta = CITIES[city_key]
    url = f"{API_BASE.rstrip('/')}/v1/air-quality"
    params = {
        "latitude": meta["latitude"],
        "longitude": meta["longitude"],
        "hourly": pollutant,
        "start_date": item_date,
        "end_date": item_date,
        "timezone": "auto",
    }
    response = await client.get(url, params=params, headers=_auth_headers())
    response.raise_for_status()
    data = response.json()
    hourly = data.get("hourly", {})
    values = hourly.get(pollutant, [])
    avg = _average_hourly(values)
    if avg is None:
        return None
    band = severity_for_value(pollutant, avg)
    return shape_item(
        {
            "city_key": city_key,
            "name": meta["name"],
            "date": item_date,
            "pollutant": pollutant,
            "value": round(avg, 1),
            "category": band,
        }
    )


def _city_key_from_name(name: str) -> str:
    for key, meta in CITIES.items():
        if meta["name"] == name:
            return key
    return name.lower().replace(" ", "_")


def _filter_mock_items(
    query: str,
    category: str = "",
    pollutant: str = "pm2_5",
    date_str: str = "",
    min_severity: str = "",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    pollutant = _normalize_pollutant(pollutant)
    matched = match_cities(query)
    allowed_keys = set(matched) if matched else set(DEFAULT_CITY_KEYS)
    results: list[dict[str, Any]] = []
    for item in MOCK_ITEMS:
        if _normalize_pollutant(str(item.get("pollutant", "pm2_5"))) != pollutant:
            continue
        city_key = _city_key_from_name(str(item.get("name", "")))
        if city_key not in allowed_keys:
            continue
        if date_str and item.get("date") != date_str:
            continue
        if category and item.get("category") != category:
            continue
        if not _meets_min_severity(str(item.get("category", "")), min_severity):
            continue
        results.append(dict(item))
    if limit is not None:
        results = results[:limit]
    return results


def _sort_items(items: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    reverse = False
    sort_key = sort_by
    if sort_by.endswith("_desc"):
        sort_key = sort_by[: -len("_desc")]
        reverse = True
    if sort_key == "value":
        return sorted(items, key=lambda i: float(i.get("value", 0)), reverse=reverse)
    return sorted(items, key=lambda i: str(i.get(sort_key, "")), reverse=reverse)


async def fetch_items(
    query: str,
    limit: int = 20,
    pollutant: str = "pm2_5",
    date_str: str = "",
) -> list[dict[str, Any]]:
    """Fetch air quality readings for cities matching query."""
    pollutant = _normalize_pollutant(pollutant)
    item_date = date_str.strip() or _today_iso()
    city_keys = _resolve_city_keys(query, limit)

    if _uses_mock_api():
        return _filter_mock_items(query=query, pollutant=pollutant, date_str=item_date, limit=limit)

    async with httpx.AsyncClient(timeout=15.0) as client:
        readings: list[dict[str, Any]] = []
        for city_key in city_keys:
            try:
                reading = await _fetch_city_reading(client, city_key, pollutant, item_date)
                if reading:
                    readings.append(reading)
            except httpx.HTTPError:  # includes timeouts and HTTP status errors
                continue
    return readings[:limit]


async def filter_items(
    query: str,
    category: str = "",
    sort_by: str = "value_desc",
    pollutant: str = "pm2_5",
    date_str: str = "",
    min_severity: str = "",
) -> list[dict[str, Any]]:
    """Re-fetch or filter readings by pollutant, date, severity band, and sort."""
    pollutant = _normalize_pollutant(pollutant)
    item_date = date_str.strip() or _today_iso()
    min_severity = min_severity.strip().lower()

    if _uses_mock_api():
        items = _filter_mock_items(
            query=query,
            category=category,
            pollutant=pollutant,
            date_str=item_date,
            min_severity=min_severity,
        )
    else:
        items = await fetch_items(query=query, limit=20, pollutant=pollutant, date_str=item_date)
        if category:
            items = [i for i in items if i.get("category") == category]
        if min_severity:
            items = [i for i in items if _meets_min_severity(str(i.get("category", "")), min_severity)]

    return _sort_items(items, sort_by)
