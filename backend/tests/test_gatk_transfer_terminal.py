import json
from pathlib import Path

import pytest
from sqlalchemy import select

from test_gatk_runtime_service import ANALYSIS_ID, _sessions, _settings, _run, _execution
from app.gatk_runtime_service import sync_gatk_stage_status
from app.models import ObsTransferLease, TransferJob
from app.wgs_observer import _current_execution_from_payload


def seed(tmp_path, stage='step1_upload', status='success', persisted=False):
    sessions, settings = _sessions(), _settings(tmp_path)
    kind, direction, slot = ('input','upload','wgs-obs-upload-01') if stage == 'step1_upload' else ('result','download','wgs-obs-download-01')
    row = _execution(stage, 3, status if persisted else 'running')
    payload = dict(analysis_id=ANALYSIS_ID, attempt=1, stage=stage, generation=3,
                   request_hash=row.request_hash, execution_id=row.execution_id,
                   status=status, receipt_hash='b'*64)
    if persisted:
        row.terminal_payload_json = payload
        row.receipt_hash = 'b'*64
    path=Path(settings.gatk_runtime_request_root)/ANALYSIS_ID/'attempt-1'/f'{stage}.request.status.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload))
    with sessions() as s:
        s.add_all([_run(),row,TransferJob(analysis_id=ANALYSIS_ID,attempt=1,
            transfer_id=f'{ANALYSIS_ID}-a1-{kind}',direction=direction,status='running',bytes_total=100,bytes_transferred=20),
            ObsTransferLease(slot_name=slot,analysis_id=ANALYSIS_ID,attempt=1,transfer_id=f'{ANALYSIS_ID}-a1-{kind}')])
        s.commit()
    return sessions,settings,path,payload


@pytest.mark.parametrize('stage',['step1_upload','step5_download'])
@pytest.mark.parametrize('status',['success','failed','canceled'])
@pytest.mark.parametrize('persisted',[False,True])
def test_terminal_receipt_repairs_transfer_and_releases_idempotently(tmp_path,stage,status,persisted):
    sessions,settings,_,_=seed(tmp_path,stage,status,persisted)
    for _ in range(2):
        with sessions() as s:
            sync_gatk_stage_status(session=s,settings=settings,analysis_id=ANALYSIS_ID,attempt=1,stage=stage)
            t=s.scalar(select(TransferJob));lease=s.scalar(select(ObsTransferLease))
            assert t.status==status
            assert t.ended_at is not None
            assert t.bytes_transferred==20  # Do not fabricate measured byte counts.
            assert lease.analysis_id is None


@pytest.mark.parametrize('mutation',['generation','request_hash','execution_id','attempt'])
def test_mismatched_receipt_never_releases(tmp_path,mutation):
    sessions,settings,path,payload=seed(tmp_path)
    payload[mutation]=2 if mutation in ('generation','attempt') else 'wrong'
    path.write_text(json.dumps(payload))
    with sessions() as s:
        try:
            sync_gatk_stage_status(session=s,settings=settings,analysis_id=ANALYSIS_ID,attempt=1,stage='step1_upload')
        except ValueError:
            pass
        assert s.scalar(select(ObsTransferLease)).analysis_id==ANALYSIS_ID
        assert s.scalar(select(TransferJob)).status=='running'


def test_other_owner_not_released(tmp_path):
    sessions,settings,_,_=seed(tmp_path)
    with sessions() as s:
        s.scalar(select(ObsTransferLease)).analysis_id='another-run'
        s.commit()
        sync_gatk_stage_status(session=s,settings=settings,analysis_id=ANALYSIS_ID,attempt=1,stage='step1_upload')
        assert s.scalar(select(ObsTransferLease)).analysis_id=='another-run'


def test_late_running_progress_rejected_after_terminal_receipt(tmp_path):
    sessions,settings,_,payload=seed(tmp_path,persisted=True)
    payload.update(orchestration_contract_version=2,status='running')
    with sessions() as s:
        assert _current_execution_from_payload(session=s,analysis_id=ANALYSIS_ID,attempt=1,stage_code='step1_upload',payload=payload) is None


def test_release_failure_is_repaired_on_next_poll(tmp_path,monkeypatch):
    import app.wgs_platform_service as service
    sessions,settings,_,_=seed(tmp_path)
    original=service.release_obs_transfer_slot
    def unavailable(**kwargs):
        raise RuntimeError('database unavailable')
    monkeypatch.setattr(service,'release_obs_transfer_slot',unavailable)
    with sessions() as s, pytest.raises(RuntimeError):
        sync_gatk_stage_status(session=s,settings=settings,analysis_id=ANALYSIS_ID,attempt=1,stage='step1_upload')
    monkeypatch.setattr(service,'release_obs_transfer_slot',original)
    with sessions() as s:
        sync_gatk_stage_status(session=s,settings=settings,analysis_id=ANALYSIS_ID,attempt=1,stage='step1_upload')
        assert s.scalar(select(ObsTransferLease)).analysis_id is None


def test_missing_progress_row_can_converge_from_receipt(tmp_path):
    sessions,settings,_,_=seed(tmp_path)
    with sessions() as s:
        s.delete(s.scalar(select(TransferJob)));s.commit()
        sync_gatk_stage_status(session=s,settings=settings,analysis_id=ANALYSIS_ID,attempt=1,stage='step1_upload')
        assert s.scalar(select(TransferJob)).status=='success'
        assert s.scalar(select(ObsTransferLease)).analysis_id is None


def test_old_generation_progress_rejected_when_new_stage_exists(tmp_path):
    sessions,settings,_,payload=seed(tmp_path)
    payload.update(orchestration_contract_version=2,status='running')
    with sessions() as s:
        s.add(_execution('step1_upload',4,'running'));s.commit()
        assert _current_execution_from_payload(session=s,analysis_id=ANALYSIS_ID,attempt=1,stage_code='step1_upload',payload=payload) is None
