"""add WGS-only platform, RBAC, transfer and CCE evidence tables

Revision ID: 20260812_0006
Revises: 20260713_0005
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260812_0006"
down_revision = "20260713_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_run", sa.Column("execution_mode", sa.String(32), nullable=False, server_default="cce"))
    op.add_column("analysis_run", sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"))

    op.create_table("user_account", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("username", sa.String(128), nullable=False, unique=True), sa.Column("password_hash", sa.Text(), nullable=False), sa.Column("role", sa.String(32), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("auth_session", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("csrf_token", sa.String(128), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_auth_session_token_hash", "auth_session", ["token_hash"], unique=True)
    op.create_table("audit_log", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("username", sa.String(128)), sa.Column("action", sa.String(128), nullable=False), sa.Column("analysis_id", sa.String(128)), sa.Column("payload_json", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_log_analysis", "audit_log", ["analysis_id"])
    op.create_table("run_attempt", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("execution_mode", sa.String(32), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("run_label", sa.String(128)), sa.Column("evidence_path", sa.Text()), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("ended_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("analysis_id", "attempt", name="uq_run_attempt_analysis_attempt"))
    op.create_index("ix_run_attempt_analysis", "run_attempt", ["analysis_id"])
    op.create_table("wgs_intake_batch", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("source_path", sa.Text(), nullable=False, unique=True), sa.Column("manifest_sha256", sa.String(64), nullable=False), sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("ready_mtime_ns", sa.BigInteger(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("transfer_job", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("direction", sa.String(16), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("manifest_path", sa.Text()), sa.Column("receipt_path", sa.Text()), sa.Column("error_message", sa.Text()), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("ended_at", sa.DateTime(timezone=True)), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_transfer_job_analysis", "transfer_job", ["analysis_id"])
    op.create_table("rule_event_raw", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("event_id", sa.String(256), nullable=False), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("payload_json", sa.JSON(), nullable=False), sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("analysis_id", "attempt", "event_id", name="uq_rule_event_raw_identity"))
    op.create_index("ix_rule_event_raw_analysis", "rule_event_raw", ["analysis_id"])
    op.create_table("rule_state", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("rule_instance_id", sa.String(128), nullable=False), sa.Column("rule_name", sa.String(256), nullable=False), sa.Column("sample_id", sa.String(128)), sa.Column("layer", sa.Integer()), sa.Column("status", sa.String(64), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("ended_at", sa.DateTime(timezone=True)), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("analysis_id", "attempt", "rule_instance_id", name="uq_rule_state_identity"))
    op.create_index("ix_rule_state_analysis", "rule_state", ["analysis_id"])
    op.create_table("kubernetes_workload", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("event_id", sa.String(256), nullable=False), sa.Column("pod_hash", sa.String(128), nullable=False), sa.Column("job_name", sa.String(256)), sa.Column("phase", sa.String(64), nullable=False), sa.Column("reason", sa.String(256)), sa.Column("exit_code", sa.Integer()), sa.Column("image_id", sa.Text()), sa.Column("resources_json", sa.JSON(), nullable=False), sa.Column("evidence_path", sa.Text()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("analysis_id", "attempt", "pod_hash", name="uq_k8s_workload_identity"))
    op.create_index("ix_k8s_workload_analysis", "kubernetes_workload", ["analysis_id"])
    op.create_table("master_slot", sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True), sa.Column("slot_name", sa.String(64), nullable=False, unique=True), sa.Column("analysis_id", sa.String(128)), sa.Column("attempt", sa.Integer()), sa.Column("leased_at", sa.DateTime(timezone=True)), sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.bulk_insert(sa.table("master_slot", sa.column("slot_name", sa.String())), [{"slot_name": f"wgs-master-pool-{number:02d}"} for number in range(1, 5)])


def downgrade() -> None:
    for table in ("master_slot", "kubernetes_workload", "rule_state", "rule_event_raw", "transfer_job", "wgs_intake_batch", "run_attempt", "audit_log", "auth_session", "user_account"):
        op.drop_table(table)
    op.drop_column("analysis_run", "attempt")
    op.drop_column("analysis_run", "execution_mode")

