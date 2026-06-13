// AUTO-GENERATED FROM schemas/v1/*.schema.json - DO NOT EDIT.
// Run `npm run codegen` to regenerate.

// evaluation_result.schema.json
export namespace EvaluationResultSchema {
  export type Evidence = {
    [k: string]: unknown | undefined;
  }[];
  export type MetricName = string;
  export type Passed = boolean;
  export type Reason = string;
  export type Score = number;

  /**
   * Result of a single evaluator on a single scenario run.
   */
  export interface EvaluationResult {
    evidence?: Evidence;
    metric_name: MetricName;
    passed: Passed;
    reason: Reason;
    score: Score;
  }
}
export type EvaluationResult = EvaluationResultSchema.EvaluationResult;

// run_summary.schema.json
export namespace RunSummarySchema {
  export type AgentName = string;
  export type AgentVersion = string;
  export type AvgCostUsd = number;
  export type AvgLatencyMs = number;
  export type DeploymentRecommendation =
    | "deploy_with_monitoring"
    | "deploy_carefully"
    | "fix_before_production"
    | "do_not_deploy";
  export type FailedScenarioIds = string[];
  export type FailedScenarios = number;
  export type FinishedAt = string | null;
  export type AverageScore = number;
  export type FailureCount = number;
  export type MaxScore = number;
  export type MetricName = string;
  export type MinScore = number;
  export type PassRate = number;
  export type MetricSummaries = MetricSummary[];
  export type OverallScore = number;
  export type P95LatencyMs = number | null;
  export type PassedScenarios = number;
  export type RagScore = number;
  export type RunId = string;
  export type Evidence = {
    [k: string]: unknown | undefined;
  } | null;
  export type Finding = string;
  export type ScenarioId = string;
  export type Severity = "critical" | "high" | "medium" | "low";
  export type SecurityFindings = SecurityFinding[];
  export type SecurityScore = number;
  export type StartedAt = string;
  export type Suite = string;
  export type ToolScore = number;
  export type TotalScenarios = number;

  export interface RunSummary {
    agent_name: AgentName;
    agent_version: AgentVersion;
    avg_cost_usd: AvgCostUsd;
    avg_latency_ms: AvgLatencyMs;
    deployment_recommendation: DeploymentRecommendation;
    failed_scenario_ids?: FailedScenarioIds;
    failed_scenarios: FailedScenarios;
    finished_at?: FinishedAt;
    metric_summaries?: MetricSummaries;
    overall_score: OverallScore;
    p95_latency_ms?: P95LatencyMs;
    passed_scenarios: PassedScenarios;
    rag_score: RagScore;
    run_id: RunId;
    security_findings?: SecurityFindings;
    security_score: SecurityScore;
    started_at: StartedAt;
    suite: Suite;
    tool_score: ToolScore;
    total_scenarios: TotalScenarios;
  }
  export interface MetricSummary {
    average_score: AverageScore;
    failure_count: FailureCount;
    max_score: MaxScore;
    metric_name: MetricName;
    min_score: MinScore;
    pass_rate: PassRate;
  }
  export interface SecurityFinding {
    evidence?: Evidence;
    finding: Finding;
    scenario_id: ScenarioId;
    severity: Severity;
  }
}
export type RunSummary = RunSummarySchema.RunSummary;

