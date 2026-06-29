# ADR 0001: Trace-First Evaluation

## Status

Accepted

## Decision

AgentGuard evaluates final answers and intermediate trace steps.

## Consequences

This makes failures explainable and framework-agnostic. Adapter quality matters because weak traces reduce evaluator precision.
