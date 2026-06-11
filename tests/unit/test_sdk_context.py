"""Tests for agentguard.sdk.context (BLUEPRINT-7 section 3.1)."""

from __future__ import annotations

import asyncio

from agentguard.schemas.trace import TraceStep
from agentguard.sdk.context import (
    current_trace,
    pop_trace,
    push_trace,
    record_step,
    trace,
)


def test_no_active_trace_outside_block() -> None:
    assert current_trace() is None
    # record_step is a no-op outside a trace
    record_step(TraceStep(type="tool_call", name="noop"))
    assert current_trace() is None


def test_trace_block_binds_and_unbinds() -> None:
    with trace(scenario_id="t") as t:
        assert current_trace() is t
        record_step(TraceStep(type="tool_call", name="x"))
    assert current_trace() is None
    assert len(t.steps) == 1
    assert t.steps[0].name == "x"
    assert t.total_latency_ms is not None
    assert t.runtime == "python"


def test_nested_traces_dont_collide() -> None:
    with trace(scenario_id="outer") as outer:
        record_step(TraceStep(type="tool_call", name="o1"))
        with trace(scenario_id="inner") as inner:
            assert current_trace() is inner
            record_step(TraceStep(type="tool_call", name="i1"))
        assert current_trace() is outer
        record_step(TraceStep(type="tool_call", name="o2"))
    assert [s.name for s in outer.steps] == ["o1", "o2"]
    assert [s.name for s in inner.steps] == ["i1"]


def test_push_pop_token_round_trip() -> None:
    from agentguard.schemas.trace import AgentTrace

    t = AgentTrace(scenario_id="manual")
    token = push_trace(t)
    try:
        assert current_trace() is t
        record_step(TraceStep(type="tool_call", name="manual"))
    finally:
        pop_trace(token)
    assert current_trace() is None
    assert len(t.steps) == 1


def test_async_concurrency_keeps_traces_separate() -> None:
    async def task(label: str) -> int:
        with trace(scenario_id=label) as t:
            await asyncio.sleep(0)
            record_step(TraceStep(type="tool_call", name=f"step-{label}"))
            await asyncio.sleep(0)
        return len(t.steps)

    async def driver() -> list[int]:
        return list(await asyncio.gather(*(task(str(i)) for i in range(10))))

    counts = asyncio.run(driver())
    assert counts == [1] * 10
