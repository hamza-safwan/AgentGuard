"""Regression diff between two run JSON payloads."""

from __future__ import annotations

from typing import Any

from agentguard.schemas.report import RegressionDelta, RegressionReport


def _metric_score(summary: dict, metric: str) -> float:
    direct_keys = {
        "overall_score": "overall_score",
        "security_score": "security_score",
        "rag_score": "rag_score",
        "tool_score": "tool_score",
    }
    if metric in direct_keys:
        return float(summary.get(direct_keys[metric], 0.0))
    for ms in summary.get("metric_summaries", []):
        if ms.get("metric_name") == metric:
            return float(ms.get("average_score", 0.0)) * 100
    return 0.0


def compute_regression(base: dict, candidate: dict) -> RegressionReport:
    base_summary = base["summary"]
    cand_summary = candidate["summary"]

    metrics_to_compare = ["overall_score", "security_score", "rag_score", "tool_score"]
    seen = set(metrics_to_compare)
    for ms in base_summary.get("metric_summaries", []) + cand_summary.get("metric_summaries", []):
        name = ms.get("metric_name")
        if name and name not in seen:
            metrics_to_compare.append(name)
            seen.add(name)

    deltas: list[RegressionDelta] = []
    for metric in metrics_to_compare:
        b = _metric_score(base_summary, metric)
        c = _metric_score(cand_summary, metric)
        delta = round(c - b, 2)
        deltas.append(
            RegressionDelta(
                metric_name=metric,
                base_score=round(b, 2),
                candidate_score=round(c, 2),
                delta=delta,
                regressed=delta < -1.0,
            )
        )

    base_failed = set(_failed_ids(base))
    cand_failed = set(_failed_ids(candidate))
    new_failures = sorted(cand_failed - base_failed)
    fixed = sorted(base_failed - cand_failed)

    overall_delta = next((d.delta for d in deltas if d.metric_name == "overall_score"), 0.0)
    security_delta = next((d.delta for d in deltas if d.metric_name == "security_score"), 0.0)
    if security_delta < -5 or overall_delta < -5 or new_failures:
        recommendation = "Do not deploy candidate: significant regression."
    elif security_delta < -1 or overall_delta < -1:
        recommendation = "Investigate before deploying: minor regression detected."
    else:
        recommendation = "Candidate is safe to deploy."

    return RegressionReport(
        base_run_id=base_summary["run_id"],
        candidate_run_id=cand_summary["run_id"],
        base_version=base_summary.get("agent_version", "?"),
        candidate_version=cand_summary.get("agent_version", "?"),
        deltas=deltas,
        new_failures=new_failures,
        fixed_scenarios=fixed,
        recommendation=recommendation,
    )


def _failed_ids(run: dict) -> list[str]:
    summary_ids = run.get("summary", {}).get("failed_scenario_ids") or []
    if summary_ids:
        return summary_ids
    return [r["scenario_id"] for r in run.get("results", []) if not r.get("passed")]


__all__ = ["compute_regression"]


# Type alias re-export for convenience
RegressionInput = dict[str, Any]
