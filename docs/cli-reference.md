# CLI Reference

The `agentguard` CLI is the main workflow for local development and CI.

## `agentguard init`

Scaffolds a project.

```bash
agentguard init
```

Creates starter configuration, scenario folders, and example content.

## `agentguard run`

Runs a scenario file or directory.

```bash
agentguard run scenarios/customer_support \
  --agent-version v1.0.0 \
  --fail-under 85 \
  --security-threshold 90
```

Important options:

| Option | Description |
|---|---|
| `--agent-version` | Version label stored in reports and DB. |
| `--fail-under` | Minimum overall score on `0-100` scale. |
| `--security-threshold` | Minimum security score on `0-100` scale. |
| `--output table/json/minimal` | Output format. |
| `--save` | Save JSON run artifact under `.agentguard/runs`. |
| `--save-db / --no-save-db` | Persist to configured database. |
| `--parallel` | Number of scenarios to run concurrently. |
| `--skip-llm-judge` | Disable LLM judges. |
| `--mock-port` | Mock tool server port. |
| `--mock-strict` | Block unregistered scoped tool calls with `424`. |

## `agentguard report`

Generates a report from a saved run.

```bash
agentguard report latest --format html
agentguard report latest --format markdown
agentguard report latest --format json
```

## `agentguard compare`

Compares two runs and reports regressions.

```bash
agentguard compare run_base run_candidate
```

## `agentguard serve`

Starts the backend API.

```bash
agentguard serve --host 0.0.0.0 --port 8000
```

## `agentguard watch`

Runs scenarios when files change.

```bash
agentguard watch scenarios/customer_support
```

Use this for prompt, scenario, and local agent iteration.

## `agentguard evaluators list`

Lists built-in and plugin evaluators.

```bash
agentguard evaluators list
```

