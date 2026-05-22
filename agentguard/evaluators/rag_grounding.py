"""RAG grounding evaluator: retrieval coverage + answer faithfulness."""

from __future__ import annotations

from agentguard.evaluators.base import BaseEvaluator
from agentguard.evaluators.llm_judge import _llm_disabled, _parse_judge_json, call_llm_judge
from agentguard.schemas.evaluator import EvaluatorMeta
from agentguard.schemas.result import AgentRunResult, EvaluationResult
from agentguard.schemas.scenario import Scenario
from agentguard.schemas.trace import AgentTrace

FAITHFULNESS_PROMPT = """You judge whether an agent's response is grounded in the retrieved documents.

Retrieved documents:
{retrieved_content}

Agent response:
{response}

Score 0.0 to 1.0 how well the response is grounded in (supported by) the documents.

Return ONLY valid JSON:
{{
  "score": <float 0.0 to 1.0>,
  "reason": "<brief explanation>"
}}"""


class RAGGroundingEvaluator(BaseEvaluator):
    @property
    def meta(self) -> EvaluatorMeta:
        return EvaluatorMeta(
            name="rag_grounding",
            description="Combines retrieval coverage and answer-grounding faithfulness.",
            category="rag",
            deterministic=False,
            requires_llm=True,
        )

    async def evaluate(
        self,
        scenario: Scenario,
        run_result: AgentRunResult,
        trace: AgentTrace,
    ) -> EvaluationResult:
        # Component 1: retrieval coverage
        required_docs = scenario.expected.must_retrieve
        retrieved_docs = trace.retrieved_doc_ids()
        if required_docs:
            missing = [d for d in required_docs if d not in retrieved_docs]
            retrieval_score = max(0.0, 1.0 - len(missing) / len(required_docs))
        else:
            missing = []
            retrieval_score = 1.0

        # Component 2: answer faithfulness (LLM judge)
        if not scenario.expected.answer_must_be_grounded:
            faithfulness_score = 1.0
            faith_reason = "Faithfulness check not requested."
        else:
            retrieved_content = []
            for step in trace.retrieval_steps():
                if isinstance(step.output, dict):
                    for doc in step.output.get("documents", []):
                        if isinstance(doc, dict):
                            retrieved_content.append(
                                f"[{doc.get('doc_id', '?')}] {doc.get('content', '')}"
                            )
            joined = "\n\n".join(retrieved_content) or "(no documents retrieved)"
            if _llm_disabled():
                faithfulness_score = 1.0
                faith_reason = "Faithfulness LLM judge skipped (no API key)."
            else:
                prompt = FAITHFULNESS_PROMPT.format(
                    retrieved_content=joined[:4000],
                    response=run_result.final_output,
                )
                try:
                    text = await call_llm_judge(prompt)
                    parsed = _parse_judge_json(text)
                    faithfulness_score = max(0.0, min(1.0, float(parsed.get("score", 0.5))))
                    faith_reason = parsed.get("reason", "(no reason from judge)")
                except Exception as e:
                    faithfulness_score = 0.5
                    faith_reason = f"Judge call failed: {e}"

        combined = (retrieval_score * 0.5) + (faithfulness_score * 0.5)
        return EvaluationResult(
            metric_name="rag_grounding",
            score=combined,
            passed=combined >= 0.7,
            reason=(
                f"retrieval={retrieval_score:.2f}, faithfulness={faithfulness_score:.2f}; "
                f"{faith_reason}"
            ),
            evidence=[
                {
                    "required_docs": required_docs,
                    "retrieved_docs": retrieved_docs,
                    "missing_docs": missing,
                    "retrieval_score": retrieval_score,
                    "faithfulness_score": faithfulness_score,
                }
            ],
        )
