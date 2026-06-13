"""Alert-rule evaluator (BLUEPRINT-7 section 12.4 / 12.10).

For each enabled :class:`AlertRule`, compare the rolling-window mean of
``rule.metric`` against the longer-window baseline. If the metric dropped by
more than ``threshold_drop_pct``, persist an :class:`AlertEvent` and POST to
each configured webhook destination.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from agentguard.storage.models import AlertEvent, AlertRule, Run

_log = logging.getLogger(__name__)


_METRIC_FIELDS = {
    "overall_score": Run.overall_score,
    "security_score": Run.security_score,
    "rag_score": Run.rag_score,
    "tool_score": Run.tool_score,
    "avg_cost_usd": Run.avg_cost_usd,
    "avg_latency_ms": Run.avg_latency_ms,
}


def _avg_for(session: Session, rule: AlertRule, since: datetime) -> float | None:
    column = _METRIC_FIELDS.get(rule.metric)
    if column is None:
        return None
    q = session.query(column).filter(Run.started_at >= since)
    if rule.agent_name:
        from agentguard.storage.models import Agent, AgentVersion

        q = (
            q.join(AgentVersion, Run.agent_version_id == AgentVersion.id)
            .join(Agent, AgentVersion.agent_id == Agent.id)
            .filter(Agent.name == rule.agent_name)
        )
    values = [v[0] for v in q.all() if v[0] is not None]
    if not values:
        return None
    return sum(values) / len(values)


def evaluate_rule(session: Session, rule: AlertRule) -> bool:
    """Evaluate one rule. Returns True if it fired (and an event was recorded)."""
    if not rule.enabled:
        return False
    now = datetime.now(UTC)
    window_start = now - timedelta(seconds=rule.window_seconds)
    baseline_start = now - timedelta(seconds=rule.window_seconds * 4)

    current = _avg_for(session, rule, since=window_start)
    if current is None:
        return False
    baseline = _avg_for(session, rule, since=baseline_start)
    if baseline is None or baseline == 0:
        return False

    drop_pct = (baseline - current) / baseline * 100.0
    if drop_pct < rule.threshold_drop_pct:
        return False

    payload = {
        "rule": rule.name,
        "metric": rule.metric,
        "agent_name": rule.agent_name,
        "current": current,
        "baseline": baseline,
        "drop_pct": drop_pct,
        "window_seconds": rule.window_seconds,
        "fired_at": now.isoformat(),
    }
    event = AlertEvent(
        rule_id=rule.id,
        metric_value=current,
        baseline_value=baseline,
        payload=payload,
    )
    session.add(event)
    session.commit()

    for dest in rule.destinations or []:
        if not isinstance(dest, dict):
            continue
        if dest.get("type") in {"webhook", "slack", "generic"} and dest.get("url"):
            try:
                httpx.post(dest["url"], json=payload, timeout=5.0)
            except httpx.HTTPError as exc:
                _log.warning("alert webhook %s failed: %s", dest.get("url"), exc)

    return True


def evaluate_all_rules(session: Session) -> int:
    """Evaluate every enabled rule. Returns the number that fired."""
    fired = 0
    for rule in session.query(AlertRule).filter(AlertRule.enabled.is_(True)).all():
        if evaluate_rule(session, rule):
            fired += 1
    return fired


# ---------------------------------------------------------------------------
# Dramatiq periodic actor (registered when REDIS_URL is set)
# ---------------------------------------------------------------------------


def _build_periodic_actor():
    import os

    import dramatiq
    from dramatiq.brokers.redis import RedisBroker

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if not isinstance(getattr(dramatiq, "_default_broker", None), RedisBroker):
        dramatiq.set_broker(RedisBroker(url=redis_url))

    @dramatiq.actor(queue_name="agentguard.alerts", max_retries=1)
    def _periodic_evaluate() -> None:
        from agentguard.storage.db import session_scope

        with session_scope() as session:
            evaluate_all_rules(session)

    return _periodic_evaluate
