"""Report generators (HTML, Markdown, JSON) and regression diff."""

from agentguard.reporting.html_report import render_html
from agentguard.reporting.markdown_report import render_markdown
from agentguard.reporting.regression import compute_regression

__all__ = ["render_html", "render_markdown", "compute_regression"]
