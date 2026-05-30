"""AgentGuard FastAPI backend."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import yaml
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agentguard.core.runner import RunOptions, run_path
from agentguard.core.scenario_loader import load_scenarios, validate_scenario
from agentguard.reporting.html_report import render_html
from agentguard.reporting.markdown_report import render_markdown
from agentguard.reporting.regression import compute_regression
from agentguard.schemas.scenario import Scenario
from agentguard.server.dependencies import db_session
from agentguard.server.routes import alerts as alerts_routes
from agentguard.server.routes import tokens as tokens_routes
from agentguard.server.routes import traces as traces_routes
from agentguard.server.serializers import run_detail, run_summary, scenario_result, trace_payload
from agentguard.storage.db import init_db
from agentguard.storage.models import Agent, Project, ReportDB, ScenarioResultDB
from agentguard.storage.persistence import save_run
from agentguard.storage.repositories import get_run, get_trace, list_runs


@asynccontextmanager
async def lifespan(app_: FastAPI):
    init_db()
    yield


app = FastAPI(title="AgentGuard API", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# v0.3 observability surface (BLUEPRINT-7 section 12).
app.include_router(traces_routes.router)
app.include_router(alerts_routes.router)
app.include_router(tokens_routes.router)


class CompareRequest(BaseModel):
    base_run_id: str
    candidate_run_id: str


class ValidateScenarioRequest(BaseModel):
    yaml_text: str


class RunCreateRequest(BaseModel):
    path: str = "scenarios"
    agent_version: str = "dev"
    agent_name: str = "unknown-agent"
    fail_under: int | None = None
    security_threshold: int | None = None
    parallel: int = 1


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    config: dict[str, Any] = {}


class AgentCreate(BaseModel):
    project_id: str
    name: str
    adapter_type: str = "http"
    config: dict[str, Any] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/runs")
def api_list_runs(limit: int = 100, session: Session = Depends(db_session)) -> dict[str, Any]:
    return {"runs": [run_summary(run) for run in list_runs(session, limit=limit)]}


@app.get("/api/runs/{run_id}")
def api_get_run(run_id: str, session: Session = Depends(db_session)) -> dict[str, Any]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run_detail(run)


@app.post("/api/runs")
def api_create_run(request: RunCreateRequest) -> dict[str, Any]:
    options = RunOptions(
        agent_version=request.agent_version,
        fail_under=request.fail_under,
        security_threshold=request.security_threshold,
        save=True,
        parallel=request.parallel,
    )
    summary, results = asyncio.run(
        run_path(Path(request.path), options, agent_name=request.agent_name)
    )
    save_run(summary, results)
    return {
        "summary": summary.model_dump(mode="json"),
        "results": [result.model_dump(mode="json") for result in results],
    }


@app.get("/api/runs/{run_id}/results")
def api_get_run_results(run_id: str, session: Session = Depends(db_session)) -> dict[str, Any]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return {"results": [scenario_result(result) for result in run.scenario_results]}


@app.get("/api/runs/{run_id}/report")
def api_get_run_report(
    run_id: str,
    format: str = "json",
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    payload = {
        "summary": run.summary_json,
        "results": [result.result_json for result in run.scenario_results],
    }
    if format == "html":
        return {"format": "html", "content": render_html(payload["summary"], payload["results"])}
    if format in {"markdown", "md"}:
        return {"format": "markdown", "content": render_markdown(payload["summary"], payload["results"])}
    return payload


@app.get("/api/scenarios")
def api_list_scenarios(path: str = "scenarios") -> dict[str, Any]:
    scenario_path = Path(path)
    if not scenario_path.exists():
        return {"scenarios": []}
    scenarios = load_scenarios(scenario_path)
    return {"scenarios": [scenario.model_dump(mode="json") for scenario in scenarios]}


@app.get("/api/scenarios/{scenario_id}")
def api_get_scenario(scenario_id: str, path: str = "scenarios") -> dict[str, Any]:
    for scenario in load_scenarios(Path(path)) if Path(path).exists() else []:
        if scenario.id == scenario_id:
            return scenario.model_dump(mode="json")
    raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")


@app.post("/api/scenarios/validate")
def api_validate_scenario(request: ValidateScenarioRequest) -> dict[str, Any]:
    try:
        data = yaml.safe_load(request.yaml_text)
        scenario = Scenario(**data)
    except Exception as e:
        return {"valid": False, "errors": [str(e)], "warnings": []}
    return {"valid": True, "errors": [], "warnings": validate_scenario(scenario)}


@app.get("/api/traces/{trace_id}")
def api_get_trace(trace_id: str, session: Session = Depends(db_session)) -> dict[str, Any]:
    trace = get_trace(session, trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
    return trace_payload(trace)


@app.get("/api/scenario-results/{result_id}/trace")
def api_get_result_trace(result_id: str, session: Session = Depends(db_session)) -> dict[str, Any]:
    result = session.get(ScenarioResultDB, result_id)
    if result is None or result.trace is None:
        raise HTTPException(status_code=404, detail=f"Trace not found for result: {result_id}")
    return trace_payload(result.trace)


@app.post("/api/compare")
def api_compare_runs(request: CompareRequest, session: Session = Depends(db_session)) -> dict[str, Any]:
    base = get_run(session, request.base_run_id)
    candidate = get_run(session, request.candidate_run_id)
    if base is None or candidate is None:
        raise HTTPException(status_code=404, detail="Both runs must exist before comparison.")
    base_payload = {"summary": base.summary_json, "results": [r.result_json for r in base.scenario_results]}
    candidate_payload = {
        "summary": candidate.summary_json,
        "results": [r.result_json for r in candidate.scenario_results],
    }
    return compute_regression(base_payload, candidate_payload).model_dump(mode="json")


@app.post("/api/reports/{run_id}/generate")
def api_generate_report(
    run_id: str,
    format: str = "json",
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    payload = {"summary": run.summary_json, "results": [r.result_json for r in run.scenario_results]}
    html = None
    content = payload
    if format == "html":
        html = render_html(payload["summary"], payload["results"])
        content = None
    elif format in {"markdown", "md"}:
        content = {"markdown": render_markdown(payload["summary"], payload["results"])}
    report = ReportDB(run_id=run.id, format=format, content=content, html_content=html)
    session.add(report)
    session.commit()
    return {"report_id": report.id, "run_id": run.id, "format": format}


@app.get("/api/reports/{report_id}")
def api_get_report(report_id: str, session: Session = Depends(db_session)) -> dict[str, Any]:
    report = session.get(ReportDB, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    return {
        "report_id": report.id,
        "run_id": report.run_id,
        "format": report.format,
        "content": report.content,
        "html_content": report.html_content,
        "created_at": report.created_at.isoformat(),
    }


@app.get("/api/reports/{report_id}/download")
def api_download_report(report_id: str, session: Session = Depends(db_session)) -> dict[str, Any]:
    return api_get_report(report_id, session)


@app.get("/api/projects")
def api_list_projects(session: Session = Depends(db_session)) -> dict[str, Any]:
    projects = session.query(Project).order_by(Project.created_at.desc()).all()
    return {
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "config": project.config,
                "created_at": project.created_at.isoformat(),
            }
            for project in projects
        ]
    }


@app.post("/api/projects")
def api_create_project(request: ProjectCreate, session: Session = Depends(db_session)) -> dict[str, Any]:
    project = Project(name=request.name, description=request.description, config=request.config)
    session.add(project)
    session.commit()
    return {"id": project.id, "name": project.name}


@app.get("/api/agents")
def api_list_agents(session: Session = Depends(db_session)) -> dict[str, Any]:
    agents = session.query(Agent).order_by(Agent.created_at.desc()).all()
    return {
        "agents": [
            {
                "id": agent.id,
                "project_id": agent.project_id,
                "name": agent.name,
                "adapter_type": agent.adapter_type,
                "config": agent.config,
            }
            for agent in agents
        ]
    }


@app.post("/api/agents")
def api_create_agent(request: AgentCreate, session: Session = Depends(db_session)) -> dict[str, Any]:
    agent = Agent(
        project_id=request.project_id,
        name=request.name,
        adapter_type=request.adapter_type,
        config=request.config,
    )
    session.add(agent)
    session.commit()
    return {"id": agent.id, "name": agent.name}


@app.get("/api/agents/{agent_id}/versions")
def api_list_agent_versions(agent_id: str, session: Session = Depends(db_session)) -> dict[str, Any]:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return {
        "versions": [
            {"id": version.id, "version": version.version, "created_at": version.created_at.isoformat()}
            for version in agent.versions
        ]
    }
