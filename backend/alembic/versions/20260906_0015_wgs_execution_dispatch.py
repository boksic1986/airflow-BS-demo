"""Add atomic WGS execution target dispatch state.

Revision ID: 20260906_0015
Revises: 20260904_0014
"""

from alembic import op
import sqlalchemy as sa


revision = "20260906_0015"
down_revision = "20260904_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wgs_execution_dispatch",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("batch", sa.String(length=64), nullable=False),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("desired_mode", sa.String(length=32), nullable=False, server_default="cce"),
        sa.Column("desired_target", sa.String(length=64), nullable=False, server_default="cce"),
        sa.Column("dispatch_state", sa.String(length=32), nullable=False, server_default="preparing"),
        sa.Column("dispatch_revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_attempt", sa.Integer(), nullable=True),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "batch", name="uq_wgs_execution_dispatch_project_batch"
        ),
        sa.UniqueConstraint("analysis_id", name="uq_wgs_execution_dispatch_analysis"),
    )
    op.create_index(
        "ix_wgs_execution_dispatch_state",
        "wgs_execution_dispatch",
        ["dispatch_state"],
    )
    op.create_index(
        "ix_wgs_execution_dispatch_target",
        "wgs_execution_dispatch",
        ["desired_target", "dispatch_state"],
    )
    op.create_table(
        "wgs_execution_target_slot",
        sa.Column("target", sa.String(length=64), nullable=False),
        sa.Column("analysis_id", sa.String(length=128), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis_run.analysis_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("target"),
    )
    slots = sa.table("wgs_execution_target_slot", sa.column("target", sa.String))
    op.bulk_insert(slots, [{"target": "node-97"}, {"target": "node-96"}])


def downgrade() -> None:
    raise RuntimeError(
        "WGS execution dispatch audit state is append-only and cannot be downgraded destructively"
    )
