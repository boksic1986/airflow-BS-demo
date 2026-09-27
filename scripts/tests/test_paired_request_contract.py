"""Producer/consumer regression for registered WGS requests, without a database."""
import json
from pathlib import Path

import pytest

from app.wgs_runtime_adapter import build_stage_request, write_stage_request
from app.wgs_stage_execution_service import _sha256
from scripts import cce_paired_runtime as paired
from scripts import wgs_runtime_gate as gate


@pytest.fixture
def request_scope(tmp_path, monkeypatch):
    runtime = tmp_path / 'runtime'
    monkeypatch.setattr(gate, 'RUNTIME_RUN_ROOT', str(runtime / 'runs'))
    monkeypatch.setattr(gate, 'REQUEST_ROOT', runtime / 'runner-requests')
    body = build_stage_request(
        analysis_id='WGS_20260927_000000_ABCDEF', attempt=1, stage='step1_upload',
        pipeline_release_id='wgs-4.2.2-abcdef0', wgs_version='V4.2.2',
        wgs_source_commit='a' * 40, control_runtime_root=str(runtime),
        analysis_project_root=str(tmp_path / 'projects'), project_name='synthetic',
        batch_no='synthetic', fq_path=str(tmp_path / 'fastq'))

    def register(changes=None):
        base = {**body, **(changes or {})}
        # Same boundary as main.py: hash the body, then attach the envelope.
        payload = {**base, 'orchestration_contract_version': 2,
                   'execution_id': 'wse_synthetic', 'generation': 1,
                   'request_hash': _sha256(base),
                   'predecessor_execution_id': 'wse_prepare',
                   'predecessor_generation': 1, 'predecessor_receipt_hash': 'b' * 64}
        path = write_stage_request(runtime / 'runner-requests', payload)
        return payload, path

    return register


def test_accepts_producer_request_with_separate_control_directory(request_scope):
    payload, path = request_scope()
    assert Path(payload['control_workdir']) != path.parent
    found, raw = paired._registered_request(payload, gate, 'wgs')
    assert found == path
    assert json.loads(raw) == payload


def test_accepts_recovery_request_hashed_with_existing_version(request_scope):
    # register_recovery_stage preserves version2 in the frozen request body.
    payload, path = request_scope({'orchestration_contract_version': 2,
                                  'resume_action_id': 'resume_synthetic'})
    found, _ = paired._registered_request(payload, gate, 'wgs')
    assert found == path


@pytest.mark.parametrize('fault', ['unregistered_payload', 'changed_registered_body'])
def test_rejects_changed_request(request_scope, fault):
    payload, path = request_scope()
    payload['batch_no'] = 'changed'
    if fault == 'changed_registered_body':
        path.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match='changed or hash differs'):
        paired._registered_request(payload, gate, 'wgs')


@pytest.mark.parametrize('wrong_directory', ['other-attempt', 'request-directory', 'outside'])
def test_rejects_control_directory_outside_exact_attempt(request_scope, wrong_directory):
    payload, path = request_scope()
    control = Path(payload['control_workdir'])
    wrong = {'other-attempt': control.with_name('attempt-2'),
             'request-directory': path.parent, 'outside': Path('/outside/runs')}[wrong_directory]
    payload, _ = request_scope({'control_workdir': str(wrong)})
    with pytest.raises((RuntimeError, ValueError), match='scope|root'):
        paired._registered_request(payload, gate, 'wgs')


def test_gatk_digest_still_covers_contract_version():
    body = {'orchestration_contract_version': 2, 'analysis_id': 'GATK_synthetic'}
    payload = {**body, 'request_hash': _sha256(body)}
    assert paired._request_digest(payload, 'gatk') == payload['request_hash']
    payload['orchestration_contract_version'] = 1
    assert paired._request_digest(payload, 'gatk') != payload['request_hash']
