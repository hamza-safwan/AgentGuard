"""Mock email tool."""

from __future__ import annotations

from typing import Any


def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    if "@" not in to:
        return {"status": "error", "reason": "invalid recipient"}
    return {"status": "sent", "message_id": f"msg_{abs(hash(to)) % 100000}"}
