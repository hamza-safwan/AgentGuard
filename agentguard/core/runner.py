"""Scenario runner — orchestrates: load → adapter → evaluators → scoring."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentguard.core.errors import AdapterError
from agentguard.core.registry import get_adapter, get_evaluator
from agentguard.core.scenario_loader import load_scenarios
from agentguard.core.scoring import aggregate_results, score_scenario
from agentguard.schemas.report import RunSummary
from agentguard.schemas.result import EvaluationResult, ScenarioResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace
from agentguard.tool_runtime.runtime import scenario_scope


@dataclass
class RunOptions:
    agent_version: str = "dev"
    fail_under: int | None = None
    security_threshold: int | None = None
    save: bool = False
    parallel: int = 1
    skip_llm_judge: bool = False
    mock_port: int | None = None
    mock_strict: bool = False


def _scenario_to_dict(scenario: Scenario) -> dict:
    """Round-trip a Scenario through dump for the YAML mocks loader."""
    return scenario.model_dump(mode="json")


async def run_single_scenario(
    scenario: Scenario,
    *,
    mock_port: int | None = None,
    mock_strict: bool = False,
) -> ScenarioResult:
    """Run a single scenario end to end and return its scored result.

    If the scenario carries ``mocks:`` or ``mocks_module:`` blocks (BLUEPRINT-7
    section 4) and a mock server is reachable, the mocks are registered for the
    duration of this scenario via ``X-AgentGuard-Scope``. Otherwise the run
    proceeds as before.
    """
    adapter = get_adapter(scenario.agent.adapter)
    scenario_dict = _scenario_to_dict(scenario)

    with scenario_scope(scenario_dict, mock_port=mock_port, strict=mock_strict) as scope_id:
        # Propagate the scope id through the agent config so adapters can set
        # X-AgentGuard-Scope on outgoing tool-server requests.
        if scope_id is not None:
            scenario.agent.headers = {
                **scenario.agent.headers,
                "X-AgentGuard-Scope": scope_id,
            }

        try:
            run_result = await adapter.run(scenario)
        except AdapterError as e:
            return ScenarioResult(
                scenario_id=scenario.id,
                suite=scenario.suite,
                passed=False,
                overall_score=0.0,
                final_output="",
                evaluations=[],
                trace=AgentTrace(scenario_id=scenario.id),
                failure_summary=f"Adapter error: {e}",
            )

    evaluations: list[EvaluationResult] = []
    for metric in scenario.metrics:
        try:
            evaluator = get_evaluator(metric)
            result = await evaluator.evaluate(scenario, run_result, run_result.trace)
        except Exception as e:
            result = EvaluationResult(
                metric_name=metric,
                score=0.0,
                passed=False,
                reason=f"Evaluator error: {e}",
            )
        evaluations.append(result)

    return score_scenario(
        scenario_id=scenario.id,
        suite=scenario.suite,
        evaluations=evaluations,
        final_output=run_result.final_output,
        trace=run_result.trace,
        cost_usd=run_result.trace.total_cost_usd,
        latency_ms=run_result.trace.total_latency_ms,
    )


async def run_scenarios(
    scenarios: list[Scenario],
    parallel: int = 1,
    on_result=None,
    mock_port: int | None = None,
    mock_strict: bool = False,
) -> list[ScenarioResult]:
    """Run a list of scenarios. ``on_result(result)`` is called as each completes."""
    results: list[ScenarioResult] = []
    if parallel <= 1:
        for scenario in scenarios:
            result = await run_single_scenario(
                scenario,
                mock_port=mock_port,
                mock_strict=mock_strict,
            )
            results.append(result)
            if on_result is not None:
                on_result(result)
        return results

    semaphore = asyncio.Semaphore(parallel)

    async def _bounded(s: Scenario) -> ScenarioResult:
        async with semaphore:
            r = await run_single_scenario(
                s,
                mock_port=mock_port,
                mock_strict=mock_strict,
            )
            if on_result is not None:
                on_result(r)
            return r

    return list(await asyncio.gather(*(_bounded(s) for s in scenarios)))


async def run_path(
    path: Path,
    options: RunOptions,
    agent_name: str = "unknown-agent",
    suite: str = "default",
    on_result=None,
) -> tuple[RunSummary, list[ScenarioResult]]:
    """Load scenarios from ``path``, run them, and return the aggregated summary."""
    scenarios = load_scenarios(path)
    if not scenarios:
        raise FileNotFoundError(f"No scenario YAML files found at {path}")

    started = datetime.now(UTC)
    results = await run_scenarios(
        scenarios,
        parallel=options.parallel,
        on_result=on_result,
        mock_port=options.mock_port,
        mock_strict=options.mock_strict,
    )
    finished = datetime.now(UTC)

    suite_name = scenarios[0].suite if scenarios else suite
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    summary = aggregate_results(
        results,
        run_id=run_id,
        agent_name=agent_name,
        agent_version=options.agent_version,
        suite=suite_name,
        started_at=started,
        finished_at=finished,
    )
    return summary, results
