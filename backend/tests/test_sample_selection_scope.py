from types import SimpleNamespace
from app.sample_selection_scope import selection_state, participates
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Base, AnalysisRun, Sample
from app.sample_selection_scope import selected_clause
from app.wgs_platform_service import sync_prepare_handoff_decisions
from app.wgs_platform_service import sync_sampleinfo_preview
from app.diagnostics_service import sync_sample_statuses


@pytest.fixture
def scope_db():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = AnalysisRun(analysis_id='mock-scope', pipeline_name='wgs', dag_id='bio_wgs',
                          workdir='/mock', attempt=3, status='running')
        session.add(run)
        for index in range(12):
            session.add(Sample(analysis_id=run.analysis_id, sample_id=f'MOCK{index}', status='running'))
        session.flush()
        yield session, run


def receipt_for(run):
    return {'schema_version': 'wgs.prepare-analysis.receipt.v1',
            'analysis_id': run.analysis_id, 'attempt': run.attempt,
            'selected': [{'sample_id': f'MOCK{i}'} for i in range(6)],
            'pending': [{'sample_id': f'MOCK{i}', 'reason_message': 'awaiting family'} for i in range(6, 12)],
            'excluded': []}


def test_twelve_candidates_six_selected_and_pending_survive_terminal_sync(scope_db):
    session, run = scope_db
    receipt = receipt_for(run)
    sync_prepare_handoff_decisions(session=session, run=run, receipt=receipt)
    assert len(session.scalars(select(Sample).where(selected_clause())).all()) == 6
    run.status = 'success'
    sync_sample_statuses(session=session, analysis_id=run.analysis_id, run_status='success')
    sync_prepare_handoff_decisions(session=session, run=run, receipt=receipt)
    selected = session.scalars(select(Sample).where(selected_clause())).all()
    assert {row.status for row in selected} == {'success'}
    pending = session.scalars(select(Sample).where(Sample.sample_id == 'MOCK8')).one()
    assert pending.status == 'pending'
    assert pending.metadata_json['pending_reason'] == 'awaiting family'
    assert len(session.scalars(select(Sample)).all()) == 12
    run.attempt = 4
    session.flush()
    assert session.scalars(select(Sample).where(selected_clause())).all() == []
    sync_sample_statuses(session=session, analysis_id=run.analysis_id, run_status='running')
    assert pending.status == 'pending'


@pytest.mark.parametrize('change', ['attempt', 'identity', 'overlap', 'incomplete'])
def test_invalid_receipt_never_changes_samples(scope_db, change):
    session, run = scope_db
    receipt = receipt_for(run)
    if change == 'attempt': receipt['attempt'] = 2
    if change == 'identity': receipt['analysis_id'] = 'another-run'
    if change == 'overlap': receipt['pending'].append({'sample_id': 'MOCK0'})
    if change == 'incomplete': receipt.pop('pending')
    with pytest.raises(ValueError):
        sync_prepare_handoff_decisions(session=session, run=run, receipt=receipt)
    assert all(not row.metadata_json for row in session.scalars(select(Sample)).all())


def test_preview_does_not_delete_audit_or_replace_current_selection(scope_db, tmp_path):
    session, run = scope_db
    run.params_json = {'batch_no': 'MOCK_BATCH'}
    sync_prepare_handoff_decisions(session=session, run=run, receipt=receipt_for(run))
    (tmp_path / 'sampleinfo').mkdir()
    (tmp_path / 'sampleinfo' / 'MOCK_BATCH.sampleinfo.txt').write_text('样本编号\t家系编号\nMOCK0\tMOCK_FAMILY\n', encoding='utf-8')
    settings = SimpleNamespace(host_results_root=str(tmp_path), wgs_analysis_project_container_root=str(tmp_path))
    sync_sampleinfo_preview(session=session, settings=settings, run=run)
    rows = session.scalars(select(Sample)).all()
    assert len(rows) == 12
    selected = next(row for row in rows if row.sample_id == 'MOCK0')
    assert selected.metadata_json['selection_decision'] == 'selected'
    assert selected.status == 'running'


def test_selected_counts_match_list_detail_dashboard_and_qc_inputs(scope_db, monkeypatch):
    from app.run_service import list_runs, get_run_detail, list_run_samples
    from app.dashboard_service import _sample_qc_by_run, _samples_for_period
    from datetime import datetime, timezone
    from app.wgs_sample_projection import get_wgs_sample_projection
    from app.operator_resources_service import list_samples_resource
    session, run = scope_db
    sync_prepare_handoff_decisions(session=session, run=run, receipt=receipt_for(run))
    assert list_runs(session=session)['items'][0]['sample_count'] == 6
    assert get_run_detail(session=session, analysis_id=run.analysis_id)['sample_count'] == 6
    assert len(list_run_samples(session=session, analysis_id=run.analysis_id)) == 6
    assert len(_sample_qc_by_run(session=session, runs=[run])[run.analysis_id]) == 6
    assert len(_samples_for_period(session=session, pipeline_names=('wgs',), since=datetime(2020, 1, 1, tzinfo=timezone.utc))) == 6
    monkeypatch.setattr('app.wgs_sample_projection._batch_root', lambda **_: None)
    assert len(get_wgs_sample_projection(session=session, settings=SimpleNamespace(), run=run)['items']) == 6
    pending = list_samples_resource(session=session, pipeline='wgs', status='pending', qc_status=None,
                                   keyword=None, limit=50, offset=0, deployed_pipelines=('wgs',))
    assert pending['total'] == 6


def test_repair_dry_run_and_idempotent_apply(scope_db, tmp_path):
    import json
    from app.sample_selection_repair import repair_sample_scope
    session, run = scope_db
    root = tmp_path / 'runs' / run.analysis_id / 'attempt-3' / 'prepare-handoff'
    root.mkdir(parents=True)
    final = receipt_for(run)
    final.update(generation=1, execution_id='MOCK_EXECUTION', request_hash='MOCK_HASH')
    preview = {**final, 'schema_version': 'wgs.prepare-sampleinfo.receipt.v1',
               'safe_candidates': final['selected'] + final['pending']}
    for stage, value in [('prepare_sampleinfo', preview), ('prepare_analysis', final)]:
        stage_root = root / stage / 'generation-1'
        stage_root.mkdir(parents=True)
        (stage_root / f'{stage}.receipt.json').write_text(json.dumps(value), encoding='utf-8')
        (stage_root / 'handoff-request.json').write_text(json.dumps(value), encoding='utf-8')
    args = dict(session=session, runtime_root=tmp_path, analysis_id=run.analysis_id, attempt=3)
    assert repair_sample_scope(**args)['before_selected'] == 12
    assert all(not row.metadata_json for row in session.scalars(select(Sample)).all())
    assert repair_sample_scope(**args, apply=True)['selected'] == 6
    assert repair_sample_scope(**args, apply=True)['before_selected'] == 6
    assert len(session.scalars(select(Sample)).all()) == 12


def test_pending_never_inherits_execution_status():
    run=SimpleNamespace(attempt=3)
    sample=SimpleNamespace(metadata_json={'selection_decision':'pending','selection_attempt':3})
    assert selection_state(sample,run)=='pending'
    assert not participates(sample,run)


def test_current_selected_legacy_and_stale_attempt():
    run=SimpleNamespace(attempt=3)
    assert participates(SimpleNamespace(metadata_json={}),run)
    assert participates(SimpleNamespace(metadata_json={'selection_decision':'selected','selection_attempt':3}),run)
    assert not participates(SimpleNamespace(metadata_json={'selection_decision':'selected','selection_attempt':2}),run)
