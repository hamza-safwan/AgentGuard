"""Render the HTML reliability report from a run JSON payload."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _score_class(value: float) -> str:
    if value >= 90:
        return "score-good"
    if value >= 70:
        return "score-warn"
    return "score-bad"


_env.globals["score_class"] = _score_class


def render_html(summary: dict, results: list[dict]) -> str:
    template = _env.get_template("report.html.j2")
    return template.render(summary=summary, results=results)
