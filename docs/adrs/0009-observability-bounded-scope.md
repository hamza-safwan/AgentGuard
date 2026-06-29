# ADR 0009: Observability Mode is a Starter-Kit, Not OTel Parity

## Status

Accepted (v0.3)

## Context

v0.3 adds a "live observability" mode: the same SDK that captures traces in
tests can ship traces from production to the AgentGuard server, where they get
sampled, persisted, evaluated, and surfaced in the dashboard.

The temptation is to chase parity with OpenTelemetry / LangSmith / Datadog -
distributed traces, span attributes, head-and-tail sampling, replay protection,
multi-tenancy, the full nine yards. That's a multi-quarter project we are not
ready to commit to in v0.3.

## Decision

v0.3 ships a deliberately **bounded** observability surface:

| In scope | Out of scope (defer to v0.4+) |
|----------|--------------------------------|
| `configure(endpoint, token, sample_rate, batch_size, ...)` SDK API | Distributed-traces with parent / child spans |
| Single ingestion endpoint `/api/v2/traces/ingest` (gzipped JSON batches) | OTel exporter compatibility |
| Head-based rate sampler + always-sample-on-error | Per-attribute sampling |
| Bearer-token auth (sha256-hashed in DB) | Multi-tenancy, RBAC, per-token rate limits |
| Per-rule alert evaluator (rolling window vs baseline) over webhooks | Email / PagerDuty native destinations |
| Inline + Dramatiq worker for ingest (Redis optional) | Durable replay queue |
| One ScenarioResult per ingested trace, flagged `source='observability'` | Per-tenant data isolation |

The boundary is explicit so we don't grow into a half-built observability
platform. If user demand justifies expanding, the wire format
(ADR 0007) and the trace context (ADR 0006) already support it without breaking
changes.

## Consequences

- Pros: ship a useful observability surface in one release. Self-hosted users
  can monitor production agents with the same tool that gates their PRs.
- Pros: token auth + bounded payload size + fail-open SDK transport all keep
  the production blast radius small.
- Cons: users wanting OTel-grade observability will go elsewhere for now.
  Documented prominently.
- Cons: alert rules in v0.3 only support webhooks; native Slack / email asks
  will arrive immediately. Track them; ship in v0.3.x patches if demand is
  consistent.
