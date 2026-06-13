"""``agentguard evaluators`` - list and describe registered evaluators.

Implements the user-facing surface of BLUEPRINT-7 section 10 (custom
evaluator plugins). Built-in evaluators are listed first, then any
third-party evaluators discovered via the ``agentguard.evaluators``
entry-point group.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from agentguard.core.registry import (
    _discovered_evaluators,
    get_evaluator,
    list_evaluators,
)

app = typer.Typer(help="Inspect built-in and third-party AgentGuard evaluators.")
console = Console()


@app.command("list")
def list_cmd(
    plugins_only: bool = typer.Option(
        False, "--plugins-only", help="Hide built-in evaluators."
    ),
) -> None:
    """List every evaluator registered in this Python environment."""
    table = Table(title="AgentGuard evaluators")
    table.add_column("Name", style="bold")
    table.add_column("Source")
    table.add_column("Category")
    table.add_column("Deterministic")

    rows: list[tuple[str, str, str, str]] = []
    if not plugins_only:
        for name in list_evaluators():
            try:
                meta = get_evaluator(name).meta
                rows.append((name, "built-in", meta.category, str(meta.deterministic)))
            except Exception as exc:
                rows.append((name, "built-in", f"error: {exc}", "?"))

    for name, cls in _discovered_evaluators().items():
        try:
            meta = cls().meta
            rows.append((name, "plugin", meta.category, str(meta.deterministic)))
        except Exception as exc:
            rows.append((name, "plugin", f"load error: {exc}", "?"))

    for row in rows:
        table.add_row(*row)
    console.print(table)


@app.command("describe")
def describe_cmd(name: str = typer.Argument(..., help="Evaluator name.")) -> None:
    """Show full metadata for a single evaluator."""
    try:
        evaluator = get_evaluator(name)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    meta = evaluator.meta
    console.print(f"[bold]{meta.name}[/bold]")
    console.print(f"  description    : {meta.description}")
    console.print(f"  category       : {meta.category}")
    console.print(f"  deterministic  : {meta.deterministic}")
    console.print(f"  requires_llm   : {meta.requires_llm}")
    console.print(f"  default_weight : {meta.default_weight}")
    console.print(f"  class          : {type(evaluator).__module__}.{type(evaluator).__name__}")
