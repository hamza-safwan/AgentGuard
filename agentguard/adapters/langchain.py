"""LangChain adapter — invokes any Runnable / LCEL chain with callback-based trace capture."""

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


class LangChainAdapter(BaseAgentAdapter):
    @property
    def meta(self) -> AdapterMeta:
        return AdapterMeta(
            name="langchain",
            description="Adapter for LangChain Runnables and LCEL chains.",
            requires_module_import=True,
            supports_streaming=True,
            supports_async=True,
        )

    async def run(self, scenario: Scenario) -> AgentRunResult:
        if not scenario.agent.module or not scenario.agent.object:
            raise AdapterError(
                f"Scenario {scenario.id}: langchain adapter requires 'agent.module' and 'agent.object'"
            )
        try:
            runnable = import_object(scenario.agent.module, scenario.agent.object)
        except Exception as e:
            raise AdapterError(f"Failed to import LangChain runnable: {e}") from e

        try:
            from langchain_core.callbacks import BaseCallbackHandler
        except ImportError as e:
            raise AdapterError(
                "langchain-core is required for the langchain adapter. "
                "Install with: pip install agentguard[langchain]"
            ) from e

        extra = scenario.agent.extra
        input_key = extra.get("input_key", "input")
        invoke_method = extra.get("invoke_method", "ainvoke")
        output_parser = extra.get("output_parser", "string")

        steps: list[TraceStep] = []

        class _TraceCallback(BaseCallbackHandler):
            def on_llm_end(self, response, **kwargs):
                steps.append(
                    TraceStep(
                        type="llm_call",
                        name=kwargs.get("name") or "llm",
                        output=str(response)[:2000],
                    )
                )

            def on_tool_end(self, output, name=None, **kwargs):
                steps.append(
                    TraceStep(
                        type="tool_call",
                        name=name or kwargs.get("name") or "tool",
                        output=str(output)[:2000],
                    )
                )

            def on_retriever_end(self, documents, **kwargs):
                docs: list[dict[str, Any]] = []
                for i, d in enumerate(documents or []):
                    docs.append(
                        {
                            "doc_id": getattr(d, "metadata", {}).get("id", str(i)),
                            "content": getattr(d, "page_content", str(d))[:1000],
                        }
                    )
                steps.append(
                    TraceStep(
                        type="retrieval",
                        name=kwargs.get("name") or "retriever",
                        output={"documents": docs},
                    )
                )

        callback = _TraceCallback()
        agent_input: Any = {input_key: scenario.input.user_message}

        start = time.time()
        try:
            if invoke_method == "ainvoke":
                output = await runnable.ainvoke(agent_input, config={"callbacks": [callback]})
            else:
                output = runnable.invoke(agent_input, config={"callbacks": [callback]})
        except Exception as e:
            raise AdapterError(f"LangChain execution error: {e}") from e
        elapsed_ms = int((time.time() - start) * 1000)

        final_output = self._parse_output(output, output_parser)
        trace = AgentTrace(
            scenario_id=scenario.id,
            steps=steps,
            final_output=final_output,
            total_latency_ms=elapsed_ms,
        )
        return AgentRunResult(
            final_output=final_output,
            trace=trace,
            raw_output={"output_repr": str(output)[:2000]},
        )

    @staticmethod
    def _parse_output(output: Any, parser_type: str) -> str:
        if parser_type == "string":
            return str(output)
        if parser_type == "dict" and isinstance(output, dict):
            return str(output.get("output", output.get("answer", output)))
        if parser_type == "messages" and hasattr(output, "content"):
            return str(output.content)
        return str(output)

    async def health_check(self) -> bool:
        try:
            import langchain_core  # noqa: F401
            return True
        except ImportError:
            return False
