"""Pytest fixtures supplied by the AgentGuard plugin."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from agentguard.schemas.trace import AgentTrace
from agentguard.sdk.context import pop_trace, push_trace


@pytest.fixture
def agentguard_trace(request: pytest.FixtureRequest) -> Iterator[AgentTrace]:
    """Bind a fresh AgentTrace to the test for the duration of the test body.

    Use together with the SDK decorators: any ``@agentguard.tool`` /
    ``@agentguard.llm_call`` calls inside the test record into this trace, which
    you can then evaluate with ``agentguard.evaluate(t, ...)``.
    """
    t = AgentTrace(scenario_id=request.node.name, runtime="python")
    token = push_trace(t)
    try:
        yield t
    finally:
        pop_trace(token)
