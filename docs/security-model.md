# Security Model

AgentGuard is a testing and evaluation tool, not a runtime sandbox.

It reduces deployment risk by detecting:

- Prompt injection compliance.
- Unauthorized tool calls.
- PII leakage.
- System prompt leakage.
- RAG hallucination and missing grounding.
- Excessive agency such as sending emails or issuing refunds without approval.

Safe testing depends on mock tools and explicit scenario expectations. Production agents should be tested against mock or staging dependencies, not live payment, email, CRM, or HR systems.
