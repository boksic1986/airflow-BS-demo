import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
import os


def service():
    assert importlib.util.find_spec('app.wgs_test_project') is not None, 'test-local project service is missing'
    from app import wgs_test_project
    return wgs_test_project


def test_production_rejects_even_with_test_gate_enabled():
    with pytest.raises(ValueError, match='test environment'):
        service().require_test(SimpleNamespace(platform_environment='production', wgs_test_project_enabled=True))


@pytest.mark.parametrize('child', ['../escape', '/absolute', 'a/../../escape', '.', 'a//b', 'a\\b'])
def test_test_target_rejects_traversal(tmp_path, child):
    with pytest.raises(ValueError):
        service().target_path(tmp_path, child)


def test_test_target_rejects_symlink_escape_and_existing_target(tmp_path):
    outside=tmp_path/'outside'; outside.mkdir()
    root=tmp_path/'root'; root.mkdir()
    (root/'link').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError): service().target_path(root, 'link/new')
    (root/'exists').mkdir()
    with pytest.raises(ValueError): service().target_path(root, 'exists')


def test_source_freezes_exact_pair_and_config(tmp_path):
    root=tmp_path/'root'; root.mkdir()
    project=root/'source'; project.mkdir(); (project/'raw').mkdir()
    (project/'sampleinfo.tsv').write_text('样本编号\t数据编号\t分析批次\t上机批次\nSYNTH1\tDATA1\t20260912A\t20260912A\n')
    (project/'config.yaml').write_text(f'fastqPath: {root}\n')
    for read in ['R1','R2']: (project/'raw'/f'DATA1.{read}.fq.gz').write_bytes(b'synthetic')
    observed=service().read_source(project, root)
    assert observed['samples'] == ['SYNTH1']
    assert len(observed['fastq']) == 2
    first=observed['fingerprint']
    (project/'raw'/'DATA1.R1.fq.gz').write_bytes(b'changed')
    assert service().read_source(project,root)['fingerprint'] != first


def test_confirm_owns_draft_is_idempotent_and_never_prepares_on_backend(tmp_path, monkeypatch):
    from sqlalchemy import create_engine,select
    from sqlalchemy.orm import Session
    from app.models import Base,AnalysisRun
    module=service()
    root=tmp_path/'root';root.mkdir(); source=root/'source';source.mkdir();(source/'raw').mkdir()
    (source/'sampleinfo.tsv').write_text('样本编号\t数据编号\t分析批次\t上机批次\nSYNTH1\tDATA1\t20260912A\t20260912A\n')
    (source/'config.yaml').write_text(f'fastqPath: {root}\n')
    for read in ['R1','R2']: (source/'raw'/f'DATA1.{read}.fq.gz').write_bytes(b'synthetic')
    monkeypatch.setattr(module,'TEST_ROOT',root)
    settings=SimpleNamespace(platform_environment='test',wgs_test_project_enabled=True,wgs_release_catalog_path=str(Path(__file__).parents[2]/'config/wgs_releases.yaml'),host_results_root=str(tmp_path/'control'),container_shared_root=str(tmp_path/'shared'),wgs_contract_v2_enabled=True)
    class Airflow:
        calls=[]
        def trigger_dag_run(self,dag_id,**kwargs): self.calls.append(kwargs);return kwargs
    airflow=Airflow();engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as session:
        draft=module.preview(session=session,settings=settings,username='owner',source_project_dir=str(source),output_child='independent',algo='Haplotyper',use_reference='no')
        assert session.scalar(select(AnalysisRun)) is None
        with pytest.raises(ValueError,match='Unknown'):
            module.confirm(session=session,settings=settings,airflow_client=airflow,username='other',draft_id=draft['draft_id'],preview_hash=draft['preview_hash'])
        first=module.confirm(session=session,settings=settings,airflow_client=airflow,username='owner',draft_id=draft['draft_id'],preview_hash=draft['preview_hash'])
        second=module.confirm(session=session,settings=settings,airflow_client=airflow,username='owner',draft_id=draft['draft_id'],preview_hash=draft['preview_hash'])
        assert first['analysis_id']==second['analysis_id']
        assert len(airflow.calls)==1
        assert first['params']['algo']=='Haplotyper'
        assert 'fastq' not in first['params']['test_project']
        assert not (root/'independent').exists()
        run=session.scalar(select(AnalysisRun))
        assert run.params_json['test_project']['samples']==['SYNTH1']
        other=module.preview(session=session,settings=settings,username='owner',source_project_dir=str(source),output_child='another',algo='Haplotyper',use_reference='no')
        independent=module.confirm(session=session,settings=settings,airflow_client=airflow,username='owner',draft_id=other['draft_id'],preview_hash=other['preview_hash'])
        other_run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==independent['analysis_id']))
        assert other_run.analysis_id!=run.analysis_id
        assert other_run.params_json['project_name']!=run.params_json['project_name']
        assert other_run.params_json['analysis_batch']==run.params_json['analysis_batch']
        import hashlib
        scopes=[f"{item.params_json['project_name']}/{item.params_json['batch_no']}" for item in (run,other_run)]
        assert len({hashlib.sha256(scope.encode()).hexdigest()[:20] for scope in scopes})==2
        assert other_run.params_json['test_project']['output_root']!=run.params_json['test_project']['output_root']
        assert other_run.params_json['test_project']['batch']==run.params_json['test_project']['batch']=='20260912A'
        assert module.sha(source/'sampleinfo.tsv')==run.params_json['test_project']['sampleinfo_sha256']
        from app.wgs_execution_dispatch_service import change_execution_choice
        with pytest.raises(ValueError,match='isolated CCE'):
            change_execution_choice(session=session,settings=settings,analysis_id=run.analysis_id,desired_mode='local',desired_target='node-97',expected_revision=1,requested_by='owner',reason='not allowed for isolated test')


