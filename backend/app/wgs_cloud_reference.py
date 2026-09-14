"""Opt-in read-only cloud journal projection. No execution or Sample writes."""
from dataclasses import dataclass
from pathlib import Path
import re
from uuid import UUID

from sqlalchemy import select, func
from app.models import (AnalysisRun, WgsStageExecution, SampleReferenceSource,
    SampleReference, SampleReferenceSnapshot, SampleReferenceOperation, SampleReferenceHistory, utc_now)
from app.sample_reference_reader import SourceError, require, opaque, canonical, digest
from app.sample_reference_service import _source_lock, record_error
from app.wgs_cloud_consumer import (CloudRequestIdentity, CloudConsumerError,
    PINNED_PRODUCER_COMMIT, read_live_pending, read_cloud_execution)


@dataclass(frozen=True)
class CloudSource:
    source_id: str
    scope_id: str
    project_root: Path
    executions: tuple[CloudRequestIdentity, ...] = ()
    source_type: str = "wgs_cloud_only"

    def __post_init__(self):
        require(type(self.source_id) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}",self.source_id),"registration_invalid")
        require(type(self.scope_id) is str and 0<len(self.scope_id.strip())<=256,"registration_invalid")
        require(isinstance(self.project_root,Path) and self.project_root.is_absolute() and ".." not in self.project_root.parts,"registration_invalid")
        require(self.source_type=="wgs_cloud_only" and type(self.executions) is tuple and len(self.executions)<=100,"registration_invalid")
        keys=set()
        for e in self.executions:
            require(isinstance(e,CloudRequestIdentity) and e.producer_commit==PINNED_PRODUCER_COMMIT,"registration_invalid")
            require(all(type(v) is str and 0<len(v.strip())<=128 for v in (e.analysis_id,e.execution_id)),"registration_invalid")
            require(type(e.attempt) is int and e.attempt>0 and type(e.generation) is int and e.generation>0,"registration_invalid")
            require(type(e.request_hash) is str and re.fullmatch(r"[0-9a-f]{64}",e.request_hash),"registration_invalid")
            require(e.execution_id not in keys,"registration_invalid"); keys.add(e.execution_id)


def _reserve(factory, source, secret):
    require(isinstance(secret,bytes) and len(secret)>=32,"identity_secret_invalid")
    registration=opaque(secret,source.scope_id,"cloud-registration",[source.source_id,str(source.project_root),PINNED_PRODUCER_COMMIT])
    with factory() as session:
        _source_lock(session,source.source_id)
        state=session.scalar(select(SampleReferenceSource).where(SampleReferenceSource.source_id==source.source_id).with_for_update())
        if state is None:
            state=SampleReferenceSource(source_id=source.source_id,source_type=source.source_type,registration_key=registration)
            session.add(state); session.flush()
        require(state.source_type==source.source_type and state.registration_key==registration,"registration_mismatch")
        token=state.next_generation; state.next_generation=token+1; state.latest_reserved_generation=token
        session.commit()
        return token


def _state(session,source,token):
    _source_lock(session,source.source_id)
    state=session.scalar(select(SampleReferenceSource).where(SampleReferenceSource.source_id==source.source_id).with_for_update())
    require(state is not None,"registration_mismatch")
    return state if state.latest_reserved_generation==token else None


def _apply_live(factory,source,token,live):
    with factory() as session:
        state=_state(session,source,token)
        if state is None: return
        now=utc_now(); content=digest(canonical(live["records"]))
        records={r.record_key:r for r in session.scalars(select(SampleReference).where(SampleReference.source_id==source.source_id))}
        current={}; counts={}
        for row in live["records"]:
            current[row["record_key"]]=row
            counts[row["record_key"]]=counts.get(row["record_key"],0)+1
        for key,row in current.items():
            record=records.get(key)
            if record is None:
                record=SampleReference(source_id=source.source_id,record_key=key); session.add(record)
            for name in ("sample_id","family_id","sequencing_batch","analysis_batch","data_id","reason_code","reason_codes"):
                setattr(record,name,row[name])
            record.pending=True; record.present_in_latest_complete=True
            record.content_version=digest(canonical(row)); record.last_good_generation=token
            record.last_good_at=now; record.updated_at=now
            record.needs_review=counts[key]>1
            record.conflict_reason="duplicate_pending_identity" if counts[key]>1 else None
        for key,record in records.items():
            if key not in current:
                record.pending=False; record.present_in_latest_complete=False
                record.reason_code=None; record.reason_codes=[]; record.updated_at=now
        if state.last_good_content_hash!=content:
            session.add(SampleReferenceSnapshot(source_id=source.source_id,generation=token,content_hash=content,
                snapshot_hash=content,status="ready",outcome="applied",row_count=live["row_count"],checked_at=now))
        state.latest_applied_generation=token; state.last_good_generation=token
        state.last_good_content_hash=content; state.last_good_at=now
        session.commit()


