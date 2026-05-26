"""OpenAI Agents SDK adapter."""

from __future__ import annotations

import time
from typing import Any

from agentguard.adapters.base import BaseAgentAdapter
from agentguard.core.errors import AdapterError
from agentguard.core.imports import import_object
from agentguard.schemas.adapter import AdapterMeta
from agentguard.schemas.result import AgentRunResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace, TraceStep


class OpenAIAgentsAdapter(BaseAgentAdapter):
    @property
    def meta(self) -> AdapterMeta:
        return AdapterMeta(
            name="openai_agents",
            description="Adapter for the OpenAI Agents SDK with built-in tracing support.",
            requires_module_import=True,
            supports_streaming=True,
            supports_async=True,
        )

    async def run(self, scenario: Scenario) -> AgentRunResult:
        if not scenario.agent.module or not scenario.agent.object:
            raise AdapterError(
                f"Scenario {scenario.id}: openai_agents adapter requires 'agent.module' and 'agent.object'"
            )
        try:
            agent = import_object(scenario.agent.module, scenario.agent.object)
        except Exception as e:
            raise AdapterError(f"Failed to import OpenAI agent: {e}") from e

        try:
            from agents import Runner
        except ImportError as e:
            raise AdapterError(
                "openai-agents is required. Install with: pip install agentguard[openai-agents]"
            ) from e

        max_turns = scenario.agent.extra.get("max_turns", 10)
        start = time.time()
        try:
            result = await Runner.run(agent, scenario.input.user_message, max_turns=max_turns)
        except Exception as e:
            raise AdapterError(f"OpenAI Agents SDK execution error: {e}") from e
        elapsed_ms = int((time.time() - start) * 1000)

        trace = self._extract_trace(result, scenario.id, elapsed_ms)
        final_output = str(getattr(result, "final_output", "")) or str(result)

        raw: dict[str, Any] = {}
        if hasattr(result, "to_dict"):
            try:
                raw = result.to_dict()
            except Exception:
                raw = {}

        return AgentRunResult(final_output=final_output, trace=trace, raw_output=raw)

    @staticmethod
    def _extract_trace(result: Any, scenario_id: str, elapsed_ms: int) -> AgentTrace:
        steps: list[TraceStep] = []

        for response in getattr(result, "raw_responses", []) or []:
            usage = getattr(response, "usage", None)
            steps.append(
                TraceStep(
                    type="llm_call",
                    name=getattr(response, "model", "openai"),
                    input=getattr(response, "input", None),
                    output=str(getattr(response, "output", ""))[:2000],
                    metadata={
                        "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
                        "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
                    },
                )
            )

        for item in getattr(result, "new_items", []) or []:
            cls_name = type(item).__name__
            if "ToolCall" in cls_name:
                steps.append(
                    TraceStep(
                        type="tool_call",
                        name=getattr(item, "name", getattr(item, "tool_name", "tool")),
                        input=getattr(item, "arguments", None),
                        output=getattr(item, "output", None),
                    )
                )
            elif "Handoff" in cls_name:
                steps.append(
                    TraceStep(
                        type="handoff",
                        name=str(getattr(item, "target_agent", "unknown")),
                        metadata={"source": str(getattr(item, "source_agent", "unknown"))},
                    )
                )
            elif "Guardrail" in cls_name:
                steps.append(
                    TraceStep(
                        type="guardrail",
                        name=getattr(item, "guardrail_name", "guardrail"),
                        output={"triggered": bool(getattr(item, "triggered", False))},
                    )
                )

        return AgentTrace(
            scenario_id=scenario_id,
            steps=steps,
            final_output=str(getattr(result, "final_output", "")) or None,
            total_latency_ms=elapsed_ms,
        )

    async def health_check(self) -> bool:
        try:
            import agents  # noqa: F401
            return True
        except ImportError:
            return False
