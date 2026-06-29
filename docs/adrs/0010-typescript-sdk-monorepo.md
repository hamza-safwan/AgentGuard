# ADR 0010: TypeScript SDK Lives in the Same Monorepo

## Status

Accepted (v0.3)

## Context

The v0.3 JavaScript / TypeScript SDK shares its wire format
(`schemas/v1/*.schema.json`) with the Python package. Two options for
repository layout:

1. **Separate repo** at `github.com/agentguard/agentguard-sdk-js`.
2. **Monorepo** with the SDK at `packages/agentguard-js/` inside the existing
   `agentguard` repo.

A separate repo means cross-repo PRs every time the schema changes - which is
exactly the kind of mechanical chore that gets skipped, leading to silent
drift between the Python source of truth and the JS types.

## Decision

The TypeScript SDK lives at `packages/agentguard-js/` in this repo.

- One PR can update the Python schema export, the generated TS types, and the
  JS SDK consumers atomically.
- CI runs both Python and JS test matrices on every PR.
- Releases are version-paired: `agentguard 0.3.x` ↔ `agentguard 0.3.x`.
- The release workflow fans out two publish jobs (PyPI + npm) on a single
  `vX.Y.Z` tag.

## Consequences

- Pros: zero schema drift. PR review sees the full chain in one place.
- Pros: single CHANGELOG, single milestone tracker, single release rehearsal.
- Cons: JS-only contributors clone a Python-heavy repo. Mitigated by a clear
  `packages/agentguard-js/README.md` and isolated tooling under that directory.
- Cons: tag namespace - we use `v0.3.0` as the canonical tag and let the npm
  publish workflow read the version from `packages/agentguard-js/package.json`.
- We will **revisit** if the JS SDK's contributor base diverges significantly
  from the Python core (e.g., a separate maintainer team), at which point a
  split is justified.
