"""CrewAI adapter — supports kickoff / kickoff_async, captures task-level trace."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from agentguard.adapters.base import BaseAgentAdapter
from agentguard.core.errors import AdapterError
from agentguard.core.imports import import_object
from agentguard.schemas.adapter import AdapterMeta
from agentguard.schemas.result import AgentRunResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace, TraceStep


class CrewAIAdapter(BaseAgentAdapter):
    @property
    def meta(self) -> AdapterMeta:
        return AdapterMeta(
            name="crewai",
            description="Adapter for CrewAI crews and flows.",
            requires_module_import=True,
            supports_streaming=False,
            supports_async=True,
        )

    async def run(self, scenario: Scenario) -> AgentRunResult:
        if not scenario.agent.module or not scenario.agent.object:
            raise AdapterError(
                f"Scenario {scenario.id}: crewai adapter requires 'agent.module' and 'agent.object'"
            )
        try:
            crew = import_object(scenario.agent.module, scenario.agent.object)
        except Exception as e:
            raise AdapterError(f"Failed to import CrewAI crew: {e}") from e

        kickoff_method = scenario.agent.extra.get("kickoff_method", "kickoff")
        input_key = scenario.agent.extra.get("input_key", "input")
        inputs: dict[str, Any] = {input_key: scenario.input.user_message}

        start = time.time()
        try:
            method = getattr(crew, kickoff_method)
            if asyncio.iscoroutinefunction(method):
                output = await method(inputs=inputs)
            else:
                output = await asyncio.to_thread(method, inputs=inputs)
        except Exception as e:
            raise AdapterError(f"CrewAI execution error: {e}") from e
        elapsed_ms = int((time.time() - start) * 1000)

        trace = self._extract_trace(output, scenario.id, elapsed_ms)
        return AgentRunResult(
            final_output=self._extract_final_output(output),
            trace=trace,
            raw_output={"output_repr": str(output)[:2000]},
        )

    @staticmethod
    def _extract_trace(output: Any, scenario_id: str, elapsed_ms: int) -> AgentTrace:
        steps: list[TraceStep] = []

        usage = getattr(output, "token_usage", None)
        if usage is not None:
            steps.append(
                TraceStep(
                    type="llm_call",
                    name="crewai_aggregate",
                    metadata={
                        "total_tokens": getattr(usage, "total_tokens", 0),
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                    },
                )
            )

        for i, task_output in enumerate(getattr(output, "tasks_output", []) or []):
            steps.append(
                TraceStep(
                    type="tool_call",
                    name=getattr(task_output, "task_name", f"task_{i}"),
                    input=getattr(task_output, "input", None),
                    output=str(getattr(task_output, "raw", task_output))[:2000],
                    metadata={"agent": str(getattr(task_output, "agent", "unknown"))},
                )
            )

        return AgentTrace(
            scenario_id=scenario_id,
            steps=steps,
            final_output=str(getattr(output, "raw", output))[:4000],
            total_latency_ms=elapsed_ms,
        )

    @staticmethod
    def _extract_final_output(output: Any) -> str:
        if hasattr(output, "raw"):
            return str(output.raw)
        return str(output)

    async def health_check(self) -> bool:
        try:
            import crewai  # noqa: F401
            return True
        except ImportError:
            return False
