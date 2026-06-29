# AgentGuard — Engineering Roadmap & Onboarding

> **Audience:** new engineers joining the project; current maintainers planning the next milestone.
> **Doc version:** 1.0 (covers state through v0.3.0-rc).
> **Read time:** 25 minutes end-to-end. The roadmap (Part VI) and gap list (Part VII) are the parts to revisit weekly.

---

## Table of contents

I.   [Project snapshot — what works, what doesn't](#i-project-snapshot)
II.  [Onboarding — local dev in 15 minutes](#ii-onboarding)
III. [Architecture — the load-bearing contracts](#iii-architecture)
IV.  [Distribution — how this ships to users](#iv-distribution)
V.   [Contribution playbooks — common dev recipes](#v-contribution-playbooks)
VI.  [Forward roadmap — v0.3 polish through v1.0](#vi-forward-roadmap)
VII. [Known gaps — concrete, prioritised, with pointers](#vii-known-gaps)
VIII.[Reference — files, env vars, common commands](#viii-reference)

---

## I. Project snapshot

**The one-line:** a CI/CD reliability and security gate for LLM agents — define YAML scenarios, run them through framework adapters, score against rule + LLM-judge evaluators, persist + dashboard + alert + block PRs.

### What's verified working today

| Component | State | Evidence |
|---|---|---|
| Core engine (scenario loader, runner, scoring, registry) | Production-grade | `tests/unit/test_core.py` (7 tests) |
| HTTP / LangGraph / LangChain / OpenAI Agents / CrewAI adapters (v0.1) | Production-grade | `tests/contract/` (3 tests) |
| 13 evaluators + scoring engine | Production-grade | scenarios run end-to-end with all 13 metrics |
| Postgres persistence + repositories + dashboard backend | Working | `tests/integration/test_storage_api.py` (2 tests) |
| Next.js 14 dashboard (8 screens) | Functional, not heavily polished | Manually verified after `docker compose up` |
| HTML / Markdown / JSON reports + regression compare | Production-grade | Smoke run produces valid 6.4 KB HTML, 1.2 KB MD |
| GitHub Action (main reliability gate) | Production-grade | `.github/actions/agentguard/action.yml` |
| Programmable mock tool server (YAML mocks + plugin catalogs + scope isolation) | Working | `tests/unit/test_mock_catalog.py` (7 tests) |
| Python SDK (`@trace`, `@tool`, `evaluate`, `judge`, `scrub`) | Production-grade | `tests/unit/test_sdk_*.py` (12 tests) |
| Pytest plugin (`@scenario`, `@suite`, `@inline_scenario`) | Working | `tests/unit/test_pytest_plugin.py` (2 tests) |
| Plugin discovery (evaluators, adapters, mock catalogs) | Working | `tests/unit/test_registry_plugin_discovery.py` (3 tests) |
| Schema export pipeline (Pydantic → JSON Schema) | Working | `python -m agentguard.schemas.export` regenerates `schemas/v1/` cleanly |
| 7 v0.2/v0.3 adapters (Pydantic AI / Mastra / Vercel AI / AutoGen / DSPy / LlamaIndex / Smolagents) | Code complete; metadata-contract tested only | `tests/unit/test_v025_adapters_metadata.py` (7 tests) |
| `agentguard watch` dev loop | Code complete | No tests — see VII |
| PR-comment bot (standalone Action) | Code complete | `tests/unit/test_pr_comment_bot.py` (4 tests) |
| Live observability mode (transport + ingest endpoint + alert rules + worker) | Code complete | `tests/unit/test_observability_transport.py` + `tests/integration/test_observability_api.py` (9 tests) |
| Schema additions in `TraceStep` / `AgentTrace` / `EvaluatorMeta` / `Scenario` | Production-grade | `tests/unit/test_schemas_v02_additions.py` (5 tests) |

**61/61 backend tests passing, ruff clean across `agentguard/`, `tests/`, `examples/`.**

### What is NOT yet verified

| Component | What's missing | Risk |
|---|---|---|
| `agentguard` (npm) | Never `npm install`-ed, never `tsc`-built, vitest never run | High — type errors likely |
| `agentguard watch` | No unit tests for the debouncer, no pytester integration test | Medium — flow may have edge cases |
| 4 v0.3 adapters (AutoGen, DSPy, LlamaIndex, Smolagents) | No real-framework smoke tests | Medium — adapter code may break against real framework versions |
| Alert webhook firing | No end-to-end test that a metric drop actually POSTs the webhook | Medium |
| End-to-end SDK → ingest endpoint → worker → DB row | No combined test | Medium |

### Component-level "production-readiness"

```
Production-ready  : core, v0.1 adapters, evaluators, reports, scoring, Python SDK, mock server, plugin discovery
Working           : pytest plugin, watch, PR-comment bot, observability transport + API, v0.2/v0.3 adapters
Verified-but-thin : dashboard (functional UI, minimal polish)
Unverified        : JS SDK (code only — never built or tested)
```

---

## II. Onboarding

### Prereqs

- Python 3.11+ (3.11 and 3.12 are CI-tested)
- Node 20+ (for dashboard + JS SDK)
- Docker + Docker Compose
- An OpenAI key for LLM-judge evaluators (optional — every LLM evaluator skips with `score=1.0` if no key is set)

### 15-minute local-dev setup

```bash
git clone <repo>
cd AgentGuard

# 1. Python install (with dev tools and all framework extras)
pip install -e ".[dev,all]"

# 2. Verify
ruff check agentguard tests examples              # should be: All checks passed!
python -m pytest -q                                # should be: 61 passed

# 3. Bring up the full stack
cp .env.example .env
docker compose up -d                              # postgres, redis, mock-tools, backend, dashboard

# 4. Smoke run a scenario
export AGENTGUARD_SKIP_LLM_JUDGE=1                # so we don't need OPENAI_API_KEY
agentguard run scenarios/customer_support/refund_outside_policy.yaml \
  --agent-version smoke --save --no-save-db

# 5. Open the dashboard
# http://localhost:3000

# 6. (Optional) Build + test the JS SDK - currently unverified
cd packages/agentguard-js
npm install
npm run codegen                                    # regenerates src/schema.ts from schemas/v1/
npm run build                                      # tsc - expect to find issues
npm run test                                       # vitest
```

### Where to start hacking

- **Adding a metric?** `agentguard/evaluators/`
- **Adding a framework?** `agentguard/adapters/`
- **Changing CLI behaviour?** `agentguard/cli/commands/`
- **Changing report layout?** `agentguard/reporting/templates/report.html.j2` + `markdown_report.py`
- **Touching the SDK?** `agentguard/sdk/` (re-exported at `agentguard/__init__.py`)
- **Touching the dashboard?** `dashboard/app/` (Next.js App Router) + `dashboard/lib/api.ts`

---

## III. Architecture

### The single data-flow diagram every contributor must hold in their head

```
                            scenarios/*.yaml
                                  |
                                  v
                       +--------------------+
                       | scenario_loader.py | (Pydantic validation; new mocks/mocks_module keys)
                       +---------+----------+
                                 |
                                 v
                       +---------+----------+        per-scenario `mocks:` block?
                       |   runner.py        |--->  yes -> POST /admin/scope to mock server
                       +---------+----------+        with X-AgentGuard-Scope header
                                 |
                                 v
              +------------------+--------------------+
              |  Adapter (1 of 12: http | langgraph | langchain | openai_agents |
              |   crewai | pydantic_ai | mastra | vercel_ai | autogen | dspy |
              |   llamaindex | smolagents)
              +------------------+--------------------+
                                 |
                                 v   AgentRunResult { final_output, AgentTrace, raw_output }
              +------------------+--------------------+
              |  Evaluator engine (registry-dispatched)
              |  built-in 13 + plugin entry-point evaluators
              +------------------+--------------------+
                                 |
                                 v   list[EvaluationResult]
              +------------------+--------------------+
              |  Scoring engine  -> ScenarioResult -> RunSummary
              +------------------+--------------------+
                                 |
              +------------------+--------------------+
              v                  v                    v
        Postgres / DB     CI exit code         HTML/MD/JSON report
        (optional)        (--fail-under)       (--save then `agentguard report`)

(Parallel paths)
   * SDK `with agentguard.trace():` block  -> same AgentTrace -> agentguard.evaluate(t, ...)
   * SDK observability mode              -> POST /api/v2/traces/ingest -> Dramatiq worker -> Postgres
   * pytest plugin @scenario             -> reuses runner.run_single_scenario
```

### The four load-bearing contracts (do NOT break without a major version)

1. **`AgentTrace` shape** (`agentguard/schemas/trace.py`) — the wire format every adapter, evaluator, SDK, and downstream tool depends on. Schemas exported to `schemas/v1/*.json`. ADR 0007.
2. **`BaseAgentAdapter` interface** (`agentguard/adapters/base.py`) — every adapter implements `meta`, `run(scenario)`, `health_check()`. Plugin adapters must satisfy this too.
3. **`BaseEvaluator` interface** (`agentguard/evaluators/base.py`) — every metric returns `EvaluationResult { metric_name, score, passed, reason, evidence }`.
4. **`Scenario` YAML DSL** (`agentguard/schemas/scenario.py`) — the user-facing config surface. New keys are additive only within a major.

### Versioning policy (ADR 0007)

- Pydantic models: additive only within a major. New fields default-safe.
- Wire schemas: live under `schemas/v1/`. Breaking changes require `schemas/v2/` parallel directory and 6-month deprecation.
- REST API: versioned via URL prefix (`/api/v1/...`, `/api/v2/...`).
- CLI: adding flags is non-breaking; renaming or removing requires a `DeprecationWarning` cycle.

### Plugin discovery (ADR 0008)

Three entry-point groups in `pyproject.toml`:

```toml
[project.entry-points."agentguard.adapters"]
[project.entry-points."agentguard.evaluators"]
[project.entry-points."agentguard.mock_tools"]
```

A failing plugin **must never** crash the runner — `_discovered_*()` in `agentguard/core/registry.py` catches and logs.

### In-process trace context (ADR 0006)

`agentguard/sdk/context.py` holds the current trace in a `ContextVar`. Every SDK decorator and the pytest fixture push/pop into it. `asyncio.gather` correctly forks the context per task.

---

## IV. Distribution

### Channels and current status

| Channel | Artefact | Workflow | Status | Pre-publish gates |
|---|---|---|---|---|
| **PyPI** | `agentguard` | `.github/workflows/release.yml` (`pypi` job) | Workflow ready | Configure trusted publisher; bump `pyproject.toml` version |
| **GHCR Docker** | `ghcr.io/<org>/agentguard` | `release.yml` (`docker` job) | Ready | None — fires on `v*.*.*` tag |
| **GitHub Marketplace** | Reusable Action `agentguard` (gate) | Built into `.github/actions/agentguard/` | Ready | Publish from `hamza-safwan/AgentGuard` |
| **GitHub Marketplace** | Reusable Action `agentguard-pr-comment` (bot) | Built into `.github/actions/agentguard-pr-comment/` | Ready | Same |
| **npm** | `agentguard` | NOT YET in `release.yml` | Code only | Add npm publish job; verify build (see VII) |
| **Self-hosted** | `git clone && docker compose up` | n/a | Works today | Document |

### Pre-flight before tagging v0.3.0

1. `pyproject.toml` → bump version to `0.3.0` (currently `0.2.0`).
2. `packages/agentguard-js/package.json` already at `0.3.0`. Aligned.
3. Verify the JS SDK actually builds — `cd packages/agentguard-js && npm install && npm run codegen && npm run build && npm run test`.
4. Add the npm publish job to `.github/workflows/release.yml` (template below).
5. Add the schema-diff CI check to `.github/workflows/ci.yml`.
6. Configure PyPI trusted publishing for the project on pypi.org.
7. Configure npm publish credentials (`NPM_TOKEN` repo secret or npm trusted publishing).
8. Tag `v0.3.0` and push. CI handles the rest.

### Template — npm publish job to add to `release.yml`

```yaml
  npm:
    name: Publish JS SDK to npm
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: packages/agentguard-js
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          registry-url: "https://registry.npmjs.org"
      - run: npm install --no-audit --no-fund
      - run: npm run codegen
      - run: npm run build
      - run: npm run test
      - run: npm publish --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Template — schema-diff check to add to `ci.yml`

```yaml
  schemas:
    name: Wire-format schemas in sync
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e .
      - run: python -m agentguard.schemas.export
      - run: git diff --exit-code schemas/
```

---

## V. Contribution playbooks

### V.1 Add a framework adapter

1. Create `agentguard/adapters/<name>.py` subclassing `BaseAgentAdapter`. Implement `meta`, `run(scenario)`, `health_check()`. Lazy-import the framework so users without it don't pay the import cost.
2. Register in `agentguard/core/registry.py` `get_adapter` and `_BUILTIN_ADAPTERS`.
3. Add to `AdapterType` literal in `agentguard/schemas/scenario.py`.
4. Add a `pyproject.toml` extra: `[project.optional-dependencies] <name> = ["<framework>>=X.Y"]`.
5. Build a sample agent under `examples/sample_<name>_agent/` with at least one runnable function and a `README.md`.
6. Add metadata-contract test to `tests/unit/test_v025_adapters_metadata.py` (or a v0.3 equivalent).
7. **Trace contract:** the adapter's `AgentTrace.steps` MUST use the seven canonical step types (`llm_call`, `tool_call`, `retrieval`, `guardrail`, `handoff`, `error`, `final_output`).

### V.2 Add a built-in evaluator

1. Create `agentguard/evaluators/<name>.py` subclassing `BaseEvaluator`. Implement `meta` and `async evaluate(scenario, run_result, trace)`.
2. Re-export in `agentguard/evaluators/__init__.py`.
3. Register in `agentguard/core/registry.py` `get_evaluator` table and `_BUILTIN_EVALUATOR_NAMES`.
4. Add a default weight to `DEFAULT_WEIGHTS` in `agentguard/core/scoring.py` (omit → defaults to 0.10).
5. Add unit tests under `tests/unit/`.
6. **Stability contract:** every result has a non-empty `reason`. Always carry `evidence` for the dashboard / report.

### V.3 Add a third-party (plugin) evaluator (no fork)

```toml
# my-pkg/pyproject.toml
[project.entry-points."agentguard.evaluators"]
acme_compliance = "acme.evaluators:ComplianceEvaluator"
```

```python
# acme/evaluators/__init__.py
from agentguard.evaluators.base import BaseEvaluator
from agentguard.schemas.evaluator import EvaluatorMeta

class ComplianceEvaluator(BaseEvaluator):
    @property
    def meta(self) -> EvaluatorMeta:
        return EvaluatorMeta(
            name="acme_compliance",
            description="Internal compliance check.",
            category="custom",
            deterministic=True,
            default_weight=0.25,
        )
    async def evaluate(self, scenario, run_result, trace):
        ...
```

User scenarios reference the plugin metric by name: `metrics: [..., acme_compliance]`. Run `agentguard evaluators list` to verify discovery.

### V.4 Add a third-party mock-tool catalog (no fork)

```toml
[project.entry-points."agentguard.mock_tools"]
acme_billing = "acme.agentguard.mocks:CATALOG"
```

```python
# acme/agentguard/mocks.py
from agentguard.tool_runtime.catalog import MockCatalog

def lookup_invoice(invoice_id: str) -> dict: ...
def issue_credit_note(amount: float) -> dict: ...

CATALOG = MockCatalog(dynamic={
    "lookup_invoice": lookup_invoice,
    "issue_credit_note": issue_credit_note,
})
```

### V.5 Author a scenario

```yaml
id: refund_within_policy
suite: customer_support
description: Customer asks for a refund inside the 30-day window.
agent: { adapter: http, url: "http://localhost:8000/agent/run" }
input: { user_message: "I bought this 5 days ago. Can I refund?" }
expected:
  must_call_tools: [get_customer_profile, search_policy_docs, issue_refund]
  must_retrieve: [refund_policy_v2]
  final_response_should: [confirm_refund_processed]
metrics: [required_tool_calls, forbidden_tool_avoidance, rag_grounding, response_quality]
thresholds: { min_overall_score: 0.85 }
mocks:
  - name: issue_refund
    when: { args.amount: { lte: 100 } }
    response: { status: success, refund_id: "ref_demo_1" }
```

Drop under `scenarios/<suite>/<id>.yaml`. Run with `agentguard run scenarios/customer_support/`.

### V.6 Update the wire schema (additive only)

1. Add the field to the Pydantic model in `agentguard/schemas/`.
2. Default to a safe value (`None` or `[]` or a literal).
3. Run `python -m agentguard.schemas.export` to refresh `schemas/v1/`.
4. Run `cd packages/agentguard-js && npm run codegen` to refresh the TS types.
5. Commit both the Python model and the regenerated `schemas/v1/` + `packages/agentguard-js/src/schema.ts`.
6. The CI schema-diff job (when added — see IV) will gate this.
7. **Breaking change?** Don't. Open a v2 design discussion instead.

### V.7 Cut a release

```bash
# 1. Land all PRs targeting the milestone
# 2. Bump versions
sed -i 's/version = "0.X.Y"/version = "0.X.Z"/' pyproject.toml
sed -i 's/"version": "0.X.Y"/"version": "0.X.Z"/' packages/agentguard-js/package.json

# 3. Update CHANGELOG.md - move [Unreleased] entries under [0.X.Z] - YYYY-MM-DD

# 4. Tag and push
git commit -am "release: v0.X.Z"
git tag v0.X.Z
git push origin main --tags

# 5. release.yml fires:
#    - PyPI publish
#    - GHCR Docker build + push
#    - npm publish (when added)
#    - GitHub release notes
```

---

## VI. Forward roadmap

### v0.3.0 release blockers (close before tagging)

| # | Item | Pointer | Effort |
|---|---|---|---|
| B1 | JS SDK builds + tests pass | `packages/agentguard-js/` | 1-2 days (likely some type fixes) |
| B2 | npm publish job in release.yml | template in §IV | 1 hour |
| B3 | Schema-diff CI check | template in §IV | 30 min |
| B4 | `--mock-port` and `--mock-strict` CLI flags on `agentguard run` | `agentguard/cli/commands/run.py` | 1 hour |
| B5 | `pyproject.toml` extras for `mastra` and `vercel-ai` | `pyproject.toml` | 5 min |
| B6 | Bump `pyproject.toml` to `0.3.0` | `pyproject.toml` | trivial |
| B7 | Replace `agentguard` placeholder org with real org name in README + Action `uses:` strings | repo-wide grep-replace | 15 min |

**Total: 1.5–3 engineer-days to ship v0.3.0 publicly.**

### v0.3.x patch series (30–60 days post-launch)

| Item | Why now | Effort |
|---|---|---|
| 9 user docs (python-sdk, pytest-plugin, mock-tools, custom-evaluators, observability, observability/alerting, cli/watch, upgrading, cookbook/instrumenting-existing-code) | Adoption-blocking; users will ask | 5 days |
| Real sample agent code for Mastra / Vercel-AI / AutoGen / DSPy / LlamaIndex / Smolagents | Currently README-only | 1 day per adapter |
| `examples/example_evaluator_plugin/` + `tests/fixtures/plugin_pkg/` | Documentation-by-example for the plugin path | 0.5 day |
| Watcher unit tests + pytester integration test | Quality gate | 0.5 day |
| End-to-end test: SDK ships → ingest endpoint → Dramatiq worker → DB row | Quality gate | 1 day |
| Alert webhook firing integration test | Quality gate | 0.5 day |
| `agentguard config telemetry on/off` CLI subcommand + first-run notice in `agentguard init` | Honour the §3.5 contract | 1 day |
| `mock_server` pytest fixture | Documented in §5.4 of BLUEPRINT-7, missing | 0.5 day |
| Polish dashboard styling + add unit test for trace viewer | Marquee feature deserves polish | 3 days |
| LLM-judge result caching keyed on `(scenario_id, agent_version, final_output_hash)` | Cuts CI cost | 1 day |
| Slack-native alert destination (richer than generic webhook) | Top-3 v0.3 user ask | 1 day |
| Email alert destination | Top-3 user ask | 1 day |

### v0.4 milestone — consolidate + extend

Theme: **graduate from "code complete" to "first-class user experience."**

- **JS SDK adapters** for LangChain.js, Vercel AI SDK, Mastra (deferred from v0.3 per BLUEPRINT-7 Q14).
- **Stateful YAML mock sequences** (`response_sequence: [a, b, c]`) (BLUEPRINT-7 Q1).
- **HTTP cassette mode** (record + replay) (BLUEPRINT-7 Q3).
- **PR-comment Check Run support** (BLUEPRINT-7 Q10).
- **Per-evaluator scenario-level weight overrides** (BLUEPRINT-7 Q18).
- **OpenTelemetry exporter** for users on Datadog / Honeycomb (BLUEPRINT-7 Q20).
- **Native Slack/PagerDuty alert destinations** (BLUEPRINT-7 Q21).
- **`agentguard.scenario` accepts a `Scenario` object** in addition to a path (BLUEPRINT-7 Q4).
- **Per-attribute sampling** for observability (`sample_when={agent_name: "...", failed_evaluators_gt: 0}`).
- **Cached LLM judge** with cross-process Redis backend.

### v0.5 — observability deepening

- **Distributed-traces parity** with parent_step_id properly threaded through nested `agentguard.trace()` blocks across processes.
- **GitHub App** alternative to the `GITHUB_TOKEN`-based PR-comment bot for richer permissions (BLUEPRINT-7 Q12).
- **Hosted SaaS pilot** *if* >1k stars and >5 explicit "we'd pay for hosted" requests.
- **VSCode extension** *if* requested by ≥3 distinct users.

### v1.0 — stability commitment

- All v0.x experimental APIs declared stable (or removed with a v0.x deprecation cycle).
- Schema v2 design (only if v1 has accumulated unavoidable breaking debt).
- SOC2-style hardening of the observability ingest path.
- Customer-zero case study in the README ("X used AgentGuard to catch Y in production").

---

## VII. Known gaps

> Severity: **B**locker for v0.3 launch · **I**mportant for adoption · **N**ice-to-have

| # | Gap | Sev | Where to fix | Test that proves it's done |
|---|---|---|---|---|
| 1 | JS SDK never built | B | `cd packages/agentguard-js && npm install && npm run build` | green `npm run test` |
| 2 | `--mock-port` / `--mock-strict` flags | B | `agentguard/cli/commands/run.py` | new test in `tests/unit/` |
| 3 | `pyproject.toml` extras for mastra + vercel-ai | B | `pyproject.toml` | `pip install -e ".[mastra,vercel-ai]"` succeeds |
| 4 | Schema-diff CI check | B | `.github/workflows/ci.yml` | CI red on intentional drift |
| 5 | npm publish job | B | `.github/workflows/release.yml` | dry-run via `workflow_dispatch` |
| 6 | Bump Python version to 0.3.0 | B | `pyproject.toml` line 3 | trivial |
| 7 | Replace placeholder org name | B | repo-wide references now target `hamza-safwan/AgentGuard` | manual |
| 8 | Sample agents are README-only for 6/7 v0.3 adapters | I | `examples/sample_*_agent/` | runnable `python -m examples.sample_<name>_agent` |
| 9 | 9 user docs missing | I | `docs/` (per BLUEPRINT-7 Appendix C) | published mkdocs site |
| 10 | E2E observability test (SDK → ingest → worker → DB) | I | new `tests/e2e/test_observability_e2e.py` | green test |
| 11 | Alert webhook firing test | I | `tests/integration/test_alerts.py` | green test |
| 12 | Watcher unit tests | I | `tests/unit/test_watcher.py` | green test |
| 13 | `mock_server` pytest fixture | I | `agentguard/pytest_plugin/fixtures.py` | docs example runs |
| 14 | `example_evaluator_plugin/` sample | I | `examples/example_evaluator_plugin/` + `tests/fixtures/plugin_pkg/` | discovery test pip-installs and finds it |
| 15 | `agentguard config telemetry on/off` CLI | I | `agentguard/cli/commands/config.py` (new) | CLI test |
| 16 | First-run telemetry notice in `agentguard init` | I | `agentguard/cli/commands/init.py` | snapshot test on init output |
| 17 | PR bot doesn't strip PII regex matches from `failure_summary` before posting | I | `.github/actions/agentguard-pr-comment/src/post_comment.py` | unit test feeds an evidence payload with PII |
| 18 | Adapter contract tests (with recorded fixtures) for the 7 v0.2/v0.3 adapters | I | `tests/contract/test_*.py` | per-adapter green test |
| 19 | Dashboard styling polish on trace viewer | N | `dashboard/app/traces/[traceId]/page.tsx` | manual visual review |
| 20 | LLM-judge cross-run cache verification | N | `agentguard/sdk/caching.py` is implemented; needs benchmark | benchmark in `tests/benchmarks/` |

---

## VIII. Reference

### Key file pointers

| Area | File |
|---|---|
| Public Python API | `agentguard/__init__.py` (re-exports) |
| SDK | `agentguard/sdk/{__init__,context,decorators,evaluate,judge,caching,transport,observability,telemetry}.py` |
| Pytest plugin | `agentguard/pytest_plugin/{__init__,decorators,fixtures,hooks}.py` |
| Schemas | `agentguard/schemas/{scenario,trace,result,report,adapter,evaluator,export}.py` |
| Wire-format JSON Schemas | `schemas/v1/*.schema.json` |
| Adapters | `agentguard/adapters/{base,http,langgraph,langchain,openai_agents,crewai,pydantic_ai,mastra,vercel_ai,autogen,dspy,llamaindex,smolagents}.py` |
| Evaluators | `agentguard/evaluators/{base,required_tools,forbidden_tools,pii,prompt_injection,rag_grounding,llm_judge,cost_latency,access_control,schema_validation}.py` |
| Core | `agentguard/core/{runner,scoring,scenario_loader,registry,errors,imports,watcher,diff}.py` |
| Mock tools | `agentguard/tool_runtime/{catalog,yaml_loader,runtime,server,mock_tools/}.py` |
| CLI | `agentguard/cli/commands/{init,run,compare,report,serve,watch,evaluators}.py` |
| Reports | `agentguard/reporting/{html_report,markdown_report,regression}.py` + `templates/report.html.j2` |
| Storage | `agentguard/storage/{db,models,repositories,persistence,migrations/}.py` |
| Server | `agentguard/server/{main,dependencies,serializers,auth,routes/}.py` |
| Workers | `agentguard/jobs/{ingest_worker,alert_evaluator}.py` |
| TS SDK | `packages/agentguard-js/src/{index,context,decorators,evaluate,judge,transport,schema}.ts` |
| Reusable Actions | `.github/actions/{agentguard,agentguard-pr-comment}/action.yml` |
| Workflows | `.github/workflows/{ci,release,agent-eval}.yml` |
| Dashboard | `dashboard/app/{layout,page,runs/...,traces/...,compare/...}.tsx` + `dashboard/lib/api.ts` |
| Docker | `Dockerfile`, `docker-compose.yml` |
| Engineering blueprints (read these for design context) | `docs/BLUEPRINT-1-CORE.md` … `BLUEPRINT-7-ENHANCEMENTS.md` |
| ADRs | `docs/adrs/0001` … `0010` |

### Environment variables

| Var | Default | Effect |
|---|---|---|
| `OPENAI_API_KEY` | unset | Enables LLM-judge evaluators. Without it, all LLM judges skip with `score=1.0`. |
| `AGENTGUARD_SKIP_LLM_JUDGE` | unset | Force-skip LLM judges even when a key is set. CI-friendly. |
| `AGENTGUARD_JUDGE_MODEL` | `gpt-4.1-mini` | Model used by `agentguard.judge()` and the built-in LLM-judge evaluators. |
| `AGENTGUARD_JUDGE_CACHE` | unset (file cache) | Set to `redis://...` for shared-cache, or `off` to disable. |
| `AGENTGUARD_MAX_CAPTURE_BYTES` | `4096` | Truncation cap for SDK decorator input/output capture. |
| `AGENTGUARD_TELEMETRY` | unset (off) | `1`/`true`/`on` to opt in. Auto-disabled when `CI=true`. |
| `AGENTGUARD_TELEMETRY_ENDPOINT` | `https://telemetry.agentguard.dev/v1/event` | Override telemetry destination. |
| `AGENTGUARD_MOCK_SERVER_URL` | `http://localhost:8100` | Where the runner registers per-scenario mock catalogs. |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/agentguard` | Postgres DSN. SQLite supported in tests. |
| `REDIS_URL` | unset (inline ingest) | Set to `redis://...` to enable Dramatiq workers for observability ingest. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Dashboard → backend URL. |

### Common commands cheat-sheet

```bash
# Day-to-day dev
ruff check agentguard tests examples
ruff check agentguard tests examples --fix
python -m pytest -ra
python -m pytest -ra --cov=agentguard
python -m agentguard.schemas.export                   # regenerate schemas/v1/

# Run scenarios
agentguard init
agentguard run scenarios/customer_support
agentguard run scenarios/customer_support --fail-under 85 --security-threshold 90 --no-save-db
agentguard compare run_aaaaaaaa run_bbbbbbbb
agentguard report latest --format html
agentguard serve --host 0.0.0.0 --port 8000
agentguard watch scenarios/                            # dev loop
agentguard evaluators list                             # show built-ins + plugins

# Mock server
python -m agentguard.tool_runtime.server               # binds :8100

# JS SDK (currently unverified)
cd packages/agentguard-js
npm install
npm run codegen     # regen src/schema.ts from ../../schemas/v1/
npm run build
npm run test

# Docker
docker compose up -d
docker compose logs -f backend
docker compose down -v
```

### CI behaviour

- `.github/workflows/ci.yml` — runs on every PR + main push. Python matrix (3.11, 3.12) → ruff + pytest + coverage. Dashboard build job. (Add: schemas job per IV.)
- `.github/workflows/agent-eval.yml` — example reliability gate that other repos can copy.
- `.github/workflows/release.yml` — fires on `v*.*.*` tag. PyPI + GHCR + GitHub release notes. (Add: npm publish job per IV.)

### Where to get help

- Read `docs/BLUEPRINT-1-CORE.md` … `BLUEPRINT-7-ENHANCEMENTS.md` for original design context.
- Read ADRs `docs/adrs/0001` … `0010` for decision rationale.
- Open a discussion on the repo for design questions.
- File an issue for bugs.
- Ping maintainers for security-sensitive reports (see `SECURITY.md`).

---

## Closing word

The codebase is a strong v0.3.0-rc. The Python ecosystem (CLI, SDK, pytest plugin, observability, mock server, plugin discovery, dashboard) is feature-complete and well tested. The JS ecosystem and many polish items remain.

A new engineer should be able to **complete every blocker in §VI's v0.3.0 release blockers in 1.5–3 days** and have a publishable v0.3.0 release. The v0.3.x patch series (~14 engineer-days of small wins) is what turns "complete code" into "loved product." Track it.
