"""Tests for the AgentGuard pytest plugin (uses pytester fixture)."""

from __future__ import annotations

import os

import pytest

os.environ["AGENTGUARD_SKIP_LLM_JUDGE"] = "1"
pytest_plugins = ["pytester"]


def test_inline_scenario_decorator_runs_in_subsession(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import os
        os.environ["AGENTGUARD_SKIP_LLM_JUDGE"] = "1"

        import agentguard

        @agentguard.inline_scenario(
            agent={"adapter": "http", "url": "http://localhost:9999"},
            user_message="anything",
            metrics=["latency"],
            thresholds={"max_latency_ms": 1000},
        )
        def test_scenario_runs(result):
            assert result.scenario_id == "test_scenario_runs"
            # Adapter cannot reach localhost:9999 -> failure path,
            # but the test still receives a ScenarioResult.
            assert hasattr(result, "evaluations")
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1)


def test_assertrepr_compare_renders_failing_evaluators(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        from agentguard.schemas.result import EvaluationResult, ScenarioResult
        from agentguard.schemas.trace import AgentTrace

        def test_repr():
            r = ScenarioResult(
                scenario_id="x",
                suite="y",
                passed=False,
                overall_score=0.4,
                final_output="",
                evaluations=[
                    EvaluationResult(
                        metric_name="forbidden_tool_avoidance",
                        score=0.0, passed=False, reason="agent called issue_refund",
                    )
                ],
                trace=AgentTrace(scenario_id="x"),
                failure_summary="forbidden_tool_avoidance: agent called issue_refund",
            )
            assert r == "expected_other"
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(failed=1)
    assert any("forbidden_tool_avoidance" in line for line in result.outlines)
