# Security

AgentGuard tests security-sensitive behavior, but it also handles potentially sensitive traces. Treat it as part of your engineering control plane.

## What AgentGuard Can Detect

- Prompt injection compliance.
- PII leakage.
- Forbidden tool calls.
- Access control violations.
- Policy noncompliance.
- Risky RAG behavior.

## What AgentGuard Does Not Guarantee

AgentGuard is not a formal proof system. Passing scenarios means the agent passed the tests you wrote. It does not guarantee safety for every possible user input.

## Data Handling

Traces may contain:

- User input.
- Tool arguments.
- Tool outputs.
- Retrieved document IDs or snippets.
- Final agent output.

Use redaction, truncation, and environment separation.

## Recommended Practices

- Do not run production secrets through local examples.
- Use mock tools in CI.
- Keep observability opt-in.
- Use HTTPS for ingestion.
- Rotate ingest tokens.
- Limit dashboard access.
- Treat stored traces as sensitive application data.

## Reporting Vulnerabilities

Use `SECURITY.md` for responsible disclosure. Do not publish exploit details in public issues before maintainers have had time to assess.

