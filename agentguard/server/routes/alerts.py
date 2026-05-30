"""``/api/v2/alerts/*`` - alert rule CRUD + manual trigger."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agentguard.server.dependencies import db_session
from agentguard.storage.models import AlertEvent, AlertRule

router = APIRouter(prefix="/api/v2/alerts", tags=["observability"])


class AlertDestination(BaseModel):
    type: str = Field(..., description="webhook|slack|generic")
    url: str


class AlertRuleCreate(BaseModel):
    project_id: str
    name: str
    metric: str
    agent_name: str | None = None
    window_seconds: int = 3600
    threshold_drop_pct: float = 5.0
    destinations: list[AlertDestination] = Field(default_factory=list)


@router.get("/rules")
def list_rules(
    project_id: str | None = None,
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    q = session.query(AlertRule)
    if project_id:
        q = q.filter(AlertRule.project_id == project_id)
    rules = q.order_by(AlertRule.created_at.desc()).all()
    return {
        "rules": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "name": r.name,
                "agent_name": r.agent_name,
                "metric": r.metric,
                "window_seconds": r.window_seconds,
                "threshold_drop_pct": r.threshold_drop_pct,
                "destinations": r.destinations,
                "enabled": r.enabled,
            }
            for r in rules
        ]
    }


@router.post("/rules", status_code=201)
def create_rule(
    payload: AlertRuleCreate,
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    rule = AlertRule(
        project_id=payload.project_id,
        name=payload.name,
        metric=payload.metric,
        agent_name=payload.agent_name,
        window_seconds=payload.window_seconds,
        threshold_drop_pct=payload.threshold_drop_pct,
        destinations=[d.model_dump() for d in payload.destinations],
    )
    session.add(rule)
    session.commit()
    return {"id": rule.id}


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, session: Session = Depends(db_session)) -> None:
    rule = session.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found.")
    session.delete(rule)
    session.commit()


@router.get("/events")
def list_events(
    rule_id: str | None = None,
    limit: int = 100,
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    q = session.query(AlertEvent)
    if rule_id:
        q = q.filter(AlertEvent.rule_id == rule_id)
    events = q.order_by(AlertEvent.fired_at.desc()).limit(limit).all()
    return {
        "events": [
            {
                "id": e.id,
                "rule_id": e.rule_id,
                "fired_at": e.fired_at.isoformat(),
                "metric_value": e.metric_value,
                "baseline_value": e.baseline_value,
                "payload": e.payload,
            }
            for e in events
        ]
    }


@router.post("/rules/{rule_id}/evaluate")
def evaluate_rule_now(
    rule_id: str,
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    """Manually trigger an evaluation of one rule (BLUEPRINT-7 section 12.4)."""
    from agentguard.jobs.alert_evaluator import evaluate_rule

    rule = session.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found.")
    fired = evaluate_rule(session, rule)
    return {"rule_id": rule.id, "fired": fired}
