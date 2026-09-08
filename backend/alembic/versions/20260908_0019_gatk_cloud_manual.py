"""Add generic submission drafts and stage executions for GATK Cloud.

Revision ID: 20260908_0019
Revises: 20260908_0018
"""

from alembic import op
import sqlalchemy as sa


revision = "20260908_0019"
down_revision = "20260908_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_submission_draft",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("draft_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("pipeline_name", sa.String(length=128), nullable=False),
        sa.Column("owner_username", sa.String(length=128), nullable=False),
        sa.Column("input_root", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("preview_json", sa.JSON(), nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=128),
            sa.ForeignKey("analysis_run.analysis_id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_pipeline_submission_draft_owner_status",
        "pipeline_submission_draft",
        ["pipeline_name", "owner_username", "status"],
    )
    op.create_index(
        "ix_pipeline_submission_draft_expiry",
        "pipeline_submission_draft",
        ["expires_at"],
    )
    op.create_table(
        "pipeline_stage_execution",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("execution_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("pipeline_name", sa.String(length=128), nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=128),
            sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("stage_code", sa.String(length=64), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("release_id", sa.String(length=128), nullable=False),
        sa.Column("predecessor_execution_id", sa.String(length=128)),
        sa.Column("predecessor_generation", sa.Integer()),
        sa.Column("predecessor_receipt_hash", sa.String(length=64)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("evidence_type", sa.String(length=64)),
        sa.Column("evidence_key", sa.Text()),
        sa.Column("receipt_hash", sa.String(length=64)),
        sa.Column("terminal_payload_json", sa.JSON(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "pipeline_name", "analysis_id", "attempt", "stage_code", "generation",
            name="uq_pipeline_stage_execution_generation",
        ),
    )
    op.create_index(
        "ix_pipeline_stage_execution_current",
        "pipeline_stage_execution",
        ["pipeline_name", "analysis_id", "attempt", "stage_code", "generation"],
    )
    op.create_index(
        "ix_pipeline_stage_execution_status",
        "pipeline_stage_execution",
        ["pipeline_name", "stage_code", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pipeline_stage_execution_status", table_name="pipeline_stage_execution"
    )
    op.drop_index(
        "ix_pipeline_stage_execution_current", table_name="pipeline_stage_execution"
    )
    op.drop_table("pipeline_stage_execution")
    op.drop_index(
        "ix_pipeline_submission_draft_expiry",
        table_name="pipeline_submission_draft",
    )
    op.drop_index(
        "ix_pipeline_submission_draft_owner_status",
        table_name="pipeline_submission_draft",
    )
    op.drop_table("pipeline_submission_draft")
