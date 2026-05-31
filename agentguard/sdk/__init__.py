"""AgentGuard Python SDK - public, semver-bound surface.

Three primitives:

* ``trace()`` / ``current_trace()`` / ``record_step()`` - capture an
  ``AgentTrace`` from arbitrary Python code via a process-wide async-safe
  ``ContextVar`` (see BLUEPRINT-7 section 3.1).
* ``@tool``, ``@llm_call``, ``@retrieval``, ``@guardrail``, ``@traceable``
  decorators that record one ``TraceStep`` per call.
* ``evaluate()`` / ``evaluate_scenario()`` / ``judge()`` to score a captured
  trace against ad-hoc criteria, a YAML scenario, or a single LLM judgment.

Stability: this module is the v0.2 public SDK. Removing or breaking any name
exported here requires a major version bump and a deprecation cycle.
"""

from agentguard.sdk.context import (
    current_trace,
    pop_trace,
    push_trace,
    record_step,
    trace,
)
from agentguard.sdk.decorators import (
    guardrail,
    llm_call,
    retrieval,
    scrub,
    tool,
    traceable,
)
from agentguard.sdk.evaluate import (
    aevaluate,
    aevaluate_scenario,
    evaluate,
    evaluate_scenario,
)
from agentguard.sdk.judge import judge

__all__ = [
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
    # evaluate
    "aevaluate",
    "aevaluate_scenario",
    "evaluate",
    "evaluate_scenario",
    # judge
    "judge",
]
