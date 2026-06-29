# ADR 0007: Wire-Format Versioning via Generated JSON Schemas

## Status

Accepted (v0.2)

## Context

The Python SDK, the JS SDK, and the v0.3 observability ingest endpoint all
need to speak the same `AgentTrace` shape. Pydantic models live in the Python
package; the JS SDK can't depend on them. Without an out-of-band contract,
even small Pydantic-side refactors would silently break the JS SDK and any
third-party tools consuming the wire format.

## Decision

- Generate JSON Schemas from the Pydantic models into `schemas/v1/` via
  `python -m agentguard.schemas.export`.
- Check the generated files into git and `git diff --exit-code` them in CI to
  block any silent schema drift.
- Include `"$schema": "https://schemas.agentguard.dev/v1/trace.json"` in every
  ingestion payload so older readers can detect a major version bump.
- The schema directory is **versioned** (`v1/`, `v2/`). Within a major:
  additive changes only. Across a major: parallel directories with a 6-month
  deprecation window.
- The JS SDK's TypeScript types are codegen'd from the same schemas via
  `json-schema-to-typescript`. CI also `git diff --exit-code`s the generated
  `src/schema.ts`.

## Consequences

- Pydantic and TypeScript types are now structurally guaranteed to agree.
- A breaking Python-side change *requires* a v2 schema directory before it can
  land - a heavyweight forcing function we accept on purpose.
- Third-party tools (and the future Go / Rust SDK if it lands) consume the
  same canonical schemas with no Python dependency.
- Users on older SDKs continue to work because v1 is frozen until at least
  v2.0 of AgentGuard.
