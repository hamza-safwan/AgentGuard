# Custom Plugins

AgentGuard supports plugins through Python entry points.

## Custom Evaluator

`pyproject.toml`:

```toml
[project.entry-points."agentguard.evaluators"]
acme_compliance = "acme.agentguard.evaluators:ComplianceEvaluator"
```

Implementation:

```python
from agentguard.evaluators.base import BaseEvaluator
from agentguard.schemas.evaluator import EvaluatorMeta
from agentguard.schemas.result import EvaluationResult

class ComplianceEvaluator(BaseEvaluator):
    @property
    def meta(self) -> EvaluatorMeta:
        return EvaluatorMeta(
            name="acme_compliance",
            description="Internal compliance check.",
            category="custom",
            deterministic=True,
            default_weight=0.25,
        )

    async def evaluate(self, scenario, run_result, trace):
        return EvaluationResult(
            metric_name="acme_compliance",
            score=1.0,
            passed=True,
            reason="Compliant.",
            evidence=[],
        )
```

Scenario:

```yaml
metrics:
  - acme_compliance
```

## Custom Adapter

```toml
[project.entry-points."agentguard.adapters"]
internal_agent = "acme.agentguard.adapters:InternalAgentAdapter"
```

Adapters must implement the `BaseAgentAdapter` contract and return `AgentRunResult`.

## Custom Mock Catalog

```toml
[project.entry-points."agentguard.mock_tools"]
billing = "acme.agentguard.mocks:CATALOG"
```

```python
from agentguard.tool_runtime.catalog import MockCatalog

def lookup_invoice(invoice_id: str) -> dict:
    return {"invoice_id": invoice_id, "status": "paid"}

CATALOG = MockCatalog(dynamic={"lookup_invoice": lookup_invoice})
```

## Plugin Failure Policy

A bad plugin should not crash the whole runner. AgentGuard logs plugin load failures and continues with available built-ins.

