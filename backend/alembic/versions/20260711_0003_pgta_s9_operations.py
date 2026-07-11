"""add PGT-A S9 operational timestamps and intake audit fields

Revision ID: 20260711_0003
Revises: 20260708_0002
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_0003"
down_revision = "20260708_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_run", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("analysis_run", sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("analysis_run", sa.Column("current_stage", sa.String(length=256), nullable=True))
    op.add_column("analysis_run", sa.Column("progress_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE analysis_run
        SET submitted_at = (
            SELECT MIN(run_action.created_at)
            FROM run_action
            WHERE run_action.analysis_id = analysis_run.analysis_id
              AND run_action.action = 'submit'
              AND run_action.result_status = 'accepted'
        )
        WHERE dag_run_id IS NOT NULL
        """
    )
    op.add_column("intake_discovery", sa.Column("source_manifest_path", sa.Text(), nullable=True))
    op.add_column("intake_discovery", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "intake_discovery",
        sa.Column("stable_observation_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("intake_discovery", "stable_observation_count")
    op.drop_column("intake_discovery", "last_error")
    op.drop_column("intake_discovery", "source_manifest_path")
    op.drop_column("analysis_run", "progress_updated_at")
    op.drop_column("analysis_run", "current_stage")
    op.drop_column("analysis_run", "progress_percent")
    op.drop_column("analysis_run", "submitted_at")
