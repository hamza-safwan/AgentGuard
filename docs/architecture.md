# Architecture

AgentGuard evaluates LLM agents with scenario files, framework adapters, normalized traces, evaluators, scorecards, and deployment reports.

The key design decision is trace-first evaluation. Every adapter returns an `AgentRunResult` with an `AgentTrace`, and every evaluator scores behavior from that shared contract. This keeps HTTP agents, LangGraph graphs, LangChain chains, OpenAI Agents SDK agents, and CrewAI crews comparable.

## Data Flow

1. Scenario YAML is loaded and validated with Pydantic.
2. The adapter runs the target agent and normalizes calls, retrievals, guardrails, handoffs, and errors into trace steps.
3. Evaluators score required tools, forbidden tools, RAG grounding, PII leakage, prompt injection resistance, cost, latency, and response quality.
4. The scoring engine creates a `RunSummary`.
5. The CLI can write local JSON and Postgres. The dashboard reads from the FastAPI backend.

## Components

- `agentguard.schemas`: stable public models.
- `agentguard.adapters`: framework-specific execution adapters.
- `agentguard.evaluators`: deterministic and LLM-assisted evaluators.
- `agentguard.core`: loader, registry, runner, and scoring.
- `agentguard.storage`: Postgres persistence through SQLAlchemy.
- `agentguard.server`: FastAPI routes for dashboard and integrations.
- `dashboard`: Next.js interface for runs, scenarios, traces, security findings, and reports.
