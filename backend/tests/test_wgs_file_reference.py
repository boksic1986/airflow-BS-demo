"""Minimal original-file projection tests; all material is synthetic."""
import importlib.util
import json
from dataclasses import replace

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session

SECRET=b"file-reference-test-secret-only-32!"
HEADER="样本编号\t上机批次\t数据编号\t分析批次\t家系编号\t订单编号\tanalysisTaskId\t姓名\textra\n"


def material(sample="S1",order="PRIVATE-ORDER",task="PRIVATE-TASK"):
    return HEADER+f"{sample}\tSEQ1\tD1\tAB1\tF1\t{order}\t{task}\tPRIVATE-NAME\tPRIVATE-NOTE\n"


def setup(tmp_path):
    assert importlib.util.find_spec("app.wgs_file_reference"), "plain WGS file source missing"
    from app.wgs_file_reference import FileSource, reconcile_file_source
    from app.models import Base
    root=tmp_path/"PRIVATE-root"; (root/"prepare").mkdir(parents=True)
    path=root/"prepare/pending_samples.tsv"; path.write_text(material(),encoding="utf-8")
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return FileSource("file-test","scope",root),sessionmaker(engine),reconcile_file_source,path


def test_original_file_without_lock_journal_or_receipts_is_idempotent_and_private(tmp_path):
    source,factory,sync,path=setup(tmp_path)
    from app.models import SampleReference as Ref,SampleReferenceSnapshot as Snapshot,SampleReferenceOperation as Op,Sample
    original=path.read_bytes()
    assert sync(factory,source,SECRET)=="ready"
    assert sync(factory,source,SECRET)=="ready"
    with factory() as s:
        row=s.scalar(select(Ref)); key=row.record_key
        assert row.pending and row.sample_id=="S1" and row.reason_code=="pending_reason_unclassified"
        assert row.origin_batch=="SEQ1" and row.destination_batch is None
        assert s.scalar(select(func.count()).select_from(Snapshot))==1
        assert s.scalar(select(Op)) is None and s.scalar(select(Sample)) is None
        dump="\n".join(s.connection().connection.driver_connection.iterdump())
        assert "PRIVATE" not in dump and str(source.project_root) not in dump
    assert path.read_bytes()==original
    # Same task overrides changed order; changing task separates full identity.
    path.write_text(material(order="PRIVATE-OTHER"),encoding="utf-8")
    assert sync(factory,source,SECRET)=="ready"
    with factory() as s: assert s.scalar(select(Ref).where(Ref.pending)).record_key==key
    path.write_text(material(task="PRIVATE-OTHER"),encoding="utf-8")
    assert sync(factory,source,SECRET)=="ready"
    with factory() as s: assert s.scalar(select(Ref).where(Ref.pending)).record_key!=key
    reason_header=HEADER.rstrip("\n")+"\treason_code\n"
    reason_row=material().splitlines()[1]+"\tfastq_ready_missing\n"
    path.write_text(reason_header+reason_row,encoding="utf-8")
    assert sync(factory,source,SECRET)=="ready"
    with factory() as s: assert s.scalar(select(Ref).where(Ref.pending)).reason_code=="fastq_ready_missing"
    path.write_text(reason_header+material().splitlines()[1]+"\tPRIVATE-FREE-TEXT\n",encoding="utf-8")
    assert sync(factory,source,SECRET)=="ready"
    with factory() as s: assert s.scalar(select(Ref).where(Ref.pending)).reason_code=="pending_reason_unclassified"
    path.write_text(HEADER,encoding="utf-8")
    assert sync(factory,source,SECRET)=="ready"
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(Ref).where(Ref.pending))==0
        assert s.scalar(select(Op)) is None


@pytest.mark.parametrize("damage",["missing","truncated","symlink","changed"])
def test_unavailable_or_changing_files_preserve_last_good(tmp_path,monkeypatch,damage):
    source,factory,sync,path=setup(tmp_path)
    from app.models import SampleReference as Ref,SampleReferenceSource as State
    from app.sample_reference_reader import Tree
    assert sync(factory,source,SECRET)=="ready"
    if damage=="missing": path.unlink()
    elif damage=="truncated": path.write_text(HEADER+"S2\tpartial",encoding="utf-8")
    elif damage=="symlink":
        other=path.with_name("other.tsv"); path.rename(other); path.symlink_to(other)
    else:
        original=Tree.read
        def changing(tree,name):
            data=original(tree,name)
            other=path.with_name("replacement.tsv"); other.write_text(material("S2"),encoding="utf-8"); other.replace(path)
            return data
        monkeypatch.setattr(Tree,"read",changing)
    assert sync(factory,source,SECRET)=="error"
    with factory() as s:
        assert s.scalar(select(Ref)).sample_id=="S1" and s.scalar(select(Ref)).pending
        assert s.scalar(select(State)).sync_status=="error"


def test_db_commit_failure_retries_and_registration_cannot_retarget(tmp_path):
    source,factory,sync,_=setup(tmp_path)
    from app.models import SampleReference as Ref
    class BadCommit(Session):
        commits=0
        def commit(self):
            type(self).commits+=1
            if type(self).commits==2: raise RuntimeError("synthetic DB failure")
            super().commit()
    assert sync(sessionmaker(bind=factory.kw["bind"],class_=BadCommit),source,SECRET)=="database_unavailable"
    with factory() as s: assert s.scalar(select(Ref)) is None
    assert sync(factory,source,SECRET)=="ready"
    assert sync(factory,replace(source,project_root=source.project_root/"other"),SECRET)=="error"


def test_operator_only_config_routes_files_without_producer_registration(tmp_path,monkeypatch):
    source,factory,_,_=setup(tmp_path)
    from app.sample_reference_config import load_reference_config
    from app.sample_reference_service import reconcile_registered
    from app.sample_reference_reader import SourceError
    config_path=tmp_path/"sources.json"
    item={"source_type":"wgs_files","source_id":source.source_id,"scope_id":source.scope_id,"project_root":str(source.project_root)}
    config_path.write_text(json.dumps([item]))
    monkeypatch.setenv("SAMPLE_REFERENCE_SOURCES_FILE",str(config_path))
    monkeypatch.setenv("SAMPLE_REFERENCE_IDENTITY_SECRET",SECRET.decode())
    monkeypatch.delenv("SAMPLE_REFERENCE_ENABLED",raising=False)
    assert load_reference_config().enabled is False
    monkeypatch.setenv("SAMPLE_REFERENCE_ENABLED","true")
    assert reconcile_registered(factory,load_reference_config())=={"file-test":"ready"}
    item["pending_path"]="/not-allowed"; config_path.write_text(json.dumps([item]))
    with pytest.raises(SourceError): load_reference_config()
