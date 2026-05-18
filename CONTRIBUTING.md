# Contributing to AgentGuard

Thanks for your interest in contributing! AgentGuard is an open-source project that aims to be the default reliability and security gate for LLM agents.

## Quick start

```bash
git clone https://github.com/hamza-safwan/AgentGuard
cd agentguard
pip install -e ".[dev]"
ruff check agentguard tests examples
pytest -ra
```

## Ways to help

- **Add a scenario.** Drop a YAML file in [`scenarios/`](scenarios/). The most useful contributions are realistic failure modes — refund/PII/access-control edge cases, real prompt-injection attempts you've seen in the wild.
- **Add an evaluator.** New metric? Subclass [`BaseEvaluator`](agentguard/evaluators/base.py), register it in [`agentguard/core/registry.py`](agentguard/core/registry.py), add unit tests.
- **Add an adapter.** New framework? Subclass [`BaseAgentAdapter`](agentguard/adapters/base.py), normalise its output into `AgentTrace`, add a sample agent under [`examples/`](examples/), and a contract test under [`tests/contract/`](tests/contract/).
- **Improve the dashboard.** All eight pages live under [`dashboard/app/`](dashboard/app/). Trace viewer polish (the marquee feature) is especially welcome.
- **Write a failure-analysis case study.** Drop a markdown file under [`docs/failure-analysis/`](docs/failure-analysis/) — concrete trace + fix stories are gold for the project.

## Pull request checklist

- [ ] `ruff check agentguard tests examples` passes.
- [ ] `pytest` passes (incl. new tests for new code).
- [ ] If you changed user-facing behavior, update the README and relevant docs in [`docs/`](docs/).
- [ ] If you added a new public API, type-annotate it.
- [ ] Conventional-commits style commit messages preferred (`feat:`, `fix:`, `docs:`, `chore:`).

## Design principles

These are the load-bearing principles for AgentGuard — please keep PRs aligned:

1. **Trace-first evaluation.** Never evaluate only the final answer. Inspect intermediate steps.
2. **Deterministic before subjective.** Rule-based evaluators run first; LLM judges only for what truly needs them.
3. **Framework-agnostic.** All adapters normalise into the same `AgentTrace` model.
4. **Safe testing.** Mock tools prevent real-world side effects.
5. **Explainable failures.** Every `EvaluationResult` carries a non-empty `reason` and `evidence`.
6. **CI-friendly.** CLI runs headlessly and exits non-zero on threshold misses.

## Releasing

Maintainers cut releases by pushing a `vX.Y.Z` tag. The [release workflow](.github/workflows/release.yml) handles PyPI, GHCR, and GitHub release notes.

## Code of conduct

By contributing you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).
