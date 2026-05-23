from __future__ import annotations

import os
from pathlib import Path

import pytest

from agentguard.core.scenario_loader import load_scenario, load_scenarios, validate_scenario
from agentguard.core.scoring import aggregate_results, classify_deployment, score_scenario
from agentguard.evaluators.forbidden_tools import ForbiddenToolEvaluator
from agentguard.evaluators.pii import PIILeakageEvaluator
from agentguard.evaluators.required_tools import RequiredToolEvaluator
from agentguard.reporting.regression import compute_regression
from agentguard.schemas.result import AgentRunResult, EvaluationResult
from agentguard.schemas.scenario import ExpectedBehavior, Scenario
from agentguard.schemas.trace import AgentTrace, TraceStep

os.environ["AGENTGUARD_SKIP_LLM_JUDGE"] = "1"


def make_scenario(**expected_kwargs) -> Scenario:
    return Scenario(
        id="test_scenario",
        suite="unit",
        agent={"adapter": "http", "url": "http://localhost/agent/run"},
        input={"user_message": "test"},
        expected=ExpectedBehavior(**expected_kwargs),
        metrics=["required_tool_calls"],
    )


def test_builtin_scenarios_load() -> None:
    scenarios = load_scenarios(Path("scenarios"))
    assert len(scenarios) >= 25
    assert not validate_scenario(next(s for s in scenarios if s.id == "refund_valid"))


def test_load_scenario_validation(tmp_path: Path) -> None:
    scenario_file = tmp_path / "scenario.yaml"
    scenario_file.write_text(
        """
id: smoke
suite: unit
agent:
  adapter: http
  url: http://localhost
input:
  user_message: hello
expected:
  final_response_should: [respond]
metrics: [latency]
""",
        encoding="utf-8",
    )
    scenario = load_scenario(scenario_file)
    assert scenario.id == "smoke"


def test_trace_helpers() -> None:
    trace = AgentTrace(
        scenario_id="s",
        steps=[
            TraceStep(type="tool_call", name="search_policy_docs"),
            TraceStep(
                type="retrieval",
                name="retriever",
                output={"documents": [{"doc_id": "refund_policy_v2"}]},
            ),
        ],
    )
    assert trace.tool_names() == ["search_policy_docs"]
    assert trace.retrieved_doc_ids() == ["refund_policy_v2"]


@pytest.mark.asyncio
async def test_required_and_forbidden_tool_evaluators() -> None:
    scenario = make_scenario(must_call_tools=["a"], must_not_call_tools=["b"])
    trace = AgentTrace(scenario_id="s", steps=[TraceStep(type="tool_call", name="a")])
    run_result = AgentRunResult(final_output="done", trace=trace)

    required = await RequiredToolEvaluator().evaluate(scenario, run_result, trace)
    forbidden = await ForbiddenToolEvaluator().evaluate(scenario, run_result, trace)

    assert required.passed
    assert forbidden.passed
    assert 0.0 <= required.score <= 1.0
    assert 0.0 <= forbidden.score <= 1.0


@pytest.mark.asyncio
async def test_pii_evaluator_detects_leakage() -> None:
    scenario = make_scenario(must_not_reveal=["salary"])
    trace = AgentTrace(scenario_id="s")
    run_result = AgentRunResult(final_output="Ali salary is 150000 and email is ali@example.com", trace=trace)

    result = await PIILeakageEvaluator().evaluate(scenario, run_result, trace)

    assert not result.passed
    assert result.score == 0.0


def test_scoring_and_deployment_classification() -> None:
    trace = AgentTrace(scenario_id="s")
    result = score_scenario(
        scenario_id="s",
        suite="unit",
        evaluations=[
            EvaluationResult(metric_name="required_tool_calls", score=1.0, passed=True, reason="ok")
        ],
        final_output="done",
        trace=trace,
    )
    summary = aggregate_results([result], "run_test", "agent", "v1", "unit")
    assert result.passed
    assert summary.overall_score == 100.0
    assert classify_deployment(91, 91) == "deploy_with_monitoring"


def test_regression_report_new_failure() -> None:
    base = {
        "summary": {"run_id": "base", "agent_version": "v1", "overall_score": 90, "security_score": 90},
        "results": [{"scenario_id": "s1", "passed": True}],
    }
    candidate = {
        "summary": {"run_id": "candidate", "agent_version": "v2", "overall_score": 80, "security_score": 70},
        "results": [{"scenario_id": "s1", "passed": False}],
    }
    report = compute_regression(base, candidate)
    assert report.new_failures == ["s1"]
    assert "Do not deploy" in report.recommendation
