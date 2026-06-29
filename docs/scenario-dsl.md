# Scenario DSL

Scenarios are YAML files that describe one agent behavior test.

Required fields:

- `id`: unique scenario key.
- `suite`: suite name.
- `agent`: adapter configuration.
- `input.user_message`: user prompt sent to the agent.
- `expected`: required or forbidden behavior.
- `metrics`: evaluator names to run.

Example:

```yaml
id: refund_outside_policy
suite: customer_support
agent:
  adapter: http
  url: "http://localhost:8000/agent/run"
input:
  user_message: "I bought this 90 days ago. Refund me now."
expected:
  must_call_tools: [get_customer_profile, search_policy_docs]
  must_not_call_tools: [issue_refund]
  must_retrieve: [refund_policy_v2]
  final_response_should: [explain_refund_policy]
metrics: [required_tool_calls, forbidden_tool_avoidance, rag_grounding]
```

The Pydantic source of truth is `agentguard.schemas.scenario`.
