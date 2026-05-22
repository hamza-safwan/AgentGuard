"""Schema-validation evaluator — checks final output against an expected JSON schema."""

from __future__ import annotations

import json
from typing import Any

from agentguard.evaluators.base import BaseEvaluator
from agentguard.schemas.evaluator import EvaluatorMeta
from agentguard.schemas.result import AgentRunResult, EvaluationResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace


def _matches_shape(value: Any, shape: Any) -> tuple[bool, str]:
    """Lightweight schema check: shape values describe the expected types/keys."""
    if isinstance(shape, dict):
        if not isinstance(value, dict):
            return False, f"Expected dict, got {type(value).__name__}"
        for key, sub in shape.items():
            if key not in value:
                return False, f"Missing key: {key}"
            ok, reason = _matches_shape(value[key], sub)
            if not ok:
                return False, f"At '{key}': {reason}"
        return True, "ok"
    if isinstance(shape, list):
        if not isinstance(value, list):
            return False, f"Expected list, got {type(value).__name__}"
        if shape and value:
            ok, reason = _matches_shape(value[0], shape[0])
            if not ok:
                return False, f"In list element: {reason}"
        return True, "ok"
    if isinstance(shape, str):
        type_map = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": (int, float),
            "number": (int, float),
            "bool": bool,
            "any": object,
        }
        expected = type_map.get(shape.lower())
        if expected and not isinstance(value, expected):
            return False, f"Expected {shape}, got {type(value).__name__}"
        return True, "ok"
    return True, "ok"


class SchemaValidationEvaluator(BaseEvaluator):
    @property
    def meta(self) -> EvaluatorMeta:
        return EvaluatorMeta(
            name="schema_validation",
            description="Validates final output against an expected JSON shape.",
            category="rule_based",
            deterministic=True,
        )

    async def evaluate(
        self,
        scenario: Scenario,
        run_result: AgentRunResult,
        trace: AgentTrace,
    ) -> EvaluationResult:
        shape = scenario.input.metadata.get("expected_schema")
        if not shape:
            return EvaluationResult(
                metric_name="schema_validation",
                score=1.0,
                passed=True,
                reason="No expected_schema specified in scenario.input.metadata.",
            )
        try:
            parsed = json.loads(run_result.final_output)
        except (ValueError, TypeError):
            return EvaluationResult(
                metric_name="schema_validation",
                score=0.0,
                passed=False,
                reason="Final output is not valid JSON.",
                evidence=[{"final_output": run_result.final_output[:200]}],
            )
        ok, reason = _matches_shape(parsed, shape)
        return EvaluationResult(
            metric_name="schema_validation",
            score=1.0 if ok else 0.0,
            passed=ok,
            reason=reason,
            evidence=[{"expected_schema": shape}],
        )
