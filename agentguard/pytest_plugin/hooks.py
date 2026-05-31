"""Pytest hooks: CLI options, marker, custom failure repr, session report."""

from __future__ import annotations

import json
import os
from datetime import UTC
from pathlib import Path
from typing import Any

import pytest

from agentguard.schemas.result import ScenarioResult


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("agentguard")
    group.addoption(
        "--agentguard-skip-llm-judge",
        action="store_true",
        default=False,
        help="Disable LLM-based AgentGuard evaluators (rule-based only).",
    )
    group.addoption(
        "--agentguard-fail-under",
        type=int,
        default=None,
        metavar="SCORE",
        help="Globally fail tests whose ScenarioResult.overall_score < SCORE/100.",
    )
    group.addoption(
        "--agentguard-save-db",
        action="store_true",
        default=False,
        help="Persist ScenarioResults from this session to the configured database.",
    )
    group.addoption(
        "--agentguard-report",
        choices=("html", "markdown", "json"),
        default=None,
        help="At session finish, write an aggregated report in the chosen format.",
    )
    group.addoption(
        "--agentguard-report-path",
        type=str,
        default=None,
        help="Override report output path (default: reports/pytest-<timestamp>.<ext>).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "agentguard: mark a test as an AgentGuard scenario (auto-applied by decorators).",
    )
    if config.getoption("--agentguard-skip-llm-judge"):
        os.environ["AGENTGUARD_SKIP_LLM_JUDGE"] = "1"


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    # Hook reserved for future use (e.g. auto-skip on missing OPENAI_API_KEY).
    return None


def pytest_assertrepr_compare(op: str, left: Any, right: Any) -> list[str] | None:
    """Render ScenarioResult comparisons with metric-level detail."""
    if not isinstance(left, ScenarioResult):
        return None
    lines = [
        f"ScenarioResult(id={left.scenario_id!r}, suite={left.suite!r})",
        f"  passed={left.passed}  overall_score={left.overall_score:.2f}",
    ]
    if left.failure_summary:
        lines.append(f"  failure_summary: {left.failure_summary[:200]}")
    failed = [ev for ev in left.evaluations if not ev.passed]
    if failed:
        lines.append("  failing evaluators:")
        for ev in failed:
            lines.append(f"    - {ev.metric_name}: score={ev.score:.2f}  reason={ev.reason[:160]}")
    return lines


def _collect_results(session: pytest.Session) -> list[ScenarioResult]:
    out: list[ScenarioResult] = []
    for item in session.items:
        for key, value in getattr(item, "user_properties", []):
            if key == "agentguard_result" and isinstance(value, ScenarioResult):
                out.append(value)
    return out


def _enforce_global_fail_under(session: pytest.Session) -> None:
    threshold = session.config.getoption("--agentguard-fail-under")
    if threshold is None:
        return
    bad: list[ScenarioResult] = []
    for r in _collect_results(session):
        if (r.overall_score * 100) < threshold:
            bad.append(r)
    if bad:
        names = ", ".join(r.scenario_id for r in bad)
        session.exitstatus = max(session.exitstatus, 1)
        terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminalreporter is not None:
            terminalreporter.section("AgentGuard global threshold", sep="=", red=True)
            terminalreporter.write_line(
                f"--agentguard-fail-under={threshold} failed on: {names}"
            )


def _write_report(session: pytest.Session) -> None:
    fmt = session.config.getoption("--agentguard-report")
    if not fmt:
        return
    results = _collect_results(session)
    if not results:
        return

    from datetime import datetime

    from agentguard.core.scoring import aggregate_results
    from agentguard.reporting.html_report import render_html
    from agentguard.reporting.markdown_report import render_markdown

    summary = aggregate_results(
        results,
        run_id=f"pytest_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}",
        agent_name="pytest-session",
        agent_version="dev",
        suite="pytest",
    )
    summary_dict = summary.model_dump(mode="json")
    results_dict = [r.model_dump(mode="json") for r in results]

    out_path_opt = session.config.getoption("--agentguard-report-path")
    ext = {"html": "html", "markdown": "md", "json": "json"}[fmt]
    out_path = (
        Path(out_path_opt)
        if out_path_opt
        else Path("reports") / f"{summary.run_id}.{ext}"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "html":
        out_path.write_text(render_html(summary_dict, results_dict), encoding="utf-8")
    elif fmt == "markdown":
        out_path.write_text(
            render_markdown(summary_dict, results_dict), encoding="utf-8"
        )
    else:
        out_path.write_text(
            json.dumps({"summary": summary_dict, "results": results_dict}, indent=2, default=str),
            encoding="utf-8",
        )

    terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if terminalreporter is not None:
        terminalreporter.write_line(f"\nAgentGuard pytest report written: {out_path}")


def _save_to_db(session: pytest.Session) -> None:
    if not session.config.getoption("--agentguard-save-db"):
        return
    results = _collect_results(session)
    if not results:
        return
    from datetime import datetime

    from agentguard.core.scoring import aggregate_results
    from agentguard.storage.persistence import save_run

    summary = aggregate_results(
        results,
        run_id=f"pytest_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}",
        agent_name="pytest-session",
        agent_version="dev",
        suite="pytest",
    )
    try:
        save_run(summary, results)
    except Exception as exc:
        terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminalreporter is not None:
            terminalreporter.write_line(
                f"AgentGuard --agentguard-save-db: persist failed ({exc})"
            )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    _enforce_global_fail_under(session)
    _save_to_db(session)
    _write_report(session)
