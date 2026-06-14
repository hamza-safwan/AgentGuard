"""AgentGuard PR-comment bot (BLUEPRINT-7 section 7.7).

Reads a saved AgentGuard run JSON, formats a Markdown summary, and upserts a
single PR comment on the pull request that triggered the workflow. Idempotent:
the comment is identified by an HTML marker ``<!-- {tag} -->`` so re-runs of
the same workflow update the existing comment instead of duplicating it.

Designed to be a fully self-contained script (stdlib + ``requests``) so it
works against any AgentGuard run JSON, regardless of the AgentGuard version
that produced it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

GITHUB_API = "https://api.github.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_run_json(value: str) -> dict:
    if value == "latest":
        runs_dir = Path(".agentguard/runs")
        if not runs_dir.exists():
            raise SystemExit("INPUT_RUN_JSON=latest but .agentguard/runs/ is missing.")
        files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            raise SystemExit("No saved runs found in .agentguard/runs/.")
        path = files[0]
    else:
        path = Path(value)
    if not path.exists():
        raise SystemExit(f"Run JSON not found at {path}.")
    return json.loads(path.read_text(encoding="utf-8"))


def _detect_pr_number() -> int | None:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return None
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    if "pull_request" in event:
        return int(event["pull_request"]["number"])
    if event.get("issue", {}).get("pull_request"):
        return int(event["issue"]["number"])
    return None


def _band_label(rec: str) -> str:
    return {
        "deploy_with_monitoring": "DEPLOY (with monitoring)",
        "deploy_carefully": "DEPLOY CAREFULLY",
        "fix_before_production": "FIX BEFORE PRODUCTION",
        "do_not_deploy": "DO NOT DEPLOY",
    }.get(rec, rec.upper())


def _emoji(rec: str) -> str:
    return {
        "deploy_with_monitoring": "OK",
        "deploy_carefully": "WARN",
        "fix_before_production": "WARN",
        "do_not_deploy": "BLOCK",
    }.get(rec, "?")


def _trace_link(scenario_id: str, results: list[dict], viewer_base: str) -> str:
    if not viewer_base:
        return ""
    for r in results:
        if r.get("scenario_id") == scenario_id:
            trace = r.get("trace") or {}
            tid = trace.get("trace_id") if isinstance(trace, dict) else None
            if tid:
                base = viewer_base.rstrip("/")
                return f" [trace]({base}/traces/{tid})"
    return ""


def format_body(run: dict, viewer_base: str = "", artifact_url: str = "") -> str:
    summary = run.get("summary") or {}
    results = run.get("results") or []

    overall = summary.get("overall_score", 0)
    security = summary.get("security_score", 0)
    rag = summary.get("rag_score", 0)
    tool = summary.get("tool_score", 0)
    rec = summary.get("deployment_recommendation", "do_not_deploy")
    suite = summary.get("suite", "default")
    version = summary.get("agent_version", "?")
    run_id = summary.get("run_id", "?")
    passed = summary.get("passed_scenarios", 0)
    total = summary.get("total_scenarios", 0)

    lines: list[str] = []
    lines.append(
        f"## AgentGuard CI - `{suite}` ({version})\n"
    )
    lines.append(
        f"**Deployment: {_emoji(rec)} {_band_label(rec)}** "
        f"&nbsp;&middot;&nbsp; overall **{overall:.0f}/100** "
        f"&nbsp;&middot;&nbsp; security **{security:.0f}/100**"
    )
    lines.append("")

    lines.append("| Metric | Score |")
    lines.append("|--------|------:|")
    lines.append(f"| Overall | {overall:.0f} |")
    lines.append(f"| Security | {security:.0f} |")
    lines.append(f"| RAG grounding | {rag:.0f} |")
    lines.append(f"| Tool correctness | {tool:.0f} |")
    lines.append(f"| Pass rate | {passed}/{total} |")
    lines.append("")

    failed_results = [r for r in results if not r.get("passed")]
    if failed_results:
        lines.append("### Failing scenarios")
        for r in failed_results[:10]:
            sid = r.get("scenario_id", "?")
            failure = (r.get("failure_summary") or "").replace("\n", " ").strip()
            link = _trace_link(sid, results, viewer_base)
            failure_text = failure[:160] + ("..." if len(failure) > 160 else "")
            lines.append(f"- `{sid}` - {failure_text}{link}")
        if len(failed_results) > 10:
            lines.append(f"- ...and {len(failed_results) - 10} more")
        lines.append("")
    else:
        lines.append("All scenarios passed.")
        lines.append("")

    extras: list[str] = []
    if artifact_url:
        extras.append(f"[Full HTML report]({artifact_url})")
    if viewer_base:
        extras.append(f"[Open dashboard]({viewer_base.rstrip('/')}/runs/{run_id})")
    if extras:
        lines.append(" &middot; ".join(extras))
        lines.append("")

    lines.append(
        "<sub>Generated by "
        "[AgentGuard CI](https://github.com/agentguard/agentguard-ci) "
        f"&middot; run `{run_id}`</sub>"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _find_existing_comment(
    repo: str, pr_number: int, token: str, tag: str
) -> dict | None:
    url = f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
    page = 1
    found = None
    while True:
        resp = requests.get(
            url, headers=_headers(token), params={"per_page": 100, "page": page}, timeout=10
        )
        if not resp.ok:
            return None
        comments = resp.json()
        if not comments:
            break
        for c in comments:
            if c.get("body", "").lstrip().startswith(f"<!-- {tag} -->"):
                if found is None:
                    found = c
                else:
                    # Clean up duplicates from any prior buggy run
                    requests.delete(
                        f"{GITHUB_API}/repos/{repo}/issues/comments/{c['id']}",
                        headers=_headers(token),
                        timeout=10,
                    )
        if len(comments) < 100:
            break
        page += 1
    return found


def upsert_comment(repo: str, pr_number: int, token: str, tag: str, body: str) -> bool:
    body_with_tag = f"<!-- {tag} -->\n{body}"
    existing = _find_existing_comment(repo, pr_number, token, tag)
    if existing:
        url = f"{GITHUB_API}/repos/{repo}/issues/comments/{existing['id']}"
        resp = requests.patch(url, headers=_headers(token), json={"body": body_with_tag}, timeout=10)
    else:
        url = f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
        resp = requests.post(url, headers=_headers(token), json={"body": body_with_tag}, timeout=10)
    if not resp.ok:
        print(f"PR comment upsert failed: {resp.status_code} {resp.text}", file=sys.stderr)
    return resp.ok


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN / GITHUB_REPOSITORY missing; skipping comment.", file=sys.stderr)
        return 0

    pr_number = _detect_pr_number()
    if pr_number is None:
        print("No pull-request context detected; skipping comment.")
        return 0

    run = _resolve_run_json(os.environ.get("INPUT_RUN_JSON", "latest"))
    body = format_body(
        run,
        viewer_base=os.environ.get("INPUT_TRACE_VIEWER_BASE_URL", ""),
        artifact_url=os.environ.get("INPUT_ARTIFACT_URL", ""),
    )
    upsert_comment(
        repo=repo,
        pr_number=pr_number,
        token=token,
        tag=os.environ.get("INPUT_TAG", "agentguard-ci-report"),
        body=body,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
