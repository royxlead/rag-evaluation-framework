"""REST endpoints for retrieving and listing reports.

GET /v1/reports list recent evaluation results
GET /v1/reports/{result_id} retrieve a stored evaluation result
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import EvalResultDB, get_db
from api.deps import get_api_key
from rag_evaluation_framework import EvalResult
from rag_evaluation_framework.models import MetricScore

router = APIRouter()


@router.get("/v1/reports")
async def list_reports(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    api_key_data: dict = Depends(get_api_key),
) -> list[dict[str, Any]]:
    """List recent evaluation results with summary scores.

    Returns results ordered by creation date (newest first).
    Useful for dashboards and trend analysis.
    """
    result = await db.execute(
        select(EvalResultDB).order_by(EvalResultDB.created_at.desc()).offset(offset).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "question": row.question,
            "overall_score": row.overall_score,
            "latency_ms": row.latency_ms,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "faithfulness_score": row.faithfulness_score,
            "hallucination_rate": row.hallucination_rate,
            "retrieval_precision": row.retrieval_precision,
            "answer_relevance": row.answer_relevance,
            "context_coverage": row.context_coverage,
            "ucm_score": row.ucm_score,
        }
        for row in rows
    ]


@router.get("/v1/reports/{result_id}")
async def get_report(
    result_id: str,
    format: str = Query("json", regex="^(json|html|pdf)$"),
    db: AsyncSession = Depends(get_db),
    api_key_data: dict = Depends(get_api_key),
) -> Any:
    """Retrieve a stored evaluation result.

    Args:
        result_id: UUID of the evaluation result.
        format: Output format: 'json', 'html', or 'pdf'.

    Returns:
        Report in the requested format.
    """
    try:
        uid = UUID(result_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid result ID format",
        )

    result = await db.execute(select(EvalResultDB).where(EvalResultDB.id == uid))
    db_row = result.scalar_one_or_none()

    if db_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )

    # Reconstruct EvalResult
    eval_result = EvalResult(
        id=str(db_row.id),
        question=db_row.question,
        context=db_row.context or [],
        answer=db_row.answer,
        overall_score=db_row.overall_score,
        faithfulness=MetricScore(
            score=db_row.faithfulness_score or 0.0,
            details=db_row.faithfulness_details or {},
        ),
        hallucination_rate=MetricScore(
            score=db_row.hallucination_rate or 0.0,
            details=db_row.hallucination_details or {},
        ),
        retrieval_precision=MetricScore(
            score=db_row.retrieval_precision or 0.0,
            details=db_row.retrieval_details or {},
        ),
        answer_relevance=MetricScore(
            score=db_row.answer_relevance or 0.0,
            details=db_row.relevance_details or {},
        ),
        context_coverage=MetricScore(
            score=db_row.context_coverage or 0.0,
            details=db_row.coverage_details or {},
        ),
        ucm_confidence=MetricScore(
            score=db_row.ucm_score or 0.0,
            details=db_row.ucm_details or {},
        ),
        metadata=db_row.extra_metadata or {},
        latency_ms=db_row.latency_ms or 0,
    )

    if format == "json":
        return eval_result.model_dump()
    elif format == "html":
        from fastapi.responses import HTMLResponse

        return HTMLResponse(content=eval_result.report(format="html"))
    elif format == "pdf":
        import tempfile

        from fastapi.responses import FileResponse

        from rag_evaluation_framework.report import ReportBuilder

        builder = ReportBuilder(eval_result)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            path = builder.to_pdf(tmp.name)
            return FileResponse(
                path, media_type="application/pdf", filename=f"report_{result_id[:8]}.pdf"
            )
        except Exception:
            # Fallback to HTML
            return HTMLResponse(content=eval_result.report(format="html"))
