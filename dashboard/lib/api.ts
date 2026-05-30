export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type RunSummary = {
  run_id: string;
  agent_name: string;
  agent_version: string;
  suite: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  overall_score: number;
  security_score: number;
  rag_score: number;
  tool_score: number;
  avg_cost_usd: number;
  avg_latency_ms: number;
  p95_latency_ms: number | null;
  deployment_recommendation: string;
  triggered_by: string;
  metric_summaries?: MetricSummary[];
  security_findings?: SecurityFinding[];
  results?: ScenarioResult[];
};

export type MetricSummary = {
  metric_name: string;
  average_score: number;
  min_score: number;
  max_score: number;
  pass_rate: number;
  failure_count: number;
};

export type SecurityFinding = {
  severity: string;
  scenario_id: string;
  finding: string;
  evidence?: unknown;
};

export type ScenarioResult = {
  id: string;
  run_id: string;
  scenario_id: string;
  status: string;
  passed: boolean;
  overall_score: number;
  failure_summary: string | null;
  final_output: string;
  cost_usd: number | null;
  latency_ms: number | null;
  trace_id: string | null;
  evaluations: EvaluationResult[];
  raw?: unknown;
};

export type EvaluationResult = {
  metric_name: string;
  score: number;
  passed: boolean;
  reason: string;
  evidence: unknown[];
};

export type TraceStep = {
  step_id: string;
  step_index: number;
  type: string;
  name: string;
  input?: unknown;
  output?: unknown;
  metadata?: Record<string, unknown>;
  latency_ms?: number | null;
};

export type Trace = {
  trace_id: string;
  scenario_id: string;
  final_output?: string;
  total_latency_ms?: number | null;
  total_cost_usd?: number | null;
  steps: TraceStep[];
};

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function listRuns(): Promise<RunSummary[]> {
  const data = await getJson<{ runs: RunSummary[] }>("/api/runs", { runs: [] });
  return data.runs;
}

export async function getRun(runId: string): Promise<RunSummary | null> {
  return getJson<RunSummary | null>(`/api/runs/${runId}`, null);
}

export async function getTrace(traceId: string): Promise<Trace | null> {
  return getJson<Trace | null>(`/api/traces/${traceId}`, null);
}

export async function listScenarios(): Promise<unknown[]> {
  const data = await getJson<{ scenarios: unknown[] }>("/api/scenarios", { scenarios: [] });
  return data.scenarios;
}
