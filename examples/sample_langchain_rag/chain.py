"""Tiny LCEL chain for AgentGuard's LangChain adapter sample.

The chain wraps a fake retriever + a tiny generation step. Designed to run
without external services so adapter integration tests stay deterministic.
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda

POLICIES = {
    "refund_policy_v2": "Refunds are allowed within 30 days of purchase.",
    "leave_policy": "Employees get 20 days of paid annual leave.",
    "data_handling": "Customer PII may not be shared.",
}


class _FakeRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager=None):
        q = query.lower()
        out = []
        for doc_id, content in POLICIES.items():
            if any(w in content.lower() or w in doc_id.lower() for w in q.split()):
                out.append(Document(page_content=content, metadata={"id": doc_id}))
        return out

    async def _aget_relevant_documents(self, query: str, *, run_manager=None):
        return self._get_relevant_documents(query)


def _format(inputs: dict[str, Any]) -> str:
    docs = inputs.get("docs", [])
    if not docs:
        return "I don't know based on the available policy documents."
    cites = ", ".join(d.metadata.get("id", "?") for d in docs)
    snippets = " ".join(d.page_content for d in docs)
    return f"According to {cites}: {snippets}"


def _build() -> Runnable:
    retriever = _FakeRetriever()

    async def _retrieve(inputs: dict[str, Any]) -> dict[str, Any]:
        query = inputs.get("input") or inputs.get("query", "")
        docs = await retriever.ainvoke(query)
        return {"input": query, "docs": docs}

    return RunnableLambda(_retrieve) | RunnableLambda(_format)


chain = _build()
