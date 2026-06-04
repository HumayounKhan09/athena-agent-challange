"""HTTP client for the assigned topic's public API."""

from __future__ import annotations

import os
from typing import Any

import httpx

# Replace with the real API base URL when the topic is assigned.
API_BASE = os.environ.get("API_BASE", "https://api.example.com")
API_KEY = os.environ.get("API_KEY", "")

MOCK_ITEMS: list[dict[str, Any]] = [
    {
        "id": "1",
        "name": "Alpha Project",
        "description": "First mock item for development.",
        "category": "general",
        "date": "2024-01-15",
    },
    {
        "id": "2",
        "name": "Beta Initiative",
        "description": "Second mock item with sample data.",
        "category": "research",
        "date": "2024-03-22",
    },
    {
        "id": "3",
        "name": "Gamma Release",
        "description": "Third mock item for widget testing.",
        "category": "general",
        "date": "2024-06-10",
    },
    {
        "id": "4",
        "name": "Delta Report",
        "description": "Fourth mock item with a longer description field.",
        "category": "reports",
        "date": "2024-09-01",
    },
]


def _uses_mock_api() -> bool:
    return "example.com" in API_BASE


def _auth_headers() -> dict[str, str]:
    if API_KEY:
        return {"Authorization": f"Bearer {API_KEY}"}
    return {}


def shape_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize API records into the widget's expected shape."""
    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", raw.get("title", "")),
        "description": raw.get("description", raw.get("summary", "")),
        "category": raw.get("category", ""),
        "date": raw.get("date", raw.get("published_at", "")),
    }


def _filter_mock_items(
    query: str,
    category: str = "",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    query_lower = query.lower().strip()
    results = []
    for item in MOCK_ITEMS:
        if category and item.get("category", "") != category:
            continue
        haystack = " ".join(
            str(item.get(field, "")) for field in ("name", "description", "category")
        ).lower()
        if query_lower and query_lower not in haystack:
            continue
        results.append(dict(item))
    if limit is not None:
        results = results[:limit]
    return results


async def fetch_items(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch items matching query from the API or mock catalog."""
    if _uses_mock_api():
        return _filter_mock_items(query=query, limit=limit)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{API_BASE}/endpoint",
            params={"q": query, "limit": limit},
            headers=_auth_headers(),
        )
        response.raise_for_status()
        raw = response.json()

    results = raw.get("results", raw.get("items", []))
    return [shape_item(item) for item in results[:limit]]


async def filter_items(
    query: str,
    category: str = "",
    sort_by: str = "name",
) -> list[dict[str, Any]]:
    """Fetch filtered items from the API or mock catalog."""
    if _uses_mock_api():
        items = _filter_mock_items(query=query, category=category)
        reverse = False
        sort_key = sort_by
        if sort_by.endswith("_desc"):
            sort_key = sort_by[: -len("_desc")]
            reverse = True
        items.sort(key=lambda item: str(item.get(sort_key, "")), reverse=reverse)
        return items

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{API_BASE}/endpoint",
            params={"q": query, "category": category, "sort": sort_by},
            headers=_auth_headers(),
        )
        response.raise_for_status()
        raw = response.json()

    results = raw.get("results", raw.get("items", []))
    return [shape_item(item) for item in results]
