# ADR 0006: In-Process Trace Context for the SDK

## Status

Accepted (v0.2)

## Context

v0.1 only built `AgentTrace` objects inside adapters. The v0.2 SDK
(`@agentguard.tool`, `agentguard.trace()`, `agentguard.evaluate()`) and the
pytest plugin both need the same `AgentTrace` to be built **inside arbitrary
user code** - from inside a `with` block, from a pytest test body, from
production code emitting traces over the wire.

Two options:

1. **Thread the trace through every call.** Decorators take a `trace=` kwarg;
   evaluators receive a trace argument; the user is responsible for plumbing.
2. **Process-wide active trace.** A `ContextVar` holds the currently active
   trace; decorators read/write it transparently.

Option 1 is cleaner in isolation but requires invasive refactors in user code.
Option 2 matches how `logging`, OpenTelemetry, LangSmith, and Jaeger all expose
"current span" / "current trace" handles.

## Decision

`agentguard/sdk/context.py` exposes a `ContextVar`-backed active trace stack:

- `current_trace()` returns the trace bound to the active async/thread context.
- `with agentguard.trace(...) as t:` binds a fresh trace for the duration of
  the block.
- `record_step(step)` is a silent no-op when no trace is active, so decorated
  functions are safe to leave in production code paths.
- `push_trace(t) / pop_trace(token)` is the imperative form used by the pytest
  plugin to attach a fixture-scoped trace.

`ContextVar` semantics give us correct fork-on-`asyncio.gather` for free.
Thread pools require an explicit `copy_context().run(...)` helper, exposed as
`agentguard.sdk.run_in_thread`.

## Consequences

- The SDK, pytest plugin, observability transport, and JS SDK
  (`AsyncLocalStorage`-backed) all share one mental model.
- Users never have to thread `trace=` kwargs.
- Tests must reset the contextvar (or scope traces with `with`) - documented in
  the SDK reference.
- Decorating a function with no active trace must remain a no-op forever - this
  is a forward-compatibility commitment.
