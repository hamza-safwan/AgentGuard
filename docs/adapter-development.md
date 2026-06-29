# Adapter Development

Adapters connect AgentGuard to an agent runtime. Every adapter must implement `BaseAgentAdapter` and return `AgentRunResult`.

Minimum contract:

```python
class MyAdapter(BaseAgentAdapter):
    @property
    def meta(self) -> AdapterMeta:
        ...

    async def run(self, scenario: Scenario) -> AgentRunResult:
        ...

    async def health_check(self) -> bool:
        ...
```

Rules:

- Preserve the final output as a string.
- Normalize intermediate behavior into `AgentTrace.steps`.
- Use `tool_call` for tool executions, `retrieval` for document fetches, `llm_call` for model calls, `guardrail` for safety checks, and `error` for recoverable failures.
- Raise `AdapterError` for execution failures.
