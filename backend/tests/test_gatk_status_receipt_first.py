import json
from pathlib import Path

import pytest

from app import gatk_runtime_service as service
from test_gatk_runtime_service import ANALYSIS_ID, _execution, _run, _sessions, _settings


def _receipt(settings, row, **overrides):
    path = Path(settings.gatk_runtime_request_root) / ANALYSIS_ID / 'attempt-1' / f'{row.stage_code}.request.status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    value = dict(analysis_id=ANALYSIS_ID, attempt=1, stage=row.stage_code,
                 generation=row.generation, execution_id=row.execution_id,
                 request_hash=row.request_hash, status='success')
    value.update(overrides)
    path.write_text(json.dumps(value))


def _slow_ingestion(**kwargs):
    raise TimeoutError('rule evidence import exceeded the HTTP deadline')


@pytest.mark.parametrize('stage', ['step1_upload', 'step3_monitor', 'step5_download', 'step6_materialize'])
@pytest.mark.parametrize('terminal', ['success', 'failed'])
def test_terminal_receipt_is_not_blocked_by_rule_ingestion(tmp_path, monkeypatch, stage, terminal):
    settings = _settings(tmp_path)
    sessions = _sessions()
    row = _execution(stage, 3, 'running')
    _receipt(settings, row, status=terminal)
    monkeypatch.setattr(service, '_ingest_gatk_evidence', _slow_ingestion)
    with sessions() as session:
        session.add_all([_run(), row])
        session.commit()
        result = service.sync_gatk_stage_status(session=session, settings=settings,
                    analysis_id=ANALYSIS_ID, attempt=1, stage=stage)
        assert result['status'] == terminal
        assert result['ready'] is (terminal == 'success')
        assert result['failed'] is (terminal == 'failed')
        assert row.receipt_hash
        assert row.terminal_payload_json['generation'] == 3


@pytest.mark.parametrize('field,value', [('analysis_id', 'OTHER'), ('attempt', 2),
    ('generation', 4), ('request_hash', 'wrong'), ('execution_id', 'wrong')])
def test_terminal_receipt_identity_is_checked_before_ingestion(tmp_path, monkeypatch, field, value):
    settings = _settings(tmp_path)
    sessions = _sessions()
    row = _execution('step3_monitor', 3, 'running')
    _receipt(settings, row, **{field: value})
    monkeypatch.setattr(service, '_ingest_gatk_evidence', _slow_ingestion)
    with sessions() as session:
        session.add_all([_run(), row])
        session.commit()
        with pytest.raises(ValueError, match='identity mismatch'):
            service.sync_gatk_stage_status(session=session, settings=settings,
                analysis_id=ANALYSIS_ID, attempt=1, stage='step3_monitor')
        assert row.status == 'running'


def test_running_receipt_still_ingests_evidence(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    sessions = _sessions()
    row = _execution('step3_monitor', 3, 'running')
    _receipt(settings, row, status='running')
    monkeypatch.setattr(service, '_ingest_gatk_evidence', _slow_ingestion)
    with sessions() as session:
        session.add_all([_run(), row])
        session.commit()
        with pytest.raises(TimeoutError, match='rule evidence import'):
            service.sync_gatk_stage_status(session=session, settings=settings,
                analysis_id=ANALYSIS_ID, attempt=1, stage='step3_monitor')
