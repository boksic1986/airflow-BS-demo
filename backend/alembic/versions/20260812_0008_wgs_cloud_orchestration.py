"""add WGS cloud orchestration snapshots, validation and transfer progress

Revision ID: 20260812_0008
Revises: 20260812_0007
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa

revision = "20260812_0008"
down_revision = "20260812_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        sa.Column("transfer_id", sa.String(128), unique=True),
        sa.Column("transfer_type", sa.String(32)),
        sa.Column("source", sa.Text()), sa.Column("destination", sa.Text()),
        sa.Column("bytes_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("bytes_transferred", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("files_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_file", sa.Text()),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("speed_bps", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("eta_seconds", sa.BigInteger()), sa.Column("estimated_finish_at", sa.DateTime(timezone=True)),
        sa.Column("checkpoint_ref", sa.Text()), sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("verification_status", sa.String(64)), sa.Column("message", sa.Text()),
    ):
        op.add_column("transfer_job", column)
    op.create_table("wgs_input_snapshot",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("batch_no", sa.String(128), nullable=False), sa.Column("fq_path", sa.Text(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("manifest_path", sa.Text(), nullable=False), sa.Column("manifest_sha256", sa.String(64)),
        sa.Column("status", sa.String(64), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("batch_no", "fq_path", name="uq_wgs_input_snapshot_batch_path"),
        sa.UniqueConstraint("analysis_id", "attempt", name="uq_wgs_input_snapshot_attempt"))
    op.create_index("ix_wgs_input_snapshot_analysis", "wgs_input_snapshot", ["analysis_id"])
    op.create_table("run_validation_issue",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("code", sa.String(128), nullable=False), sa.Column("severity", sa.String(32), nullable=False, server_default="error"),
        sa.Column("scope_type", sa.String(32)), sa.Column("sample_id", sa.String(128)), sa.Column("family_id", sa.String(128)),
        sa.Column("file_path", sa.Text()), sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True)))
    op.create_index("ix_run_validation_issue_analysis", "run_validation_issue", ["analysis_id"])
    op.create_table("obs_transfer_lease", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("slot_name", sa.String(64), nullable=False, unique=True), sa.Column("analysis_id", sa.String(128)),
        sa.Column("attempt", sa.Integer()), sa.Column("transfer_id", sa.String(128)),
        sa.Column("leased_at", sa.DateTime(timezone=True)), sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.bulk_insert(sa.table("obs_transfer_lease", sa.column("slot_name", sa.String())), [{"slot_name": "wgs-obs-transfer-01"}])


def downgrade() -> None:
    op.drop_table("obs_transfer_lease")
    op.drop_table("run_validation_issue")
    op.drop_table("wgs_input_snapshot")
    for name in ("message", "verification_status", "heartbeat_at", "checkpoint_ref", "estimated_finish_at", "eta_seconds", "speed_bps", "progress_percent", "current_file", "files_completed", "files_total", "bytes_transferred", "bytes_total", "destination", "source", "transfer_type", "transfer_id"):
        op.drop_column("transfer_job", name)
