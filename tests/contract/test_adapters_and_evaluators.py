from __future__ import annotations

import os

import pytest
from httpx import Request, Response

from agentguard.adapters.crewai import CrewAIAdapter
from agentguard.adapters.http import HTTPAdapter
from agentguard.adapters.langchain import LangChainAdapter
from agentguard.adapters.langgraph import LangGraphAdapter
from agentguard.adapters.openai_agents import OpenAIAgentsAdapter
from agentguard.core.registry import get_evaluator, list_evaluators
from agentguard.schemas.result import AgentRunResult
from agentguard.schemas.scenario import Scenario

os.environ["AGENTGUARD_SKIP_LLM_JUDGE"] = "1"


def test_adapter_metadata_contracts() -> None:
    adapters = [
        HTTPAdapter(),
        LangGraphAdapter(),
        LangChainAdapter(),
        OpenAIAgentsAdapter(),
        CrewAIAdapter(),
    ]
    for adapter in adapters:
        assert adapter.meta.name
        assert isinstance(adapter.meta.supports_async, bool)


@pytest.mark.asyncio
async def test_http_adapter_run_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAsyncClient:
        def __init__(self, timeout: int):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method: str, url: str, json: dict, headers: dict):
            return Response(
                200,
                request=Request(method, url),
                json={
                    "final_output": "done",
                    "trace": {"steps": [{"type": "tool_call", "name": "search_policy_docs"}]},
                    "latency_ms": 25,
                    "cost_usd": 0.001,
                },
            )

    monkeypatch.setattr("agentguard.adapters.http.httpx.AsyncClient", FakeAsyncClient)
    scenario = Scenario(
        id="http_contract",
        suite="contract",
        agent={"adapter": "http", "url": "http://agent.test/agent/run"},
        input={"user_message": "hello"},
        expected={"must_call_tools": ["search_policy_docs"]},
        metrics=["required_tool_calls"],
    )

    result = await HTTPAdapter().run(scenario)

    assert isinstance(result, AgentRunResult)
    assert result.final_output == "done"
    assert result.trace.tool_names() == ["search_policy_docs"]


@pytest.mark.asyncio
async def test_all_evaluators_return_bounded_results() -> None:
    scenario = Scenario(
        id="eval_contract",
        suite="contract",
        agent={"adapter": "http", "url": "http://localhost"},
        input={"user_message": "hello"},
        expected={
            "must_call_tools": [],
            "must_not_call_tools": [],
            "final_response_should": ["respond"],
        },
        metrics=list_evaluators(),
        thresholds={"max_latency_ms": 1000, "max_cost_usd": 0.01},
    )
    trace = HTTPAdapter._extract_trace(
        {"final_output": "hello", "trace": {"steps": []}},
        "eval_contract",
        10,
    )
    run_result = AgentRunResult(final_output="hello", trace=trace)

    for metric in list_evaluators():
        evaluator = get_evaluator(metric)
        result = await evaluator.evaluate(scenario, run_result, trace)
        assert result.metric_name in {metric, "required_tool_calls"}
        assert 0.0 <= result.score <= 1.0
        assert result.reason
