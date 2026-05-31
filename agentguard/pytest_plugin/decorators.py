"""Decorators that turn AgentGuard scenarios into pytest tests."""

from __future__ import annotations

import asyncio
import contextlib
import functools
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from agentguard.core.runner import run_single_scenario
from agentguard.core.scenario_loader import load_scenario, load_scenarios
from agentguard.schemas.result import ScenarioResult
from agentguard.schemas.scenario import Scenario


def _run(scenario: Scenario) -> ScenarioResult:
    """Run a single scenario synchronously, safe inside or outside an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_single_scenario(scenario))

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(lambda: asyncio.run(run_single_scenario(scenario))).result()


def _attach(node, result: ScenarioResult) -> None:
    """Stash a ScenarioResult on the active pytest node for session reporting."""
    with contextlib.suppress(AttributeError):
        node.user_properties.append(("agentguard_result", result))


def scenario(path_or_scenario: str | Path | Scenario) -> Callable:
    """Run a single YAML scenario (or a pre-built Scenario object) as a pytest test.

    The decorated function may accept ``result: ScenarioResult`` as a kwarg::

        @agentguard.scenario("scenarios/customer_support/refund_outside_policy.yaml")
        def test_refund_outside_policy(result):
            assert result.passed
            assert result.overall_score >= 0.85
    """
    if isinstance(path_or_scenario, Scenario):
        loaded = path_or_scenario
    else:
        loaded = load_scenario(Path(path_or_scenario))

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(request: pytest.FixtureRequest, *args: Any, **kwargs: Any) -> Any:
            result = _run(loaded)
            _attach(request.node, result)
            return fn(*args, result=result, **kwargs)

        # Inject `request` so we can stash the result; pytest will provide it.
        wrapper.__signature__ = _signature_with_request(fn)  # type: ignore[attr-defined]
        return pytest.mark.agentguard(wrapper)

    return deco


def suite(path: str | Path) -> Callable:
    """Parametrize a test across every scenario in a directory."""
    scenarios = load_scenarios(Path(path))
    if not scenarios:
        raise FileNotFoundError(f"No scenarios found at {path}")
    ids = [s.id for s in scenarios]

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(
            request: pytest.FixtureRequest,
            scenario: Scenario,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            result = _run(scenario)
            _attach(request.node, result)
            return fn(*args, result=result, scenario=scenario, **kwargs)

        wrapper.__signature__ = _signature_with_request_and_scenario(fn)  # type: ignore[attr-defined]
        wrapper = pytest.mark.parametrize("scenario", scenarios, ids=ids)(wrapper)
        return pytest.mark.agentguard(wrapper)

    return deco


def inline_scenario(
    *,
    agent: dict,
    user_message: str,
    metrics: list[str],
    must_call_tools: list[str] | None = None,
    must_not_call_tools: list[str] | None = None,
    must_retrieve: list[str] | None = None,
    must_not_reveal: list[str] | None = None,
    final_response_should: list[str] | None = None,
    answer_must_be_grounded: bool = False,
    suite: str = "inline",
    description: str | None = None,
    thresholds: dict | None = None,
) -> Callable:
    """Build a Scenario in code and run it as a pytest test."""

    def deco(fn: Callable) -> Callable:
        scenario_obj = Scenario(
            id=fn.__name__,
            suite=suite,
            description=description,
            agent=agent,
            input={"user_message": user_message},
            expected={
                "must_call_tools": must_call_tools or [],
                "must_not_call_tools": must_not_call_tools or [],
                "must_retrieve": must_retrieve or [],
                "must_not_reveal": must_not_reveal or [],
                "final_response_should": final_response_should or [],
                "answer_must_be_grounded": answer_must_be_grounded,
            },
            metrics=metrics,
            thresholds=thresholds,
        )

        @functools.wraps(fn)
        def wrapper(request: pytest.FixtureRequest, *args: Any, **kwargs: Any) -> Any:
            result = _run(scenario_obj)
            _attach(request.node, result)
            return fn(*args, result=result, **kwargs)

        wrapper.__signature__ = _signature_with_request(fn)  # type: ignore[attr-defined]
        return pytest.mark.agentguard(wrapper)

    return deco


def _signature_with_request(fn: Callable):
    """Construct a Signature that prepends a ``request`` parameter for pytest."""
    import inspect

    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    # Drop the synthetic `result` kwarg from the signature pytest sees - we inject it.
    params = [p for p in params if p.name != "result"]
    request_param = inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    return sig.replace(parameters=[request_param, *params])


def _signature_with_request_and_scenario(fn: Callable):
    import inspect

    sig = inspect.signature(fn)
    params = [
        p for p in sig.parameters.values() if p.name not in {"result", "scenario"}
    ]
    return sig.replace(
        parameters=[
            inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("scenario", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            *params,
        ]
    )
