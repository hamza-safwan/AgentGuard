"""Score in-memory traces against ad-hoc criteria or a YAML scenario.

These helpers reuse ``agentguard.core.scoring`` and the evaluator registry so
the SDK and the CLI runner produce byte-identical scorecards for the same
inputs. The sync wrappers (``evaluate``/``evaluate_scenario``) safely run their
async counterparts even when called from inside a running event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from agentguard.core.registry import get_evaluator
from agentguard.core.scenario_loader import load_scenario
from agentguard.core.scoring import score_scenario
from agentguard.schemas.result import AgentRunResult, EvaluationResult, ScenarioResult
from agentguard.schemas.scenario import (
    AgentConfig,
    ExpectedBehavior,
    Scenario,
    ScenarioInput,
)
from agentguard.schemas.trace import AgentTrace


def _build_adhoc_scenario(
    *,
    trace: AgentTrace,
    metrics: list[str],
    expected: ExpectedBehavior,
) -> Scenario:
    return Scenario(
        id=trace.scenario_id or "ad-hoc",
        suite="ad-hoc",
        agent=AgentConfig(adapter="http", url="http://localhost"),
        input=ScenarioInput(user_message=""),
        expected=expected,
        metrics=metrics,
    )


async def aevaluate(
    trace: AgentTrace,
    *,
    metrics: list[str],
    must_call_tools: list[str] | None = None,
    must_not_call_tools: list[str] | None = None,
    must_retrieve: list[str] | None = None,
    must_not_reveal: list[str] | None = None,
    final_response_should: list[str] | None = None,
    answer_must_be_grounded: bool = False,
) -> ScenarioResult:
    """Async: score an in-memory trace against ad-hoc expected-behavior criteria."""
    expected = ExpectedBehavior(
        must_call_tools=must_call_tools or [],
        must_not_call_tools=must_not_call_tools or [],
        must_retrieve=must_retrieve or [],
        must_not_reveal=must_not_reveal or [],
        final_response_should=final_response_should or [],
        answer_must_be_grounded=answer_must_be_grounded,
    )
    scenario = _build_adhoc_scenario(trace=trace, metrics=metrics, expected=expected)
    run_result = AgentRunResult(
        final_output=trace.final_output or "",
        trace=trace,
    )

    evaluations: list[EvaluationResult] = []
    for metric in metrics:
        try:
            evaluator = get_evaluator(metric)
            evaluations.append(await evaluator.evaluate(scenario, run_result, trace))
        except Exception as exc:
            evaluations.append(
                EvaluationResult(
                    metric_name=metric,
                    score=0.0,
                    passed=False,
                    reason=f"Evaluator error: {exc}",
                )
            )

    return score_scenario(
        scenario_id=scenario.id,
        suite=scenario.suite,
        evaluations=evaluations,
        final_output=run_result.final_output,
        trace=trace,
        cost_usd=trace.total_cost_usd,
        latency_ms=trace.total_latency_ms,
    )


async def aevaluate_scenario(
    trace: AgentTrace, scenario_path: str | Path
) -> ScenarioResult:
    """Async: evaluate an in-memory trace against the metrics + expected of a YAML scenario."""
    scenario = load_scenario(Path(scenario_path))
    return await aevaluate(
        trace,
        metrics=scenario.metrics,
        must_call_tools=scenario.expected.must_call_tools,
        must_not_call_tools=scenario.expected.must_not_call_tools,
        must_retrieve=scenario.expected.must_retrieve,
        must_not_reveal=scenario.expected.must_not_reveal,
        final_response_should=scenario.expected.final_response_should,
        answer_must_be_grounded=scenario.expected.answer_must_be_grounded,
    )


def _run_sync(coro):
    """Run a coroutine even if the caller is already inside an event loop.

    Inside a running loop (e.g. Jupyter, FastAPI handler), ``asyncio.run`` would
    raise ``RuntimeError``. We detect that case and fall back to a fresh thread
    with its own loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import concurrent.futures

    def _runner():
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_runner).result()


def evaluate(trace: AgentTrace, **kwargs) -> ScenarioResult:
    """Sync wrapper around :func:`aevaluate`. Safe inside a running event loop."""
    return _run_sync(aevaluate(trace, **kwargs))


def evaluate_scenario(trace: AgentTrace, scenario_path: str | Path) -> ScenarioResult:
    """Sync wrapper around :func:`aevaluate_scenario`."""
    return _run_sync(aevaluate_scenario(trace, scenario_path))
