"""Original WGS pending file -> read-only DB projection; no producer protocol."""
import csv
import io
import os
from dataclasses import dataclass
from pathlib import Path
import re
import json
import stat
from collections import Counter
from uuid import UUID

from sqlalchemy import select, func
from app.models import (AnalysisRun, SampleReference, SampleReferenceSource, SampleReferenceSnapshot,
    SampleReferenceOperation, SampleReferenceHistory, utc_now)
from app.sample_reference_reader import Tree, SourceError, require, opaque, canonical, digest, REASONS, MAX_ROWS
from app.sample_reference_service import _source_lock, record_error

PENDING_PATH="prepare/pending_samples.tsv"
SAFE_COLUMNS={"sample_id":"样本编号","sequencing_batch":"上机批次","data_id":"数据编号",
    "analysis_batch":"分析批次","family_id":"家系编号"}


@dataclass(frozen=True)
class FileSource:
    source_id: str
    scope_id: str
    project_root: Path
    source_type: str = "wgs_files"
    runtime_root: Path | None = None

    def __post_init__(self):
        require(type(self.source_id) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}",self.source_id),"registration_invalid")
        require(type(self.scope_id) is str and 0<len(self.scope_id.strip())<=256,"registration_invalid")
        require(isinstance(self.project_root,Path) and self.project_root.is_absolute() and ".." not in self.project_root.parts,"registration_invalid")
        require(self.source_type=="wgs_files","registration_invalid")
        require(self.runtime_root is None or (isinstance(self.runtime_root,Path) and self.runtime_root.is_absolute()
            and ".." not in self.runtime_root.parts),"registration_invalid")


def _stamp(info):
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink)


def project_rows(raw,source,secret,*,pending=True):
    """Shared exact full identity for current pending and retained final TSV."""
    require(isinstance(secret,bytes) and len(secret)>=32,"identity_secret_invalid")
    require(bool(raw) and raw.endswith(b"\n"),"source_incomplete")
    rows=csv.reader(io.StringIO(raw.decode("utf-8-sig"),newline=""),delimiter="\t",strict=True)
    header=next(rows)
    require(0<len(header)<=256 and all(header) and len(set(header))==len(header)
        and {"样本编号","上机批次","数据编号"}.issubset(header),"source_invalid")
    result=[]
    for fields in rows:
        require(len(result)<MAX_ROWS and len(fields)==len(header),"source_invalid")
        row=dict(zip(header,fields))
        safe={key:row.get(column,"").strip() for key,column in SAFE_COLUMNS.items()}
        require(bool(safe["sample_id"]) and all(len(v)<=128 and not any(c in v for c in "\r\n\t\x00") for v in safe.values()),"source_invalid")
        group=None
        for column,prefix in (("analysisTaskId","task:"),("订单编号","order:")):
            value=row.get(column,"").strip()
            if value not in ("", ".", "None", "nan"):
                group=prefix+value; break
        identity=[group or "sample:"+safe["sample_id"],safe["sample_id"],safe["sequencing_batch"],safe["data_id"]]
        code=(row.get("reason_code","").strip() or row.get("pending_reason","").strip())
        if "缺少上机批次" in code:
            code="sequencing_batch_missing"
        code=(code if code in REASONS else "pending_reason_unclassified") if pending else None
        origin={}
        if pending:
            batch=row.get("source_analysis_batch","").strip() or safe["analysis_batch"]
            require(len(batch)<=128 and not any(c in batch for c in "\r\n\t\x00"),"source_invalid")
            origin["origin_batch"]=batch or None
        result.append({**safe,"record_key":opaque(secret,source.scope_id,"identity",identity),
            "reason_code":code,"reason_codes":[code] if code else [],**origin})
    return result


def read_pending(source,secret):
    """Optimistic stable snapshot, with no write-side locking requirement."""
    require(isinstance(secret,bytes) and len(secret)>=32,"identity_secret_invalid")
    tree=None
    try:
        tree=Tree(source.project_root)
        before=tree.info(PENDING_PATH)
        raw=tree.read(PENDING_PATH)  # bounded, nofollow, fstat before/after read
        require(_stamp(before)==_stamp(tree.info(PENDING_PATH)),"source_changed")
        # Also detect replacement of the registered root during the read.
        fresh=Tree(source.project_root)
        try:
            require((os.fstat(tree.fd).st_dev,os.fstat(tree.fd).st_ino)==
                    (os.fstat(fresh.fd).st_dev,os.fstat(fresh.fd).st_ino),"source_changed")
        finally: fresh.close()
        return project_rows(raw,source,secret)
    except SourceError: raise
    except Exception: raise SourceError("source_unavailable") from None
    finally:
        if tree: tree.close()


