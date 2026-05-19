"""Trace model - normalized agent execution record."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TraceStepType = Literal[
    "llm_call",
    "tool_call",
    "retrieval",
    "guardrail",
    "handoff",
    "error",
    "final_output",
]

TraceStepSource = Literal["adapter", "sdk", "ingest"]
TraceRuntime = Literal["python", "js", "unknown"]


class TraceStep(BaseModel):
    """One step in an AgentTrace.

    v0.2 additions (all optional, additive): ``parent_step_id`` for nesting,
    ``source`` to distinguish adapter-captured vs SDK-captured vs ingested,
    ``redactions`` listing field paths that were scrubbed prior to serialization,
    ``cost_usd`` per-step cost, ``tokens`` for LLM-call accounting.
    """

    model_config = ConfigDict(extra="ignore")

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TraceStepType
    name: str
    # ``input`` and ``output`` accept any JSON-able shape (dict, list, scalar,
    # or pre-stringified payload). Adapters and the SDK serialize / truncate
    # before construction; we don't want Pydantic to re-validate the shape.
    input: Any = None
    output: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    latency_ms: int | None = None

    # v0.2 additions
    parent_step_id: str | None = None
    source: TraceStepSource = "adapter"
    redactions: list[str] = Field(default_factory=list)
    cost_usd: float | None = None
    tokens: dict[str, int] | None = None


class AgentTrace(BaseModel):
    """Normalized record of a single agent run.

    v0.2 additions (additive): ``schema_version`` sanity field, ``runtime``
    ("python" / "js" / "unknown"), and ``sampling`` metadata set by the
    observability SDK when a trace was head- or tail-sampled.
    """

    model_config = ConfigDict(extra="ignore")

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    agent_name: str | None = None
    agent_version: str | None = None
    steps: list[TraceStep] = Field(default_factory=list)
    final_output: str | None = None
    total_cost_usd: float | None = None
    total_latency_ms: int | None = None

    # v0.2 additions
    schema_version: str = "1.0"
    runtime: TraceRuntime = "unknown"
    sampling: dict[str, Any] | None = None

    def tool_names(self) -> list[str]:
        return [step.name for step in self.steps if step.type == "tool_call"]

    def tool_calls(self) -> list[TraceStep]:
        return [step for step in self.steps if step.type == "tool_call"]

    def retrieval_steps(self) -> list[TraceStep]:
        return [step for step in self.steps if step.type == "retrieval"]

    def retrieved_doc_ids(self) -> list[str]:
        docs: list[str] = []
        for step in self.steps:
            if step.type == "retrieval" and isinstance(step.output, dict):
                for doc in step.output.get("documents", []):
                    if isinstance(doc, dict) and "doc_id" in doc:
                        docs.append(doc["doc_id"])
        return docs

    def llm_calls(self) -> list[TraceStep]:
        return [step for step in self.steps if step.type == "llm_call"]

    def errors(self) -> list[TraceStep]:
        return [step for step in self.steps if step.type == "error"]

    def guardrail_events(self) -> list[TraceStep]:
        return [step for step in self.steps if step.type == "guardrail"]
