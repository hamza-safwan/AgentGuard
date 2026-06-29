# ADR 0008: Plugin Discovery via Python Entry Points

## Status

Accepted (v0.2)

## Context

Three v0.2 surfaces benefit from third-party extension:

1. **Custom evaluators** - companies have private metrics
   (domain-specific compliance, regulator-specific PII).
2. **Framework adapters** - users want to register adapters for frameworks the
   core team hasn't shipped yet.
3. **Mock-tool catalogs** - users want shared catalogs of mocked tools without
   forking the package.

Without a discovery mechanism, users fork. Forks rot. Bug reports get
fragmented. Everything regresses.

## Decision

Adopt the standard Python entry-point mechanism for all three:

| Group | Loaded as | Used by |
|-------|-----------|---------|
| `agentguard.evaluators` | `BaseEvaluator` subclass | `get_evaluator` |
| `agentguard.adapters` | `BaseAgentAdapter` subclass | `get_adapter` |
| `agentguard.mock_tools` | `MockCatalog` / dict / callable | mock-tools server |

Discovery happens once per process behind `@lru_cache(maxsize=1)`. A failing
entry point logs a warning and is skipped - we **never** crash the runner
because of one bad plugin.

Built-in items always win when names collide; the runner consults the plugin
table only as a fallback.

## Consequences

- Third-party authors publish a regular Python package with one entry-point
  block in `pyproject.toml`. No fork required.
- Plugin discovery has zero runtime cost after the first call.
- A misbehaving plugin can't take down a CI run, only its own metric / scenario.
- Users see all available evaluators / adapters via `agentguard evaluators list`
  / `agentguard list-adapters`, with a `source` column to distinguish built-in
  from plugin.
