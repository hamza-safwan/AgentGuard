"""`agentguard serve` — run the FastAPI backend (and optionally point at the dashboard)."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def start_server(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind."),
    port: int = typer.Option(8000, "--port", help="Port to bind."),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes."),
) -> None:
    """Start the AgentGuard FastAPI backend."""
    try:
        import uvicorn
    except ImportError as e:
        console.print("[red]uvicorn not installed.[/red] Install with: pip install agentguard")
        raise typer.Exit(code=2) from e
    console.print(f"[bold cyan]Starting AgentGuard API on http://{host}:{port}[/bold cyan]")
    console.print("[dim]Dashboard expects this API at NEXT_PUBLIC_API_URL.[/dim]\n")
    uvicorn.run("agentguard.server.main:app", host=host, port=port, reload=reload)
