"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2026-01-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("key_hash", sa.String(60), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_count", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("rate_limit_per_hour", sa.Integer(), server_default="100"),
    )

    # Evaluation results table
    op.create_table(
        "eval_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("context", JSONB(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("faithfulness_score", sa.Float(), nullable=True),
        sa.Column("faithfulness_details", JSONB(), nullable=True),
        sa.Column("hallucination_rate", sa.Float(), nullable=True),
        sa.Column("hallucination_details", JSONB(), nullable=True),
        sa.Column("retrieval_precision", sa.Float(), nullable=True),
        sa.Column("retrieval_details", JSONB(), nullable=True),
        sa.Column("answer_relevance", sa.Float(), nullable=True),
        sa.Column("relevance_details", JSONB(), nullable=True),
        sa.Column("context_coverage", sa.Float(), nullable=True),
        sa.Column("coverage_details", JSONB(), nullable=True),
        sa.Column("ucm_score", sa.Float(), nullable=True),
        sa.Column("ucm_details", JSONB(), nullable=True),
        sa.Column("llm_used", sa.String(100), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("api_key_id", UUID(as_uuid=True), sa.ForeignKey("api_keys.id"), nullable=True),
        sa.Column("metadata", JSONB(), server_default="{}"),
    )

    # Batch jobs table
    op.create_table(
        "batch_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("completed_items", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_ids", JSONB(), server_default="[]"),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("api_key_id", UUID(as_uuid=True), sa.ForeignKey("api_keys.id"), nullable=True),
    )

    # Indexes
    op.create_index("ix_eval_results_created_at", "eval_results", ["created_at"])
    op.create_index("ix_eval_results_api_key_id", "eval_results", ["api_key_id"])
    op.create_index("ix_eval_results_overall_score", "eval_results", ["overall_score"])


def downgrade() -> None:
    op.drop_index("ix_eval_results_overall_score")
    op.drop_index("ix_eval_results_api_key_id")
    op.drop_index("ix_eval_results_created_at")
    op.drop_table("batch_jobs")
    op.drop_table("eval_results")
    op.drop_table("api_keys")
