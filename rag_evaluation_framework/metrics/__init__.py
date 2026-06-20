"""Metrics package init."""

from rag_evaluation_framework.metrics.answer_relevance import score_answer_relevance
from rag_evaluation_framework.metrics.context_coverage import score_context_coverage
from rag_evaluation_framework.metrics.faithfulness import score_faithfulness
from rag_evaluation_framework.metrics.hallucination import score_hallucination
from rag_evaluation_framework.metrics.retrieval_precision import score_retrieval_precision
from rag_evaluation_framework.metrics.ucm_confidence import score_ucm_confidence

__all__ = [
"score_faithfulness",
"score_hallucination",
"score_retrieval_precision",
"score_answer_relevance",
"score_context_coverage",
"score_ucm_confidence",
]

METRIC_REGISTRY = {
"faithfulness": score_faithfulness,
"hallucination": score_hallucination,
"retrieval_precision": score_retrieval_precision,
"answer_relevance": score_answer_relevance,
"context_coverage": score_context_coverage,
"ucm_confidence": score_ucm_confidence,
}
