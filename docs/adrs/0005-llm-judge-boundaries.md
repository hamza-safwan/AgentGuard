# ADR 0005: LLM-as-Judge Is Bounded, Cacheable, and Skippable

## Status

Accepted

## Context

Some metrics (response quality, policy compliance, RAG faithfulness, prompt-injection compliance) are inherently subjective. Rule-based evaluators can't catch them. LLM-as-judge is the standard answer, but it introduces three problems:

1. **Cost.** Every CI run hitting a paid LLM is unattractive.
2. **Non-determinism.** Different runs of the same scenario score differently, hurting regression-diff signal.
3. **Hard dependency.** A user without an API key shouldn't be locked out of AgentGuard.

## Decision

- LLM-judge evaluators (`task_success`, `response_quality`, `policy_compliance`, `rag_grounding` faithfulness component, `prompt_injection` judge component) read the model name from `AGENTGUARD_JUDGE_MODEL` (default `gpt-4.1-mini`) and the API key from `OPENAI_API_KEY`.
- If `AGENTGUARD_SKIP_LLM_JUDGE=1` (or `--skip-llm-judge` is passed) **or** there is no API key, every LLM-judge evaluator returns `score=1.0, passed=True` with `reason='LLM judge skipped'`. The CI gate then runs purely on deterministic evaluators.
- Judge calls are made at temperature 0 to maximise reproducibility. Output is parsed via a strict JSON schema with a tolerant fallback.
- The `prompt_injection` evaluator weights its judge component at only 30% — the deterministic forbidden-tool (40%) and system-prompt-leakage (30%) checks dominate, so a flaky judge can't single-handedly fail a scenario.

## Consequences

- **Pros:** Zero-config first run; no API key required. CI pipelines can opt out of all LLM cost. Deterministic evaluators always carry the load. Regression diffs stay meaningful even with judges enabled, because they're a small fraction of the score.
- **Cons:** `score=1.0` on skip is optimistic — quality metrics that depend on the judge effectively disappear. Documented prominently in the security model and README.
- **Future:** Cached judge responses keyed on `(scenario_id, agent_version, final_output_hash)` are planned for 0.2 to make LLM-judged CI runs near-free for unchanged outputs.
