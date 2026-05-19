"""Report and run-summary models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DeploymentRecommendation = Literal[
    "deploy_with_monitoring",
    "deploy_carefully",
    "fix_before_production",
    "do_not_deploy",
]


class MetricSummary(BaseModel):
    metric_name: str
    average_score: float
    min_score: float
    max_score: float
    pass_rate: float
    failure_count: int


class SecurityFinding(BaseModel):
    severity: Literal["critical", "high", "medium", "low"]
    scenario_id: str
    finding: str
    evidence: dict | None = None


class RunSummary(BaseModel):
    run_id: str
    agent_name: str
    agent_version: str
    suite: str
    started_at: datetime
    finished_at: datetime | None = None
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    overall_score: float
    security_score: float
    rag_score: float
    tool_score: float
    avg_cost_usd: float
    avg_latency_ms: float
    p95_latency_ms: float | None = None
    deployment_recommendation: DeploymentRecommendation
    metric_summaries: list[MetricSummary] = Field(default_factory=list)
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    failed_scenario_ids: list[str] = Field(default_factory=list)


class RegressionDelta(BaseModel):
    metric_name: str
    base_score: float
    candidate_score: float
    delta: float
    regressed: bool


class RegressionReport(BaseModel):
    base_run_id: str
    candidate_run_id: str
    base_version: str
    candidate_version: str
    deltas: list[RegressionDelta]
    new_failures: list[str]
    fixed_scenarios: list[str]
    recommendation: str
