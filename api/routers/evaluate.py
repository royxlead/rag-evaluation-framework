"""REST endpoints for single evaluation.

POST /v1/evaluate run a single evaluation
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import EvalResultDB, get_db
from api.deps import require_rate_limit
from rag_evaluation_framework import Evaluator

router = APIRouter()


@router.post("/v1/evaluate")
async def evaluate(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    api_key_data: dict = Depends(require_rate_limit),
) -> dict[str, Any]:
    """Run a single evaluation.

    Request body:
        question: str
        context: list[str]
        answer: str
        metrics: list[str] = ["all"]
        llm: str = "openai/gpt-4o"
        options: dict = {}
    """
    question = body.get("question")
    context = body.get("context", [])
    answer = body.get("answer")
    metrics = body.get("metrics", ["all"])
    llm = body.get("llm", "openai/gpt-4o")
    options = body.get("options", {})

    if not question or not answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'question' and 'answer' are required",
        )

    evaluator = Evaluator(llm=llm, model_config=options, cache=True)
    result = await evaluator.async_score(
        question=question,
        context=context,
        answer=answer,
        metrics=metrics,
        **options,
    )

    # Persist to database
    db_result = EvalResultDB(
        id=uuid.UUID(result.id),
        question=result.question,
        context=result.context,
        answer=result.answer,
        overall_score=result.overall_score,
        faithfulness_score=result.faithfulness.score,
        faithfulness_details=result.faithfulness.details,
        hallucination_rate=result.hallucination_rate.score,
        hallucination_details=result.hallucination_rate.details,
        retrieval_precision=result.retrieval_precision.score,
        retrieval_details=result.retrieval_precision.details,
        answer_relevance=result.answer_relevance.score,
        relevance_details=result.answer_relevance.details,
        context_coverage=result.context_coverage.score,
        coverage_details=result.context_coverage.details,
        ucm_score=result.ucm_confidence.score,
        ucm_details=result.ucm_confidence.details,
        llm_used=llm,
        latency_ms=result.latency_ms,
        api_key_id=uuid.UUID(api_key_data["id"])
        if isinstance(api_key_data.get("id"), str)
        else None,
    )
    db.add(db_result)
    await db.commit()

    return result.model_dump()
