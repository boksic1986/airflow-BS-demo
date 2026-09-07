"""Add immutable Step7 retry generations and frozen target identity.

Revision ID: 20260908_0018
Revises: 20260907_0017
"""

from alembic import op
import sqlalchemy as sa


revision = "20260908_0018"
down_revision = "20260907_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wgs_maintenance_action",
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "wgs_maintenance_action",
        sa.Column("retry_of_action_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "wgs_maintenance_action",
        sa.Column(
            "target_snapshot_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.drop_constraint(
        "uq_wgs_maintenance_action_attempt_type",
        "wgs_maintenance_action",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_wgs_maintenance_action_attempt_type_generation",
        "wgs_maintenance_action",
        ["analysis_id", "attempt", "action_type", "generation"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "Step7 generation history is audited operational state and cannot be downgraded destructively"
    )
