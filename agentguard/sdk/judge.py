"""One-shot LLM judge (BLUEPRINT-7 section 6.5.3).

Wraps :func:`agentguard.evaluators.llm_judge.call_llm_judge` with a sane
default prompt template, JSON parsing, and (by default) a file-backed cache.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from agentguard.evaluators.llm_judge import _parse_judge_json, call_llm_judge
from agentguard.sdk.caching import judge_cache

DEFAULT_JUDGE_PROMPT = """You are evaluating an AI response.

Criteria: {criteria}

Response:
{response}

Score 0.0 (fully fails the criteria) to 1.0 (fully meets it).
Return ONLY valid JSON:
{{"score": <float>, "reason": "<brief>"}}"""


def _llm_disabled() -> bool:
    if os.getenv("AGENTGUARD_SKIP_LLM_JUDGE", "").lower() in {"1", "true", "yes"}:
        return True
    return not os.getenv("OPENAI_API_KEY")


def judge(
    response: str,
    *,
    criteria: str,
    prompt_template: str | None = None,
    model: str | None = None,
    cache: bool = True,
    pass_threshold: float = 0.7,
) -> dict[str, Any]:
    """Score an arbitrary response against a free-text criterion.

    Returns ``{"score": float, "reason": str, "passed": bool, "model": str,
    "cached": bool, "skipped": bool}``. If no API key is configured (or
    ``AGENTGUARD_SKIP_LLM_JUDGE=1``), returns ``{"skipped": True, "score": 1.0,
    "passed": True, "reason": "LLM judge skipped"}`` so callers in CI never
    fail just because no LLM is available.
    """
    if _llm_disabled():
        return {
            "score": 1.0,
            "passed": True,
            "reason": "LLM judge skipped (no API key or AGENTGUARD_SKIP_LLM_JUDGE set).",
            "model": model or os.getenv("AGENTGUARD_JUDGE_MODEL", "gpt-4.1-mini"),
            "cached": False,
            "skipped": True,
        }

    template = prompt_template or DEFAULT_JUDGE_PROMPT
    prompt = template.format(criteria=criteria, response=response)

    if cache:
        cached = judge_cache.get(prompt)
        if cached is not None:
            return {**cached, "cached": True, "skipped": False}

    raw = asyncio.run(call_llm_judge(prompt))
    parsed = _parse_judge_json(raw)
    score = max(0.0, min(1.0, float(parsed.get("score", 0.5))))
    out: dict[str, Any] = {
        "score": score,
        "passed": score >= pass_threshold,
        "reason": parsed.get("reason", "(no reason returned by judge)"),
        "model": model or os.getenv("AGENTGUARD_JUDGE_MODEL", "gpt-4.1-mini"),
        "cached": False,
        "skipped": False,
    }
    if cache:
        judge_cache.set(prompt, {k: v for k, v in out.items() if k != "cached"})
    return out
