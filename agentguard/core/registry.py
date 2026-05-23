"""Adapter and evaluator registries.

Built-in adapters and evaluators are looked up first; if no built-in matches,
the registry consults third-party plugins discovered via Python entry points
(BLUEPRINT-7 section 3.3):

* ``agentguard.adapters`` - register a ``BaseAgentAdapter`` subclass.
* ``agentguard.evaluators`` - register a ``BaseEvaluator`` subclass.
* ``agentguard.mock_tools`` - register a ``MockCatalog`` instance.

A failing entry point never crashes the runner; it is logged and skipped.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentguard.adapters.base import BaseAgentAdapter
    from agentguard.evaluators.base import BaseEvaluator

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


_BUILTIN_ADAPTERS = {
    "http",
    "langgraph",
    "langchain",
    "openai_agents",
    "crewai",
    "pydantic_ai",
    "mastra",
    "vercel_ai",
    "autogen",
    "dspy",
    "llamaindex",
    "smolagents",
}


@lru_cache(maxsize=1)
def _discovered_adapters() -> dict[str, type]:
    out: dict[str, type] = {}
    try:
        eps = entry_points(group="agentguard.adapters")
    except Exception as exc:
        _log.warning("entry_points() failed for agentguard.adapters: %s", exc)
        return out
    for ep in eps:
        try:
            out[ep.name] = ep.load()
        except Exception as exc:
            _log.warning("failed to load adapter plugin %s: %s", ep.name, exc)
    return out


def get_adapter(adapter_type: str) -> BaseAgentAdapter:
    """Instantiate an adapter by name. Imports lazily so optional extras stay optional."""
    if adapter_type == "http":
        from agentguard.adapters.http import HTTPAdapter
        return HTTPAdapter()
    if adapter_type == "langgraph":
        from agentguard.adapters.langgraph import LangGraphAdapter
        return LangGraphAdapter()
    if adapter_type == "langchain":
        from agentguard.adapters.langchain import LangChainAdapter
        return LangChainAdapter()
    if adapter_type == "openai_agents":
        from agentguard.adapters.openai_agents import OpenAIAgentsAdapter
        return OpenAIAgentsAdapter()
    if adapter_type == "crewai":
        from agentguard.adapters.crewai import CrewAIAdapter
        return CrewAIAdapter()
    if adapter_type == "pydantic_ai":
        from agentguard.adapters.pydantic_ai import PydanticAIAdapter
        return PydanticAIAdapter()
    if adapter_type == "mastra":
        from agentguard.adapters.mastra import MastraAdapter
        return MastraAdapter()
    if adapter_type == "vercel_ai":
        from agentguard.adapters.vercel_ai import VercelAIAdapter
        return VercelAIAdapter()
    if adapter_type == "autogen":
        from agentguard.adapters.autogen import AutoGenAdapter
        return AutoGenAdapter()
    if adapter_type == "dspy":
        from agentguard.adapters.dspy import DSPyAdapter
        return DSPyAdapter()
    if adapter_type == "llamaindex":
        from agentguard.adapters.llamaindex import LlamaIndexAdapter
        return LlamaIndexAdapter()
    if adapter_type == "smolagents":
        from agentguard.adapters.smolagents import SmolagentsAdapter
        return SmolagentsAdapter()

    plugins = _discovered_adapters()
    if adapter_type in plugins:
        return plugins[adapter_type]()

    available = sorted(_BUILTIN_ADAPTERS | set(plugins.keys()))
    raise ValueError(
        f"Unknown adapter: {adapter_type}. Available: {', '.join(available)}"
    )


def list_adapters() -> list[str]:
    return sorted(_BUILTIN_ADAPTERS | set(_discovered_adapters().keys()))


# ---------------------------------------------------------------------------
# Evaluators
# ---------------------------------------------------------------------------


_BUILTIN_EVALUATOR_NAMES = [
    "task_success",
    "tool_call_correctness",
    "required_tool_calls",
    "forbidden_tool_avoidance",
    "rag_grounding",
    "pii_leakage",
    "prompt_injection",
    "cost",
    "latency",
    "response_quality",
    "policy_compliance",
    "access_control_compliance",
    "schema_validation",
]


@lru_cache(maxsize=1)
def _discovered_evaluators() -> dict[str, type]:
    out: dict[str, type] = {}
    try:
        eps = entry_points(group="agentguard.evaluators")
    except Exception as exc:
        _log.warning("entry_points() failed for agentguard.evaluators: %s", exc)
        return out
    for ep in eps:
        try:
            out[ep.name] = ep.load()
        except Exception as exc:
            _log.warning("failed to load evaluator plugin %s: %s", ep.name, exc)
    return out


def get_evaluator(metric_name: str) -> BaseEvaluator:
    from agentguard.evaluators import (
        AccessControlEvaluator,
        CostEvaluator,
        ForbiddenToolEvaluator,
        LatencyEvaluator,
        LLMJudgeEvaluator,
        PIILeakageEvaluator,
        PromptInjectionEvaluator,
        RAGGroundingEvaluator,
        RequiredToolEvaluator,
        SchemaValidationEvaluator,
    )

    table: dict[str, type] = {
        "task_success": LLMJudgeEvaluator,
        "tool_call_correctness": RequiredToolEvaluator,
        "required_tool_calls": RequiredToolEvaluator,
        "forbidden_tool_avoidance": ForbiddenToolEvaluator,
        "rag_grounding": RAGGroundingEvaluator,
        "pii_leakage": PIILeakageEvaluator,
        "prompt_injection": PromptInjectionEvaluator,
        "cost": CostEvaluator,
        "latency": LatencyEvaluator,
        "response_quality": LLMJudgeEvaluator,
        "policy_compliance": LLMJudgeEvaluator,
        "access_control_compliance": AccessControlEvaluator,
        "schema_validation": SchemaValidationEvaluator,
    }

    if metric_name in table:
        cls = table[metric_name]
        if cls is LLMJudgeEvaluator:
            return cls(metric_name=metric_name)  # type: ignore[call-arg]
        return cls()

    plugins = _discovered_evaluators()
    if metric_name in plugins:
        return plugins[metric_name]()

    available = sorted(set(_BUILTIN_EVALUATOR_NAMES) | set(plugins.keys()))
    raise ValueError(
        f"Unknown evaluator metric: {metric_name}. Available: {', '.join(available)}"
    )


def list_evaluators() -> list[str]:
    return list(_BUILTIN_EVALUATOR_NAMES)


def list_all_evaluators() -> list[tuple[str, str]]:
    """Return ``[(name, source)]`` for every evaluator, built-in or plugin."""
    out: list[tuple[str, str]] = [(n, "built-in") for n in _BUILTIN_EVALUATOR_NAMES]
    for name in _discovered_evaluators():
        out.append((name, "plugin"))
    return out


# ---------------------------------------------------------------------------
# Mock-tool catalogs (used by the programmable mock server, BLUEPRINT-7 section 4)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _discovered_mock_catalogs() -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        eps = entry_points(group="agentguard.mock_tools")
    except Exception as exc:
        _log.warning("entry_points() failed for agentguard.mock_tools: %s", exc)
        return out
    for ep in eps:
        try:
            out[ep.name] = ep.load()
        except Exception as exc:
            _log.warning("failed to load mock-tool plugin %s: %s", ep.name, exc)
    return out


def list_mock_catalogs() -> list[str]:
    return sorted(_discovered_mock_catalogs().keys())


def get_mock_catalog(name: str) -> Any:
    catalogs = _discovered_mock_catalogs()
    if name not in catalogs:
        raise ValueError(
            f"Unknown mock catalog: {name}. "
            f"Available: {', '.join(sorted(catalogs.keys())) or '(none registered)'}"
        )
    return catalogs[name]
