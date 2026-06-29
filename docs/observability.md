# Observability

AgentGuard can ingest SDK-produced traces from running applications. This mode is optional and self-hosted.

## Use Cases

- Monitor production agent behavior.
- Sample traces for later evaluation.
- Detect metric drops.
- Trigger alert rules.
- Compare production traces to CI scenarios.

## Python

```python
from agentguard.sdk.observability import configure_observability

configure_observability(
    endpoint="https://agentguard.example.com/api/v2/traces/ingest",
    token=os.environ["AGENTGUARD_TOKEN"],
    sample_rate=0.05,
)
```

## JavaScript

```ts
import { configureObservability } from "agentguard";

configureObservability({
  endpoint: "https://agentguard.example.com/api/v2/traces/ingest",
  token: process.env.AGENTGUARD_TOKEN!,
  sampleRate: 0.05,
});
```

## Ingest Endpoint

```text
POST /api/v2/traces/ingest
Authorization: Bearer <token>
Content-Type: application/json
```

Payload:

```json
{
  "traces": [
    {
      "scenario_id": "prod_chat",
      "runtime": "python",
      "steps": []
    }
  ]
}
```

## Security Notes

- Observability is opt-in.
- Do not send raw secrets.
- Use redaction and truncation.
- Use HTTPS.
- Rotate ingest tokens.
- Apply retention policies.

## Alerting

Alert rules can evaluate drops in metrics such as security score or failure rate and send webhook notifications.

