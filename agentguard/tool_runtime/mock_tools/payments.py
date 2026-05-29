"""Mock payments tool."""

from __future__ import annotations

from typing import Any


def issue_refund(customer_id: str, amount: float) -> dict[str, Any]:
    if amount > 100:
        return {"status": "blocked", "reason": "Refunds above $100 require manager approval."}
    return {"status": "success", "refund_id": f"ref_{customer_id}_{int(amount)}"}
