from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass


class Pipeline(Base):
    __tablename__ = "pipeline"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    dag_id: Mapped[str] = mapped_column(String(256), nullable=False)
    version: Mapped[str | None] = mapped_column(String(128))
    runner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AnalysisRun(Base):
    __tablename__ = "analysis_run"
    __table_args__ = (
        UniqueConstraint("analysis_id", name="uq_analysis_run_analysis_id"),
        Index("ix_analysis_run_pipeline_status", "pipeline_name", "status"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(String(128), nullable=False)
    pipeline_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dag_id: Mapped[str] = mapped_column(String(256), nullable=False)
    dag_run_id: Mapped[str | None] = mapped_column(String(256))
    parent_analysis_id: Mapped[str | None] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(64), nullable=False, default="new")
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="cce")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="submitted")
    sample_sheet_path: Mapped[str | None] = mapped_column(Text)
    workdir: Mapped[str] = mapped_column(Text, nullable=False)
    params_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    airflow_url: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[str | None] = mapped_column(String(128))
    email_to: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pipeline_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(256))
    progress_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text)


class Sample(Base):
    __tablename__ = "sample"
    __table_args__ = (
        UniqueConstraint("analysis_id", "sample_id", name="uq_sample_analysis_sample"),
        Index("ix_sample_analysis_id", "analysis_id"),
        Index("ix_sample_sample_id", "sample_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_id: Mapped[str] = mapped_column(String(128), nullable=False)
    family_id: Mapped[str | None] = mapped_column(String(128))
    sample_type: Mapped[str | None] = mapped_column(String(64))
    sex: Mapped[str | None] = mapped_column(String(32))
    fq1: Mapped[str | None] = mapped_column(Text)
    fq2: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    qc_status: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")


class SnakemakeRuleEvent(Base):
    __tablename__ = "snakemake_rule_event"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "rule",
            "sample_id",
            "snakemake_jobid",
            name="uq_rule_event_job",
        ),
        Index("ix_rule_event_analysis_id", "analysis_id"),
        Index("ix_rule_event_rule", "rule"),
        Index("ix_rule_event_sample_id", "sample_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )
    rule: Mapped[str] = mapped_column(String(256), nullable=False)
    sample_id: Mapped[str | None] = mapped_column(String(128))
    wildcards_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    snakemake_jobid: Mapped[str | None] = mapped_column(String(128))
    qsub_jobid: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    stdout_path: Mapped[str | None] = mapped_column(Text)
    stderr_path: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    return_code: Mapped[int | None] = mapped_column(Integer)
    resources_json: Mapped[dict | None] = mapped_column(JSON)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class QcMetric(Base):
    __tablename__ = "qc_metric"
    __table_args__ = (
        Index("ix_qc_metric_analysis_id", "analysis_id"),
        Index("ix_qc_metric_sample_id", "sample_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_id: Mapped[str | None] = mapped_column(String(128))
    metric_name: Mapped[str] = mapped_column(String(256), nullable=False)
    metric_value: Mapped[str | None] = mapped_column(Text)
    metric_numeric: Mapped[Decimal | None] = mapped_column(Numeric)
    threshold: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    source_file: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class Artifact(Base):
    __tablename__ = "artifact"
    __table_args__ = (Index("ix_artifact_analysis_id", "analysis_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(256))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RunAction(Base):
    __tablename__ = "run_action"
    __table_args__ = (Index("ix_run_action_analysis_id", "analysis_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(128))
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    result_status: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)


class IntakeDiscovery(Base):
    __tablename__ = "intake_discovery"
    __table_args__ = (
        UniqueConstraint("pipeline_name", "root_path", "batch_id", name="uq_intake_pipeline_root_batch"),
        Index("ix_intake_pipeline_state", "pipeline_name", "ready_state", "submit_state"),
        Index("ix_intake_analysis_id", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    pipeline_name: Mapped[str] = mapped_column(String(128), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    batch_id: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    max_mtime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_state: Mapped[str] = mapped_column(String(64), nullable=False, default="observed")
    analysis_id: Mapped[str | None] = mapped_column(String(128))
    submit_state: Mapped[str] = mapped_column(String(64), nullable=False, default="not_submitted")
    source_manifest_path: Mapped[str | None] = mapped_column(Text)
    last_error: Mapped[str | None] = mapped_column(Text)
    stable_observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    state_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archive_reason: Mapped[str | None] = mapped_column(String(128))
    archive_path: Mapped[str | None] = mapped_column(Text)


class UserAccount(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AuthSession(Base):
    __tablename__ = "auth_session"
    __table_args__ = (Index("ix_auth_session_token_hash", "token_hash", unique=True),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_analysis", "analysis_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    username: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    analysis_id: Mapped[str | None] = mapped_column(String(128))
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RunAttempt(Base):
    __tablename__ = "run_attempt"
    __table_args__ = (
        UniqueConstraint("analysis_id", "attempt", name="uq_run_attempt_analysis_attempt"),
        Index("ix_run_attempt_analysis", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    run_label: Mapped[str | None] = mapped_column(String(128))
    evidence_path: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WgsIntakeBatch(Base):
    __tablename__ = "wgs_intake_batch"

    __table_args__ = (
        Index("ix_wgs_intake_batch_state", "state"),
        Index("ix_wgs_intake_batch_sequencing_batch", "sequencing_batch"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    chip_id: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    sequencing_batch: Mapped[str] = mapped_column(String(16), nullable=False)
    analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_run.analysis_id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    barcode_stat_mtime_ns: Mapped[int | None] = mapped_column(BigInteger)
    barcode_stat_size: Mapped[int | None] = mapped_column(BigInteger)
    eligible_pair_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_addon_pair_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pair_issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_fingerprint: Mapped[str | None] = mapped_column(String(64))
    observed_fingerprint: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(64), nullable=False, default="waiting_barcode_stat")
    last_error: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class WgsIntakeScannerState(Base):
    __tablename__ = "wgs_intake_scanner_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    first_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_scanned_directory_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_error: Mapped[str | None] = mapped_column(Text)


class WgsMaintenanceAction(Base):
    __tablename__ = "wgs_maintenance_action"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "attempt",
            "action_type",
            name="uq_wgs_maintenance_action_attempt_type",
        ),
        Index("ix_wgs_maintenance_action_analysis", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    action_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    linkage_group: Mapped[str] = mapped_column(String(32), nullable=False, default="cram")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="requested")
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    source_dag_run_id: Mapped[str | None] = mapped_column(String(256))
    maintenance_dag_run_id: Mapped[str | None] = mapped_column(String(256))
    evidence_path: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class TransferJob(Base):
    __tablename__ = "transfer_job"
    __table_args__ = (Index("ix_transfer_job_analysis", "analysis_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    transfer_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    transfer_type: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(Text)
    destination: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    bytes_total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_transferred: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    files_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_file: Mapped[str | None] = mapped_column(Text)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    speed_bps: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    progress_detail_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    eta_seconds: Mapped[int | None] = mapped_column(BigInteger)
    estimated_finish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkpoint_ref: Mapped[str | None] = mapped_column(Text)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str | None] = mapped_column(String(64))
    message: Mapped[str | None] = mapped_column(Text)
    manifest_path: Mapped[str | None] = mapped_column(Text)
    receipt_path: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class TransferFileState(Base):
    __tablename__ = "transfer_file_state"
    __table_args__ = (
        UniqueConstraint("transfer_id", "file_key", name="uq_transfer_file_state_identity"),
        Index("ix_transfer_file_state_transfer_status", "transfer_id", "status"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    transfer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    file_key: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="accepted")
    bytes_total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_transferred: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    speed_bps: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    checksum_status: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class WgsInputSnapshot(Base):
    __tablename__ = "wgs_input_snapshot"
    __table_args__ = (
        UniqueConstraint("batch_no", "fq_path", name="uq_wgs_input_snapshot_batch_path"),
        UniqueConstraint("analysis_id", "attempt", name="uq_wgs_input_snapshot_attempt"),
        Index("ix_wgs_input_snapshot_analysis", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    batch_no: Mapped[str] = mapped_column(String(128), nullable=False)
    fq_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    manifest_path: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunValidationIssue(Base):
    __tablename__ = "run_validation_issue"
    __table_args__ = (Index("ix_run_validation_issue_analysis", "analysis_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="error")
    scope_type: Mapped[str | None] = mapped_column(String(32))
    sample_id: Mapped[str | None] = mapped_column(String(128))
    family_id: Mapped[str | None] = mapped_column(String(128))
    file_path: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ObsTransferLease(Base):
    __tablename__ = "obs_transfer_lease"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    slot_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    analysis_id: Mapped[str | None] = mapped_column(String(128))
    attempt: Mapped[int | None] = mapped_column(Integer)
    transfer_id: Mapped[str | None] = mapped_column(String(128))
    leased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuleEventRaw(Base):
    __tablename__ = "rule_event_raw"
    __table_args__ = (
        UniqueConstraint("analysis_id", "attempt", "event_id", name="uq_rule_event_raw_identity"),
        Index("ix_rule_event_raw_analysis", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RuleState(Base):
    __tablename__ = "rule_state"
    __table_args__ = (
        UniqueConstraint("analysis_id", "attempt", "rule_instance_id", name="uq_rule_state_identity"),
        Index("ix_rule_state_analysis", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(256), nullable=False)
    sequence: Mapped[int | None] = mapped_column(BigInteger)
    phase: Mapped[str | None] = mapped_column(String(128))
    snakemake_jobid: Mapped[str | None] = mapped_column(String(128))
    sample_id: Mapped[str | None] = mapped_column(String(128))
    family_id: Mapped[str | None] = mapped_column(String(128))
    wildcards_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    layer: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    log_paths_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RunStageState(Base):
    __tablename__ = "run_stage_state"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "attempt", "stage_code", name="uq_run_stage_state_identity"
        ),
        Index("ix_run_stage_state_analysis", "analysis_id", "attempt"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_code: Mapped[str] = mapped_column(String(64), nullable=False)
    step_number: Mapped[int | None] = mapped_column(Integer)
    stage_label: Mapped[str] = mapped_column(String(128), nullable=False)
    stage_status: Mapped[str] = mapped_column(String(64), nullable=False)
    progress_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    progress_percent: Mapped[int | None] = mapped_column(Integer)
    completed_units: Mapped[int | None] = mapped_column(BigInteger)
    total_units: Mapped[int | None] = mapped_column(BigInteger)
    unit: Mapped[str | None] = mapped_column(String(32))
    current_item: Mapped[str | None] = mapped_column(Text)
    speed_bps: Mapped[int | None] = mapped_column(BigInteger)
    eta_seconds: Mapped[int | None] = mapped_column(BigInteger)
    progress_source: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    evidence_key: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class WgsStageExecution(Base):
    __tablename__ = "wgs_stage_execution"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "attempt", "stage_code", "generation",
            name="uq_wgs_stage_execution_generation",
        ),
        Index("ix_wgs_stage_execution_current", "analysis_id", "attempt", "stage_code", "generation"),
        Index("ix_wgs_stage_execution_status", "stage_code", "status"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_code: Mapped[str] = mapped_column(String(64), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    release_id: Mapped[str] = mapped_column(String(128), nullable=False)
    predecessor_execution_id: Mapped[str | None] = mapped_column(String(128))
    predecessor_generation: Mapped[int | None] = mapped_column(Integer)
    predecessor_receipt_hash: Mapped[str | None] = mapped_column(String(64))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_type: Mapped[str | None] = mapped_column(String(64))
    evidence_key: Mapped[str | None] = mapped_column(Text)
    receipt_hash: Mapped[str | None] = mapped_column(String(64))
    terminal_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class WgsSubmissionDraft(Base):
    __tablename__ = "wgs_submission_draft"
    __table_args__ = (
        Index("ix_wgs_submission_draft_owner_status", "owner_username", "status"),
        Index("ix_wgs_submission_draft_expiry", "expires_at"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    draft_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    owner_username: Mapped[str] = mapped_column(String(128), nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    sequencing_batch: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_batch: Mapped[str] = mapped_column(String(128), nullable=False)
    fastq_root_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fastq_path: Mapped[str] = mapped_column(Text, nullable=False)
    use_reference: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    source_fingerprint: Mapped[str | None] = mapped_column(String(64))
    preview_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resolved_config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    private_workdir: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_run.analysis_id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlatformResourceSnapshot(Base):
    __tablename__ = "platform_resource_snapshot"
    __table_args__ = (Index("ix_platform_resource_snapshot_type", "resource_type"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    resource_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="stale")
    current_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    history_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class KubernetesWorkload(Base):
    __tablename__ = "kubernetes_workload"
    __table_args__ = (
        UniqueConstraint("analysis_id", "attempt", "pod_hash", name="uq_k8s_workload_identity"),
        Index("ix_k8s_workload_analysis", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[str] = mapped_column(String(256), nullable=False)
    pod_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    job_name: Mapped[str | None] = mapped_column(String(256))
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(256))
    exit_code: Mapped[int | None] = mapped_column(Integer)
    image_id: Mapped[str | None] = mapped_column(Text)
    resources_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_path: Mapped[str | None] = mapped_column(Text)
    resource_version: Mapped[str | None] = mapped_column(String(128))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    node_name: Mapped[str | None] = mapped_column(String(256))
    message: Mapped[str | None] = mapped_column(Text)
    job_status_json: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class EvidenceCursor(Base):
    __tablename__ = "evidence_cursor"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "attempt",
            "relative_path",
            name="uq_evidence_cursor_file",
        ),
        Index("ix_evidence_cursor_analysis", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_identity: Mapped[str | None] = mapped_column(String(256))
    byte_offset: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    line_number: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    observed_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    observed_mtime_ns: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class ObserverRunState(Base):
    __tablename__ = "observer_run_state"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "attempt", name="uq_observer_run_state_attempt"
        ),
        Index("ix_observer_run_state_analysis", "analysis_id"),
        Index("ix_observer_run_state_lifecycle", "lifecycle_status"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    pipeline_release_id: Mapped[str] = mapped_column(String(256), nullable=False)
    run_label: Mapped[str] = mapped_column(String(128), nullable=False)
    relative_evidence_path: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="stopped"
    )
    monitoring_health: Mapped[str] = mapped_column(
        String(32), nullable=False, default="healthy"
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    @property
    def status(self) -> str:
        """Compatibility alias for callers migrating to monitoring_health."""
        return self.monitoring_health

    @status.setter
    def status(self, value: str) -> None:
        self.monitoring_health = value
