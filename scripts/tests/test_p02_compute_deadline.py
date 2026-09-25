"""Original compute deadline survives native replacement and monitor restart."""
from datetime import datetime, timezone
import json

import pytest

from test_p02_resume_final import adapter, mirrored_final, final_inputs, view_inputs, handoff, runtime
from test_p02_registered_recovery import registered


@pytest.mark.parametrize('view_inputs',[
    {'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}], indirect=True)
@pytest.mark.parametrize('expired', [False, True])
def test_native_replacement_keeps_original_deadline(adapter, expired):
    state, invoke, bundle, cap, h = adapter
    cap.compute_deadline = h.now + (-1 if expired else 90)
    if expired:
        with pytest.raises(TimeoutError, match='compute deadline'):
            invoke()
        assert (state.deletes, state.creates, state.starts) == (0, 0, 0)
    else:
        result = invoke()
        from pathlib import Path
        selected = Path(result['bundle'])
        assert runtime._read_master_handoff(selected, h.contract)['deadline_epoch'] == cap.compute_deadline
        invoke()
        assert (state.deletes, state.creates, state.starts) == (1, 1, 1)
        cap.compute_deadline += 60
        with pytest.raises(RuntimeError, match='reconciliation'):
            invoke()


@pytest.mark.parametrize('view_inputs',[
    {'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}], indirect=True)
@pytest.mark.parametrize('active', [False, True])
def test_registered_request_deadline_reaches_native(registered, active):
    import hashlib
    state, invoke, gate, payload, request, policy, bundle, h = registered
    if active:
        state.job['status'] = {'active':1}
    payload['cce_recovery_deadline'] = datetime.fromtimestamp(h.now-1, timezone.utc).isoformat()
    excluded = {'request_hash'} if payload.get('pipeline') == 'gatk' else {
        'execution_id','generation','request_hash','predecessor_execution_id',
        'predecessor_generation','predecessor_receipt_hash'}
    payload['request_hash'] = hashlib.sha256(json.dumps({k:v for k,v in payload.items()
        if k not in excluded},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    request.write_text(json.dumps(payload))
    with pytest.raises(TimeoutError, match='compute deadline'):
        invoke()
    assert (state.deletes, state.creates, state.starts) == (0, 0, 0)


def test_monitor_restart_and_sleep_share_absolute_deadline(monkeypatch):
    from scripts import cce_recovery_deadline as deadline
    clock = [1000.0]
    monkeypatch.setattr(deadline.time, 'time', lambda:clock[0])
    payload = {'cce_recovery_deadline':datetime.fromtimestamp(1010, timezone.utc).isoformat()}
    assert deadline.monitor_wait(payload, 30) == 10
    clock[0] = 1008
    assert deadline.monitor_wait(dict(payload), 30) == 2
    clock[0] = 1010
    with pytest.raises(TimeoutError, match='compute deadline'):
        deadline.monitor_wait(dict(payload), 30)
    assert deadline.monitor_wait({}, 30) == 30  # Default-off and historical requests unchanged.


@pytest.mark.parametrize('value', [None, 1000, 'bad', '2026-09-25T12:00:00'])
def test_invalid_registered_deadline_is_not_legacy(value):
    from scripts.cce_recovery_deadline import deadline_epoch
    with pytest.raises(ValueError, match='compute deadline'):
        deadline_epoch({'cce_recovery_deadline':value})


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
def test_actual_monitor_loop_expires_without_reset_or_second_poll(tmp_path, monkeypatch, pipeline):
    import sys
    from scripts import cce_paired_runtime as paired, cce_recovery_deadline as deadline
    from scripts import wgs_runtime_gate, gatk_runtime_gate
    gate = wgs_runtime_gate if pipeline == 'wgs' else gatk_runtime_gate
    monkeypatch.setitem(sys.modules, 'cce_paired_runtime', paired)
    monkeypatch.setitem(sys.modules, 'cce_recovery_deadline', deadline)
    clock, polls, sleeps = [1000.0], [], []
    payload = dict(analysis_id='synthetic',attempt=1,stage='step3_monitor',generation=1,
        cce_recovery_deadline=datetime.fromtimestamp(1002, timezone.utc).isoformat(),
        _cce_master_result={'bundle':'synthetic-selected'})
    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    def observe(*a, **kw):
        polls.append(1)
        return {'master_state':'RUNNING','message':'synthetic active Master'}
    monkeypatch.setattr(deadline.time, 'time', lambda:clock[0])
    monkeypatch.setattr(gate.time, 'sleep', sleep)
    monkeypatch.setattr(paired, 'monitor_registered', observe)
    monkeypatch.setattr(paired, 'prepare_monitor_registered', lambda *a, **kw:None)
    monkeypatch.setattr(gate, '_load_binding', lambda p:{'run_label':'synthetic'})
    monkeypatch.setattr(gate, '_write_status', lambda *a, **kw:None)
    monkeypatch.setattr(gate, '_sync_rule_evidence' if pipeline == 'wgs' else '_sync_evidence', lambda *a, **kw:None)
    if pipeline == 'wgs':
        monkeypatch.setattr(gate, '_binding_run_label', lambda b:'synthetic')
        invoke = lambda:gate._monitor_step3(dict(payload))
    else:
        monkeypatch.setattr(gate, '_load', lambda *a:(tmp_path/'request.json', dict(payload)))
        invoke = lambda:gate._execute_stage('synthetic',1,'step3_monitor',1)
    with pytest.raises(TimeoutError, match='compute deadline'):
        invoke()
    with pytest.raises(TimeoutError, match='compute deadline'):
        invoke()  # Restarting the same registered request must not grant more time.
    assert sleeps == [2.0] and polls == [1]


@pytest.mark.parametrize('boundary', ['delete', 'create', 'start'])
def test_deadline_rechecked_at_native_side_effect_boundaries(adapter, monkeypatch, boundary):
    state, invoke, bundle, cap, h = adapter
    cap.compute_deadline = h.now + 10
    if boundary == 'delete':
        original = cap.claim
        def delayed_claim(*a, **kw):
            original(*a, **kw)
            h.now += 11
        monkeypatch.setattr(cap, 'claim', delayed_claim)
    elif boundary == 'create':
        original = runtime._delete_recovery_master
        def delayed_delete(*a, **kw):
            original(*a, **kw)
            h.now += 11
        monkeypatch.setattr(runtime, '_delete_recovery_master', delayed_delete)
    else:
        original = runtime._create_job_from_path
        def delayed_create(*a, **kw):
            result = original(*a, **kw)
            h.now += 11
            return result
        monkeypatch.setattr(runtime, '_create_job_from_path', delayed_create)
    with pytest.raises(TimeoutError, match='compute deadline'):
        invoke()
    assert state.deletes == (boundary != 'delete')
    assert state.creates == (boundary == 'start')
    assert state.starts == 0


@pytest.mark.parametrize('view_inputs',[
    {'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}], indirect=True)
def test_untagged_manual_resume_keeps_accepted_native_signature(adapter, monkeypatch):
    state, invoke, bundle, cap, h = adapter
    advance = runtime._advance_recovery_view
    def accepted_signature(*a, **kw):
        assert 'compute_deadline' not in kw  # Existing Task5 artifact has no new keyword.
        return advance(*a, **kw)
    monkeypatch.setattr(runtime, '_advance_recovery_view', accepted_signature)
    invoke()
    assert (state.deletes, state.creates, state.starts) == (1, 1, 1)
