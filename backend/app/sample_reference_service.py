"""Recovery-safe database projection. File authority never receives feedback."""
from datetime import datetime
import hashlib
import os
from threading import Lock, Thread
from sqlalchemy import select, text
from app.models import (AnalysisRun, SampleReference, SampleReferenceSource, SampleReferenceSnapshot,
                        SampleReferenceOperation, SampleReferenceHistory, utc_now)
from app.sample_reference_reader import SourceError, canonical, digest, opaque, read_source, require

def _source_lock(session, source_id):
    # The same per-source transaction fence protects reservation, apply and errors.
    # No database operation takes place while the file reader holds SH flock.
    if session.bind.dialect.name == "postgresql":
        # Applies also to injected test factories. Never wait indefinitely for
        # advisory or row locks; statement timeout bounds the remaining SQL.
        session.execute(text("SET LOCAL statement_timeout = '15s'"))
        session.execute(text("SET LOCAL lock_timeout = '500ms'"))
        key=int.from_bytes(hashlib.sha256(("sample-reference:"+source_id).encode()).digest()[:8],"big",signed=True)
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"),{"key":key})
    elif session.bind.dialect.name == "sqlite":
        session.execute(text("BEGIN IMMEDIATE"))
    else:
        raise SourceError("database_unsupported")

def reserve_check(factory, source, secret):
    with factory() as session:
        _source_lock(session,source.source_id)
        state=session.scalar(select(SampleReferenceSource).where(SampleReferenceSource.source_id==source.source_id).with_for_update())
        registration=opaque(secret,source.scope_id,"registration",source.source_id)
        if state is None:
            state=SampleReferenceSource(source_id=source.source_id,source_type="wgs_shared_handoff",registration_key=registration)
            session.add(state); session.flush()
        token=state.next_generation; state.next_generation=token+1; state.latest_reserved_generation=token
        if state.registration_key!=registration:
            state.sync_status="error"; state.sync_reason="registration_mismatch"; state.last_checked_at=utc_now()
            state.updated_at=state.last_checked_at; session.commit()
            raise SourceError("registration_mismatch")
        state.updated_at=utc_now(); session.commit()
        return token

def record_error(factory, source, token, code):
    with factory() as session:
        _source_lock(session,source.source_id)
        state=session.scalar(select(SampleReferenceSource).where(SampleReferenceSource.source_id==source.source_id).with_for_update())
        if state and state.latest_reserved_generation==token:
            state.sync_status="error"; state.sync_reason=code
            state.last_checked_at=utc_now(); state.updated_at=state.last_checked_at
        session.commit()

def apply_projection(factory, source, token, projection):
    with factory() as session:
        _source_lock(session,source.source_id)
        state=session.scalar(select(SampleReferenceSource).where(SampleReferenceSource.source_id==source.source_id).with_for_update())
        require(state is not None,"registration_mismatch")
        if token!=state.latest_reserved_generation:
            return "superseded"
        applied=state.latest_applied_generation or 0
        require(projection["sequence"]>=applied,"stale_source_version")
        if projection["sequence"]==applied:
            require(projection["head_hash"]==state.last_good_content_hash,"operation_conflict")
        existing={op.operation_id:op for op in session.scalars(select(SampleReferenceOperation).where(SampleReferenceOperation.source_id==source.source_id))}
        require(set(existing).issubset({x["operation_id"] for x in projection["operations"]}),"chain_invalid")
        cloud_versions={}; executions={}; consumed=set()
        for op in projection["operations"]:
            require(op["execution_key"] not in executions,"execution_conflict")
            executions[op["execution_key"]]=op["request_hash"]
            if op["cloud_key"]:
                version=(op["attempt"],op["generation"])
                require(op["cloud_key"] not in cloud_versions or version>cloud_versions[op["cloud_key"]],"stale_cloud_generation")
                cloud_versions[op["cloud_key"]]=version
            for link in op["links"]:
                if link["kind"]=="consumed":
                    require(link["record_key"] not in consumed,"consumed_identity_replay")
                    consumed.add(link["record_key"])
            previous=existing.get(op["operation_id"])
            if previous:
                require(previous.intent_hash==op["intent_hash"] and previous.commit_hash==op["commit_hash"]
                        and previous.sequence==op["sequence"],"operation_conflict")
                continue
            require(op["sequence"]>applied,"operation_conflict")
            # A public run link is optional and must bind a retained WGS run.
            run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==op["cloud_analysis_id"],
                AnalysisRun.pipeline_name=="wgs",AnalysisRun.attempt>=op["attempt"])) if op["cloud_analysis_id"] else None
            fields={k:op[k] for k in ("operation_id","sequence","intent_hash","commit_hash","pending_hash","execution_key",
                "request_hash","previous_operation_id","mode","cloud_key","attempt","generation","producer_commit")}
            stored=SampleReferenceOperation(source_id=source.source_id,**fields,analysis_id=run.analysis_id if run else None,
                # Keep the published 0023 non-null legacy column populated for
                # storage compatibility. Provenance is carried separately and
                # the API never exposes this value as actual completion time.
                completed_at=datetime.fromisoformat(op["logical_transaction_at"].replace("Z","+00:00")),
                logical_time_source="authenticated_intent.created_at")
            session.add(stored); session.flush()
            for role,rows in op["tables"].items():
                for row in rows:
                    session.add(SampleReferenceHistory(operation_pk=stored.id,role=role,row_number=row["row_number"],
                        record_key=row["record_key"],safe_json={**{k:v for k,v in row.items() if k not in ("record_key","row_number")},
                            "origin_batch":row["source_analysis_batch"],"destination_batch":row["target_analysis_batch"]}))
            for number,link in enumerate(op["links"],1):
                session.add(SampleReferenceHistory(operation_pk=stored.id,role="decision_"+link["kind"],row_number=number,
                    record_key=link["record_key"],resolved_key=link["resolved_key"],
                    safe_json={k:link[k] for k in ("origin_batch","destination_batch","sample_id","family_id","reason_codes")}))
            session.add(SampleReferenceSnapshot(source_id=source.source_id,generation=op["sequence"],content_hash=op["pending_hash"],
                status="ready",row_count=len(op["tables"]["pending_after"]),snapshot_hash=op["intent_hash"],outcome="applied",checked_at=utc_now()))
        now=utc_now()
        records={r.record_key:r for r in session.scalars(select(SampleReference).where(SampleReference.source_id==source.source_id))}
        # Keep immutable full row history, including duplicate identities. Current
        # summary keys remain unique; duplicates are explicitly flagged for review.
        all_rows={}
        for op in projection["operations"]:
            for role in ("source","pending_before","selected","pending_current","pending_after"):
                for row in op["tables"][role]: all_rows[row["record_key"]]=row
        current={}; counts={}
        for row in projection["operations"][-1]["tables"]["pending_after"]:
            current[row["record_key"]]=row; counts[row["record_key"]]=counts.get(row["record_key"],0)+1
        all_rows.update(current)
        for key,row in all_rows.items():
            record=records.get(key)
            if record is None:
                record=SampleReference(source_id=source.source_id,record_key=key); session.add(record)
            for name in ("sample_id","family_id","sequencing_batch","analysis_batch","data_id"):
                setattr(record,name,row[name])
            record.pending=key in current; record.present_in_latest_complete=key in current
            record.reason_code=row["reason_code"] if record.pending else None
            record.reason_codes=row["reason_codes"] if record.pending else []
            record.origin_batch=row["source_analysis_batch"]; record.destination_batch=row["target_analysis_batch"]
            record.content_version=digest(canonical(row)); record.last_good_generation=projection["sequence"]
            record.last_good_at=now; record.updated_at=now
            record.needs_review=counts.get(key,0)>1
            record.conflict_reason="duplicate_pending_identity" if record.needs_review else None
        for key,record in records.items():
            if key not in all_rows:
                record.pending=False; record.present_in_latest_complete=False
        state.latest_applied_generation=projection["sequence"]; state.last_good_generation=projection["sequence"]
        state.last_good_content_hash=projection["head_hash"]; state.last_good_at=now
        state.last_checked_at=now; state.updated_at=now; state.sync_status="ready"; state.sync_reason=None
        session.commit()
    return "ready"

