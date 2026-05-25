# Sample LangGraph Agent — AgentGuard hero demo

A small customer-support agent built with [LangGraph](https://github.com/langchain-ai/langgraph).
This is the **hero sample** for AgentGuard — the trace viewer demo and launch
video both feature it.

## Run

```bash
pip install agentguard[langgraph]
# Optional: real LLM routing
export OPENAI_API_KEY=sk-...

agentguard run scenarios/customer_support
```

## What this agent does

- Routes intent (refund, PII request, account deletion, …)
- Calls a small set of mock tools: `get_customer_profile`, `search_policy_docs`,
  `issue_refund`, `send_email`
- Falls back to deterministic keyword routing when no `OPENAI_API_KEY` is set
  so demos are reproducible offline
