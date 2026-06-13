"""Trace-ingest worker (BLUEPRINT-7 section 12.4).

Each ingested ``AgentTrace`` is converted into a one-scenario ``Run`` row
flagged ``source='observability', triggered_by='observability'`` and persisted
through the existing repository layer. When a Redis broker is reachable, we
hand the work to Dramatiq; otherwise we process inline so single-node
deployments still work.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from agentguard.core.scoring import aggregate_results, score_scenario
from agentguard.schemas.result import EvaluationResult, ScenarioResult
from agentguard.schemas.trace import AgentTrace
from agentguard.storage.db import session_scope
from agentguard.storage.repositories import save_run_payload

_log = logging.getLogger(__name__)


def _trace_to_scenario_result(trace: AgentTrace) -> ScenarioResult:
    """Build a single ScenarioResult from an ingested trace, with no evaluators run.

    Live traces don't carry expected-behaviour metadata, so the worker stores
    them as a passing 1.0 evaluation; downstream alert rules read the raw
    metric scores from the saved trace and ScenarioResult, not from this stub.
    """
    eval_stub = EvaluationResult(
        metric_name="ingested",
        score=1.0,
        passed=True,
        reason="Trace ingested via /api/v2/traces/ingest.",
    )
    return score_scenario(
        scenario_id=trace.scenario_id or "live",
        suite="observability",
        evaluations=[eval_stub],
        final_output=trace.final_output or "",
        trace=trace,
        cost_usd=trace.total_cost_usd,
        latency_ms=trace.total_latency_ms,
    )


def _persist(trace: AgentTrace, project_id: str) -> str:
    result = _trace_to_scenario_result(trace)
    summary = aggregate_results(
        [result],
        run_id=f"obs_{trace.trace_id[:8]}",
        agent_name=trace.agent_name or "unknown",
        agent_version=trace.agent_version or "live",
        suite="observability",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
    )
    with session_scope() as session:
        run = save_run_payload(
            session,
            summary,
            [result],
            project_name="Default Project",
            triggered_by="observability",
        )
        run.source = "observability"
        run.sampling_meta = trace.sampling
        return run.id


# ---------------------------------------------------------------------------
# Dramatiq integration (lazy / optional)
# ---------------------------------------------------------------------------


def _have_dramatiq() -> bool:
    try:
        import dramatiq  # noqa: F401
    except Exception:
        return False
    return bool(os.getenv("REDIS_URL"))


def _build_dramatiq_actor():
    import dramatiq
    from dramatiq.brokers.redis import RedisBroker

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if not isinstance(getattr(dramatiq, "_default_broker", None), RedisBroker):
        broker = RedisBroker(url=redis_url)
        dramatiq.set_broker(broker)

    @dramatiq.actor(queue_name="agentguard.ingest", max_retries=3)
    def _ingest(trace_dict: dict[str, Any], project_id: str) -> None:
        try:
            trace = AgentTrace(**trace_dict)
            _persist(trace, project_id)
        except Exception:
            _log.exception("ingest worker failed for trace %s", trace_dict.get("trace_id"))
            raise

    return _ingest


_ACTOR = None


def enqueue_trace(trace: AgentTrace, *, project_id: str) -> None:
    """Hand a trace off to the worker (Dramatiq if available, inline otherwise)."""
    if _have_dramatiq():
        global _ACTOR
        if _ACTOR is None:
            _ACTOR = _build_dramatiq_actor()
        _ACTOR.send(trace.model_dump(mode="json"), project_id)
        return
    # Inline fallback - ingest endpoint stays responsive but persistence is sync.
    try:
        _persist(trace, project_id)
    except Exception:
        _log.exception("inline ingest failed for trace %s", trace.trace_id)
