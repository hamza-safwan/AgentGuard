# AgentGuard PR-Comment Bot

Composite action that reads a saved AgentGuard run JSON and upserts a single
structured comment on the pull request that triggered the workflow. Idempotent
on re-runs: the comment is identified by an HTML marker, so each push updates
the existing comment instead of spawning duplicates.

## Quick use

```yaml
- uses: actions/checkout@v4
- uses: agentguard/agentguard-ci/.github/actions/agentguard@v1
  with:
    scenarios: scenarios
    fail-under: "85"
    security-threshold: "90"

- uses: agentguard/agentguard-ci/.github/actions/agentguard-pr-comment@v1
  if: always()           # post even when the gate failed
  with:
    run-json: latest
    trace-viewer-base-url: https://dash.example.com   # optional
```

## Permissions

The workflow needs `pull-requests: write`:

```yaml
permissions:
  contents: read
  pull-requests: write
```

## Inputs

| Name | Default | Notes |
|------|---------|-------|
| `run-json` | `latest` | Path to a saved run JSON, or `latest` to pick the newest under `.agentguard/runs/`. |
| `tag` | `agentguard-ci-report` | HTML marker used for idempotent upsert. |
| `trace-viewer-base-url` | _(empty)_ | If set, failing scenarios link to `<base>/traces/<id>`. |
| `artifact-url` | _(empty)_ | If set, comment links to the uploaded HTML report. |
| `python-version` | `3.11` | Python version used to run the bot script. |

The bot is a self-contained Python script (`src/post_comment.py`) using only
the stdlib + `requests`, so it works against run JSONs produced by any
AgentGuard release.
