# Deployment

AgentGuard can be used in three modes:

1. CLI-only in CI.
2. CLI plus local reports.
3. Self-hosted backend, database, workers, and dashboard.

## CLI-Only

Best for early adoption:

```bash
pip install agentguard
agentguard run scenarios --fail-under 85 --security-threshold 90 --no-save-db
```

## Docker Compose

```bash
cp .env.example .env
docker compose up -d
```

Use this for local dashboard evaluation and demos.

## Production Self-Hosting

Recommended components:

- Backend API behind TLS.
- Managed Postgres.
- Redis for workers.
- Dashboard served behind your internal auth.
- Mock tool server isolated from production systems.

## Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy database URL. |
| `REDIS_URL` | Worker queue backend. |
| `OPENAI_API_KEY` | Enables LLM judges. |
| `AGENTGUARD_SKIP_LLM_JUDGE` | Force-disables LLM judges. |
| `AGENTGUARD_MOCK_SERVER_URL` | Mock server base URL. |
| `NEXT_PUBLIC_API_URL` | Dashboard backend URL. |

## Release Artifacts

- PyPI: `agentguard`
- npm: `agentguard`
- Docker: `ghcr.io/<org>/agentguard`
- GitHub Actions: `.github/actions/agentguard`

