# Security Policy

## Supported versions

The latest minor release of AgentGuard receives security fixes. Older versions are best-effort.

## Reporting a vulnerability

**Please do not file public issues for security vulnerabilities.**

Instead, open a [private security advisory](https://github.com/hamza-safwan/AgentGuard/security/advisories/new) on GitHub, or email the maintainers (see [CONTRIBUTING.md](CONTRIBUTING.md)). Include:

- A clear description of the vulnerability.
- Reproduction steps and a minimal proof-of-concept if possible.
- Impact: what an attacker can do, who is affected, what data or actions are at risk.
- Any suggested fixes.

We aim to acknowledge reports within **3 business days** and to ship a fix or coordinated disclosure within **30 days** for high-severity issues.

## Scope

In-scope:

- The `agentguard` Python package (CLI, runner, adapters, evaluators, server, storage).
- Built-in scenario YAMLs and red-team packs.
- The Next.js dashboard.
- The official Docker images and reusable GitHub Action.

Out-of-scope (please report to the appropriate upstream):

- Vulnerabilities in third-party agent frameworks (LangGraph, LangChain, OpenAI Agents SDK, CrewAI).
- Vulnerabilities in user-supplied agent code or scenarios.
- Bugs in OpenAI / Anthropic / other LLM provider APIs.

## Hardening notes

- AgentGuard does **not** require an LLM API key by default. The `--skip-llm-judge` flag (and the `AGENTGUARD_SKIP_LLM_JUDGE=1` env var) disables LLM-based evaluators entirely, which is the recommended posture for environments where outbound LLM calls aren't allowed.
- The mock tool runtime listens on `:8100` by default and **is intended for local/test use only**. Do not expose it to the public internet.
- Database credentials, API keys, and similar secrets should be supplied via environment variables, not committed to YAML.
