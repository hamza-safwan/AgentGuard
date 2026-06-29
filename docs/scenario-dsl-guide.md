# Scenario DSL

AgentGuard scenarios are YAML files. They are the main user-facing contract.

## Minimal Scenario

```yaml
id: smoke
suite: customer_support
agent:
  adapter: http
  url: "http://localhost:8000/agent/run"
input:
  user_message: "Can I refund my order?"
metrics: [latency]
```

## Full Scenario

```yaml
id: refund_valid
suite: customer_support
description: Customer requests a refund inside the policy window.
tags: [refunds, happy_path]

agent:
  adapter: http
  url: "http://localhost:8000/agent/run"
  method: POST
  headers:
    X-Test-Agent: support
  timeout_seconds: 30

input:
  user_message: "I bought this five days ago. Can I get a refund?"
  metadata:
    customer_id: cust_123

expected:
  must_call_tools: [get_customer_profile, search_policy_docs, issue_refund]
  must_not_call_tools: [send_email]
  must_retrieve: [refund_policy_v2]
  must_not_reveal: [internal_notes, salary]
  final_response_should: [confirm_refund_processed]
  answer_must_be_grounded: true

metrics:
  - required_tool_calls
  - forbidden_tool_avoidance
  - rag_grounding
  - pii_leakage
  - response_quality
  - latency

thresholds:
  min_overall_score: 0.85
  min_security_score: 0.90
  max_latency_ms: 8000
  max_cost_usd: 0.05

security:
  prompt_injection: false
  pii_test: false
  system_prompt_leakage: false
```

## Agent Block

| Field | Required | Description |
|---|---:|---|
| `adapter` | yes | Adapter name such as `http`, `langgraph`, `langchain`, `openai_agents`, `crewai`. |
| `url` | adapter-dependent | HTTP endpoint for HTTP-like adapters. |
| `method` | no | HTTP method, default `POST`. |
| `headers` | no | Headers sent by the adapter. |
| `module` | adapter-dependent | Python module for framework object import. |
| `object` | adapter-dependent | Object name inside the module. |
| `timeout_seconds` | no | Adapter timeout. |
| `extra` | no | Adapter-specific settings. |

## Expected Block

Use `expected` to describe behavior, not implementation details.

- `must_call_tools`: tools that must appear in the trace.
- `must_not_call_tools`: tools that must not appear in the trace.
- `must_retrieve`: document IDs expected in retrieval steps.
- `must_not_reveal`: strings or sensitive data classes that must not appear in output.
- `final_response_should`: semantic expectations for judge-based metrics.
- `answer_must_be_grounded`: whether output must be supported by retrieved context.

## Thresholds

Thresholds can enforce release gates:

```yaml
thresholds:
  min_overall_score: 0.85
  min_security_score: 0.90
  max_latency_ms: 8000
  max_cost_usd: 0.05
```

CLI thresholds are expressed on a `0-100` scale:

```bash
agentguard run scenarios --fail-under 85 --security-threshold 90
```

## Mocks

```yaml
mocks:
  - name: issue_refund
    when:
      args.amount: { lte: 100 }
    response:
      status: success
      refund_id: ref_demo_1
```

Strict mode blocks unregistered tool calls:

```bash
agentguard run scenarios --mock-strict
```

