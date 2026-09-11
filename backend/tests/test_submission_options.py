from pathlib import Path
from types import SimpleNamespace

import pytest

from app import wgs_release_catalog


def test_current_release_offers_only_actual_owner_callers():
    release = wgs_release_catalog.load_wgs_release_catalog(Path('/src/config/wgs_releases.yaml')).release
    options = getattr(wgs_release_catalog, 'submission_options', lambda _: {})(release)
    assert options.get('callers') == [
        {'value': 'DNAscope', 'label': 'Sentieon DNAscope'},
        {'value': 'Haplotyper', 'label': 'Sentieon Haplotyper'},
    ]
    assert options['reference_values'] == ['all', 'ref', 'no']
    assert options['defaults']=={'algo':'DNAscope','use_reference':'all'}
    assert len(options['effective_config']['prepare_sha256'])==64
    assert options['effective_config']['source_commit']==release.source_commit


def test_unknown_release_never_inherits_current_options():
    options = getattr(wgs_release_catalog, 'submission_options', lambda _: {})(SimpleNamespace(source_commit='0'*40))
    assert options.get('callers') == []
    assert 'defaults' not in options


def test_configuration_review_cannot_change_first_step_frozen_reference():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.models import Base, AnalysisRun
    from app.wgs_submission_service import approve_wgs_config
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(AnalysisRun(analysis_id='WGS_20260912_000000_ABCDEF', pipeline_name='wgs', dag_id='bio_wgs', workdir='/synthetic', status='running', params_json={'submission_mode':'three_stage', 'submission_phase':'config_review', 'use_reference':'all', 'submission_options':{'use_reference':'all','algo':'DNAscope'}}))
        session.commit()
        with pytest.raises(ValueError, match='frozen'):
            approve_wgs_config(session=session, analysis_id='WGS_20260912_000000_ABCDEF', requested_by='tester', use_reference='no', resource_set='default')


@pytest.mark.parametrize('flag,contract',[(False,''),(True,''),(False,'wgs-submission-options.v1'),(True,'old-gate')])
@pytest.mark.parametrize('overrides',[{'algo':'Haplotyper'},{'use_reference':'no'}])
def test_unactivated_catalog_options_reject_before_record_creation(flag,contract,overrides):
    from app.wgs_submission_service import create_and_submit_run
    settings=SimpleNamespace(wgs_release_catalog_path='/src/config/wgs_releases.yaml',wgs_config_options_enabled=flag,wgs_config_options_runtime_contract=contract,wgs_test_project_enabled=True)
    with pytest.raises(ValueError,match='configuration options are not activated'):
        create_and_submit_run(session=None,settings=settings,airflow_client=None,username='operator',project_id='ignored',platform='T7',batch='20260912A',fastq_root_id='ignored',**overrides)


def test_release_api_reports_catalog_activation_separately_from_audited_enums(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    settings=SimpleNamespace(wgs_release_catalog_path='/src/config/wgs_releases.yaml',wgs_config_options_enabled=True,wgs_config_options_runtime_contract='',wgs_test_project_enabled=True,platform_environment='test')
    monkeypatch.setattr(main,'get_settings',lambda:settings)
    with TestClient(main.app) as client:
        inactive=client.get('/api/wgs/release').json()
        assert inactive['config_options_enabled'] is False
        assert inactive['submission_options']['callers']
        settings.wgs_config_options_runtime_contract='wgs-submission-options.v1'
        assert client.get('/api/wgs/release').json()['config_options_enabled'] is True
