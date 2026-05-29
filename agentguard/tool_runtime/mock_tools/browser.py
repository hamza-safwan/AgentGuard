"""Mock web search."""

from __future__ import annotations

from typing import Any


def search_web(query: str) -> dict[str, Any]:
    return {
        "results": [
            {"title": f"Result for: {query}", "url": "https://example.com/1", "snippet": "..."},
        ]
    }
