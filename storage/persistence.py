"""CLI-facing persistence functions."""

from __future__ import annotations

from agentguard.schemas.report import RunSummary
from agentguard.schemas.result import ScenarioResult
from agentguard.storage.db import init_db, session_scope
from agentguard.storage.repositories import save_run_payload


def save_run(summary: RunSummary, results: list[ScenarioResult]) -> str:
    init_db()
    with session_scope() as session:
        run = save_run_payload(session, summary, results)
        return run.id
