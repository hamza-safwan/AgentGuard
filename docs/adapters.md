# Adapters

Adapters run agents and normalize output into `AgentTrace`.

## Adapter Contract

Every adapter implements:

- `meta`
- `run(scenario)`
- `health_check()`

The result is:

- `final_output`
- `trace`
- `raw_output`

## Supported Adapters

| Adapter | Purpose | Install |
|---|---|---|
| `http` | Any agent exposed as REST. | included |
| `langgraph` | LangGraph compiled graphs. | `agentguard[langgraph]` |
| `langchain` | LangChain Runnable / LCEL chains. | `agentguard[langchain]` |
| `openai_agents` | OpenAI Agents SDK. | `agentguard[openai-agents]` |
| `crewai` | CrewAI crews and flows. | `agentguard[crewai]` |
| `pydantic_ai` | Pydantic AI agents. | `agentguard[pydantic-ai]` |
| `mastra` | Mastra agents via HTTP bridge. | included |
| `vercel_ai` | Vercel AI SDK agents via HTTP bridge. | included |
| `autogen` | AutoGen agents. | `agentguard[autogen]` |
| `dspy` | DSPy modules. | `agentguard[dspy]` |
| `llamaindex` | LlamaIndex query engines / agents. | `agentguard[llamaindex]` |
| `smolagents` | Hugging Face Smolagents. | `agentguard[smolagents]` |

## HTTP Adapter

Scenario:

```yaml
agent:
  adapter: http
  url: "http://localhost:8000/agent/run"
```

Expected response:

```json
{
  "final_output": "Refunds after 30 days require escalation.",
  "trace": {
    "steps": [
      {
        "type": "tool_call",
        "name": "search_policy_docs",
        "output": {"documents": [{"doc_id": "refund_policy_v2"}]}
      }
    ]
  }
}
```

## Framework Object Adapters

Framework adapters usually import an object:

```yaml
agent:
  adapter: langchain
  module: examples.sample_langchain_rag.chain
  object: chain
```

Keep framework imports lazy. Users who do not install a framework should still be able to use the CLI, schemas, and other adapters.

