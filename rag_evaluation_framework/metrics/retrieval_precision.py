"""Retrieval precision metric embedding-based relevance scoring for retrieved chunks."""

from __future__ import annotations

import numpy as np

from rag_evaluation_framework.adapters.base import LLMAdapter
from rag_evaluation_framework.models import MetricScore
from rag_evaluation_framework.utils import clamp_score, cosine_similarity


async def score_retrieval_precision(
question: str,
context: list[str],
answer: str,
adapter: LLMAdapter,
relevance_threshold: float = 0.3,
) -> MetricScore:
    """Score retrieval precision using embedding similarity.

    Computes semantic relevance between question and each context chunk
    using cosine similarity of sentence-transformer embeddings.

    No LLM call needed pure embedding-based.

    Returns:
        MetricScore with score = fraction of chunks above relevance threshold.
    """
    if not context:
        return MetricScore(
            score=1.0,
            explanation="No context chunks to evaluate vacuously perfect precision.",
            confidence=0.5,
            details={"total_chunks": 0, "relevant_chunks": 0, "threshold": relevance_threshold},
        )

    # Compute embeddings
    question_embedding = await adapter.embed(question)
    chunk_embeddings = await adapter.embed(context)

    if question_embedding.ndim == 1:
        question_embedding = question_embedding.reshape(1, -1)
    if chunk_embeddings.ndim == 1:
        chunk_embeddings = chunk_embeddings.reshape(1, -1)

    # Compute similarity scores
    similarities = []
    for chunk_emb in chunk_embeddings:
        sim = cosine_similarity(question_embedding[0], chunk_emb)
        similarities.append(sim)

    # Count relevant chunks
    relevant = sum(1 for s in similarities if s >= relevance_threshold)
    total = len(context)
    precision = clamp_score(relevant / total) if total > 0 else 1.0

    # MRR (Mean Reciprocal Rank) rank of first relevant chunk
    mrr = 0.0
    for rank, sim in enumerate(sorted(similarities, reverse=True), 1):
        if sim >= relevance_threshold:
            mrr = 1.0 / rank
            break

    explanation = (
        f"Retrieval precision {precision:.3f}: {relevant}/{total} chunks are relevant "
        f"(similarity >= {relevance_threshold}). "
        f"MRR: {mrr:.3f}. "
        f"Avg similarity: {float(np.mean(similarities)):.3f}."
    )

    chunk_details = []
    for i, (chunk, sim) in enumerate(zip(context, similarities)):
        chunk_details.append(
            {
                "chunk_index": i,
                "similarity": float(sim),
                "relevant": sim >= relevance_threshold,
                "preview": chunk[:100] + "..." if len(chunk) > 100 else chunk,
            }
        )

    details = {
        "chunks": chunk_details,
        "total_chunks": total,
        "relevant_chunks": relevant,
        "threshold": relevance_threshold,
        "mrr": float(mrr),
        "avg_similarity": float(np.mean(similarities)),
        "similarities": [float(s) for s in similarities],
    }

    # Confidence based on number of chunks evaluated
    confidence = clamp_score(min(1.0, total / 10.0))

    return MetricScore(
        score=precision, explanation=explanation, confidence=confidence, details=details
    )
