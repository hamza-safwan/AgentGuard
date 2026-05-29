"""Mock CRM tools — safe customer data lookup."""

from __future__ import annotations

from typing import Any

CUSTOMERS: dict[str, dict[str, Any]] = {
    "cust_123": {
        "id": "cust_123",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-0123",
        "plan": "pro",
        "orders": [
            {"id": "ord_456", "date": "2026-04-28", "amount": 299.99, "status": "delivered"},
        ],
    },
    "cust_789": {
        "id": "cust_789",
        "name": "Ali Khan",
        "email": "ali@example.com",
        "phone": "+92-300-1234567",
        "plan": "enterprise",
        "cnic": "12345-6789012-3",
        "salary": 150000,
    },
}


def get_customer_profile(customer_id: str) -> dict[str, Any]:
    """Return a safe subset of customer info (no PII fields)."""
    if customer_id not in CUSTOMERS:
        return {"error": "Customer not found"}
    c = CUSTOMERS[customer_id]
    return {
        "id": c["id"],
        "name": c["name"],
        "plan": c["plan"],
        "orders": c.get("orders", []),
    }


def update_customer(customer_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    if customer_id not in CUSTOMERS:
        return {"error": "Customer not found"}
    return {"status": "ok", "updated": list(fields.keys())}


def create_ticket(customer_id: str, issue: str) -> dict[str, Any]:
    return {"ticket_id": f"tkt_{abs(hash(issue)) % 10000}", "status": "open"}
