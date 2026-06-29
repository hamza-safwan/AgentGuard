# JavaScript SDK

The JavaScript SDK is published as `agentguard`.

## Install

```bash
npm install agentguard
```

## Trace and Evaluate

```ts
import { trace, tool, evaluate } from "agentguard";

const searchPolicyDocs = tool("search_policy_docs", async (query: string) => {
  return { documents: [{ doc_id: "refund_policy_v2" }] };
});

const { trace: t } = await trace(
  { scenarioId: "refund_policy", agentName: "support" },
  async () => {
    await searchPolicyDocs("refund after 90 days");
  },
);

const result = await evaluate({
  trace: t,
  metrics: ["required_tool_calls", "forbidden_tool_avoidance"],
  mustCallTools: ["search_policy_docs"],
  mustNotCallTools: ["issue_refund"],
});
```

## Function Wrappers

- `tool`
- `llmCall`
- `retrieval`
- `guardrail`
- `traceable`

## Judge

```ts
import { judge } from "agentguard";

const verdict = await judge({
  response: "I issued the refund.",
  criteria: "The agent must not issue a refund after 30 days.",
});
```

If `OPENAI_API_KEY` is not set or `AGENTGUARD_SKIP_LLM_JUDGE=1`, judge calls skip.

## Observability

```ts
import { configureObservability } from "agentguard";

configureObservability({
  endpoint: "https://agentguard.example.com/api/v2/traces/ingest",
  token: process.env.AGENTGUARD_TOKEN!,
  sampleRate: 0.05,
});
```

Once configured, traces are shipped asynchronously.

## Type Safety

The SDK generates `src/schema.ts` from the canonical Python JSON Schemas in `schemas/v1`. This keeps Python and TypeScript clients aligned on the wire format.

