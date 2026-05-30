"""Repository helpers for API and CLI persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from agentguard.schemas.report import RunSummary
from agentguard.schemas.result import ScenarioResult
from agentguard.storage.models import (
    Agent,
    AgentVersion,
    EvaluationResultDB,
    Project,
    Run,
    ScenarioResultDB,
    ScenarioSuite,
    TraceDB,
    TraceStepDB,
)


def get_or_create_project(session: Session, name: str = "Default Project") -> Project:
    project = session.scalar(select(Project).where(Project.name == name))
    if project is not None:
        return project
    project = Project(name=name, description="AgentGuard evaluation project")
    session.add(project)
    session.flush()
    return project


def get_or_create_agent(
    session: Session,
    project: Project,
    name: str,
    adapter_type: str = "http",
) -> Agent:
    agent = session.scalar(
        select(Agent).where(Agent.project_id == project.id, Agent.name == name)
    )
    if agent is not None:
        return agent
    agent = Agent(project_id=project.id, name=name, adapter_type=adapter_type)
    session.add(agent)
    session.flush()
    return agent


def get_or_create_agent_version(session: Session, agent: Agent, version: str) -> AgentVersion:
    agent_version = session.scalar(
        select(AgentVersion).where(AgentVersion.agent_id == agent.id, AgentVersion.version == version)
    )
    if agent_version is not None:
        return agent_version
    agent_version = AgentVersion(agent_id=agent.id, version=version)
    session.add(agent_version)
    session.flush()
    return agent_version


def get_or_create_suite(session: Session, project: Project, name: str) -> ScenarioSuite:
    suite = session.scalar(
        select(ScenarioSuite).where(ScenarioSuite.project_id == project.id, ScenarioSuite.name == name)
    )
    if suite is not None:
        return suite
    suite = ScenarioSuite(project_id=project.id, name=name)
    session.add(suite)
    session.flush()
    return suite


def save_run_payload(
    session: Session,
    summary: RunSummary,
    results: list[ScenarioResult],
    project_name: str = "Default Project",
    triggered_by: str = "cli",
) -> Run:
    project = get_or_create_project(session, project_name)
    agent = get_or_create_agent(session, project, summary.agent_name, adapter_type="mixed")
    version = get_or_create_agent_version(session, agent, summary.agent_version)
    suite = get_or_create_suite(session, project, summary.suite)

    existing = session.get(Run, summary.run_id)
    if existing is not None:
        session.delete(existing)
        session.flush()

    run = Run(
        id=summary.run_id,
        project_id=project.id,
        agent_version_id=version.id,
        suite_id=suite.id,
        status="completed",
        overall_score=summary.overall_score,
        security_score=summary.security_score,
        rag_score=summary.rag_score,
        tool_score=summary.tool_score,
        avg_cost_usd=summary.avg_cost_usd,
        avg_latency_ms=summary.avg_latency_ms,
        p95_latency_ms=summary.p95_latency_ms,
        deployment_recommendation=summary.deployment_recommendation,
        total_scenarios=summary.total_scenarios,
        passed_scenarios=summary.passed_scenarios,
        failed_scenarios=summary.failed_scenarios,
        triggered_by=triggered_by,
        started_at=summary.started_at,
        finished_at=summary.finished_at,
        summary_json=summary.model_dump(mode="json"),
    )
    session.add(run)
    session.flush()

    for result in results:
        scenario_result = ScenarioResultDB(
            run_id=run.id,
            scenario_key=result.scenario_id,
            status="passed" if result.passed else "failed",
            overall_score=result.overall_score,
            failure_summary=result.failure_summary,
            final_output=result.final_output,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            result_json=result.model_dump(mode="json"),
        )
        session.add(scenario_result)
        session.flush()

        trace = TraceDB(
            id=result.trace.trace_id,
            scenario_result_id=scenario_result.id,
            trace_json=result.trace.model_dump(mode="json"),
        )
        session.add(trace)
        for index, step in enumerate(result.trace.steps):
            session.add(
                TraceStepDB(
                    trace_id=trace.id,
                    step_index=index,
                    step_type=step.type,
                    name=step.name,
                    input=step.input,
                    output=step.output,
                    metadata_json=step.metadata,
                    latency_ms=step.latency_ms,
                    started_at=step.started_at,
                    ended_at=step.ended_at,
                )
            )

        for evaluation in result.evaluations:
            session.add(
                EvaluationResultDB(
                    scenario_result_id=scenario_result.id,
                    metric_name=evaluation.metric_name,
                    score=evaluation.score,
                    passed=evaluation.passed,
                    reason=evaluation.reason,
                    evidence=evaluation.evidence,
                )
            )

    session.flush()
    return run


def list_runs(session: Session, limit: int = 100) -> list[Run]:
    stmt = (
        select(Run)
        .options(selectinload(Run.agent_version).selectinload(AgentVersion.agent), selectinload(Run.suite))
        .order_by(Run.started_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def get_run(session: Session, run_id: str) -> Run | None:
    stmt = (
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.agent_version).selectinload(AgentVersion.agent),
            selectinload(Run.suite),
            selectinload(Run.scenario_results).selectinload(ScenarioResultDB.evaluations),
            selectinload(Run.scenario_results).selectinload(ScenarioResultDB.trace).selectinload(TraceDB.steps),
        )
    )
    return session.scalar(stmt)


def get_trace(session: Session, trace_id: str) -> TraceDB | None:
    stmt = select(TraceDB).where(TraceDB.id == trace_id).options(selectinload(TraceDB.steps))
    return session.scalar(stmt)
