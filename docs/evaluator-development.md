# Evaluator Development

Evaluators score one metric for one scenario result.

Minimum contract:

```python
class MyEvaluator(BaseEvaluator):
    @property
    def meta(self) -> EvaluatorMeta:
        ...

    async def evaluate(self, scenario, run_result, trace) -> EvaluationResult:
        ...
```

Evaluator rules:

- Scores must be bounded from `0.0` to `1.0`.
- `reason` must explain the pass or failure.
- `evidence` should contain machine-readable context for reports and the dashboard.
- Prefer deterministic checks before LLM-as-judge checks.
