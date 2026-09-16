from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Base
from app.wgs_submission_service import create_and_submit_run


HEADERS = '上机批次 分析批次 上传批次 重新实验/暂停分析 注意事项 家系人数 projectId 订单编号 样本条码 家系编号 家系名 姓名 样本编号 数据编号 样本类型 是否患者 家系关系 性别 出生日期 收样日期 预计报告日期 送检医院 送检医生 项目编号 检测项目 检测方法 临床主诉 中文关键词 英文关键词 医院编号 医院条码号'.split()
VALUES = {key: '' for key in HEADERS}
VALUES.update(上机批次='20260910A', 分析批次='20260910A', 样本编号='SYNTH1', 数据编号='DATA1', 姓名='PRIVATE_SYNTHETIC')
TABLE = '\t'.join(HEADERS) + '\n' + '\t'.join(VALUES[key] for key in HEADERS) + '\n'


def setup(tmp_path):
    root = Path(__file__).parents[2]
    output = tmp_path / 'projects'
    output.mkdir()
    settings = SimpleNamespace(
        wgs_project_catalog_path=str(root / 'config/wgs_projects.yaml'),
        wgs_release_catalog_path=str(root / 'config/wgs_releases.yaml'),
        wgs_contract_v2_enabled=True,
        host_results_root=str(tmp_path / 'control'), container_shared_root=str(tmp_path / 'control'),
        wgs_analysis_project_container_root=str(output),
        wgs_analysis_project_node200_root=str(output),
        wgs_runtime_request_root=str(tmp_path / 'requests'),
    )
    class Airflow:
        def __init__(self): self.calls = []
        def trigger_dag_run(self, dag_id, **kwargs):
            self.calls.append(kwargs)
            return kwargs
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    return settings, Airflow(), engine


def submit(session, settings, airflow, **overrides):
    args = dict(session=session, settings=settings, airflow_client=airflow, username='owner',
                project_id='WGS_Clinical', platform='T7', batch='20260910A_CCE_TEST', fastq_root_id='T7_Fastq',
                sampleinfo_text=TABLE)
    return create_and_submit_run(**{**args, **overrides})


def test_uploaded_table_is_private_idempotent_and_independent(tmp_path):
    settings, airflow, engine = setup(tmp_path)
    with Session(engine) as session:
        first = submit(session, settings, airflow)
        again = submit(session, settings, airflow)
        second = submit(session, settings, airflow, batch='20260910A_CCE_TEST2')
        assert again['analysis_id'] == first['analysis_id'] != second['analysis_id']
        assert len(airflow.calls) == 2
        assert first['params']['submission_phase'] == 'preparing_sampleinfo'
        assert 'PRIVATE_SYNTHETIC' not in str(first) + str(airflow.calls)
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == first['analysis_id']))
        assert run.params_json['fastq_root'] == '/bi/fastq/T7_Fastq'
        assert run.params_json['project_name'] == 'WGS_Clinical'
        assert run.params_json['analysis_batch'] == '20260910A_CCE_TEST'
        assert run.params_json['sequencing_batch'] == '20260910A'
        saved = Path(settings.wgs_runtime_request_root) / run.analysis_id / 'sampleinfo-upload.tsv'
        assert saved.read_text() == TABLE.replace('20260910A\t20260910A\t', '20260910A\t20260910A_CCE_TEST\t')
        assert saved.stat().st_mode & 0o007 == 0
        assert list(Path(settings.wgs_analysis_project_container_root).iterdir()) == []
        with pytest.raises(ValueError, match='different'):
            submit(session, settings, airflow, sampleinfo_text=TABLE.replace('DATA1', 'DATA2'))
        with pytest.raises(ValueError, match='owner'):
            submit(session, settings, airflow, username='someone-else')
        with pytest.raises(ValueError, match='YYYYMMDDX'):
            submit(session, settings, airflow, sampleinfo_text=None)


@pytest.mark.parametrize('overrides', [
    {'batch': '../escape'}, {'batch': '/absolute'},
    {'batch': '20260910A'},
    {'sampleinfo_text': TABLE + TABLE.splitlines(True)[1]},
    {'sampleinfo_text': ''}, {'sampleinfo_text': 'x' * (512 * 1024 + 1)},
])
def test_invalid_upload_does_not_create_run(tmp_path, overrides):
    settings, airflow, engine = setup(tmp_path)
    with Session(engine) as session:
        with pytest.raises(ValueError): submit(session, settings, airflow, **overrides)
        assert session.scalar(select(AnalysisRun)) is None
        assert not airflow.calls


