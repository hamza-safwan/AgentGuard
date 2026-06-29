# Installation

AgentGuard ships as a Python package, a TypeScript SDK, reusable GitHub Actions, and a Docker Compose stack for the backend/dashboard.

## Requirements

- Python 3.11 or 3.12.
- Node.js 20+ for the dashboard and JavaScript SDK development.
- Docker and Docker Compose for the self-hosted stack.
- Optional `OPENAI_API_KEY` for LLM-judge evaluators. Without it, LLM judges skip with a passing score so local CI stays deterministic.

## Python CLI and SDK

```bash
pip install agentguard
```

For development:

```bash
pip install -e ".[dev]"
```

For all supported Python framework integrations:

```bash
pip install "agentguard[all]"
```

Common extras:

```bash
pip install "agentguard[langgraph]"
pip install "agentguard[langchain]"
pip install "agentguard[openai-agents]"
pip install "agentguard[crewai]"
pip install "agentguard[pydantic-ai]"
pip install "agentguard[llm]"
```

## JavaScript SDK

```bash
npm install agentguard
```

The `openai` package is optional. Install it only if you want JS-side LLM judging:

```bash
npm install openai
```

## Self-Hosted Stack

```bash
cp .env.example .env
docker compose up -d
```

This starts the backend dependencies and mock tool server. For dashboard development:

```bash
cd dashboard
npm install
npm run dev
```

## Verify the Repository Locally

```bash
ruff check agentguard tests examples
python -m pytest -q
python -m agentguard.schemas.export
```

For the JS SDK:

```bash
cd packages/agentguard-js
npm install --no-audit --no-fund
npm run build
npm run test
```

