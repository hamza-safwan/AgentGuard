"""``agentguard watch`` - re-run scenarios on file change (BLUEPRINT-7 section 11)."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer
from rich.console import Console

from agentguard.core.diff import render_delta
from agentguard.core.runner import RunOptions, run_path
from agentguard.core.watcher import serve_forever, watch_paths

console = Console()


def _resolve_watch_paths(scenario_path: Path, extra: list[Path]) -> list[Path]:
    paths: list[Path] = [scenario_path]
    paths.extend(extra)
    examples_dir = Path("examples")
    if examples_dir.exists():
        paths.append(examples_dir)
    agentguard_dir = Path("agentguard")
    if agentguard_dir.exists():
        paths.append(agentguard_dir)
    # de-dupe
    seen: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    return seen


def watch_cmd(
    path: Path = typer.Argument(..., help="Scenario file or directory to watch."),
    watch_paths_extra: list[Path] = typer.Option(
        [],
        "--watch-paths",
        help="Additional paths to watch for re-runs (repeatable).",
    ),
    debounce: int = typer.Option(250, "--debounce", help="Debounce window (ms)."),
    skip_llm_judge: bool = typer.Option(
        False,
        "--skip-llm-judge",
        help="Disable LLM-based evaluators (rule-based only).",
        envvar="AGENTGUARD_SKIP_LLM_JUDGE",
    ),
    parallel: int = typer.Option(1, "--parallel", help="Parallel scenario workers."),
    clear: bool = typer.Option(True, "--clear/--no-clear", help="Clear screen between runs."),
    agent_version: str = typer.Option("watch", "--agent-version"),
) -> None:
    """Watch ``path`` and rerun scenarios when YAML / agent / evaluator code changes."""
    if skip_llm_judge:
        os.environ["AGENTGUARD_SKIP_LLM_JUDGE"] = "1"

    options = RunOptions(
        agent_version=agent_version,
        save=False,
        parallel=parallel,
        skip_llm_judge=skip_llm_judge,
    )

    watched = _resolve_watch_paths(path, watch_paths_extra)
    console.print(
        "[bold cyan]agentguard watch[/bold cyan] - "
        f"scenarios=[bold]{path}[/bold]  "
        f"watching=[dim]{', '.join(str(p) for p in watched)}[/dim]"
    )

    state: dict = {"baseline": None, "running": False, "lock": asyncio.Lock()}

    def _run_once() -> None:
        if state["running"]:
            return
        state["running"] = True
        try:
            if clear:
                console.clear()
            try:
                summary, results = asyncio.run(run_path(path, options))
            except Exception as exc:
                console.print(f"[bold red]Run failed:[/bold red] {exc}")
                return
            render_delta(state["baseline"], (summary, results))
            state["baseline"] = (summary, results)
        finally:
            state["running"] = False

    # Initial baseline run
    _run_once()

    def on_change(paths: set[str]) -> None:
        files = ", ".join(sorted(Path(p).name for p in paths)[:5])
        console.print(f"\n[dim]change detected: {files}[/dim]")
        _run_once()

    observer = watch_paths(watched, on_change=on_change, debounce_ms=debounce)
    console.print("[dim]Watching for changes... (Ctrl+C to stop)[/dim]\n")
    serve_forever(observer)
