"""Typer entrypoint — wires up every CLI subcommand."""

from __future__ import annotations

import typer

from agentguard.cli.commands import compare, evaluators, init, report, run, serve, watch

app = typer.Typer(
    name="agentguard",
    help="CI/CD reliability and security testing for LLM agents.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.command(name="init", help="Scaffold a new AgentGuard project.")(init.init_project)
app.command(name="run", help="Run scenarios against an agent.")(run.run_scenarios_cmd)
app.command(name="compare", help="Compare two runs and show regressions.")(compare.compare_runs)
app.command(name="report", help="Generate an HTML/Markdown/JSON report from a run.")(
    report.generate_report
)
app.command(name="serve", help="Start the AgentGuard backend API + dashboard.")(serve.start_server)
app.command(name="watch", help="Re-run scenarios on file change (dev loop).")(watch.watch_cmd)
app.add_typer(evaluators.app, name="evaluators", help="Inspect built-in and plugin evaluators.")


if __name__ == "__main__":
    app()
