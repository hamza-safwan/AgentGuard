"""`agentguard compare` — diff two runs."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentguard.reporting.regression import compute_regression

console = Console()


def _load_run(run_id_or_path: str) -> dict:
    candidate = Path(run_id_or_path)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    local = Path(".agentguard/runs") / f"{run_id_or_path}.json"
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        f"No run found for {run_id_or_path!r}. "
        f"Pass a run JSON path or a run_id present under .agentguard/runs/."
    )


def compare_runs(
    base: str = typer.Argument(..., help="Base run ID (or JSON path)."),
    candidate: str = typer.Argument(..., help="Candidate run ID (or JSON path)."),
) -> None:
    """Compare two runs and show a regression report."""
    try:
        base_data = _load_run(base)
        cand_data = _load_run(candidate)
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=2) from e

    report = compute_regression(base_data, cand_data)
    base_summary = base_data["summary"]
    cand_summary = cand_data["summary"]

    console.print(
        Panel.fit(
            f"[bold]Base:[/bold] {base_summary['run_id']} ({base_summary['agent_version']})\n"
            f"[bold]Candidate:[/bold] {cand_summary['run_id']} ({cand_summary['agent_version']})",
            title="[bold cyan]Regression Comparison[/bold cyan]",
            border_style="cyan",
        )
    )

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Base", justify="right")
    table.add_column("New", justify="right")
    table.add_column("Delta", justify="right")
    for d in report.deltas:
        delta_color = "red" if d.regressed else "green"
        sign = "+" if d.delta >= 0 else ""
        table.add_row(
            d.metric_name,
            f"{d.base_score:.1f}",
            f"{d.candidate_score:.1f}",
            f"[{delta_color}]{sign}{d.delta:.1f}[/{delta_color}]",
        )
    console.print(table)

    if report.new_failures:
        console.print("\n[bold red]New failures in candidate:[/bold red]")
        for s in report.new_failures:
            console.print(f"  [red]-[/red] {s}")
    if report.fixed_scenarios:
        console.print("\n[bold green]Fixed in candidate:[/bold green]")
        for s in report.fixed_scenarios:
            console.print(f"  [green]+[/green] {s}")
    console.print(f"\n[bold]Recommendation:[/bold] {report.recommendation}\n")