// scenario.schema.json
export namespace ScenarioSchema {
  export type Adapter =
    | "http"
    | "langgraph"
    | "langchain"
    | "openai_agents"
    | "crewai"
    | "pydantic_ai"
    | "mastra"
    | "vercel_ai"
    | "autogen"
    | "dspy"
    | "llamaindex"
    | "smolagents";
  export type Method = string;
  export type Module = string | null;
  export type Object = string | null;
  export type TimeoutSeconds = number;
  export type Url = string | null;
  export type Description = string | null;
  export type AnswerMustBeGrounded = boolean;
  export type FinalResponseShould = string[];
  export type MustCallTools = string[];
  export type MustNotCallTools = string[];
  export type MustNotReveal = string[];
  export type MustRetrieve = string[];
  export type Id = string;
  export type Files = string[];
  export type UserMessage = string;
  export type Metrics = string[];
  export type DelayMs = number;
  export type Name = string;
  export type Raises = string | null;
  export type Status = number;
  export type When = {
    [k: string]: unknown | undefined;
  } | null;
  export type Mocks = MockSpecYAML[];
  export type MocksModule = string | null;
  export type PiiTest = boolean;
  export type PromptInjection = boolean;
  export type SystemPromptLeakage = boolean;
  export type Suite = string;
  export type Tags = string[];
  export type MaxCostUsd = number | null;
  export type MaxLatencyMs = number | null;
  export type MinOverallScore = number | null;
  export type MinSecurityScore = number | null;

  export interface Scenario {
    agent: AgentConfig;
    description?: Description;
    expected?: ExpectedBehavior;
    id: Id;
    input: ScenarioInput;
    metrics: Metrics;
    mocks?: Mocks;
    mocks_module?: MocksModule;
    security?: SecurityConfig | null;
    suite: Suite;
    tags?: Tags;
    thresholds?: ThresholdConfig | null;
  }
  export interface AgentConfig {
    adapter: Adapter;
    extra?: Extra;
    headers?: Headers;
    method?: Method;
    module?: Module;
    object?: Object;
    timeout_seconds?: TimeoutSeconds;
    url?: Url;
  }
  export interface Extra {
    [k: string]: unknown | undefined;
  }
  export interface Headers {
    [k: string]: string | undefined;
  }
  export interface ExpectedBehavior {
    answer_must_be_grounded?: AnswerMustBeGrounded;
    final_response_should?: FinalResponseShould;
    must_call_tools?: MustCallTools;
    must_not_call_tools?: MustNotCallTools;
    must_not_reveal?: MustNotReveal;
    must_retrieve?: MustRetrieve;
  }
  export interface ScenarioInput {
    files?: Files;
    metadata?: Metadata;
    user_message: UserMessage;
  }
  export interface Metadata {
    [k: string]: unknown | undefined;
  }
  /**
   * A single entry in a scenario's ``mocks:`` block (BLUEPRINT-7 section 4.3.1).
   */
  export interface MockSpecYAML {
    delay_ms?: DelayMs;
    name: Name;
    raises?: Raises;
    response?: Response;
    status?: Status;
    when?: When;
  }
  export interface Response {
    [k: string]: unknown | undefined;
  }
  export interface SecurityConfig {
    pii_test?: PiiTest;
    prompt_injection?: PromptInjection;
    system_prompt_leakage?: SystemPromptLeakage;
  }
  export interface ThresholdConfig {
    max_cost_usd?: MaxCostUsd;
    max_latency_ms?: MaxLatencyMs;
    min_overall_score?: MinOverallScore;
    min_security_score?: MinSecurityScore;
  }
}
export type Scenario = ScenarioSchema.Scenario;

// scenario_result.schema.json
export namespace ScenarioResultSchema {
  export type CostUsd = number | null;
  export type Evidence = {
    [k: string]: unknown | undefined;
  }[];
  export type MetricName = string;
  export type Passed = boolean;
  export type Reason = string;
  export type Score = number;
  export type Evaluations = EvaluationResult[];
  export type FailureSummary = string | null;
  export type FinalOutput = string;
  export type LatencyMs = number | null;
  export type OverallScore = number;
  export type Passed1 = boolean;
  export type ScenarioId = string;
  export type Suite = string;
  export type AgentName = string | null;
  export type AgentVersion = string | null;
  export type FinalOutput1 = string | null;
  export type Runtime = "python" | "js" | "unknown";
  export type Sampling = {
    [k: string]: unknown | undefined;
  } | null;
  export type ScenarioId1 = string;
  export type SchemaVersion = string;
  export type CostUsd1 = number | null;
  export type EndedAt = string | null;
  export type LatencyMs1 = number | null;
  export type Name = string;
  export type ParentStepId = string | null;
  export type Redactions = string[];
  export type Source = "adapter" | "sdk" | "ingest";
  export type StartedAt = string | null;
  export type StepId = string;
  export type Tokens = {
    [k: string]: number | undefined;
  } | null;
  export type Type = "llm_call" | "tool_call" | "retrieval" | "guardrail" | "handoff" | "error" | "final_output";
  export type Steps = TraceStep[];
  export type TotalCostUsd = number | null;
  export type TotalLatencyMs = number | null;
  export type TraceId = string;

