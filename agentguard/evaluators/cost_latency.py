"""Cost and latency evaluators (rule-based)."""

from __future__ import annotations

from agentguard.evaluators.base import BaseEvaluator
from agentguard.schemas.evaluator import EvaluatorMeta
from agentguard.schemas.result import AgentRunResult, EvaluationResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace


def _band(actual: float | None, threshold: float | None) -> tuple[float, str]:
    if threshold is None or actual is None:
        return 1.0, "No threshold set."
    if actual <= threshold:
        return 1.0, f"Within threshold ({actual:.4g} <= {threshold:.4g})."
    if actual <= threshold * 1.25:
        return 0.5, f"Slightly over threshold ({actual:.4g} > {threshold:.4g})."
    return 0.0, f"Far over threshold ({actual:.4g} > {threshold:.4g})."


class CostEvaluator(BaseEvaluator):
    @property
    def meta(self) -> EvaluatorMeta:
        return EvaluatorMeta(
            name="cost",
            description="Scores agent cost against a max-cost threshold.",
            category="performance",
            deterministic=True,
        )

    async def evaluate(
        self,
        scenario: Scenario,
        run_result: AgentRunResult,
        trace: AgentTrace,
    ) -> EvaluationResult:
        threshold = scenario.thresholds.max_cost_usd if scenario.thresholds else None
        actual = trace.total_cost_usd
        score, reason = _band(actual, threshold)
        return EvaluationResult(
            metric_name="cost",
            score=score,
            passed=score >= 0.5,
            reason=reason,
            evidence=[{"actual_cost_usd": actual, "max_cost_usd": threshold}],
        )


class LatencyEvaluator(BaseEvaluator):
    @property
    def meta(self) -> EvaluatorMeta:
        return EvaluatorMeta(
            name="latency",
            description="Scores agent latency against a max-latency threshold.",
            category="performance",
            deterministic=True,
        )

    async def evaluate(
        self,
        scenario: Scenario,
        run_result: AgentRunResult,
        trace: AgentTrace,
    ) -> EvaluationResult:
        threshold = scenario.thresholds.max_latency_ms if scenario.thresholds else None
        actual = trace.total_latency_ms
        actual_f = float(actual) if actual is not None else None
        threshold_f = float(threshold) if threshold is not None else None
        score, reason = _band(actual_f, threshold_f)
        return EvaluationResult(
            metric_name="latency",
            score=score,
            passed=score >= 0.5,
            reason=reason,
            evidence=[{"actual_latency_ms": actual, "max_latency_ms": threshold}],
        )
