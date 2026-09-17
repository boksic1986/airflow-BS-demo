"""Focused original-receipt integration, only synthetic materials."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import select, func
from app.models import AnalysisRun, Sample, SampleReference, SampleReferenceOperation, SampleReferenceHistory
from app.sample_reference_config import load_reference_config
from app.sample_reference_worker import reconcile_once
from test_wgs_file_reference import setup, material, SECRET

ANALYSIS="WGS_20260910_010203_A1B2C3"


def encoded(value): return json.dumps(value,ensure_ascii=False,sort_keys=True).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()


def history(source, runtime, generation=1, task="PRIVATE-TASK"):
    attempt=runtime/"runs"/ANALYSIS/"attempt-1"
    directory=attempt/"prepare-handoff/prepare_analysis"/f"generation-{generation}"
    directory.mkdir(parents=True)
    binding={"schema_version":"wgs-runtime.batch-binding.v2","analysis_id":ANALYSIS,"attempt":1,
        "pipeline_release_id":"wgs-4.2.1-cc9bde3","analysis_project_root":str(source.project_root),
        "control_workdir":str(attempt),"batch":"WGS_AB1","batch_root":str(source.project_root/"WGS_AB1"),
        "expected_batch_root":str(source.project_root/"WGS_AB1")}
    (attempt/"batch-binding.json").write_bytes(encoded(binding))
    identity={"analysis_id":ANALYSIS,"attempt":1,"generation":generation,"execution_id":f"E{generation}","request_hash":str(generation)*64,"release_id":"wgs-4.2.1-cc9bde3"}
    request={"schema_version":"wgs.prepare-handoff.request.v1",**identity,"stage":"prepare_analysis","artifact_root":str(directory),
        "artifact_keys":{"final_sampleinfo":"final-sampleinfo.snapshot.tsv","private_pending_payload":"private-pending-output.tsv"},
        "source_sampleinfo":{"snapshot_id":ANALYSIS+"-a1-sampleinfo","sha256":"a"*64}}
    selected={"sample_id":"S1","sequencing_batch":"SEQ1","data_id":"D1","analysis_batch":"AB1","family_id":"F1",
        "sample_type":"blood","family_relation":"child","sex":"M","decision":"selected","reason_code":"selected","reason_message":"PRIVATE"}
    final=material(task=task).encode()
    receipt={"schema_version":"wgs.prepare-analysis.receipt.v1",**identity,
        "source_sampleinfo_snapshot_id":request["source_sampleinfo"]["snapshot_id"],"source_sampleinfo_sha256":"a"*64,
        "final_sampleinfo":{"artifact_key":"final-sampleinfo.snapshot.tsv","sha256":sha(final),"row_count":1},
        "selected":[selected],"pending":[],"excluded":[]}
    (directory/"handoff-request.json").write_bytes(encoded(request))
    (directory/"prepare_analysis.receipt.json").write_bytes(encoded(receipt))
    (directory/"final-sampleinfo.snapshot.tsv").write_bytes(final)
    return directory


def configured(tmp_path,monkeypatch):
    source,factory,_,pending=setup(tmp_path)
    runtime=tmp_path/"runtime"
    directory=history(source,runtime)
    item={"source_type":"wgs_files","source_id":source.source_id,"scope_id":source.scope_id,
          "project_root":str(source.project_root),"runtime_root":str(runtime)}
    path=tmp_path/"registered.json"; path.write_bytes(encoded([item]))
    monkeypatch.setenv("SAMPLE_REFERENCE_ENABLED","true")
    monkeypatch.setenv("SAMPLE_REFERENCE_IDENTITY_SECRET",SECRET.decode())
    monkeypatch.setenv("SAMPLE_REFERENCE_SOURCES_FILE",str(path))
    return source,factory,pending,directory


def test_worker_imports_repeat_selected_destinations_without_touching_current_pending(tmp_path,monkeypatch):
    source,factory,pending,directory=configured(tmp_path,monkeypatch)
    with factory() as s:
        s.add(AnalysisRun(analysis_id=ANALYSIS,pipeline_name="wgs",dag_id="bio_wgs",workdir="/synthetic")); s.commit()
    config=load_reference_config()
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    with factory() as s:
        op=s.scalar(select(SampleReferenceOperation)); row=s.scalar(select(SampleReference))
        selected=s.scalar(select(SampleReferenceHistory).where(SampleReferenceHistory.role=="decision_selected"))
        assert row.pending and selected.record_key==row.record_key
        assert selected.safe_json["origin_batch"]=="SEQ1" and selected.safe_json["destination_batch"]=="AB1"
        assert op.analysis_id==ANALYSIS and op.producer_commit=="unknown"
        assert s.scalar(select(func.count()).select_from(SampleReferenceOperation))==1
        assert s.scalar(select(Sample)) is None
        dump="\n".join(s.connection().connection.driver_connection.iterdump())
        assert "PRIVATE" not in dump and str(source.project_root) not in dump
    # Same sample but another private task remains a distinct retained identity.
    history(source,config.sources[0].runtime_root,2,task="PRIVATE-OTHER")
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    with factory() as s:
        selected=s.scalars(select(SampleReferenceHistory).where(SampleReferenceHistory.role=="decision_selected")).all()
        assert len(selected)==2 and selected[0].record_key!=selected[1].record_key
        assert s.scalar(select(SampleReference)).pending is True
    # Changed immutable receipt is rejected, but cannot starve a later execution.
    receipt=directory/"prepare_analysis.receipt.json"
    value=json.loads(receipt.read_bytes()); value["selected"][0]["reason_message"]="PRIVATE-CHANGED"
    receipt.write_bytes(encoded(value))
    history(source,config.sources[0].runtime_root,3,task="PRIVATE-THIRD")
    assert reconcile_once(factory,config)=={source.source_id:"error"}
    with factory() as s: assert s.scalar(select(func.count()).select_from(SampleReferenceOperation))==3
    from app import sample_reference_api as api
    monkeypatch.setattr(api,"get_sessionmaker",lambda:factory)
    response=api.operations(source_id=source.source_id,record_key=None,sample_id=None,family_id=None,origin_batch="SEQ1",destination_batch="AB1",limit=50,offset=0)
    assert response["total"]==3
    assert response["items"][0]["selection_history"]["selection_only"] is True
    assert response["items"][0]["completed_at"] is None
    assert response["items"][0]["cloud_readiness"] is None


@pytest.mark.parametrize("damage",["hash","identity","selected","binding"])
def test_bad_history_preserves_history_and_does_not_block_current_file(tmp_path,monkeypatch,damage):
    source,factory,pending,directory=configured(tmp_path,monkeypatch)
    config=load_reference_config()
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    with factory() as s: previous=s.scalar(select(SampleReferenceOperation)).commit_hash
    path=directory/"prepare_analysis.receipt.json"
    value=json.loads(path.read_bytes())
    if damage=="hash": value["final_sampleinfo"]["sha256"]="b"*64
    elif damage=="identity": value["execution_id"]="OTHER"
    elif damage=="selected": value["selected"][0]["data_id"]="OTHER"
    else:
        path=directory.parents[2]/"batch-binding.json"; value=json.loads(path.read_bytes())
        value["analysis_project_root"]="/unregistered"
    path.write_bytes(encoded(value))
    pending.write_text(material("S2"),encoding="utf-8")
    assert reconcile_once(factory,config)=={source.source_id:"error"}
    with factory() as s:
        assert s.scalar(select(SampleReferenceOperation)).commit_hash==previous
        assert s.scalar(select(SampleReference).where(SampleReference.pending)).sample_id=="S2"


def test_valid_history_still_imports_when_current_file_missing_and_no_run_is_created(tmp_path,monkeypatch):
    source,factory,pending,_=configured(tmp_path,monkeypatch)
    pending.unlink()
    assert reconcile_once(factory,load_reference_config())=={source.source_id:"error"}
    with factory() as s:
        assert s.scalar(select(SampleReferenceOperation)).analysis_id is None
        assert s.scalar(select(AnalysisRun)) is None and s.scalar(select(Sample)) is None


def test_shared_runtime_filters_other_project_roots_without_deleting_imported_history(tmp_path,monkeypatch):
    source,factory,_,directory=configured(tmp_path,monkeypatch)
    config=load_reference_config()
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    with factory() as s:
        previous=s.scalar(select(SampleReferenceOperation)).id
    # A retained, self-consistent binding for a different project root is not
    # evidence for this registered source. Do not read that root or erase history.
    binding_path=directory.parents[2]/"batch-binding.json"
    binding=json.loads(binding_path.read_bytes())
    binding.update(analysis_project_root="/other-clinical-root",
        batch_root="/other-clinical-root/WGS_AB1",
        expected_batch_root="/other-clinical-root/WGS_AB1")
    binding_path.write_bytes(encoded(binding))
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    with factory() as s:
        assert s.scalar(select(SampleReferenceOperation)).id==previous
        assert s.scalar(select(func.count()).select_from(SampleReferenceHistory))==2
    # An independent source must not import that other-root selection at all.
    config=replace(config,sources=(replace(config.sources[0],source_id="second-source"),))
    assert reconcile_once(factory,config)=={"second-source":"ready"}
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(SampleReferenceOperation))==1


def test_unpublished_generation_waits_for_receipt_then_imports_once(tmp_path,monkeypatch):
    source,factory,_,directory=configured(tmp_path,monkeypatch)
    config=load_reference_config()
    receipt=directory/"prepare_analysis.receipt.json"
    receipt_bytes=receipt.read_bytes(); receipt.unlink()
    later=history(source,config.sources[0].runtime_root,2)
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(SampleReferenceOperation))==1
        assert s.scalar(select(SampleReferenceOperation)).generation==2
    receipt.write_bytes(receipt_bytes)
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    assert reconcile_once(factory,config)=={source.source_id:"ready"}
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(SampleReferenceOperation))==2
    # Once a receipt exists, missing published artifacts must still be an error.
    (later/"final-sampleinfo.snapshot.tsv").unlink()
    assert reconcile_once(factory,config)=={source.source_id:"error"}