  /**
   * Full scored result for one scenario.
   */
  export interface ScenarioResult {
    cost_usd?: CostUsd;
    evaluations: Evaluations;
    failure_summary?: FailureSummary;
    final_output: FinalOutput;
    latency_ms?: LatencyMs;
    overall_score: OverallScore;
    passed: Passed1;
    scenario_id: ScenarioId;
    suite: Suite;
    trace: AgentTrace;
  }
  /**
   * Result of a single evaluator on a single scenario run.
   */
  export interface EvaluationResult {
    evidence?: Evidence;
    metric_name: MetricName;
    passed: Passed;
    reason: Reason;
    score: Score;
  }
  /**
   * Normalized record of a single agent run.
   *
   * v0.2 additions (additive): ``schema_version`` sanity field, ``runtime``
   * ("python" / "js" / "unknown"), and ``sampling`` metadata set by the
   * observability SDK when a trace was head- or tail-sampled.
   */
  export interface AgentTrace {
    agent_name?: AgentName;
    agent_version?: AgentVersion;
    final_output?: FinalOutput1;
    runtime?: Runtime;
    sampling?: Sampling;
    scenario_id: ScenarioId1;
    schema_version?: SchemaVersion;
    steps?: Steps;
    total_cost_usd?: TotalCostUsd;
    total_latency_ms?: TotalLatencyMs;
    trace_id?: TraceId;
  }
  /**
   * One step in an AgentTrace.
   *
   * v0.2 additions (all optional, additive): ``parent_step_id`` for nesting,
   * ``source`` to distinguish adapter-captured vs SDK-captured vs ingested,
   * ``redactions`` listing field paths that were scrubbed prior to serialization,
   * ``cost_usd`` per-step cost, ``tokens`` for LLM-call accounting.
   */
  export interface TraceStep {
    cost_usd?: CostUsd1;
    ended_at?: EndedAt;
    input?: Input;
    latency_ms?: LatencyMs1;
    metadata?: Metadata;
    name: Name;
    output?: Output;
    parent_step_id?: ParentStepId;
    redactions?: Redactions;
    source?: Source;
    started_at?: StartedAt;
    step_id?: StepId;
    tokens?: Tokens;
    type: Type;
  }
  export interface Input {
    [k: string]: unknown | undefined;
  }
  export interface Metadata {
    [k: string]: unknown | undefined;
  }
  export interface Output {
    [k: string]: unknown | undefined;
  }
}
export type ScenarioResult = ScenarioResultSchema.ScenarioResult;

// trace.schema.json
export namespace AgentTraceSchema {
  export type AgentName = string | null;
  export type AgentVersion = string | null;
  export type FinalOutput = string | null;
  export type Runtime = "python" | "js" | "unknown";
  export type Sampling = {
    [k: string]: unknown | undefined;
  } | null;
  export type ScenarioId = string;
  export type SchemaVersion = string;
  export type CostUsd = number | null;
  export type EndedAt = string | null;
  export type LatencyMs = number | null;
  export type Name = string;
  export type ParentStepId = string | null;
  export type Redactions = string[];
  export type Source = "adapter" | "sdk" | "ingest";
  export type StartedAt = string | null;
  export type StepId = string;
  export type Tokens = {
    [k: string]: number | undefined;
  } | null;
  export type Type = "llm_call" | "tool_call" | "retrieval" | "guardrail" | "handoff" | "error" | "final_output";
  export type Steps = TraceStep[];
  export type TotalCostUsd = number | null;
  export type TotalLatencyMs = number | null;
  export type TraceId = string;

