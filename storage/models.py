"""SQLAlchemy models for run persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentguard.storage.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    agents: Mapped[list[Agent]] = relationship(back_populates="project", cascade="all, delete-orphan")
    suites: Mapped[list[ScenarioSuite]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    runs: Mapped[list[Run]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_agent_project_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(64), nullable=False, default="http")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="agents")
    versions: Mapped[list[AgentVersion]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version", name="uq_agent_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    agent: Mapped[Agent] = relationship(back_populates="versions")
    runs: Mapped[list[Run]] = relationship(back_populates="agent_version")


class ScenarioSuite(Base):
    __tablename__ = "scenario_suites"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_suite_project_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="suites")
    scenarios: Mapped[list[ScenarioRecord]] = relationship(
        back_populates="suite", cascade="all, delete-orphan"
    )
    runs: Mapped[list[Run]] = relationship(back_populates="suite")


class ScenarioRecord(Base):
    __tablename__ = "scenarios"
    __table_args__ = (UniqueConstraint("suite_id", "scenario_key", name="uq_scenario_suite_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    suite_id: Mapped[str] = mapped_column(ForeignKey("scenario_suites.id", ondelete="CASCADE"))
    scenario_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    yaml_path: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    suite: Mapped[ScenarioSuite] = relationship(back_populates="scenarios")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    agent_version_id: Mapped[str | None] = mapped_column(ForeignKey("agent_versions.id"))
    suite_id: Mapped[str | None] = mapped_column(ForeignKey("scenario_suites.id"))
    status: Mapped[str] = mapped_column(String(32), default="completed")
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    security_score: Mapped[float] = mapped_column(Float, default=0.0)
    rag_score: Mapped[float] = mapped_column(Float, default=0.0)
    tool_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p95_latency_ms: Mapped[float | None] = mapped_column(Float)
    deployment_recommendation: Mapped[str] = mapped_column(String(64), nullable=False)
    total_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    passed_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    failed_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    triggered_by: Mapped[str] = mapped_column(String(64), default="cli")
    source: Mapped[str] = mapped_column(String(32), default="cli", nullable=False)
    sampling_meta: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped[Project] = relationship(back_populates="runs")
    agent_version: Mapped[AgentVersion | None] = relationship(back_populates="runs")
    suite: Mapped[ScenarioSuite | None] = relationship(back_populates="runs")
    scenario_results: Mapped[list[ScenarioResultDB]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    reports: Mapped[list[ReportDB]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ScenarioResultDB(Base):
    __tablename__ = "scenario_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    scenario_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    failure_summary: Mapped[str | None] = mapped_column(Text)
    final_output: Mapped[str] = mapped_column(Text, default="")
    cost_usd: Mapped[float | None] = mapped_column(Float)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[Run] = relationship(back_populates="scenario_results")
    trace: Mapped[TraceDB | None] = relationship(
        back_populates="scenario_result", cascade="all, delete-orphan", uselist=False
    )
    evaluations: Mapped[list[EvaluationResultDB]] = relationship(
        back_populates="scenario_result", cascade="all, delete-orphan"
    )


class TraceDB(Base):
    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_result_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_results.id", ondelete="CASCADE")
    )
    trace_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    scenario_result: Mapped[ScenarioResultDB] = relationship(back_populates="trace")
    steps: Mapped[list[TraceStepDB]] = relationship(back_populates="trace", cascade="all, delete-orphan")


class TraceStepDB(Base):
    __tablename__ = "trace_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trace_id: Mapped[str] = mapped_column(ForeignKey("traces.id", ondelete="CASCADE"))
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    input: Mapped[dict | str | None] = mapped_column(JSON)
    output: Mapped[dict | str | None] = mapped_column(JSON)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trace: Mapped[TraceDB] = relationship(back_populates="steps")


class EvaluationResultDB(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    scenario_result_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_results.id", ondelete="CASCADE")
    )
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    scenario_result: Mapped[ScenarioResultDB] = relationship(back_populates="evaluations")


class ReportDB(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    format: Mapped[str] = mapped_column(String(32), nullable=False, default="json")
    content: Mapped[dict | None] = mapped_column(JSON)
    html_content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[Run] = relationship(back_populates="reports")


# ---------------------------------------------------------------------------
# v0.3 - observability tables (BLUEPRINT-7 section 12 / Appendix B)
# ---------------------------------------------------------------------------


class AuthToken(Base):
    """Bearer tokens used by the SDK observability transport."""

    __tablename__ = "auth_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship()


class AlertRule(Base):
    """A rolling-window threshold rule that fires alerts on metric drops."""

    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(255))
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    threshold_drop_pct: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    destinations: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship()
    events: Mapped[list[AlertEvent]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class AlertEvent(Base):
    """A historical record of a rule firing."""

    __tablename__ = "alert_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"))
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    metric_value: Mapped[float | None] = mapped_column(Float)
    baseline_value: Mapped[float | None] = mapped_column(Float)
    payload: Mapped[dict | None] = mapped_column(JSON)

    rule: Mapped[AlertRule] = relationship(back_populates="events")