def test_server_path_import_preserves_source_and_returns_standard_project_path(tmp_path):
    settings, airflow, engine = setup(tmp_path)
    source = Path(settings.wgs_analysis_project_container_root) / 'old' / 'sampleinfo.tsv'
    source.parent.mkdir()
    source.write_text(TABLE)
    settings.wgs_analysis_project_node200_root = '/approved/WGS_Clinical'
    from app.main import WgsCatalogRunRequest
    request = WgsCatalogRunRequest(project_id='WGS_Clinical', platform='T7',
                                  batch='20260910A_CCE_TEST', fastq_root_id='T7_Fastq',
                                  sampleinfo_path='/approved/WGS_Clinical/old/sampleinfo.tsv')
    with Session(engine) as session:
        result = create_and_submit_run(session=session, settings=settings, airflow_client=airflow,
                                       username='owner', **request.model_dump())
        assert result['params']['sampleinfo_source_path'] == '/approved/WGS_Clinical/old/sampleinfo.tsv'
        assert result['params']['prepared_project_path'] == '/approved/WGS_Clinical/WGS_20260910A_CCE_TEST_T7Hg38V4.2.1'
        assert source.read_text() == TABLE
        assert 'PRIVATE_SYNTHETIC' not in str(result) + str(airflow.calls)
        assert not (source.parent.parent / 'prepare').exists()


def test_server_path_rejects_outside_file_and_escaping_symlink_before_submission(tmp_path):
    settings, airflow, engine = setup(tmp_path)
    outside = tmp_path / 'sampleinfo.tsv'
    outside.write_text(TABLE)
    link = Path(settings.wgs_analysis_project_container_root) / 'sampleinfo.tsv'
    link.symlink_to(outside)
    with Session(engine) as session:
        for source in (outside, link):
            with pytest.raises(ValueError):
                submit(session, settings, airflow, sampleinfo_text=None, sampleinfo_path=str(source))
        assert session.scalar(select(AnalysisRun)) is None
        assert not airflow.calls


def test_existing_or_symlinked_destination_is_not_adopted(tmp_path):
    settings, airflow, engine = setup(tmp_path)
    root = Path(settings.wgs_analysis_project_container_root)
    target = root / 'WGS_20260910A_CCE_TEST_T7Hg38V4.2.1'
    target.mkdir()
    with Session(engine) as session:
        with pytest.raises(ValueError, match='exists'): submit(session, settings, airflow)
        (root / 'WGS_20260910A_LINK_T7Hg38V4.2.1').symlink_to(target, target_is_directory=True)
        with pytest.raises(ValueError): submit(session, settings, airflow, batch='20260910A_LINK')
        assert session.scalar(select(AnalysisRun)) is None


def test_missing_native_columns_rejected_before_creating_run(tmp_path):
    settings, airflow, engine = setup(tmp_path)
    incomplete = '上机批次\t分析批次\t样本编号\t数据编号\n20260910A\t20260910A\tSYNTH1\tDATA1\n'
    with Session(engine) as session:
        with pytest.raises(ValueError, match='columns'):
            submit(session, settings, airflow, sampleinfo_text=incomplete)
        assert session.scalar(select(AnalysisRun)) is None
        assert not airflow.calls


def test_interrupted_private_write_does_not_publish_partial_input(tmp_path, monkeypatch):
    import os
    settings, airflow, engine = setup(tmp_path)
    def interrupted(_fd):
        raise OSError('synthetic interrupted write')
    with Session(engine) as session, monkeypatch.context() as patch:
        patch.setattr(os, 'fsync', interrupted)
        with pytest.raises(OSError, match='interrupted'):
            submit(session, settings, airflow)
        assert not list(Path(settings.wgs_runtime_request_root).glob('*/sampleinfo-upload.tsv'))
        session.rollback()
    with Session(engine) as session:
        result = submit(session, settings, airflow)
        assert result['status'] == 'submitted'
