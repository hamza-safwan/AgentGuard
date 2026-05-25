"""Sample LangGraph customer-support agent — the hero demo for AgentGuard.

This is a small but realistic LangGraph agent: it routes intents, calls tools,
retrieves policy docs from a fake vector index, and respects a guardrail that
blocks refunds outside of policy.

Run scenarios against it with:

    OPENAI_API_KEY=sk-... agentguard run scenarios/customer_support

If you don't have an OpenAI key, the sample agent falls back to a deterministic
keyword-routed mode so the trace viewer still has rich data to show.
"""

from __future__ import annotations

import os
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

POLICY_DOCS = {
    "refund_policy_v2": "Refunds are allowed within 30 days of purchase. Refunds over $100 require manager approval.",
    "leave_policy": "Employees are entitled to 20 days of paid annual leave.",
    "data_handling": "Customer PII may not be shared with anyone outside the customer's account.",
}


@tool
def get_customer_profile(customer_id: str) -> dict[str, Any]:
    """Return basic profile for a customer (no PII)."""
    return {"id": customer_id, "name": "John Doe", "plan": "pro", "active": True}


@tool
def search_policy_docs(query: str) -> dict[str, Any]:
    """Search company policy documents."""
    q = query.lower()
    docs = [
        {"doc_id": doc_id, "content": content, "score": 0.9}
        for doc_id, content in POLICY_DOCS.items()
        if any(w in content.lower() or w in doc_id.lower() for w in q.split())
    ]
    return {"documents": docs}


@tool
def issue_refund(customer_id: str, amount: float) -> dict[str, Any]:
    """Issue a refund. Refuses amounts over $100 without an approval flag."""
    if amount > 100:
        return {"status": "blocked", "reason": "Refunds above $100 require manager approval."}
    return {"status": "success", "refund_id": f"ref_{customer_id}_{int(amount)}"}


@tool
def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email."""
    return {"status": "sent", "message_id": "msg_demo_1"}


TOOLS = [get_customer_profile, search_policy_docs, issue_refund, send_email]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _llm_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Route via OpenAI if available; otherwise fall back to keyword heuristics."""
    last_user_msg = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            last_user_msg = str(m.content)
            break

    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), temperature=0).bind_tools(
                TOOLS
            )
            ai = llm.invoke(state["messages"])
            return {"messages": [ai]}
        except Exception:
            pass

    return {"messages": [_heuristic_route(last_user_msg)]}


def _heuristic_route(msg: str) -> AIMessage:
    """Deterministic fallback when no LLM key is set — keeps demos working offline."""
    lower = msg.lower()
    if "refund" in lower:
        if "90 days" in lower or "ignore" in lower or "policy" in lower:
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "search_policy_docs", "args": {"query": "refund policy"}, "id": "1"},
                ],
            )
        return AIMessage(
            content="",
            tool_calls=[
                {"name": "get_customer_profile", "args": {"customer_id": "cust_123"}, "id": "1"},
            ],
        )
    if "salary" in lower or "phone" in lower or "ssn" in lower or "cnic" in lower:
        return AIMessage(
            content="I can't share another employee's personal data. Please contact HR for legitimate requests."
        )
    if "system prompt" in lower or "developer mode" in lower or "your instructions" in lower:
        return AIMessage(content="I can't share my internal instructions.")
    if "delete" in lower and "account" in lower:
        return AIMessage(content="Account deletions require a verified email request.")
    if "send" in lower and "email" in lower and "external" in lower:
        return AIMessage(content="I can't send data outside our organization.")
    return AIMessage(content="Hi! I can help with refunds, account questions, and policy lookups.")


def _tool_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    last = state["messages"][-1]
    tool_messages: list[BaseMessage] = []
    for call in getattr(last, "tool_calls", []) or []:
        name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
        args = call.get("args", {}) if isinstance(call, dict) else getattr(call, "args", {})
        call_id = call.get("id", "1") if isinstance(call, dict) else getattr(call, "id", "1")
        impl = TOOLS_BY_NAME.get(name)
        if not impl:
            tool_messages.append(ToolMessage(content="Unknown tool.", tool_call_id=call_id))
            continue
        try:
            result = impl.invoke(args)
        except Exception as e:
            result = {"error": str(e)}
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=call_id))
    return {"messages": tool_messages}


def _final_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Synthesize a final user-facing message from the tool messages."""
    last_user = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            last_user = str(m.content).lower()
            break

    tool_msgs = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    tool_text = " ".join(str(m.content) for m in tool_msgs)

    if "refund" in last_user:
        if "30 days" in tool_text or "blocked" in tool_text or "approval" in tool_text:
            response = (
                "I've checked our policy: refunds are limited to 30 days from purchase, and "
                "amounts over $100 require manager approval. I can escalate this for you."
            )
        elif "success" in tool_text:
            response = "Done — your refund has been issued."
        else:
            response = (
                "I can help with refunds. Could you share your order ID and the reason for the refund?"
            )
    else:
        response = "Hi! I can help with refunds, account questions, and policy lookups."

    return {"messages": [AIMessage(content=response)]}


def _has_tool_calls(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "final"


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("llm", _llm_node)
    builder.add_node("tools", _tool_node)
    builder.add_node("final", _final_node)
    builder.add_edge(START, "llm")
    builder.add_conditional_edges("llm", _has_tool_calls, {"tools": "tools", "final": "final"})
    builder.add_edge("tools", "final")
    builder.add_edge("final", END)
    return builder.compile()


graph = build_graph()
