"""LangGraph adapter — runs compiled graphs and captures stream events as TraceSteps.

LangGraph is the hero adapter for AgentGuard. The blueprint specifies stream
events (``astream_events`` v2) as the primary capture mechanism, with a separate
``ainvoke`` to obtain the final state. We do both, in that order, so step capture
is rich and the final output reflects the full graph state.
"""

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


class LangGraphAdapter(BaseAgentAdapter):
    @property
    def meta(self) -> AdapterMeta:
        return AdapterMeta(
            name="langgraph",
            description="Adapter for LangGraph compiled graphs with state management.",
            requires_module_import=True,
            supports_streaming=True,
            supports_async=True,
        )

    async def run(self, scenario: Scenario) -> AgentRunResult:
        if not scenario.agent.module or not scenario.agent.object:
            raise AdapterError(
                f"Scenario {scenario.id}: langgraph adapter requires 'agent.module' and 'agent.object'"
            )
        try:
            graph = import_object(scenario.agent.module, scenario.agent.object)
        except Exception as e:
            raise AdapterError(f"Failed to import LangGraph graph: {e}") from e

        try:
            from langchain_core.messages import HumanMessage
        except ImportError as e:
            raise AdapterError(
                "langchain-core is required for the langgraph adapter. "
                "Install with: pip install agentguard[langgraph]"
            ) from e

        extra = scenario.agent.extra
        input_key = extra.get("input_key", "messages")
        output_key = extra.get("output_key", "messages")
        thread_id = extra.get("thread_id", f"agentguard-{scenario.id}")

        agent_input = {input_key: [HumanMessage(content=scenario.input.user_message)]}
        config = {"configurable": {"thread_id": thread_id}}

        steps: list[TraceStep] = []
        start_time = time.time()
        try:
            async for event in graph.astream_events(agent_input, config=config, version="v2"):
                step = self._event_to_step(event)
                if step:
                    steps.append(step)
            final_state = await graph.ainvoke(agent_input, config=config)
        except Exception as e:
            raise AdapterError(f"LangGraph execution error: {e}") from e

        elapsed_ms = int((time.time() - start_time) * 1000)
        final_output = self._extract_final_output(final_state, output_key)

        trace = AgentTrace(
            scenario_id=scenario.id,
            agent_name=getattr(graph, "name", None),
            steps=steps,
            final_output=final_output,
            total_latency_ms=elapsed_ms,
        )

        return AgentRunResult(
            final_output=final_output,
            trace=trace,
            raw_output={"state_repr": str(final_state)[:2000]},
        )

    @staticmethod
    def _event_to_step(event: dict[str, Any]) -> TraceStep | None:
        kind = event.get("event", "")
        data = event.get("data", {}) or {}
        name = event.get("name", kind)

        if kind == "on_chat_model_end":
            return TraceStep(
                type="llm_call",
                name=name,
                input=str(data.get("input"))[:1000] if data.get("input") is not None else None,
                output=str(data.get("output"))[:2000] if data.get("output") is not None else None,
                metadata=event.get("metadata", {}),
            )
        if kind == "on_tool_end":
            return TraceStep(
                type="tool_call",
                name=name,
                input=data.get("input"),
                output=str(data.get("output"))[:2000] if data.get("output") is not None else None,
                metadata=event.get("metadata", {}),
            )
        if kind == "on_retriever_end":
            output = data.get("output", [])
            documents: list[dict[str, Any]] = []
            try:
                for doc in output or []:
                    documents.append(
                        {
                            "doc_id": getattr(doc, "metadata", {}).get("id", "?"),
                            "content": getattr(doc, "page_content", str(doc))[:1000],
                            "score": getattr(doc, "metadata", {}).get("score"),
                        }
                    )
            except TypeError:
                pass
            return TraceStep(
                type="retrieval",
                name=name,
                input=data.get("input"),
                output={"documents": documents},
                metadata=event.get("metadata", {}),
            )
        return None

    @staticmethod
    def _extract_final_output(state: Any, output_key: str) -> str:
        if isinstance(state, dict):
            messages = state.get(output_key, [])
            if messages:
                last = messages[-1]
                if hasattr(last, "content"):
                    return str(last.content)
                return str(last)
        return str(state)

    async def health_check(self) -> bool:
        try:
            import langgraph  # noqa: F401
            return True
        except ImportError:
            return False
