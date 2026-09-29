"""Only a frozen recovery deadline may bound the native writer probe."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import cce_paired_runtime as paired


class _WriterReached(Exception):
    pass


def _case(tmp_path, monkeypatch, *, pipeline, stage, deadline=None):
    analysis_id = pipeline.upper() + '_20260929_010203_A1B2C3'
    bundle = tmp_path / 'bundle'
    path = tmp_path / 'requests' / analysis_id / 'attempt-1' / (stage + '.json')
    path.parent.mkdir(parents=True)
    payload = dict(schema_version='deadline-handoff-synthetic.v1', pipeline=pipeline,
        analysis_id=analysis_id, attempt=1, stage=stage, generation=2,
        execution_id=analysis_id + '-a1-' + stage + '-g2',
        orchestration_contract_version=2, resume_action_id='recovery-action',
        stage_execution={'protocol':'cce.stage-execution.v1'})
    if deadline is not None:
        payload['cce_recovery_deadline'] = deadline
    payload['request_hash'] = paired._request_digest(payload, pipeline)
    path.write_text(json.dumps(payload), encoding='utf-8')
    gate = SimpleNamespace(_request_path=lambda *_:path)
    if pipeline == 'wgs':
        gate.RUNTIME_RUN_ROOT = str(tmp_path / 'run-root')
        gate._workdir = lambda request: (Path(gate.RUNTIME_RUN_ROOT).resolve()
            / request['analysis_id'] / f"attempt-{request['attempt']}")
    seen = []

    def writer_for_bundle(*args, **kwargs):
        seen.append(kwargs)
        raise _WriterReached

    runtime = SimpleNamespace(_load=lambda *_: ({}, {}, ()),
        writer_for_bundle=writer_for_bundle)
    monkeypatch.setattr(paired, 'load_runtime', lambda:runtime)
    return payload, path, {'cce_bundle':str(bundle)}, gate, seen


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
@pytest.mark.parametrize('stage', ['step2_master', 'step3_monitor'])
def test_recovery_writer_receives_only_registered_original_deadline(
        tmp_path, monkeypatch, pipeline, stage):
    deadline = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    payload, _, binding, gate, seen = _case(tmp_path, monkeypatch,
        pipeline=pipeline, stage=stage, deadline=deadline)
    with pytest.raises(_WriterReached):
        paired.resume_registered(payload, binding=binding, gate=gate,
            pipeline=pipeline)
    assert seen == [{'probe_deadline_epoch':datetime.fromisoformat(deadline).timestamp()}]


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
def test_recovery_without_frozen_deadline_keeps_previous_writer_interface(
        tmp_path, monkeypatch, pipeline):
    payload, _, binding, gate, seen = _case(tmp_path, monkeypatch,
        pipeline=pipeline, stage='step3_monitor')
    with pytest.raises(_WriterReached):
        paired.resume_registered(payload, binding=binding, gate=gate,
            pipeline=pipeline)
    assert seen == [{}]


@pytest.mark.parametrize('deadline', ['invalid', '2030-01-01T00:00:00'])
def test_invalid_frozen_deadline_rejected_before_writer(tmp_path, monkeypatch, deadline):
    payload, _, binding, gate, seen = _case(tmp_path, monkeypatch,
        pipeline='gatk', stage='step3_monitor', deadline=deadline)
    with pytest.raises(ValueError, match='invalid original compute deadline'):
        paired.resume_registered(payload, binding=binding, gate=gate,
            pipeline='gatk')
    assert not seen


def test_expired_original_deadline_rejected_before_writer(tmp_path, monkeypatch):
    deadline = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    payload, _, binding, gate, seen = _case(tmp_path, monkeypatch,
        pipeline='gatk', stage='step3_monitor', deadline=deadline)
    with pytest.raises(TimeoutError, match='original compute deadline exhausted'):
        paired.resume_registered(payload, binding=binding, gate=gate,
            pipeline='gatk')
    assert not seen


def test_changed_frozen_request_rejected_before_writer(tmp_path, monkeypatch):
    deadline = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    payload, _, binding, gate, seen = _case(tmp_path, monkeypatch,
        pipeline='gatk', stage='step3_monitor', deadline=deadline)
    payload['cce_recovery_deadline'] = (
        datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    with pytest.raises(RuntimeError, match='registered recovery request changed'):
        paired.resume_registered(payload, binding=binding, gate=gate,
            pipeline='gatk')
    assert not seen
