"""AgentGuard: CI/CD reliability and security testing for LLM agents.

Top-level convenience re-exports for the v0.2 SDK so users can write::

    import agentguard

    @agentguard.tool
    def get_customer_profile(customer_id: str) -> dict:
        ...

    with agentguard.trace(scenario_id="prod_chat") as t:
        my_agent.run("hello")

    result = agentguard.evaluate(t, metrics=["forbidden_tool_avoidance"], must_not_call_tools=["issue_refund"])

The ``agentguard.sdk`` namespace is the canonical, semver-bound public surface;
these top-level names are stable aliases to it.
"""

from agentguard.schemas.result import ScenarioResult
from agentguard.schemas.trace import AgentTrace, TraceStep
from agentguard.sdk import (
    aevaluate,
    aevaluate_scenario,
    current_trace,
    evaluate,
    evaluate_scenario,
    guardrail,
    judge,
    llm_call,
    pop_trace,
    push_trace,
    record_step,
    retrieval,
    scrub,
    tool,
    trace,
    traceable,
)

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "AgentTrace",
    "ScenarioResult",
    "TraceStep",
    # context
    "current_trace",
    "pop_trace",
    "push_trace",
    "record_step",
    "trace",
    # decorators
    "guardrail",
    "llm_call",
    "retrieval",
    "scrub",
    "tool",
    "traceable",
    # evaluate / judge
    "aevaluate",
    "aevaluate_scenario",
    "evaluate",
    "evaluate_scenario",
    "judge",
]
