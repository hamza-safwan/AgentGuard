"""Mock calendar tools."""

from __future__ import annotations

from typing import Any

EVENTS: list[dict[str, Any]] = []


def create_calendar_event(title: str, when: str, attendees: list[str] | None = None) -> dict[str, Any]:
    event = {
        "id": f"evt_{len(EVENTS) + 1}",
        "title": title,
        "when": when,
        "attendees": attendees or [],
    }
    EVENTS.append(event)
    return event


def list_calendar_events(user_id: str) -> dict[str, Any]:
    return {"events": EVENTS}
