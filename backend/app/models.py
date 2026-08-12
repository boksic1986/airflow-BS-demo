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

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False, unique=True)
    ready_mtime_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class TransferJob(Base):
    __tablename__ = "transfer_job"
    __table_args__ = (Index("ix_transfer_job_analysis", "analysis_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_path: Mapped[str | None] = mapped_column(Text)
    receipt_path: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


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
    sample_id: Mapped[str | None] = mapped_column(String(128))
    layer: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class MasterSlot(Base):
    __tablename__ = "master_slot"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    slot_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    analysis_id: Mapped[str | None] = mapped_column(String(128))
    attempt: Mapped[int | None] = mapped_column(Integer)
    leased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
