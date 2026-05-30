"""Serialize SQLAlchemy rows into dashboard-friendly JSON."""

from __future__ import annotations

from typing import Any

from agentguard.storage.models import Run, ScenarioResultDB, TraceDB


def run_summary(run: Run) -> dict[str, Any]:
    agent = run.agent_version.agent if run.agent_version else None
    return {
        "run_id": run.id,
        "agent_name": agent.name if agent else "unknown-agent",
        "agent_version": run.agent_version.version if run.agent_version else "unknown",
        "suite": run.suite.name if run.suite else "default",
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "total_scenarios": run.total_scenarios,
        "passed_scenarios": run.passed_scenarios,
        "failed_scenarios": run.failed_scenarios,
        "overall_score": run.overall_score,
        "security_score": run.security_score,
        "rag_score": run.rag_score,
        "tool_score": run.tool_score,
        "avg_cost_usd": run.avg_cost_usd,
        "avg_latency_ms": run.avg_latency_ms,
        "p95_latency_ms": run.p95_latency_ms,
        "deployment_recommendation": run.deployment_recommendation,
        "triggered_by": run.triggered_by,
        "summary": run.summary_json,
    }


def scenario_result(result: ScenarioResultDB) -> dict[str, Any]:
    trace_id = result.trace.id if result.trace else None
    return {
        "id": result.id,
        "run_id": result.run_id,
        "scenario_id": result.scenario_key,
        "status": result.status,
        "passed": result.status == "passed",
        "overall_score": result.overall_score,
        "failure_summary": result.failure_summary,
        "final_output": result.final_output,
        "cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
        "trace_id": trace_id,
        "evaluations": [
            {
                "metric_name": ev.metric_name,
                "score": ev.score,
                "passed": ev.passed,
                "reason": ev.reason,
                "evidence": ev.evidence,
            }
            for ev in result.evaluations
        ],
        "raw": result.result_json,
    }


def trace_payload(trace: TraceDB) -> dict[str, Any]:
    payload = dict(trace.trace_json)
    payload["steps"] = sorted(
        [
            {
                "step_id": step.id,
                "step_index": step.step_index,
                "type": step.step_type,
                "name": step.name,
                "input": step.input,
                "output": step.output,
                "metadata": step.metadata_json,
                "latency_ms": step.latency_ms,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "ended_at": step.ended_at.isoformat() if step.ended_at else None,
            }
            for step in trace.steps
        ],
        key=lambda item: item.get("step_index", 0),
    )
    return payload


def run_detail(run: Run) -> dict[str, Any]:
    return {
        **run_summary(run),
        "results": [scenario_result(result) for result in run.scenario_results],
        "security_findings": run.summary_json.get("security_findings", []),
        "metric_summaries": run.summary_json.get("metric_summaries", []),
    }
