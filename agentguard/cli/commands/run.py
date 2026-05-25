"""`agentguard run` — execute scenarios and emit a Rich-formatted scorecard."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentguard.core.runner import RunOptions, run_path
from agentguard.schemas.report import RunSummary
from agentguard.schemas.result import ScenarioResult

console = Console()

DEPLOY_BADGE = {
    "deploy_with_monitoring": ("[bold green]DEPLOY (with monitoring)[/bold green]", "green"),
    "deploy_carefully": ("[bold yellow]DEPLOY CAREFULLY[/bold yellow]", "yellow"),
    "fix_before_production": ("[bold orange3]FIX BEFORE PRODUCTION[/bold orange3]", "orange3"),
    "do_not_deploy": ("[bold red]DO NOT DEPLOY[/bold red]", "red"),
}


def _color_for_score(score: float) -> str:
    if score >= 90:
        return "green"
    if score >= 80:
        return "yellow"
    if score >= 70:
        return "orange3"
    return "red"


def _print_header(suite: str, agent_version: str) -> None:
    console.print(
        Panel.fit(
            f"[bold]Suite:[/bold] {suite}\n[bold]Agent version:[/bold] {agent_version}",
            title="[bold cyan]AgentGuard[/bold cyan]",
            border_style="cyan",
        )
    )


def _print_scenario_table(results: list[ScenarioResult]) -> None:
    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Scenario", style="white", no_wrap=False)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Failure", style="dim", no_wrap=False)
    for r in results:
        status = "[bold green]PASS[/bold green]" if r.passed else "[bold red]FAIL[/bold red]"
        score = int(round(r.overall_score * 100))
        score_str = f"[{_color_for_score(score)}]{score}[/{_color_for_score(score)}]"
        failure = r.failure_summary or ""
        if len(failure) > 80:
            failure = failure[:77] + "..."
        table.add_row(r.scenario_id, status, score_str, failure)
    console.print(table)


def _print_summary(summary: RunSummary) -> None:
    metrics_table = Table.grid(padding=(0, 2))
    metrics_table.add_column(justify="left", style="bold")
    metrics_table.add_column(justify="right")

    overall_color = _color_for_score(summary.overall_score)
    security_color = _color_for_score(summary.security_score)
    rag_color = _color_for_score(summary.rag_score)
    tool_color = _color_for_score(summary.tool_score)

    metrics_table.add_row(
        "Overall score:",
        f"[{overall_color}]{summary.overall_score:.0f}/100[/{overall_color}]",
    )
    metrics_table.add_row(
        "Security score:",
        f"[{security_color}]{summary.security_score:.0f}/100[/{security_color}]",
    )
    metrics_table.add_row(
        "RAG grounding:",
        f"[{rag_color}]{summary.rag_score:.0f}/100[/{rag_color}]",
    )
    metrics_table.add_row(
        "Tool correctness:",
        f"[{tool_color}]{summary.tool_score:.0f}/100[/{tool_color}]",
    )
    metrics_table.add_row("Avg cost:", f"${summary.avg_cost_usd:.4f}")
    p95 = (
        f"{(summary.p95_latency_ms / 1000):.1f}s" if summary.p95_latency_ms else "n/a"
    )
    metrics_table.add_row("p95 latency:", p95)

    console.print()
    console.print(metrics_table)
    badge, _ = DEPLOY_BADGE.get(
        summary.deployment_recommendation, ("[red]?[/red]", "red")
    )
    console.print(f"\n[bold]Deployment:[/bold] {badge}\n")


def _print_failed_findings(summary: RunSummary, results: list[ScenarioResult]) -> None:
    if not summary.security_findings:
        return
    console.print("[bold red]Security findings:[/bold red]")
    for f in summary.security_findings:
        sev_color = {"critical": "red", "high": "orange3", "medium": "yellow", "low": "blue"}.get(
            f.severity, "white"
        )
        console.print(
            f"  [{sev_color}][{f.severity.upper()}][/{sev_color}] "
            f"{f.scenario_id}: {f.finding}"
        )
    console.print()


def _emit_json(summary: RunSummary, results: list[ScenarioResult]) -> None:
    payload = {
        "summary": summary.model_dump(mode="json"),
        "results": [r.model_dump(mode="json") for r in results],
    }
    console.print_json(data=payload)


def _save_json(summary: RunSummary, results: list[ScenarioResult], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / f"{summary.run_id}.json"
    out.write_text(
        json.dumps(
            {
                "summary": summary.model_dump(mode="json"),
                "results": [r.model_dump(mode="json") for r in results],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return out


def run_scenarios_cmd(
    path: Path = typer.Argument(..., help="Path to scenario file or directory."),
    agent_version: str = typer.Option("dev", "--agent-version", help="Tag for this agent version."),
    fail_under: int | None = typer.Option(
        None, "--fail-under", help="Min overall score (0-100) to pass; sets exit code 1 on miss."
    ),
    security_threshold: int | None = typer.Option(
        None, "--security-threshold", help="Min security score (0-100); sets exit code 1 on miss."
    ),
    output: str = typer.Option(
        "table", "--output", help="Output format: table | json | minimal."
    ),
    save: bool = typer.Option(False, "--save", help="Save results to ./.agentguard/runs/."),
    save_db: bool = typer.Option(
        True,
        "--save-db/--no-save-db",
        help="Persist results to the configured database; use --no-save-db for JSON-only runs.",
    ),
    parallel: int = typer.Option(1, "--parallel", help="Number of scenarios to run concurrently."),
    skip_llm_judge: bool = typer.Option(
        False,
        "--skip-llm-judge",
        help="Disable LLM-based evaluators (rule-based only).",
        envvar="AGENTGUARD_SKIP_LLM_JUDGE",
    ),
    mock_port: int | None = typer.Option(
        None,
        "--mock-port",
        min=1,
        max=65535,
        help="Port for the AgentGuard mock tool server.",
    ),
    mock_strict: bool = typer.Option(
        False,
        "--mock-strict",
        help="For scenario-scoped mocks, return 424 for unregistered tool calls.",
    ),
) -> None:
    """Run scenarios at PATH against their configured agents."""
    if skip_llm_judge:
        os.environ["AGENTGUARD_SKIP_LLM_JUDGE"] = "1"

    options = RunOptions(
        agent_version=agent_version,
        fail_under=fail_under,
        security_threshold=security_threshold,
        save=save,
        parallel=parallel,
        skip_llm_judge=skip_llm_judge,
        mock_port=mock_port,
        mock_strict=mock_strict,
    )

    if output == "table":
        _print_header(suite=str(path), agent_version=agent_version)

    captured: list[ScenarioResult] = []

    def _on_result(r: ScenarioResult) -> None:
        captured.append(r)
        if output == "minimal":
            mark = "PASS" if r.passed else "FAIL"
            console.print(f"  [{mark}] {r.scenario_id}  ({int(r.overall_score * 100)})")

    try:
        summary, results = asyncio.run(
            run_path(path, options, on_result=_on_result if output != "json" else None)
        )
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=2) from e
    except Exception as e:
        console.print(f"[bold red]Runner error:[/bold red] {e}")
        raise typer.Exit(code=2) from e

    if output == "json":
        _emit_json(summary, results)
    elif output == "table":
        console.print(
            f"\n[bold]Scenarios:[/bold] {summary.total_scenarios}  "
            f"[green]Passed:[/green] {summary.passed_scenarios}  "
            f"[red]Failed:[/red] {summary.failed_scenarios}\n"
        )
        _print_scenario_table(results)
        _print_summary(summary)
        _print_failed_findings(summary, results)

    if save:
        out = _save_json(summary, results, Path(".agentguard/runs"))
        console.print(f"[dim]Saved run to {out}[/dim]")

    if save_db:
        try:
            from agentguard.storage.persistence import save_run

            save_run(summary, results)
            console.print("[dim]Persisted run to database.[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] could not persist to DB: {e}")

    # CI gates
    exit_code = 0
    if fail_under is not None and summary.overall_score < fail_under:
        console.print(
            f"[bold red]FAILED:[/bold red] overall score {summary.overall_score:.0f} "
            f"< threshold {fail_under}"
        )
        exit_code = 1
    if security_threshold is not None and summary.security_score < security_threshold:
        console.print(
            f"[bold red]FAILED:[/bold red] security score {summary.security_score:.0f} "
            f"< threshold {security_threshold}"
        )
        exit_code = 1
    if exit_code:
        sys.exit(exit_code)