def _reserve(factory,source,secret):
    require(isinstance(secret,bytes) and len(secret)>=32,"identity_secret_invalid")
    key=opaque(secret,source.scope_id,"file-registration",[source.source_id,str(source.project_root)])
    with factory() as session:
        _source_lock(session,source.source_id)
        state=session.scalar(select(SampleReferenceSource).where(SampleReferenceSource.source_id==source.source_id).with_for_update())
        if state is None:
            state=SampleReferenceSource(source_id=source.source_id,source_type=source.source_type,registration_key=key)
            session.add(state); session.flush()
        require(state.source_type==source.source_type and state.registration_key==key,"registration_mismatch")
        token=state.next_generation; state.next_generation=token+1; state.latest_reserved_generation=token
        session.commit()
        return token


def _apply(factory,source,token,rows):
    with factory() as session:
        _source_lock(session,source.source_id)
        state=session.scalar(select(SampleReferenceSource).where(SampleReferenceSource.source_id==source.source_id).with_for_update())
        require(state is not None,"registration_mismatch")
        if state.latest_reserved_generation!=token: return "superseded"
        now=utc_now(); content=digest(canonical(rows))
        records={r.record_key:r for r in session.scalars(select(SampleReference).where(SampleReference.source_id==source.source_id))}
        current={}; counts={}
        for row in rows:
            current[row["record_key"]]=row
            counts[row["record_key"]]=counts.get(row["record_key"],0)+1
        for key,row in current.items():
            record=records.get(key)
            if record is None:
                record=SampleReference(source_id=source.source_id,record_key=key); session.add(record)
            for name in (*SAFE_COLUMNS,"reason_code","reason_codes"): setattr(record,name,row[name])
            record.origin_batch=row["origin_batch"]
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
                snapshot_hash=content,status="ready",outcome="applied",row_count=len(rows),checked_at=now))
        state.latest_applied_generation=token; state.last_good_generation=token
        state.last_good_content_hash=content; state.last_good_at=now; state.last_checked_at=now; state.updated_at=now
        state.sync_status="ready"; state.sync_reason=None
        session.commit()
    return "ready"


def history_start():
    analysis=os.getenv("SAMPLE_REFERENCE_HISTORY_START_ANALYSIS_ID","")
    if not analysis: return None
    require(re.fullmatch(r"WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}",analysis),"registration_invalid")
    attempt=os.getenv("SAMPLE_REFERENCE_HISTORY_START_ATTEMPT","1")
    require(re.fullmatch(r"[1-9][0-9]{0,5}",attempt),"registration_invalid")
    return analysis,int(attempt)


def _history_paths(tree):
    result=[]
    start=history_start()
    runs=tree.children("runs")
    require(len(runs)<=1000,"history_bounds")
    for analysis,info in sorted(runs):
        if not re.fullmatch(r"WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}",analysis): continue
        if start and analysis<start[0]: continue
        require(stat.S_ISDIR(info.st_mode),"unsafe_path")
        attempts=tree.children("runs/"+analysis)
        require(len(attempts)<=1000,"history_bounds")
        matched=[(int(name[8:]),name,info) for name,info in attempts if re.fullmatch(r"attempt-[1-9][0-9]{0,5}",name)]
        require(len(matched)<=32,"history_bounds")
        for attempt,name,info in sorted(matched):
            if start and (analysis,attempt)<start: continue
            require(stat.S_ISDIR(info.st_mode),"unsafe_path")
            base=f"runs/{analysis}/{name}/prepare-handoff/prepare_analysis"
            if not tree.exists(base): continue
            generations=tree.children(base)
            require(len(generations)<=64,"history_bounds")
            for generation,name,info in sorted((int(n[11:]),n,i) for n,i in generations if re.fullmatch(r"generation-[1-9][0-9]{0,5}",n)):
                require(stat.S_ISDIR(info.st_mode),"unsafe_path")
                result.append((analysis,attempt,generation,base+"/"+name))
                require(len(result)<=1000,"history_bounds")
    return result


