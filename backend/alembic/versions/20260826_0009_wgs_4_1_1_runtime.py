"""align biodemo with the WGS 4.1.1 Step1-Step6 runtime

Revision ID: 20260826_0009
Revises: 20260812_0008
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0009"
down_revision = "20260812_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transfer_job",
        sa.Column(
            "progress_detail_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.drop_table("master_slot")


def downgrade() -> None:
    op.create_table(
        "master_slot",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("slot_name", sa.String(64), nullable=False, unique=True),
        sa.Column("analysis_id", sa.String(128)),
        sa.Column("attempt", sa.Integer()),
        sa.Column("leased_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    )
    op.drop_column("transfer_job", "progress_detail_available")
