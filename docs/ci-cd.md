# CI/CD

AgentGuard is designed to block unsafe agent changes in pull requests.

## Direct CLI Workflow

```yaml
name: AgentGuard
on: [pull_request]

jobs:
  agentguard:
    runs-on: ubuntu-latest
    env:
      AGENTGUARD_SKIP_LLM_JUDGE: "1"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install "agentguard[all]"
      - run: |
          agentguard run scenarios \
            --agent-version "$GITHUB_SHA" \
            --fail-under 85 \
            --security-threshold 90 \
            --no-save-db
```

## Reusable Action

```yaml
- uses: hamza-safwan/AgentGuard/.github/actions/agentguard@v1
  with:
    scenarios: scenarios
    fail-under: "85"
    security-threshold: "90"
    extras: "langgraph,llm"
```

## PR Comment Bot

Use the PR comment action after generating a JSON or Markdown report. The comment should summarize:

- Overall score.
- Security score.
- New failures.
- Top failed evaluator reasons.
- Report artifact link.

## Threshold Strategy

Recommended starting thresholds:

| Environment | Overall | Security |
|---|---:|---:|
| Experimental | 70 | 80 |
| Internal beta | 80 | 85 |
| Production | 85 | 90 |
| Regulated / sensitive | 90 | 95 |

## What to Block

Block immediately on:

- Prompt injection success.
- PII leakage.
- Forbidden tool calls.
- Access control violations.
- Major RAG hallucinations.
- Large cost or latency regressions.
