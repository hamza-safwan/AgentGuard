"""Base agent adapter interface — every framework adapter implements this."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentguard.schemas.adapter import AdapterMeta
from agentguard.schemas.result import AgentRunResult
from agentguard.schemas.scenario import Scenario


class BaseAgentAdapter(ABC):
    """Abstract base for all agent adapters."""

    @property
    @abstractmethod
    def meta(self) -> AdapterMeta:
        """Return adapter metadata."""

    @abstractmethod
    async def run(self, scenario: Scenario) -> AgentRunResult:
        """Execute the agent with the scenario input and return normalized result."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the agent is reachable/importable."""