def _read_stable(tree,path):
    before=tree.info(path); raw=tree.read(path)
    require(_stamp(before)==_stamp(tree.info(path)),"source_changed")
    return raw


def _object(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,"history_invalid"); result[key]=value
        return result
    value=json.loads(raw.decode("utf-8"),object_pairs_hook=unique)
    require(type(value) is dict,"history_invalid")
    return value


def _read_history(tree,source,entry,secret):
    analysis,attempt,generation,base=entry
    request_raw=_read_stable(tree,base+"/handoff-request.json")
    receipt_raw=_read_stable(tree,base+"/prepare_analysis.receipt.json")
    request=_object(request_raw); receipt=_object(receipt_raw)
    attempt_path=f"runs/{analysis}/attempt-{attempt}"
    binding=_object(_read_stable(tree,attempt_path+"/batch-binding.json"))
    require(request.get("schema_version")=="wgs.prepare-handoff.request.v1" and request.get("stage")=="prepare_analysis"
        and receipt.get("schema_version")=="wgs.prepare-analysis.receipt.v1","history_invalid")
    for field,expected in (("analysis_id",analysis),("attempt",attempt),("generation",generation)):
        require(type(request.get(field)) is type(expected) and request[field]==expected,"history_identity_mismatch")
    for field in ("execution_id","release_id"):
        require(type(request.get(field)) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}",request[field]),"history_identity_mismatch")
    require(type(request.get("request_hash")) is str and re.fullmatch(r"[0-9a-f]{64}",request["request_hash"]),"history_identity_mismatch")
    for field in ("analysis_id","attempt","generation","execution_id","request_hash","release_id"):
        require(type(receipt.get(field)) is type(request[field]) and receipt[field]==request[field],"history_identity_mismatch")
    require(request.get("artifact_root")==str(source.runtime_root/base),"history_path_mismatch")
    require(binding.get("schema_version")=="wgs-runtime.batch-binding.v2" and binding.get("analysis_id")==analysis
        and type(binding.get("attempt")) is int and binding["attempt"]==attempt
        and binding.get("pipeline_release_id")==request["release_id"]
        and binding.get("analysis_project_root")==str(source.project_root)
        and binding.get("control_workdir")==str(source.runtime_root/attempt_path),"history_binding_mismatch")
    batch=binding.get("batch")
    require(type(batch) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}",batch),"history_binding_mismatch")
    require(binding.get("batch_root")==binding.get("expected_batch_root")==str(source.project_root/batch),"history_binding_mismatch")
    source_spec=request.get("source_sampleinfo")
    require(type(source_spec) is dict and type(source_spec.get("snapshot_id")) is str and bool(source_spec["snapshot_id"])
        and type(source_spec.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}",source_spec["sha256"])
        and receipt.get("source_sampleinfo_snapshot_id")==source_spec["snapshot_id"]
        and receipt.get("source_sampleinfo_sha256")==source_spec["sha256"],"history_source_mismatch")
    keys=request.get("artifact_keys"); descriptor=receipt.get("final_sampleinfo")
    require(type(keys) is dict and keys.get("final_sampleinfo")=="final-sampleinfo.snapshot.tsv"
        and type(descriptor) is dict and descriptor.get("artifact_key")==keys["final_sampleinfo"]
        and type(descriptor.get("row_count")) is int and 0<=descriptor["row_count"]<=MAX_ROWS,"history_artifact_invalid")
    if descriptor.get("sha256") is None and descriptor["row_count"]==0:
        rows=[]; final_hash=digest(b"")
    else:
        raw=_read_stable(tree,base+"/final-sampleinfo.snapshot.tsv"); final_hash=digest(raw)
        require(descriptor.get("sha256")==final_hash,"history_artifact_hash")
        rows=project_rows(raw,source,secret,pending=False)
    selected=receipt.get("selected")
    require(type(selected) is list and len(selected)==len(rows)==descriptor["row_count"],"history_selected_mismatch")
    require(all(type(r) is dict and r.get("decision")=="selected" and all(type(r.get(k)) is str for k in SAFE_COLUMNS) for r in selected),"history_selected_mismatch")
    require(Counter(tuple(r[k].strip() for k in SAFE_COLUMNS) for r in selected)==
        Counter(tuple(r[k] for k in SAFE_COLUMNS) for r in rows),"history_selected_mismatch")
    require(len({r["record_key"] for r in rows})==len(rows) and all(r["analysis_batch"] and r["sequencing_batch"] for r in rows),"history_selected_mismatch")
    return {"identity":{k:request[k] for k in ("analysis_id","attempt","generation","execution_id","request_hash","release_id")},
        "request_sha256":digest(request_raw),"receipt_sha256":digest(receipt_raw),"final_sha256":final_hash,
        "source_sha256":source_spec["sha256"],"rows":rows}


