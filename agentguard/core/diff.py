"""Render scorecard deltas between two RunSummaries / result lists.

Used by ``agentguard watch`` to show only what changed between the previous
run and the new one. Reuses the regression-diff data model so the UX is
consistent with ``agentguard compare``.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from agentguard.reporting.regression import compute_regression
from agentguard.schemas.report import RunSummary
from agentguard.schemas.result import ScenarioResult

console = Console()


def _payload(summary: RunSummary, results: list[ScenarioResult]) -> dict:
    return {
        "summary": summary.model_dump(mode="json"),
        "results": [r.model_dump(mode="json") for r in results],
    }


def render_delta(
    base: tuple[RunSummary, list[ScenarioResult]] | None,
    candidate: tuple[RunSummary, list[ScenarioResult]],
) -> None:
    """Print a Rich table of metric deltas + new failures / fixes / unchanged."""
    summary, results = candidate
    if base is None:
        # First run -> no delta, just headline
        console.rule(f"[bold cyan]agentguard watch  -  baseline run {summary.run_id}[/bold cyan]")
        console.print(
            f"overall {summary.overall_score:.0f}/100  "
            f"security {summary.security_score:.0f}/100  "
            f"passed {summary.passed_scenarios}/{summary.total_scenarios}"
        )
        return

    base_summary, base_results = base
    report = compute_regression(_payload(base_summary, base_results), _payload(summary, results))

    console.rule(
        f"[bold cyan]agentguard watch  -  rerun {summary.run_id} "
        f"(was {base_summary.run_id})[/bold cyan]"
    )
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Was", justify="right")
    table.add_column("Now", justify="right")
    table.add_column("Delta", justify="right")
    any_change = False
    for d in report.deltas:
        if abs(d.delta) < 0.001:
            continue
        any_change = True
        color = "red" if d.regressed else "green"
        sign = "+" if d.delta >= 0 else ""
        table.add_row(
            d.metric_name,
            f"{d.base_score:.1f}",
            f"{d.candidate_score:.1f}",
            f"[{color}]{sign}{d.delta:.1f}[/{color}]",
        )
    if any_change:
        console.print(table)
    else:
        console.print("[dim]No metric changes.[/dim]")

    if report.new_failures:
        console.print("[bold red]New failures:[/bold red]")
        for s in report.new_failures:
            console.print(f"  - {s}")
    if report.fixed_scenarios:
        console.print("[bold green]Fixed:[/bold green]")
        for s in report.fixed_scenarios:
            console.print(f"  + {s}")
    if not report.new_failures and not report.fixed_scenarios and not any_change:
        console.print("[dim]Suite is unchanged since last run.[/dim]")
