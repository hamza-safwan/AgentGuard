"""Evaluator metadata model."""

from __future__ import annotations

from pydantic import BaseModel


class EvaluatorMeta(BaseModel):
    """Metadata advertised by an evaluator class.

    v0.2 adds ``default_weight`` so third-party evaluators can suggest a scoring
    weight (used by ``score_scenario`` when the metric isn't in DEFAULT_WEIGHTS).
    """

    name: str
    description: str
    category: str  # "rule_based", "llm_judge", "rag", "security", "performance", "custom"
    deterministic: bool
    requires_llm: bool = False
    default_weight: float = 0.10
