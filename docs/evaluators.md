# Evaluators

Evaluators score a single behavior for a single agent run.

## Result Shape

Every evaluator returns:

```json
{
  "metric_name": "forbidden_tool_avoidance",
  "score": 0.0,
  "passed": false,
  "reason": "Agent called forbidden tool issue_refund.",
  "evidence": [{"violations": ["issue_refund"]}]
}
```

## Built-In Metrics

| Category | Metrics |
|---|---|
| Tool use | `required_tool_calls`, `tool_call_correctness`, `forbidden_tool_avoidance` |
| Security | `prompt_injection`, `pii_leakage`, `access_control_compliance` |
| RAG | `rag_grounding` |
| Quality | `task_success`, `response_quality`, `policy_compliance`, `schema_validation` |
| Performance | `cost`, `latency` |

## Deterministic vs LLM-Assisted

Deterministic evaluators inspect trace steps, output text, cost, latency, or schema shape.

LLM-assisted evaluators use `agentguard.judge()`. If no API key is configured or `AGENTGUARD_SKIP_LLM_JUDGE=1`, they skip with a passing score so CI remains usable without paid model calls.

## Choosing Metrics

For tool-calling agents:

```yaml
metrics:
  - required_tool_calls
  - forbidden_tool_avoidance
  - tool_call_correctness
```

For RAG agents:

```yaml
metrics:
  - rag_grounding
  - response_quality
  - policy_compliance
```

For security regression tests:

```yaml
metrics:
  - prompt_injection
  - pii_leakage
  - access_control_compliance
```

## Custom Evaluators

Custom evaluators are registered through Python entry points. See [Custom Plugins](custom-plugins.md).

