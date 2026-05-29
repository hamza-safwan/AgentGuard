"""Mock permissions / authorization tool."""

from __future__ import annotations

from typing import Any

ALLOW = {
    ("admin", "*"),
    ("support_lead", "issue_refund"),
    ("support_lead", "send_email"),
}


def check_user_permissions(user_id: str, resource: str) -> dict[str, Any]:
    role = "support_agent" if user_id != "admin" else "admin"
    if (role, "*") in ALLOW or (role, resource) in ALLOW:
        return {"allowed": True, "role": role}
    return {"allowed": False, "role": role, "reason": "Insufficient permissions"}
