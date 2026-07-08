"""add intake discovery table

Revision ID: 20260708_0002
Revises: 20260702_0001
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0002"
down_revision = "20260702_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intake_discovery",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("pipeline_name", sa.String(length=128), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("batch_id", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("max_mtime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_state", sa.String(length=64), nullable=False, server_default="observed"),
        sa.Column("analysis_id", sa.String(length=128), nullable=True),
        sa.Column("submit_state", sa.String(length=64), nullable=False, server_default="not_submitted"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("pipeline_name", "root_path", "batch_id", name="uq_intake_pipeline_root_batch"),
    )
    op.create_index("ix_intake_pipeline_state", "intake_discovery", ["pipeline_name", "ready_state", "submit_state"])
    op.create_index("ix_intake_analysis_id", "intake_discovery", ["analysis_id"])


def downgrade() -> None:
    op.drop_index("ix_intake_analysis_id", table_name="intake_discovery")
    op.drop_index("ix_intake_pipeline_state", table_name="intake_discovery")
    op.drop_table("intake_discovery")