def reconcile_source(factory, source, secret):
    try: token=reserve_check(factory,source,secret)
    except SourceError: return "error"
    except Exception: return "database_unavailable"
    try:
        projection=read_source(source,secret)
        return apply_projection(factory,source,token,projection)
    except SourceError as exc:
        try: record_error(factory,source,token,exc.code)
        except Exception: return "database_unavailable"
        return "error"
    except Exception:
        # A failed DB transaction (including timeout) cannot reliably persist
        # its own diagnostic. Do not reacquire the contended source lock.
        return "database_unavailable"

def reconcile_registered(factory, config):
    if not config.enabled: return {}
    from app.wgs_cloud_reference import CloudSource, reconcile_cloud_source
    from app.wgs_file_reference import FileSource, reconcile_file_source
    def handler(source):
        if isinstance(source,FileSource): return reconcile_file_source
        if isinstance(source,CloudSource): return reconcile_cloud_source
        return reconcile_source
    return {source.source_id:handler(source)(factory,source,config.secret) for source in config.sources}

def best_effort_prepare_sync(factory=None):
    # Its own transactions, called ONLY after the successful receipt commit.
    # Never propagate projection/registration/database errors to execution.
    try:
        from app.sample_reference_config import load_reference_config
        config=load_reference_config()
        if not config.enabled: return {}
        if factory is None:
            from app.db import get_reference_sessionmaker
            factory=get_reference_sessionmaker()
        return reconcile_registered(factory,config)
    except Exception:
        return {"status":"projection_unavailable"}


_prepare_sync_lock = Lock()
_prepare_sync_thread = None
_prepare_sync_pending = False


def _run_prepare_sync():
    global _prepare_sync_thread, _prepare_sync_pending
    while True:
        with _prepare_sync_lock:
            if not _prepare_sync_pending:
                _prepare_sync_thread = None
                return
            _prepare_sync_pending = False
        # No notification lock is held during configuration, file or DB work.
        # A hung pass occupies at most this one daemon thread, never a request.
        try:
            best_effort_prepare_sync()
        except Exception:
            pass  # Independent 60-second worker is the durable recovery path.


def notify_prepare_sync():
    """Nonblocking, process-local hint; at most one active and one pending pass.

    No file/config/DB reads on the request thread. Contention/start failure may
    drop a hint; no durable queue is needed because the independent worker polls.
    """
    global _prepare_sync_thread, _prepare_sync_pending
    if os.getenv("SAMPLE_REFERENCE_ENABLED", "false").lower() not in ("true", "1", "yes"):
        return False
    if not _prepare_sync_lock.acquire(blocking=False):
        return False
    try:
        _prepare_sync_pending = True
        if _prepare_sync_thread is None:
            _prepare_sync_thread = Thread(target=_run_prepare_sync, name="sample-reference-prepare-hint", daemon=True)
            try:
                _prepare_sync_thread.start()
            except Exception:
                _prepare_sync_thread = None
                _prepare_sync_pending = False
                return False
        return True
    finally:
        _prepare_sync_lock.release()
