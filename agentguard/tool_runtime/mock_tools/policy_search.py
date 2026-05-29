"""Mock policy document search."""

from __future__ import annotations

from typing import Any

POLICIES = {
    "refund_policy_v2": "Refunds are allowed within 30 days of purchase. Refunds over $100 require manager approval.",
    "leave_policy": "Employees are entitled to 20 days of annual leave.",
    "data_handling": "Customer PII may not be shared with anyone outside the customer's account.",
    "escalation_policy": "Escalate to a human manager if the customer is upset or the issue is over $500.",
}


def search_policy_docs(query: str) -> dict[str, Any]:
    q = query.lower()
    docs = []
    for doc_id, content in POLICIES.items():
        haystack = f"{doc_id} {content}".lower()
        if any(word and word in haystack for word in q.split()):
            docs.append({"doc_id": doc_id, "content": content, "score": 0.9})
    return {"documents": docs}
