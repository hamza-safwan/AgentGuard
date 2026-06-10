/**
 * In-process trace context for the JS SDK.
 *
 * Backed by Node's AsyncLocalStorage so nested async calls share the active
 * trace and concurrent tasks (e.g. `Promise.all`) each see their own copy.
 */

import { AsyncLocalStorage } from "node:async_hooks";

import type { AgentTrace, TraceStep } from "./schema.js";
import { maybeShipTrace } from "./transport.js";

export type TraceOptions = {
  scenarioId?: string;
  agentName?: string;
  agentVersion?: string;
};

export type TraceResult<T> = { result: T; trace: AgentTrace };

const storage = new AsyncLocalStorage<AgentTrace>();

export function currentTrace(): AgentTrace | undefined {
  return storage.getStore();
}

function uuid(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  // Fallback for ancient runtimes: time + random; not cryptographic, fine for IDs.
  return (
    Date.now().toString(16) + Math.random().toString(16).slice(2, 10)
  );
}

export function newTraceStep(partial: Partial<TraceStep> & Pick<TraceStep, "type" | "name">): TraceStep {
  return {
    step_id: partial.step_id ?? uuid(),
    type: partial.type,
    name: partial.name,
    input: partial.input,
    output: partial.output,
    metadata: partial.metadata ?? {},
    started_at: partial.started_at,
    ended_at: partial.ended_at,
    latency_ms: partial.latency_ms ?? null,
    parent_step_id: partial.parent_step_id,
    source: partial.source ?? "sdk",
    redactions: partial.redactions ?? [],
    cost_usd: partial.cost_usd ?? null,
    tokens: partial.tokens ?? null,
  };
}

export function recordStep(
  step: Partial<TraceStep> & Pick<TraceStep, "type" | "name">,
): void {
  const t = storage.getStore();
  if (!t) return;
  t.steps ??= [];
  t.steps.push(newTraceStep(step));
}

export async function trace<T>(
  opts: TraceOptions,
  fn: () => Promise<T> | T,
): Promise<TraceResult<T>> {
  const t: AgentTrace = {
    trace_id: uuid(),
    scenario_id: opts.scenarioId ?? "ad-hoc",
    agent_name: opts.agentName ?? null,
    agent_version: opts.agentVersion ?? null,
    steps: [],
    final_output: null,
    total_cost_usd: null,
    total_latency_ms: null,
    schema_version: "1.0",
    runtime: "js",
    sampling: null,
  };

  const start = Date.now();
  const result = await storage.run(t, async () => fn());
  if (t.total_latency_ms === null) {
    t.total_latency_ms = Date.now() - start;
  }
  // Ship to the configured observability endpoint if any (no-op otherwise).
  void maybeShipTrace(t);
  return { result, trace: t };
}
