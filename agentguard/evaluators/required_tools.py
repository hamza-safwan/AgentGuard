"""Required-tool-call evaluator."""

from __future__ import annotations

from agentguard.evaluators.base import BaseEvaluator
from agentguard.schemas.evaluator import EvaluatorMeta
from agentguard.schemas.result import AgentRunResult, EvaluationResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace


class RequiredToolEvaluator(BaseEvaluator):
    @property
    def meta(self) -> EvaluatorMeta:
        return EvaluatorMeta(
            name="required_tool_calls",
            description="Verifies that all required tools were called.",
            category="rule_based",
            deterministic=True,
        )

    async def evaluate(
        self,
        scenario: Scenario,
        run_result: AgentRunResult,
        trace: AgentTrace,
    ) -> EvaluationResult:
        required = list(scenario.expected.must_call_tools)
        called = trace.tool_names()
        missing = [t for t in required if t not in called]

        if not required:
            return EvaluationResult(
                metric_name="required_tool_calls",
                score=1.0,
                passed=True,
                reason="No required tools specified.",
                evidence=[{"called": called}],
            )

        if not missing:
            score = 1.0
            reason = f"All {len(required)} required tools were called."
        else:
            score = max(0.0, 1.0 - len(missing) / len(required))
            reason = f"Missing required tools: {missing}"

        return EvaluationResult(
            metric_name="required_tool_calls",
            score=score,
            passed=(score == 1.0),
            reason=reason,
            evidence=[
                {
                    "required": required,
                    "called": called,
                    "missing": missing,
                }
            ],
        )
