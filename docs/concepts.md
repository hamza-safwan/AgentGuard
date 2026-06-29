# Core Concepts

## Scenario

A scenario is a YAML test case. It defines:

- Which agent adapter to use.
- What input the user sends.
- What behavior is expected.
- Which metrics should score the run.
- Optional thresholds and mocks.

## Adapter

An adapter runs an agent in a framework-specific way and returns a normalized `AgentRunResult`.

Every adapter produces the same `AgentTrace` shape, so evaluators and reports do not need to know whether the agent used LangGraph, HTTP, CrewAI, or another framework.

## AgentTrace

An `AgentTrace` is the stable wire record of an agent run. It contains:

- `trace_id`
- `scenario_id`
- `steps`
- `final_output`
- cost and latency metadata
- runtime and sampling metadata

Trace steps use canonical types:

- `llm_call`
- `tool_call`
- `retrieval`
- `guardrail`
- `handoff`
- `error`
- `final_output`

## Evaluator

An evaluator scores one behavior. It returns:

- metric name
- score from `0.0` to `1.0`
- pass/fail
- reason
- evidence

## Scoring

AgentGuard aggregates evaluator results into:

- overall score
- security score
- RAG score
- tool score
- deployment recommendation

The CLI can fail CI using score thresholds.

## Mock Catalog

A mock catalog is a deterministic set of tool responses. Scenarios can define mocks inline or load them from plugin catalogs. This makes tool-calling tests repeatable.

## SDK Instrumentation

The Python and JavaScript SDKs let users create traces directly inside code. This is useful when:

- The agent does not fit a framework adapter.
- You want lightweight unit tests.
- You want production observability.

