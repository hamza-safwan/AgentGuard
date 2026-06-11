"""Tests for agentguard.sdk decorators, evaluate, and judge (BLUEPRINT-7 section 6)."""

from __future__ import annotations

import asyncio
import os

import pytest

import agentguard
from agentguard.sdk.decorators import scrub

os.environ["AGENTGUARD_SKIP_LLM_JUDGE"] = "1"


def test_tool_decorator_records_step_in_active_trace() -> None:
    @agentguard.tool
    def get_customer_profile(customer_id: str) -> dict:
        return {"id": customer_id, "name": "demo"}

    with agentguard.trace(scenario_id="t") as t:
        out = get_customer_profile("cust_42")
    assert out == {"id": "cust_42", "name": "demo"}
    assert len(t.steps) == 1
    step = t.steps[0]
    assert step.type == "tool_call"
    assert step.name == "get_customer_profile"
    assert step.source == "sdk"
    assert step.latency_ms is not None


def test_decorator_factory_form_with_explicit_name() -> None:
    @agentguard.retrieval(name="policy_search")
    def fetch(query: str) -> list[dict]:
        return [{"doc_id": "p1", "score": 0.9}]

    with agentguard.trace(scenario_id="t") as t:
        fetch("refund")
    assert t.steps[0].type == "retrieval"
    assert t.steps[0].name == "policy_search"


def test_async_decorator_supported() -> None:
    @agentguard.llm_call(model="gpt-4.1-mini")
    async def classify(text: str) -> str:
        await asyncio.sleep(0)
        return "intent_x"

    async def go() -> str:
        with agentguard.trace(scenario_id="t") as t:
            out = await classify("hello")
        assert out == "intent_x"
        assert t.steps[0].type == "llm_call"
        return out

    asyncio.run(go())


def test_decorator_records_error_step_on_exception() -> None:
    @agentguard.tool
    def boom() -> None:
        raise ValueError("nope")

    with agentguard.trace(scenario_id="t") as t, pytest.raises(ValueError):
        boom()
    assert len(t.steps) == 1
    assert t.steps[0].type == "error"
    assert "nope" in str(t.steps[0].output)


def test_scrub_redacts_keys_in_capture() -> None:
    scrub("super_secret")

    @agentguard.tool
    def login(username: str, super_secret: str) -> dict:
        return {"username": username, "ok": True}

    with agentguard.trace(scenario_id="t") as t:
        login("alice", "hunter2")
    captured_input = t.steps[0].input
    assert isinstance(captured_input, dict)
    assert captured_input["super_secret"] == "***"
    assert "super_secret" in t.steps[0].redactions


def test_evaluate_against_in_memory_trace() -> None:
    @agentguard.tool
    def issue_refund(customer_id: str, amount: float) -> dict:
        return {"status": "success"}

    with agentguard.trace(scenario_id="adhoc") as t:
        issue_refund("cust_42", 50)

    result = agentguard.evaluate(
        t,
        metrics=["forbidden_tool_avoidance"],
        must_not_call_tools=["issue_refund"],
    )
    assert not result.passed
    assert any(ev.metric_name == "forbidden_tool_avoidance" and not ev.passed for ev in result.evaluations)


def test_judge_skip_when_no_api_key() -> None:
    out = agentguard.judge(response="anything", criteria="test")
    assert out["skipped"] is True
    assert out["passed"] is True
    assert out["score"] == 1.0