  /**
   * Normalized record of a single agent run.
   *
   * v0.2 additions (additive): ``schema_version`` sanity field, ``runtime``
   * ("python" / "js" / "unknown"), and ``sampling`` metadata set by the
   * observability SDK when a trace was head- or tail-sampled.
   */
  export interface AgentTrace {
    agent_name?: AgentName;
    agent_version?: AgentVersion;
    final_output?: FinalOutput;
    runtime?: Runtime;
    sampling?: Sampling;
    scenario_id: ScenarioId;
    schema_version?: SchemaVersion;
    steps?: Steps;
    total_cost_usd?: TotalCostUsd;
    total_latency_ms?: TotalLatencyMs;
    trace_id?: TraceId;
  }
  /**
   * One step in an AgentTrace.
   *
   * v0.2 additions (all optional, additive): ``parent_step_id`` for nesting,
   * ``source`` to distinguish adapter-captured vs SDK-captured vs ingested,
   * ``redactions`` listing field paths that were scrubbed prior to serialization,
   * ``cost_usd`` per-step cost, ``tokens`` for LLM-call accounting.
   */
  export interface TraceStep {
    cost_usd?: CostUsd;
    ended_at?: EndedAt;
    input?: Input;
    latency_ms?: LatencyMs;
    metadata?: Metadata;
    name: Name;
    output?: Output;
    parent_step_id?: ParentStepId;
    redactions?: Redactions;
    source?: Source;
    started_at?: StartedAt;
    step_id?: StepId;
    tokens?: Tokens;
    type: Type;
  }
  export interface Input {
    [k: string]: unknown | undefined;
  }
  export interface Metadata {
    [k: string]: unknown | undefined;
  }
  export interface Output {
    [k: string]: unknown | undefined;
  }
}
export type AgentTrace = AgentTraceSchema.AgentTrace;

// trace_step.schema.json
export namespace TraceStepSchema {
  export type CostUsd = number | null;
  export type EndedAt = string | null;
  export type LatencyMs = number | null;
  export type Name = string;
  export type ParentStepId = string | null;
  export type Redactions = string[];
  export type Source = "adapter" | "sdk" | "ingest";
  export type StartedAt = string | null;
  export type StepId = string;
  export type Tokens = {
    [k: string]: number | undefined;
  } | null;
  export type Type = "llm_call" | "tool_call" | "retrieval" | "guardrail" | "handoff" | "error" | "final_output";

  /**
   * One step in an AgentTrace.
   *
   * v0.2 additions (all optional, additive): ``parent_step_id`` for nesting,
   * ``source`` to distinguish adapter-captured vs SDK-captured vs ingested,
   * ``redactions`` listing field paths that were scrubbed prior to serialization,
   * ``cost_usd`` per-step cost, ``tokens`` for LLM-call accounting.
   */
  export interface TraceStep {
    cost_usd?: CostUsd;
    ended_at?: EndedAt;
    input?: Input;
    latency_ms?: LatencyMs;
    metadata?: Metadata;
    name: Name;
    output?: Output;
    parent_step_id?: ParentStepId;
    redactions?: Redactions;
    source?: Source;
    started_at?: StartedAt;
    step_id?: StepId;
    tokens?: Tokens;
    type: Type;
  }
  export interface Input {
    [k: string]: unknown | undefined;
  }
  export interface Metadata {
    [k: string]: unknown | undefined;
  }
  export interface Output {
    [k: string]: unknown | undefined;
  }
}
export type TraceStep = TraceStepSchema.TraceStep;
