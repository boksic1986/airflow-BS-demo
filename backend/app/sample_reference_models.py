"""Exact inactive 0020 tables plus additive 0023 journal projection fields."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base, ID_TYPE, utc_now

class SampleReferenceSource(Base):
    __tablename__ = "sample_reference_source"
    __table_args__ = (Index("ix_sample_reference_source_type_status", "source_type", "sync_status"),)
    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    next_generation: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1", default=1)
    latest_reserved_generation: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    latest_applied_generation: Mapped[int | None] = mapped_column(Integer)
    last_good_generation: Mapped[int | None] = mapped_column(Integer)
    last_good_content_hash: Mapped[str | None] = mapped_column(String(64))
    last_good_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="never", server_default="never")
    sync_reason: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    # 0023: stable registration/secret fence; no raw scope or configured path.
    registration_key: Mapped[str | None] = mapped_column(String(64))

class SampleReferenceSnapshot(Base):
    __tablename__ = "sample_reference_snapshot"
    __table_args__ = (UniqueConstraint("source_id","generation",name="uq_sample_reference_snapshot_generation"),
                     Index("ix_sample_reference_snapshot_source_status","source_id","status"))
    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(128), ForeignKey("sample_reference_source.source_id",ondelete="RESTRICT"),nullable=False)
    generation: Mapped[int] = mapped_column(Integer,nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32),nullable=False)
    diagnostic_code: Mapped[str | None] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer,nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64),nullable=False)
    outcome: Mapped[str] = mapped_column(String(16),nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)

class SampleReference(Base):
    __tablename__ = "sample_reference"
    __table_args__ = (UniqueConstraint("source_id","record_key",name="uq_sample_reference_source_record"),
        Index("ix_sample_reference_sample_source","sample_id","source_id","record_key"),
        Index("ix_sample_reference_family","family_id"),Index("ix_sample_reference_order","order_number_masked"),
        Index("ix_sample_reference_batches","sequencing_batch","analysis_batch"),
        Index("ix_sample_reference_membership","present_in_latest_complete","pending"))
    id: Mapped[int] = mapped_column(ID_TYPE,primary_key=True,autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(128),ForeignKey("sample_reference_source.source_id",ondelete="RESTRICT"),nullable=False)
    record_key: Mapped[str] = mapped_column(String(64),nullable=False)
    sample_id: Mapped[str] = mapped_column(String(128),nullable=False)
    family_id: Mapped[str | None] = mapped_column(String(128))
    order_number_masked: Mapped[str | None] = mapped_column(String(32))
    sequencing_batch: Mapped[str | None] = mapped_column(String(128))
    analysis_batch: Mapped[str | None] = mapped_column(String(128))
    data_id: Mapped[str | None] = mapped_column(String(128))
    pending: Mapped[bool] = mapped_column(Boolean,nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    content_version: Mapped[str] = mapped_column(String(64),nullable=False)
    last_good_generation: Mapped[int] = mapped_column(Integer,nullable=False)
    last_good_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    present_in_latest_complete: Mapped[bool] = mapped_column(Boolean,nullable=False,server_default=text("true"),default=True)
    needs_review: Mapped[bool] = mapped_column(Boolean,nullable=False,server_default=text("false"),default=False)
    conflict_reason: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
    reason_codes: Mapped[list] = mapped_column(JSON,nullable=False,default=list,server_default="[]")
    origin_batch: Mapped[str | None] = mapped_column(String(128))
    destination_batch: Mapped[str | None] = mapped_column(String(128))

class SampleReferenceOperation(Base):
    __tablename__ = "sample_reference_operation"
    __table_args__ = (UniqueConstraint("source_id","operation_id",name="uq_reference_operation_id"),
        UniqueConstraint("source_id","sequence",name="uq_reference_operation_sequence"),
        UniqueConstraint("source_id","execution_key",name="uq_reference_operation_execution"))
    id: Mapped[int] = mapped_column(ID_TYPE,primary_key=True,autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(128),ForeignKey("sample_reference_source.source_id",ondelete="RESTRICT"),nullable=False)
    operation_id: Mapped[str] = mapped_column(String(36),nullable=False)
    sequence: Mapped[int] = mapped_column(Integer,nullable=False)
    intent_hash: Mapped[str] = mapped_column(String(64),nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(64),nullable=False)
    pending_hash: Mapped[str] = mapped_column(String(64),nullable=False)
    execution_key: Mapped[str] = mapped_column(String(64),nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64),nullable=False)
    previous_operation_id: Mapped[str | None] = mapped_column(String(36))
    mode: Mapped[str] = mapped_column(String(16),nullable=False)
    cloud_key: Mapped[str | None] = mapped_column(String(64))
    analysis_id: Mapped[str | None] = mapped_column(String(128),ForeignKey("analysis_run.analysis_id",ondelete="RESTRICT"))
    attempt: Mapped[int | None] = mapped_column(Integer)
    generation: Mapped[int | None] = mapped_column(Integer)
    producer_commit: Mapped[str] = mapped_column(String(40),nullable=False)
    logical_time_source: Mapped[str | None] = mapped_column(String(64))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)

class SampleReferenceHistory(Base):
    __tablename__ = "sample_reference_history"
    __table_args__ = (UniqueConstraint("operation_pk","role","row_number",name="uq_reference_history_row"),
                     Index("ix_reference_history_key","record_key","resolved_key"))
    id: Mapped[int] = mapped_column(ID_TYPE,primary_key=True,autoincrement=True)
    operation_pk: Mapped[int] = mapped_column(ID_TYPE,ForeignKey("sample_reference_operation.id",ondelete="RESTRICT"),nullable=False)
    role: Mapped[str] = mapped_column(String(32),nullable=False)
    row_number: Mapped[int] = mapped_column(Integer,nullable=False)
    record_key: Mapped[str] = mapped_column(String(64),nullable=False)
    resolved_key: Mapped[str | None] = mapped_column(String(64))
    safe_json: Mapped[dict] = mapped_column(JSON,nullable=False)
