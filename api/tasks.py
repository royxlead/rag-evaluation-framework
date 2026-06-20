"""Celery task definitions for batch evaluation processing."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import BatchJob, async_session_factory

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "rag-evaluation-framework",
    broker=f"{REDIS_URL}/0",
    backend=f"{REDIS_URL}/1",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_max_retries=3,
)


@celery_app.task(bind=True, max_retries=3)
def run_batch_evaluation(
    self,
    job_id: str,
    items: list[dict],
    llm: str,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Process a batch of evaluation items.

    Celery task runs each item through the Evaluator, persists results,
    and calls webhook URL on completion.

    Args:
        job_id: UUID string for the batch job.
        items: List of dicts with question, context, answer.
        llm: Model string for evaluation.
        webhook_url: Optional URL to POST results to on completion.

    Returns:
        Dict with job_id, status, result_ids.
    """
    # Run async processing in sync Celery task
    return asyncio.run(_run_batch_async(self, job_id, items, llm, webhook_url))


async def _run_batch_async(
    task,
    job_id: str,
    items: list[dict],
    llm: str,
    webhook_url: str | None,
) -> dict[str, Any]:
    """Async batch processing logic."""
    from rag_evaluation_framework import Evaluator

    evaluator = Evaluator(llm=llm, cache=True)
    result_ids: list[str] = []

    async with async_session_factory() as session:
        # Update job status to running
        job = await _get_job(session, job_id)
        if job is None:
            return {"job_id": job_id, "status": "failed", "error": "Job not found"}
        job.status = "running"

        for idx, item in enumerate(items):
            try:
                result = await evaluator.async_score(
                    question=item["question"],
                    context=item.get("context", []),
                    answer=item["answer"],
                )
                result_ids.append(result.id)

                # Persist to DB
                await _persist_result(session, result)

                # Update progress
                job.completed_items = idx + 1
                job.result_ids = result_ids
                await session.commit()

                # Update task state
                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": idx + 1,
                        "total": len(items),
                        "result_ids": result_ids,
                    },
                )
            except Exception as e:
                task.update_state(
                    state="FAILURE",
                    meta={"current": idx + 1, "total": len(items), "error": str(e)},
                )
                job.status = "failed"
                job.error = str(e)
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e),
                    "result_ids": result_ids,
                }

        # Mark as completed
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.result_ids = result_ids
        await session.commit()

        # Call webhook if provided
        if webhook_url:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.post(
                        webhook_url,
                        json={"job_id": job_id, "status": "completed", "result_ids": result_ids},
                    )
            except Exception:
                pass

        return {"job_id": job_id, "status": "completed", "result_ids": result_ids}


async def _get_job(session: AsyncSession, job_id: str) -> Any | None:
    """Get a batch job by ID."""
    from uuid import UUID

    try:
        uid = UUID(job_id)
    except ValueError:
        return None

    result = await session.execute(select(BatchJob).where(BatchJob.id == uid))
    return result.scalar_one_or_none()


async def _persist_result(session: AsyncSession, result) -> None:
    """Persist an EvalResult to the database."""
    from api.database import EvalResultDB

    db_result = EvalResultDB(
        id=result.id,
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
        llm_used=result.metadata.get("llm", ""),
        latency_ms=result.latency_ms,
    )
    session.add(db_result)
