"""Batch evaluation endpoints.

POST /v1/batch submit batch evaluation
GET /v1/jobs/{job_id} poll batch job status
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import BatchJob, get_db
from api.deps import get_api_key, require_rate_limit
from api.tasks import celery_app

router = APIRouter()


@router.post("/v1/batch")
async def batch_evaluate(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    api_key_data: dict = Depends(require_rate_limit),
) -> dict[str, Any]:
    """Submit a batch evaluation job.

    Request body:
        items: list[{ question, context, answer }]
        llm: str = "openai/gpt-4o"
        webhook_url: str | null
    """
    items = body.get("items", [])
    llm = body.get("llm", "openai/gpt-4o")
    webhook_url = body.get("webhook_url")

    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'items' list is required",
        )

    if len(items) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 items per batch",
        )

    # Create job record
    job_id = uuid.uuid4()
    job = BatchJob(
        id=job_id,
        status="queued",
        total_items=len(items),
        webhook_url=webhook_url,
        api_key_id=uuid.UUID(api_key_data["id"])
        if isinstance(api_key_data.get("id"), str)
        else None,
    )
    db.add(job)
    await db.commit()

    # Submit to Celery
    celery_app.send_task(
        "api.tasks.run_batch_evaluation",
        args=[str(job_id), items, llm, webhook_url],
    )

    estimated_seconds = len(items) * 3
    return {
        "job_id": str(job_id),
        "status": "queued",
        "estimated_seconds": estimated_seconds,
    }


@router.get("/v1/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    api_key_data: dict = Depends(get_api_key),
) -> dict[str, Any]:
    """Get the status of a batch job."""
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    result = await db.execute(select(BatchJob).where(BatchJob.id == uid))
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return {
        "job_id": str(job.id),
        "status": job.status,
        "total_items": job.total_items,
        "completed_items": job.completed_items,
        "result_ids": job.result_ids,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
