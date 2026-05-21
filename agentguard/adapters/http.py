"""HTTP/REST adapter — universal connector for any agent exposed as an API."""

from __future__ import annotations

import time
from typing import Any

import httpx

from agentguard.adapters.base import BaseAgentAdapter
from agentguard.core.errors import AdapterError, AdapterTimeoutError
from agentguard.schemas.adapter import AdapterMeta
from agentguard.schemas.result import AgentRunResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace, TraceStep


class HTTPAdapter(BaseAgentAdapter):
    @property
    def meta(self) -> AdapterMeta:
        return AdapterMeta(
            name="http",
            description="Universal HTTP/REST adapter for any agent exposed as an API endpoint.",
            requires_module_import=False,
            supports_streaming=False,
            supports_async=True,
        )

    async def run(self, scenario: Scenario) -> AgentRunResult:
        if not scenario.agent.url:
            raise AdapterError(f"Scenario {scenario.id}: HTTP adapter requires 'agent.url'")
        url = scenario.agent.url
        method = scenario.agent.method or "POST"
        headers = scenario.agent.headers.copy()
        timeout = scenario.agent.timeout_seconds

        payload: dict[str, Any] = {
            "input": scenario.input.user_message,
            "metadata": {
                "scenario_id": scenario.id,
                "agentguard": True,
                **scenario.input.metadata,
            },
        }
        if scenario.input.files:
            payload["files"] = scenario.input.files

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise AdapterTimeoutError(
                f"Agent at {url} did not respond within {timeout}s"
            ) from e
        except httpx.HTTPStatusError as e:
            raise AdapterError(
                f"Agent returned HTTP {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.HTTPError as e:
            raise AdapterError(f"HTTP adapter error: {e}") from e

        elapsed_ms = int((time.time() - start_time) * 1000)

        try:
            data = response.json()
        except ValueError:
            data = {"final_output": response.text}

        if not isinstance(data, dict):
            data = {"final_output": str(data)}

        trace = self._extract_trace(data, scenario.id, elapsed_ms)
        final_output = data.get("final_output") or data.get("output") or str(data)

        return AgentRunResult(
            final_output=str(final_output),
            trace=trace,
            raw_output=data,
        )

    @staticmethod
    def _extract_trace(data: dict, scenario_id: str, elapsed_ms: int) -> AgentTrace:
        trace_data = data.get("trace") or {}
        if not isinstance(trace_data, dict):
            trace_data = {}
        steps: list[TraceStep] = []
        for i, step in enumerate(trace_data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            steps.append(
                TraceStep(
                    step_id=step.get("step_id", f"step_{i}"),
                    type=step.get("type", "tool_call"),
                    name=step.get("name", step.get("tool", "unknown")),
                    input=step.get("input", step.get("args")),
                    output=step.get("output"),
                    metadata=step.get("metadata", {}),
                    latency_ms=step.get("latency_ms"),
                )
            )
        return AgentTrace(
            scenario_id=scenario_id,
            steps=steps,
            final_output=data.get("final_output") or data.get("output"),
            total_cost_usd=data.get("cost_usd"),
            total_latency_ms=data.get("latency_ms", elapsed_ms),
        )

    async def health_check(self) -> bool:
        return True
