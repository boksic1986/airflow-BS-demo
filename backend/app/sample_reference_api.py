"""Authenticated, paginated read-only resources. No disk reads on page refresh."""
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, exists, func, or_, select
from app.db import get_sessionmaker
from app.models import (SampleReference,SampleReferenceSource,SampleReferenceOperation,SampleReferenceHistory)

router=APIRouter(prefix="/api/sample-references",tags=["sample-references"])

def page(session, query, limit, offset, serialize):
    total=session.scalar(select(func.count()).select_from(query.subquery())) or 0
    return {"items":[serialize(x) for x in session.scalars(query.limit(limit).offset(offset))],
            "total":total,"limit":limit,"offset":offset}

def health(row):
    return {k:getattr(row,k) for k in ("source_id","source_type","sync_status","sync_reason",
        "latest_applied_generation","last_good_generation","last_good_at","last_checked_at")}

@router.get("/sources")
def sources(limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),sync_error:bool|None=None):
    query=select(SampleReferenceSource).order_by(SampleReferenceSource.source_id)
    if sync_error is not None:
        query=query.where((SampleReferenceSource.sync_status=="error") if sync_error else (SampleReferenceSource.sync_status!="error"))
    with get_sessionmaker()() as session:
        return page(session,query,limit,offset,health)

@router.get("")
def references(source_id:str|None=Query(None,max_length=128),sample_id:str|None=Query(None,max_length=128),
        family_id:str|None=Query(None,max_length=128),origin_batch:str|None=Query(None,max_length=128),
        destination_batch:str|None=Query(None,max_length=128),pending:bool|None=None,sync_error:bool|None=None,
        limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0)):
    query=select(SampleReference).join(SampleReferenceSource,SampleReference.source_id==SampleReferenceSource.source_id)
    for name,value in (("source_id",source_id),("sample_id",sample_id),("family_id",family_id),
                       ("origin_batch",origin_batch),("destination_batch",destination_batch),("pending",pending)):
        if value is not None: query=query.where(getattr(SampleReference,name)==value)
    if sync_error is not None:
        query=query.where((SampleReferenceSource.sync_status=="error") if sync_error else (SampleReferenceSource.sync_status!="error"))
    query=query.order_by(SampleReference.source_id,SampleReference.record_key)
    with get_sessionmaker()() as session:
        states={s.source_id:s for s in session.scalars(select(SampleReferenceSource))}
        def serialize(row):
            value={k:getattr(row,k) for k in ("source_id","record_key","sample_id","family_id","sequencing_batch",
                "analysis_batch","data_id","pending","present_in_latest_complete","reason_code","reason_codes",
                "origin_batch","destination_batch","needs_review","conflict_reason","last_good_generation","last_good_at")}
            value.update(sync_status=states[row.source_id].sync_status,sync_reason=states[row.source_id].sync_reason)
            return value
        return page(session,query,limit,offset,serialize)

@router.get("/operations")
def operations(source_id:str|None=Query(None,max_length=128),record_key:str|None=Query(None,pattern="^[0-9a-f]{64}$"),
        sample_id:str|None=Query(None,max_length=128),family_id:str|None=Query(None,max_length=128),
        origin_batch:str|None=Query(None,max_length=128),destination_batch:str|None=Query(None,max_length=128),
        limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0)):
    if record_key and not source_id:
        raise HTTPException(422,detail={"code":"SOURCE_REQUIRED","message":"record_key requires source_id."})
    query=select(SampleReferenceOperation)
    from app.wgs_file_reference import history_start
    start=history_start()
    if start:
        file_sources=select(SampleReferenceSource.source_id).where(SampleReferenceSource.source_type=="wgs_files")
        query=query.where(or_(SampleReferenceOperation.source_id.not_in(file_sources),
            SampleReferenceOperation.analysis_id>start[0],
            and_(SampleReferenceOperation.analysis_id==start[0],SampleReferenceOperation.attempt>=start[1])))
    if source_id is not None: query=query.where(SampleReferenceOperation.source_id==source_id)
    # Each filter is scoped to rows of this operation. Identity filters match the
    # original or resolved alias, never approximate sample/order matching.
    history=select(SampleReferenceHistory.id).where(SampleReferenceHistory.operation_pk==SampleReferenceOperation.id)
    if record_key: history=history.where(or_(SampleReferenceHistory.record_key==record_key,SampleReferenceHistory.resolved_key==record_key))
    for name,value in (("sample_id",sample_id),("family_id",family_id),("origin_batch",origin_batch),("destination_batch",destination_batch)):
        if value is not None: history=history.where(SampleReferenceHistory.safe_json[name].as_string()==value)
    if any(x is not None for x in (record_key,sample_id,family_id,origin_batch,destination_batch)):
        query=query.where(exists(history))
    query=query.order_by(SampleReferenceOperation.source_id,SampleReferenceOperation.sequence.desc())
    with get_sessionmaker()() as session:
        def serialize(op):
            value={k:getattr(op,k) for k in ("source_id","operation_id","sequence","mode","analysis_id","producer_commit")}
            proven=op.logical_time_source=="authenticated_intent.created_at"
            value.update(
                logical_transaction_at=op.completed_at if proven else None,
                logical_transaction_time_source=op.logical_time_source if proven else None,
                logical_transaction_time_semantics=("logical transaction identity; not completion or duration"
                    if proven else "unknown legacy provenance"),
                completed_at=None,
                observed_at=op.imported_at,
                observed_time_source="database_imported_at" if op.imported_at else None,
            )
            value["attempt"]=op.attempt if op.analysis_id else None
            links=select(SampleReferenceHistory).where(SampleReferenceHistory.operation_pk==op.id,
                SampleReferenceHistory.role.in_(("decision_selected","decision_pending","decision_consumed")))
            if record_key: links=links.where(or_(SampleReferenceHistory.record_key==record_key,SampleReferenceHistory.resolved_key==record_key))
            # Bound expanded members independently of operation page size.
            value["links_total"]=session.scalar(select(func.count()).select_from(links.subquery())) or 0
            value["links"]=[{"role":r.role.removeprefix("decision_"),"record_key":r.record_key,
                             "resolved_key":r.resolved_key,**r.safe_json} for r in session.scalars(links.order_by(SampleReferenceHistory.id).limit(200))]
            value["links_truncated"]=value["links_total"]>200
            from app.wgs_cloud_reference import readiness
            value["cloud_readiness"]=readiness(session,op)
            if value["cloud_readiness"] is not None:
                value["sequence_semantics"]="database_import_order"
                value["logical_transaction_time_semantics"]="unknown; observed_at is database import time only"
            selection=session.scalar(select(SampleReferenceHistory).where(SampleReferenceHistory.operation_pk==op.id,SampleReferenceHistory.role=="file_selection"))
            if selection is not None:
                value["selection_history"]=selection.safe_json
                value["sequence_semantics"]="database_import_order"
                value["logical_transaction_time_semantics"]="unknown; selected evidence does not prove execution completion"
            return value
        return page(session,query,limit,offset,serialize)
