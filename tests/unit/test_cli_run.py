from __future__ import annotations

from datetime import UTC, datetime

from typer.testing import CliRunner

from agentguard.cli import main
from agentguard.cli.commands import run as run_command
from agentguard.core.runner import RunOptions
from agentguard.schemas.report import RunSummary
from agentguard.schemas.result import ScenarioResult
from agentguard.schemas.trace import AgentTrace


def _summary() -> RunSummary:
    now = datetime.now(UTC)
    return RunSummary(
        run_id="run_test",
        agent_name="agent",
        agent_version="dev",
        suite="unit",
        started_at=now,
        finished_at=now,
        total_scenarios=1,
        passed_scenarios=1,
        failed_scenarios=0,
        overall_score=100,
        security_score=100,
        rag_score=100,
        tool_score=100,
        avg_cost_usd=0,
        avg_latency_ms=1,
        deployment_recommendation="deploy_with_monitoring",
    )


def test_run_command_accepts_mock_port_and_strict(monkeypatch) -> None:
    captured: dict[str, RunOptions] = {}

    async def fake_run_path(path, options, agent_name="unknown-agent", suite="default", on_result=None):
        captured["options"] = options
        return _summary(), [
            ScenarioResult(
                scenario_id="s",
                suite="unit",
                passed=True,
                overall_score=1,
                final_output="ok",
                evaluations=[],
                trace=AgentTrace(scenario_id="s"),
            )
        ]

    monkeypatch.setattr(run_command, "run_path", fake_run_path)

    result = CliRunner().invoke(
        main.app,
        [
            "run",
            "scenarios",
            "--output",
            "json",
            "--no-save-db",
            "--mock-port",
            "8123",
            "--mock-strict",
        ],
    )

    assert result.exit_code == 0
    assert captured["options"].mock_port == 8123
    assert captured["options"].mock_strict is True
