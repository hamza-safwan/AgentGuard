# Dashboard

The dashboard is a Next.js application for inspecting runs, scenarios, traces, and comparisons.

## Start Locally

Start backend dependencies:

```bash
docker compose up -d
```

Start the backend:

```bash
agentguard serve --host 0.0.0.0 --port 8000
```

Start the dashboard:

```bash
cd dashboard
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Main Views

- Run list.
- Run detail.
- Scenario result detail.
- Trace viewer.
- Comparison view.

## Environment

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Production Notes

For public or team deployments:

- Put the backend behind TLS.
- Protect the backend with network controls or auth.
- Use managed Postgres for persistent data.
- Configure retention for traces and run artifacts.

