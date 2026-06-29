# ADR 0004: Postgres Required for Persistence; Opt-In for First Run

## Status

Accepted

## Context

The dashboard, regression compare, and reports all need durable, queryable storage. Two options:

1. **Persistence-required.** Every `agentguard run` writes to Postgres. Setup requires `docker compose up` first.
2. **In-memory by default, persistence opt-in.** First-run `agentguard run` works with no infra; persistence comes online when the user passes `--save-db` or `--save`.

Option 1 is operationally consistent but raises the bar for first-time users (and for CI pipelines that don't need history). Option 2 keeps the friction-free first run that drives adoption.

## Decision

- The reference storage backend is Postgres 16 (matched in Docker Compose, the GitHub Actions service container, and SQLAlchemy connection strings). SQLite is permitted as a test backend (`tests/integration/`) because SQLAlchemy abstracts the dialect.
- `agentguard run` is **opt-in for persistence**: pass `--save-db` for Postgres or `--save` for a local JSON snapshot under `.agentguard/runs/`. The default is in-memory with a Rich-formatted scorecard.
- The dashboard, regression compare, and report generation always require persisted runs.

## Consequences

- **Pros:** A user who `pip install agentguard`s and runs a scenario sees output in seconds, with no infra. Teams that need history opt in by passing one flag. CI pipelines that just want a gate can skip persistence entirely.
- **Cons:** Two code paths (in-memory vs persisted). Mitigated by funneling both through the same `RunSummary` and `ScenarioResult` models.
- **Future:** A native SQLite default for dashboard/reports may land in 0.2 if launch feedback shows Postgres is a real adoption blocker.
