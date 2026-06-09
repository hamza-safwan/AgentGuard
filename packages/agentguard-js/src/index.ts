/**
 * agentguard - JavaScript / TypeScript SDK for AgentGuard.
 *
 * BLUEPRINT-7 section 8. Mirrors the Python SDK surface:
 *
 *  - `trace(opts, fn)` and `recordStep` / `currentTrace` for in-process capture
 *  - `tool`, `llmCall`, `retrieval`, `guardrail`, `traceable` decorator-style wrappers
 *  - `evaluate`, `evaluateScenario` for ad-hoc scoring of an in-memory trace
 *  - `judge` for one-shot LLM judgments
 *  - `configureObservability` to ship traces to a self-hosted AgentGuard instance
 */

export {
  currentTrace,
  newTraceStep,
  recordStep,
  trace,
  type TraceOptions,
  type TraceResult,
} from "./context.js";

export {
  guardrail,
  llmCall,
  retrieval,
  tool,
  traceable,
  scrub,
} from "./decorators.js";

export {
  evaluate,
  evaluateScenario,
  type EvaluateOptions,
  type ScenarioResultJSON,
} from "./evaluate.js";

export { judge, type JudgeOptions, type JudgeResult } from "./judge.js";

export { configureObservability } from "./transport.js";

export type {
  AgentTrace,
  TraceStep,
  EvaluationResult,
  ScenarioResult,
  RunSummary,
  Scenario,
} from "./schema.js";
