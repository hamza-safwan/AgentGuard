# Reports

AgentGuard can emit reports for humans and machines.

## Save a Run

```bash
agentguard run scenarios/customer_support --save --no-save-db
```

Saved runs are written under `.agentguard/runs`.

## Generate HTML

```bash
agentguard report latest --format html
```

Use HTML reports for release review, CI artifacts, and failure analysis.

## Generate Markdown

```bash
agentguard report latest --format markdown
```

Use Markdown reports for GitHub comments, PR summaries, and docs.

## Generate JSON

```bash
agentguard run scenarios --output json
```

Use JSON output for automation.

## Compare Runs

```bash
agentguard compare run_base run_candidate
```

Comparison highlights:

- New failures.
- Fixed scenarios.
- Score deltas.
- Deployment recommendation changes.

