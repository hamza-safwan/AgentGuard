"""In-process trace context (BLUEPRINT-7 section 3.1).

Every v0.2 surface that captures or reads a trace from inside user code goes
through this module. The active trace is held in a ``ContextVar`` so:

* Each ``with agentguard.trace(): ...`` block scopes a fresh trace.
* ``asyncio.gather`` correctly forks the context: each task sees its own copy
  of the active trace.
* No active trace = ``record_step`` is a silent no-op (safe to leave decorators
  in production code paths even when AgentGuard isn't in use).

Thread pools do not propagate ContextVars by default; use
``agentguard.sdk.run_in_thread`` (defined here) when you need that.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Iterator
from concurrent.futures import Executor
from contextlib import contextmanager
from contextvars import ContextVar, Token, copy_context
from typing import Any, TypeVar

from agentguard.schemas.trace import AgentTrace, TraceStep

T = TypeVar("T")

_active: ContextVar[AgentTrace | None] = ContextVar(
    "agentguard_active_trace", default=None
)


def current_trace() -> AgentTrace | None:
    """Return the AgentTrace bound to the current async/thread context, or None."""
    return _active.get()


def push_trace(trace: AgentTrace) -> Token:
    """Push a trace onto the active stack. Pair with ``pop_trace``.

    Used by the pytest plugin to attach the test-bound trace to a fixture.
    """
    return _active.set(trace)


def pop_trace(token: Token) -> None:
    """Restore the previous active trace using a token returned by ``push_trace``."""
    _active.reset(token)


@contextmanager
def trace(
    scenario_id: str = "ad-hoc",
    agent_name: str | None = None,
    agent_version: str | None = None,
) -> Iterator[AgentTrace]:
    """Bind a fresh AgentTrace to the current context for the duration of the block.

    The trace's ``total_latency_ms`` is set on exit. Existing values for
    ``final_output`` / ``total_cost_usd`` are preserved (the user code can set
    them mid-block). On exit the trace is also passed to the observability
    transport (if one has been configured via
    :func:`agentguard.observability.configure`).
    """
    t = AgentTrace(
        scenario_id=scenario_id,
        agent_name=agent_name,
        agent_version=agent_version,
        runtime="python",
    )
    token = _active.set(t)
    started = time.time()
    try:
        yield t
    finally:
        if t.total_latency_ms is None:
            t.total_latency_ms = int((time.time() - started) * 1000)
        _active.reset(token)
        # Lazy import to avoid a circular dependency at module load time.
        try:
            from agentguard.sdk.transport import ship_trace as _ship

            _ship(t)
        except Exception:
            # Observability must never break user code; swallow any error.
            pass


def record_step(step: TraceStep) -> None:
    """Append a step to the active trace. No-op when no trace is active."""
    t = _active.get()
    if t is not None:
        t.steps.append(step)


def run_in_thread(
    executor: Executor, fn: Callable[..., T], *args: Any, **kwargs: Any
) -> Any:
    """Submit ``fn(*args, **kwargs)`` to ``executor`` carrying the current trace context.

    Returns whatever ``executor.submit`` returns (typically a Future). Without
    this helper, threads do not see the active trace because ``ContextVar`` is
    not auto-propagated across thread boundaries.
    """
    ctx = copy_context()
    return executor.submit(ctx.run, fn, *args, **kwargs)


async def with_trace(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    scenario_id: str = "ad-hoc",
    agent_name: str | None = None,
) -> tuple[T, AgentTrace]:
    """Async helper: run ``await coro_factory()`` inside a fresh trace and return both."""
    with trace(scenario_id=scenario_id, agent_name=agent_name) as t:
        result = await coro_factory()
    return result, t
