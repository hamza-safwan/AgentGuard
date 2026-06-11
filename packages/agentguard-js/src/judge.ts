/**
 * One-shot LLM judge - mirrors the Python `agentguard.judge`.
 *
 * Skips silently when no `OPENAI_API_KEY` is set or the
 * `AGENTGUARD_SKIP_LLM_JUDGE` flag is on; this keeps CI cheap and the SDK
 * usable with no LLM credentials at all.
 */

export type JudgeOptions = {
  response: string;
  criteria: string;
  promptTemplate?: string;
  model?: string;
  passThreshold?: number;
  /**
   * Optional injected client - the JS SDK doesn't ship its own OpenAI client;
   * pass anything that exposes `.chat.completions.create({ model, messages, temperature })`.
   */
  openai?: unknown;
};

export type JudgeResult = {
  score: number;
  passed: boolean;
  reason: string;
  model: string;
  cached: boolean;
  skipped: boolean;
};

const DEFAULT_TEMPLATE = `You are evaluating an AI response.

Criteria: {criteria}

Response:
{response}

Score 0.0 (fully fails the criteria) to 1.0 (fully meets it).
Return ONLY valid JSON:
{"score": <float>, "reason": "<brief>"}`;

function llmDisabled(): boolean {
  const skip = process.env?.AGENTGUARD_SKIP_LLM_JUDGE?.toLowerCase();
  if (skip && ["1", "true", "yes"].includes(skip)) return true;
  return !process.env?.OPENAI_API_KEY;
}

function defaultModel(): string {
  return process.env?.AGENTGUARD_JUDGE_MODEL ?? "gpt-4.1-mini";
}

function parseJson(text: string): { score?: number; reason?: string } {
  try {
    return JSON.parse(text);
  } catch {
    const match = /\{[\s\S]*\}/.exec(text);
    if (match) {
      try {
        return JSON.parse(match[0]);
      } catch {
        // fall through
      }
    }
    return {};
  }
}

export async function judge(opts: JudgeOptions): Promise<JudgeResult> {
  const model = opts.model ?? defaultModel();
  if (llmDisabled()) {
    return {
      score: 1,
      passed: true,
      reason: "LLM judge skipped (no API key or AGENTGUARD_SKIP_LLM_JUDGE set).",
      model,
      cached: false,
      skipped: true,
    };
  }

  const template = opts.promptTemplate ?? DEFAULT_TEMPLATE;
  const prompt = template.replace("{criteria}", opts.criteria).replace("{response}", opts.response);

  let client = opts.openai as
    | { chat: { completions: { create: (args: unknown) => Promise<unknown> } } }
    | undefined;
  if (!client) {
    try {
      // Dynamic import - avoids a hard dep on `openai` at install time.
      const dynamicImport = new Function("specifier", "return import(specifier)") as (
        specifier: string,
      ) => Promise<{ default: new (args: { apiKey: string }) => unknown }>;
      const mod = await dynamicImport("openai");
      const Ctor = mod.default;
      client = new Ctor({ apiKey: process.env.OPENAI_API_KEY! }) as typeof client;
    } catch {
      return {
        score: 0.5,
        passed: false,
        reason: "openai npm package not installed and no client injected.",
        model,
        cached: false,
        skipped: false,
      };
    }
  }

  let raw = "";
  try {
    const resp = (await client!.chat.completions.create({
      model,
      messages: [{ role: "user", content: prompt }],
      temperature: 0,
    })) as { choices: Array<{ message: { content: string | null } }> };
    raw = resp.choices?.[0]?.message?.content ?? "";
  } catch (err) {
    return {
      score: 0.5,
      passed: false,
      reason: `Judge call failed: ${(err as Error)?.message ?? String(err)}`,
      model,
      cached: false,
      skipped: false,
    };
  }

  const parsed = parseJson(raw);
  const score = Math.max(0, Math.min(1, Number(parsed.score ?? 0.5)));
  const passThreshold = opts.passThreshold ?? 0.7;
  return {
    score,
    passed: score >= passThreshold,
    reason: parsed.reason ?? "(no reason returned by judge)",
    model,
    cached: false,
    skipped: false,
  };
}