@pytest.mark.skipif(not os.getenv('OPT_SUBMISSION_TEST_DATABASE_URL'),reason='isolated PostgreSQL DSN required')
def test_concurrent_confirmation_creates_one_analysis(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    from sqlalchemy import create_engine,select,func
    from sqlalchemy.orm import Session
    from app.models import Base,AnalysisRun
    module=service();root=tmp_path/'root';root.mkdir();source=root/'source';source.mkdir();(source/'raw').mkdir()
    (source/'sampleinfo.tsv').write_text('样本编号\t数据编号\t分析批次\t上机批次\nSYNTH1\tDATA1\t20260912A\t20260912A\n')
    (source/'config.yaml').write_text(f'fastqPath: {root}\n')
    for read in ['R1','R2']:(source/'raw'/f'DATA1.{read}.fq.gz').write_bytes(b'synthetic')
    monkeypatch.setattr(module,'TEST_ROOT',root)
    settings=SimpleNamespace(platform_environment='test',wgs_test_project_enabled=True,wgs_release_catalog_path=str(Path(__file__).parents[2]/'config/wgs_releases.yaml'),host_results_root=str(tmp_path/'control'),container_shared_root=str(tmp_path/'shared'),wgs_contract_v2_enabled=True)
    engine=create_engine(os.environ['OPT_SUBMISSION_TEST_DATABASE_URL']);Base.metadata.create_all(engine)
    class Airflow:
        def __init__(self): self.runs={};self.lock=threading.Lock()
        def get_dag_run(self,dag_id,dag_run_id): return self.runs.get(dag_run_id)
        def trigger_dag_run(self,dag_id,*,dag_run_id,conf):
            with self.lock:
                self.runs.setdefault(dag_run_id,{'conf':conf})
                return self.runs[dag_run_id]
    airflow=Airflow()
    with Session(engine) as session:
        draft=module.preview(session=session,settings=settings,username='owner',source_project_dir=str(source),output_child='independent',algo='Haplotyper',use_reference='no')
    def call():
        with Session(engine) as session:
            return module.confirm(session=session,settings=settings,airflow_client=airflow,username='owner',draft_id=draft['draft_id'],preview_hash=draft['preview_hash'])['analysis_id']
    with ThreadPoolExecutor(max_workers=4) as pool: ids=list(pool.map(lambda _:call(),range(4)))
    assert len(set(ids))==1
    with Session(engine) as session: assert session.scalar(select(func.count(AnalysisRun.id)))==1
    assert len(airflow.runs)==1
    assert not (root/'independent').exists()
