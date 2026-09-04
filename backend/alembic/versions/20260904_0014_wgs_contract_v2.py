"""WGS orchestration contract v2 stage and transfer evidence.

Revision ID: 20260904_0014
Revises: 20260901_0013
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_0014"
down_revision = "20260901_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wgs_stage_execution",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_id", sa.String(length=128), nullable=False),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("stage_code", sa.String(length=64), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("release_id", sa.String(length=128), nullable=False),
        sa.Column("predecessor_execution_id", sa.String(length=128), nullable=True),
        sa.Column("predecessor_generation", sa.Integer(), nullable=True),
        sa.Column("predecessor_receipt_hash", sa.String(length=64), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_type", sa.String(length=64), nullable=True),
        sa.Column("evidence_key", sa.Text(), nullable=True),
        sa.Column("receipt_hash", sa.String(length=64), nullable=True),
        sa.Column("terminal_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id"),
        sa.UniqueConstraint("analysis_id", "attempt", "stage_code", "generation", name="uq_wgs_stage_execution_generation"),
    )
    op.create_index("ix_wgs_stage_execution_current", "wgs_stage_execution", ["analysis_id", "attempt", "stage_code", "generation"])
    op.create_index("ix_wgs_stage_execution_status", "wgs_stage_execution", ["stage_code", "status"])

    op.create_table(
        "transfer_file_state",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("transfer_id", sa.String(length=128), nullable=False),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("file_key", sa.String(length=256), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("bytes_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("bytes_transferred", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("speed_bps", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("checksum_status", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transfer_id", "file_key", name="uq_transfer_file_state_identity"),
    )
    op.create_index("ix_transfer_file_state_transfer_status", "transfer_file_state", ["transfer_id", "status"])


def downgrade() -> None:
    raise RuntimeError("WGS contract v2 evidence is append-only and cannot be downgraded destructively")
