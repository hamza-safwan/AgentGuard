"""Result models — adapter output, evaluation outputs, scenario scorecards."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agentguard.schemas.trace import AgentTrace


class AgentRunResult(BaseModel):
    """Normalized output from running an agent through an adapter."""

    final_output: str
    trace: AgentTrace
    raw_output: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Result of a single evaluator on a single scenario run."""

    metric_name: str
    score: float
    passed: bool
    reason: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    """Full scored result for one scenario."""

    scenario_id: str
    suite: str
    passed: bool
    overall_score: float
    final_output: str
    evaluations: list[EvaluationResult]
    trace: AgentTrace
    failure_summary: str | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
