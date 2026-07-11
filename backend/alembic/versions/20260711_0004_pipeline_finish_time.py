"""add immutable pipeline finish time

Revision ID: 20260711_0004
Revises: 20260711_0003
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_0004"
down_revision = "20260711_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_run", sa.Column("pipeline_finished_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("analysis_run", "pipeline_finished_at")