def _apply_history(factory,source,token,value,secret):
    # Stage readiness may advance; immutable selected/pending identity cannot.
    immutable={k:value[k] for k in ("producer_commit","analysis_id","attempt","generation","execution_id","request_hash","selected","historical_pending")}
    content=digest(canonical(immutable))
    key=opaque(secret,source.scope_id,"cloud-execution",value["execution_id"])
    with factory() as session:
        state=_state(session,source,token)
        if state is None: return
        op=session.scalar(select(SampleReferenceOperation).where(SampleReferenceOperation.source_id==source.source_id,SampleReferenceOperation.execution_key==key))
        if op is not None: require(op.commit_hash==content,"operation_conflict")
        run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==value["analysis_id"],AnalysisRun.pipeline_name=="wgs"))
        if op is None:
            seq=(session.scalar(select(func.max(SampleReferenceOperation.sequence)).where(SampleReferenceOperation.source_id==source.source_id)) or 0)+1
            op=SampleReferenceOperation(source_id=source.source_id,operation_id=str(UUID(key[:32])),sequence=seq,
                intent_hash=value["request_hash"],commit_hash=content,pending_hash=digest(canonical(value["historical_pending"])),
                execution_key=key,request_hash=value["request_hash"],previous_operation_id=None,mode="cce",
                cloud_key=opaque(secret,source.scope_id,"cloud-analysis",value["analysis_id"]),analysis_id=run.analysis_id if run else None,
                attempt=value["attempt"],generation=value["generation"],producer_commit=value["producer_commit"],
                completed_at=utc_now(),logical_time_source="database_imported_at")
            session.add(op); session.flush()
            for role,rows in (("decision_selected",value["selected"]),("historical_pending",value["historical_pending"])):
                for n,row in enumerate(rows,1):
                    session.add(SampleReferenceHistory(operation_pk=op.id,role=role,row_number=n,record_key=row["record_key"],
                        safe_json={k:v for k,v in row.items() if k!="record_key"}))
        elif run and op.analysis_id is None:
            op.analysis_id=run.analysis_id
        stage=session.scalar(select(WgsStageExecution).where(WgsStageExecution.execution_id==value["execution_id"],
            WgsStageExecution.analysis_id==value["analysis_id"],WgsStageExecution.attempt==value["attempt"],
            WgsStageExecution.generation==value["generation"],WgsStageExecution.request_hash==value["request_hash"],
            WgsStageExecution.stage_code=="prepare_analysis"))
        metadata=session.scalar(select(SampleReferenceHistory).where(SampleReferenceHistory.operation_pk==op.id,SampleReferenceHistory.role=="cloud_readiness"))
        if metadata is None:
            metadata=SampleReferenceHistory(operation_pk=op.id,role="cloud_readiness",row_number=1,record_key=key,safe_json={})
            session.add(metadata)
        old_status=metadata.safe_json.get("stage_status")
        require(old_status not in ("artifact_ready","no_analysis_needed") or old_status==value["stage_status"],"operation_conflict")
        metadata.safe_json={"stage_status":value["stage_status"],"stage_execution_pk":stage.id if stage else None,
            "execution_id_sha256":digest(value["execution_id"].encode()),
            "analysis_state":"not_started","source_kind":"synthetic","execution_allowed":False}
        session.commit()


def reconcile_cloud_source(factory,source,secret):
    try: token=_reserve(factory,source,secret)
    except SourceError: return "error"
    except Exception: return "database_unavailable"
    errors=[]
    try:
        live=read_live_pending(source.project_root,identity_secret=secret,scope_id=source.scope_id)
        if live["status"]=="available": _apply_live(factory,source,token,live)
        else: errors.append("live_unavailable")
        for expected in source.executions:
            try:
                value=read_cloud_execution(source.project_root,expected,identity_secret=secret,scope_id=source.scope_id)
                _apply_history(factory,source,token,value,secret)
            except (SourceError,CloudConsumerError) as exc: errors.append(exc.code)
        if errors:
            record_error(factory,source,token,errors[0]); return "error"
        with factory() as session:
            state=_state(session,source,token)
            if state is None: return "superseded"
            state.sync_status="ready"; state.sync_reason=None; state.last_checked_at=utc_now(); state.updated_at=state.last_checked_at
            session.commit()
        return "ready"
    except (SourceError,CloudConsumerError) as exc:
        try: record_error(factory,source,token,exc.code)
        except Exception: return "database_unavailable"
        return "error"
    except Exception: return "database_unavailable"


def readiness(session,op):
    """Read-only informational gate. This result is NEVER execution authority."""
    metadata=session.scalar(select(SampleReferenceHistory).where(SampleReferenceHistory.operation_pk==op.id,SampleReferenceHistory.role=="cloud_readiness"))
    if metadata is None: return None
    data=metadata.safe_json
    run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==op.analysis_id)) if op.analysis_id else None
    stage=session.get(WgsStageExecution,data["stage_execution_pk"]) if data.get("stage_execution_pk") else None
    latest=session.scalar(select(func.max(WgsStageExecution.generation)).where(WgsStageExecution.analysis_id==op.analysis_id,
        WgsStageExecution.attempt==op.attempt,WgsStageExecution.stage_code=="prepare_analysis")) if run else None
    matches=bool(run and stage and run.pipeline_name=="wgs" and run.attempt==op.attempt
        and stage.analysis_id==op.analysis_id and stage.attempt==op.attempt and stage.stage_code=="prepare_analysis"
        and digest(stage.execution_id.encode())==data.get("execution_id_sha256")
        and stage.generation==op.generation==latest and stage.request_hash==op.request_hash)
    return {"stage_status":data["stage_status"],"artifact_ready":data["stage_status"]=="artifact_ready",
        "current_identity_matches":matches,"analysis_state":"not_started","execution_allowed":False,"reason":"synthetic_execution_denied"}
