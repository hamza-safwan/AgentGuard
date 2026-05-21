"""Base evaluator interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentguard.schemas.evaluator import EvaluatorMeta
from agentguard.schemas.result import AgentRunResult, EvaluationResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace


class BaseEvaluator(ABC):
    @property
    @abstractmethod
    def meta(self) -> EvaluatorMeta:
        ...

    @abstractmethod
    async def evaluate(
        self,
        scenario: Scenario,
        run_result: AgentRunResult,
        trace: AgentTrace,
    ) -> EvaluationResult:
        ...
