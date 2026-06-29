# ADR 0002: Framework-Agnostic Adapters

## Status

Accepted

## Context

Agent frameworks (LangGraph, LangChain, OpenAI Agents SDK, CrewAI, …) iterate quickly and disagree on data shapes, callbacks, and tracing. We must run agents from any of them and still apply the same evaluators, scoring, dashboard, and reports.

Two routes were considered:

1. **Per-framework evaluators.** Each evaluator knows about every framework's native trace shape.
2. **Adapter normalisation.** Every adapter converts framework output to a single internal `AgentTrace`. Evaluators only see the normalised model.

Option 1 means O(adapters × evaluators) coupling and ties evaluator quality to the user's framework choice. Option 2 means O(adapters + evaluators) and lets new evaluators land without touching adapters at all.

## Decision

All adapters implement `BaseAgentAdapter` and return an `AgentRunResult` containing a normalised `AgentTrace` with seven step types: `llm_call`, `tool_call`, `retrieval`, `guardrail`, `handoff`, `error`, `final_output`.

Framework-specific data is preserved in `TraceStep.metadata` for forensic inspection, but evaluators MUST only depend on the normalised contract.

## Consequences

- **Pros:** Evaluators, scoring, dashboard, and reports are framework-agnostic. New adapters plug in without ecosystem-wide changes. Trace-shape contract tests catch normalisation regressions early.
- **Cons:** Adapter authors carry the burden of normalisation. Some framework-native richness is flattened. Mitigated by `metadata` and by per-adapter sample agents under `examples/`.
- **Forcing function:** `tests/contract/test_adapters_and_evaluators.py` requires every adapter to satisfy the trace contract.
