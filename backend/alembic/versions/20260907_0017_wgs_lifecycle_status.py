"""Add independent WGS post-workflow lifecycle status.

Revision ID: 20260907_0017
Revises: 20260907_0016
"""

from alembic import op
import sqlalchemy as sa


revision = "20260907_0017"
down_revision = "20260907_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wgs_lifecycle_status",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_key", sa.String(length=256), nullable=False),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="not_started"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "scope_type", "scope_key", name="uq_wgs_lifecycle_kind_scope"),
    )
    op.create_index(
        "ix_wgs_lifecycle_analysis",
        "wgs_lifecycle_status",
        ["analysis_id", "attempt"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "WGS lifecycle status is audited operational state and cannot be downgraded destructively"
    )
