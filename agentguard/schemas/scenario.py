"""Scenario DSL Pydantic models - see docs/BLUEPRINT-1-CORE.md and BLUEPRINT-7."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AdapterType = Literal[
    "http",
    "langgraph",
    "langchain",
    "openai_agents",
    "crewai",
    # v0.2 additions
    "pydantic_ai",
    "mastra",
    "vercel_ai",
    "autogen",
    "dspy",
    "llamaindex",
    "smolagents",
]


class AgentConfig(BaseModel):
    adapter: AdapterType
    url: str | None = None
    method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    module: str | None = None
    object: str | None = None
    timeout_seconds: int = 60
    extra: dict[str, Any] = Field(default_factory=dict)


class ScenarioInput(BaseModel):
    user_message: str
    files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExpectedBehavior(BaseModel):
    must_call_tools: list[str] = Field(default_factory=list)
    must_not_call_tools: list[str] = Field(default_factory=list)
    must_retrieve: list[str] = Field(default_factory=list)
    must_not_reveal: list[str] = Field(default_factory=list)
    final_response_should: list[str] = Field(default_factory=list)
    answer_must_be_grounded: bool = False


class ThresholdConfig(BaseModel):
    min_overall_score: float | None = None
    min_security_score: float | None = None
    max_latency_ms: int | None = None
    max_cost_usd: float | None = None


class SecurityConfig(BaseModel):
    prompt_injection: bool = False
    pii_test: bool = False
    system_prompt_leakage: bool = False


class MockSpecYAML(BaseModel):
    """A single entry in a scenario's ``mocks:`` block (BLUEPRINT-7 section 4.3.1)."""

    name: str
    when: dict[str, Any] | None = None
    status: int = 200
    response: Any = None
    delay_ms: int = 0
    raises: str | None = None


class Scenario(BaseModel):
    id: str
    suite: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    agent: AgentConfig
    input: ScenarioInput
    expected: ExpectedBehavior = Field(default_factory=ExpectedBehavior)
    metrics: list[str]
    thresholds: ThresholdConfig | None = None
    security: SecurityConfig | None = None

    # v0.2 - programmable mocks
    mocks: list[MockSpecYAML] = Field(default_factory=list)
    mocks_module: str | None = None
