"""`agentguard report` — generate HTML/Markdown/JSON reports from a saved run."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from agentguard.reporting.html_report import render_html
from agentguard.reporting.markdown_report import render_markdown

console = Console()


def _resolve_run(run_id_or_path: str) -> tuple[Path, dict]:
    candidate = Path(run_id_or_path)
    if candidate.exists():
        return candidate, json.loads(candidate.read_text(encoding="utf-8"))
    if run_id_or_path == "latest":
        runs_dir = Path(".agentguard/runs")
        if not runs_dir.exists():
            raise FileNotFoundError("No runs directory found. Did you pass --save earlier?")
        files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            raise FileNotFoundError("No saved runs in .agentguard/runs/.")
        return files[0], json.loads(files[0].read_text(encoding="utf-8"))
    local = Path(".agentguard/runs") / f"{run_id_or_path}.json"
    if local.exists():
        return local, json.loads(local.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"No run found for {run_id_or_path!r}.")


def generate_report(
    run_id: str = typer.Argument(..., help="Run ID, JSON path, or 'latest'."),
    format: str = typer.Option("html", "--format", help="html | markdown | json."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file (defaults to ./reports/<run_id>.<ext>)."
    ),
) -> None:
    """Generate a report file from a saved run JSON."""
    try:
        path, data = _resolve_run(run_id)
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=2) from e

    summary = data["summary"]
    results = data["results"]

    fmt = format.lower()
    ext = {"html": "html", "markdown": "md", "md": "md", "json": "json"}.get(fmt)
    if ext is None:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(code=2)

    out = output or Path("reports") / f"{summary['run_id']}.{ext}"
    out.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "html":
        out.write_text(render_html(summary, results), encoding="utf-8")
    elif fmt in ("markdown", "md"):
        out.write_text(render_markdown(summary, results), encoding="utf-8")
    else:  # json
        out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    console.print(f"[bold green]Wrote report:[/bold green] {out}")
