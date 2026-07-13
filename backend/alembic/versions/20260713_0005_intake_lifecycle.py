"""add intake discovery lifecycle fields

Revision ID: 20260713_0005
Revises: 20260711_0004
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_0005"
down_revision = "20260711_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("intake_discovery", sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("intake_discovery", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("intake_discovery", sa.Column("archive_reason", sa.String(length=128), nullable=True))
    op.add_column("intake_discovery", sa.Column("archive_path", sa.Text(), nullable=True))
    op.execute(
        "UPDATE intake_discovery SET state_changed_at = COALESCE(last_seen_at, first_seen_at, CURRENT_TIMESTAMP)"
    )
    op.alter_column("intake_discovery", "state_changed_at", nullable=False)
    op.create_index("ix_intake_archived_at", "intake_discovery", ["archived_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_intake_archived_at", table_name="intake_discovery")
    op.drop_column("intake_discovery", "archive_path")
    op.drop_column("intake_discovery", "archive_reason")
    op.drop_column("intake_discovery", "archived_at")
    op.drop_column("intake_discovery", "state_changed_at")
