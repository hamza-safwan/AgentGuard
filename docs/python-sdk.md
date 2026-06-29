# Python SDK

The Python SDK is for direct instrumentation, local evaluation, pytest usage, and observability.

## Install

```bash
pip install agentguard
```

## Trace a Block

```python
import agentguard

with agentguard.trace(scenario_id="refund_check", agent_name="support") as trace:
    trace.final_output = "Refunds after 30 days require escalation."
```

## Tool Decorator

```python
import agentguard

@agentguard.tool("search_policy_docs")
def search_policy_docs(query: str) -> dict:
    return {"documents": [{"doc_id": "refund_policy_v2"}]}

with agentguard.trace(scenario_id="refund_check") as trace:
    search_policy_docs("refund policy")
```

## Evaluate a Trace

```python
result = agentguard.evaluate(
    trace,
    metrics=["required_tool_calls", "pii_leakage"],
    must_call_tools=["search_policy_docs"],
)

assert result.passed
```

## One-Shot Judge

```python
verdict = agentguard.judge(
    response="The refund was issued.",
    criteria="The agent should not issue refunds after 30 days.",
)
```

If LLM judging is unavailable, set:

```bash
export AGENTGUARD_SKIP_LLM_JUDGE=1
```

## Redaction

Use SDK scrubbers and avoid capturing secrets in test output. The SDK is designed to truncate and redact common sensitive keys, but users should still avoid passing raw credentials through traces.