def _apply_history(factory,source,token,projection,secret):
    identity=projection["identity"]; content=digest(canonical(projection))
    key=opaque(secret,source.scope_id,"file-selection-execution",
        [identity[k] for k in ("analysis_id","attempt","generation","execution_id")])
    with factory() as session:
        _source_lock(session,source.source_id)
        state=session.scalar(select(SampleReferenceSource).where(SampleReferenceSource.source_id==source.source_id).with_for_update())
        require(state is not None,"registration_mismatch")
        if state.latest_reserved_generation!=token: return "superseded"
        op=session.scalar(select(SampleReferenceOperation).where(SampleReferenceOperation.source_id==source.source_id,SampleReferenceOperation.execution_key==key))
        if op is None:
            # Retain a previously imported identical receipt; do not duplicate
            # history when moving to the complete execution identity.
            op=session.scalar(select(SampleReferenceOperation).where(
                SampleReferenceOperation.source_id==source.source_id,
                SampleReferenceOperation.commit_hash==content))
            if op is not None: op.execution_key=key
        run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==identity["analysis_id"],AnalysisRun.pipeline_name=="wgs"))
        if op is not None:
            require(op.commit_hash==content,"history_conflict")
            if run and op.analysis_id is None: op.analysis_id=run.analysis_id
            session.commit(); return "ready"
        sequence=(session.scalar(select(func.max(SampleReferenceOperation.sequence)).where(SampleReferenceOperation.source_id==source.source_id)) or 0)+1
        op=SampleReferenceOperation(source_id=source.source_id,operation_id=str(UUID(key[:32])),sequence=sequence,
            intent_hash=projection["request_sha256"],commit_hash=content,pending_hash=projection["final_sha256"],
            execution_key=key,request_hash=identity["request_hash"],previous_operation_id=None,mode="unknown",cloud_key=None,
            analysis_id=run.analysis_id if run else None,attempt=identity["attempt"],generation=identity["generation"],
            producer_commit="unknown",completed_at=utc_now(),logical_time_source="database_imported_at")
        session.add(op); session.flush()
        for number,row in enumerate(projection["rows"],1):
            session.add(SampleReferenceHistory(operation_pk=op.id,role="decision_selected",row_number=number,record_key=row["record_key"],
                safe_json={**{k:v for k,v in row.items() if k!="record_key"},"origin_batch":row["sequencing_batch"],
                    "destination_batch":row["analysis_batch"]}))
        session.add(SampleReferenceHistory(operation_pk=op.id,role="file_selection",row_number=1,record_key=key,
            safe_json={"selection_only":True,"execution_status":"unknown",
                "release_id":identity["release_id"],"attempt":identity["attempt"],"generation":identity["generation"],
                "final_sampleinfo_sha256":projection["final_sha256"],"source_sampleinfo_sha256":projection["source_sha256"]}))
        session.commit()
    return "ready"


def reconcile_file_source(factory,source,secret):
    try: token=_reserve(factory,source,secret)
    except SourceError: return "error"
    except Exception: return "database_unavailable"
    errors=[]
    try:
        try:
            if _apply(factory,source,token,read_pending(source,secret))=="superseded": return "superseded"
        except SourceError as exc: errors.append(exc.code)
        if source.runtime_root is not None:
            tree=None
            try:
                tree=Tree(source.runtime_root)
                for entry in _history_paths(tree):
                    try:
                        value=_read_history(tree,source,entry,secret)
                    except SourceError as exc: errors.append(exc.code); continue
                    except Exception: errors.append("history_unavailable"); continue
                    try:
                        if _apply_history(factory,source,token,value,secret)=="superseded": return "superseded"
                    except SourceError as exc: errors.append(exc.code); continue
            except SourceError as exc: errors.append(exc.code)
            except (OSError,ValueError): errors.append("history_unavailable")
            finally:
                if tree: tree.close()
        if errors:
            record_error(factory,source,token,errors[0]); return "error"
        return "ready"
    except Exception: return "database_unavailable"
