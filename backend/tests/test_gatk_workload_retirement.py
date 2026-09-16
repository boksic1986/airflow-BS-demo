"""GATK stopped Pods must not strand the explicit SFS release action."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Base, KubernetesWorkload, PipelineStageExecution
from app.gatk_step7_service import _check
from app.wgs_observer import _apply_pod_event


LABEL = 'cce-run-0123456789abcdef'


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('bridge', Path(__file__).parents[2]/'scripts/wgs_evidence_bridge.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = tmp_path/'master.yaml'
    manifest.write_text(json.dumps({'metadata': {'labels': {'cce.biosan.cn/run-id': LABEL}}}))
    output = tmp_path/'evidence'
    output.mkdir()
    (output/'.workload-snapshot-cursor.json').write_text(json.dumps({'pods:old-pod': '7'}))
    monkeypatch.setattr(module, '_job_snapshot_items', lambda **kw: [])
    args = dict(config={'kubernetes': {'kubectl_bin': 'kubectl', 'kubeconfig': '/mock/config'}},
                namespace='mock', master_job='master', master_manifest=manifest, output=output,
                run_label_key='cce.biosan.cn/run-id')
    return module, args


def test_complete_inventory_retires_missing_pod_once(bridge, monkeypatch):
    module, args = bridge
    def inventory(command):
        assert '-l' not in command  # Namespace inventory also detects changed labels.
        return {'items': []}
    monkeypatch.setattr(module, '_run_json', inventory)
    assert module._sync_workload_snapshots(**args) == 1
    event = json.loads((args['output']/'raw/pod-events.jsonl').read_text())
    assert event['phase'] == 'Deleted'
    assert event['reason'] == 'PodNotFound'
    assert event['run_label'] == LABEL
    assert module._sync_workload_snapshots(**args) == 0


@pytest.mark.parametrize('inventory', [{}, {'items': None}, {'items': [], 'metadata': {'continue': 'next'}}])
def test_incomplete_inventory_cannot_retire_pods(bridge, monkeypatch, inventory):
    module, args = bridge
    monkeypatch.setattr(module, '_run_json', lambda command: inventory)
    with pytest.raises(ValueError):
        module._sync_workload_snapshots(**args)
    assert not (args['output']/'raw/pod-events.jsonl').exists()


def test_running_pod_with_changed_label_is_not_absent(bridge, monkeypatch):
    module, args = bridge
    monkeypatch.setattr(module, '_run_json', lambda command: {'items': [{
        'metadata': {'name': 'old-pod', 'resourceVersion': '8', 'labels': {'cce.biosan.cn/run-id': 'other'}},
        'status': {'phase': 'Running'}}]})
    with pytest.raises(ValueError):
        module._sync_workload_snapshots(**args)
    assert not (args['output']/'raw/pod-events.jsonl').exists()


@pytest.mark.parametrize('phase,reason,blocked', [('Deleted','PodNotFound',False),
    ('Deleted',None,True),('Unknown',None,True),('Running',None,True),('Succeeded',None,False)])
def test_cleanup_only_accepts_confirmed_inactive_workloads(phase, reason, blocked):
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = AnalysisRun(analysis_id='GATK_mock', pipeline_name='gatk', attempt=1,
                          dag_id='bio_gatk', status='success', workdir='/mock', params_json={})
        session.add(run)
        for stage in ('step5_download','step6_materialize'):
            session.add(PipelineStageExecution(execution_id=stage, pipeline_name='gatk',
                analysis_id=run.analysis_id, attempt=1, stage_code=stage, generation=1,
                status='success', request_hash='a'*64, receipt_hash='b'*64, release_id='mock'))
        session.add(KubernetesWorkload(analysis_id=run.analysis_id, attempt=1,
            pod_hash='pod', event_id='pod:7', phase=phase, reason=reason))
        session.flush()
        if blocked:
            with pytest.raises(ValueError, match='cce_workload_active'):
                _check(session, SimpleNamespace(gatk_execution_enabled=True), run)
        else:
            assert _check(session, SimpleNamespace(gatk_execution_enabled=True), run).stage_code == 'step6_materialize'


def test_late_running_event_cannot_reopen_confirmed_missing_pod():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        binding = SimpleNamespace(analysis_id='GATK_mock', attempt=1)
        row = KubernetesWorkload(analysis_id=binding.analysis_id, attempt=1, pod_hash='pod',
            event_id='deleted:7', phase='Deleted', reason='PodNotFound', resource_version='7',
            observed_at=datetime(2026,9,16,2,tzinfo=timezone.utc))
        session.add(row)
        session.flush()
        _apply_pod_event(session,binding,'raw/pod-events.jsonl',{'pod_hash':'pod',
            'event_key':'pod:7','phase':'Running','resource_version':'7',
            'observed_at_utc':'2026-09-16T01:00:00Z'})
        assert row.phase == 'Deleted'


def test_terminal_collection_refreshes_after_reader_cleanup(bridge, monkeypatch):
    module,args = bridge
    calls=[]
    monkeypatch.setattr(module,'_sync_workload_snapshots', lambda **kw: calls.append('snapshot') or 0)
    monkeypatch.setattr(module,'_master_pod',lambda *a: None)
    monkeypatch.setattr(module,'_final_reader_chunks',lambda *a: calls.append('reader') or ([],None,None))
    config=args.pop('config')
    path=args['output']/'config.yaml'
    path.write_text(json.dumps(config))
    module.sync_rule_events_once(**args,operator_config=path,
        source_dir='/workspace/run/evidence/raw/rule-status/raw',analysis_log_source=None,terminal=True)
    assert calls == ['snapshot','reader','snapshot']


@pytest.mark.parametrize('error', [None, 'query unavailable'])
def test_delivery_refreshes_workloads_without_reopening_analysis(tmp_path, monkeypatch, error):
    spec = importlib.util.spec_from_file_location('gate', Path(__file__).parents[2]/'scripts/gatk_runtime_gate.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    payload = {'analysis_id':'GATK_mock','attempt':1,'stage':'step6_materialize'}
    calls=[]
    monkeypatch.setattr(gate,'_load',lambda *a: (tmp_path/'request.json',payload))
    monkeypatch.setattr(gate,'_materialize',lambda p: calls.append('delivery'))
    monkeypatch.setattr(gate,'_load_binding',lambda p: {})
    def sync(p,b,*,terminal):
        assert terminal is False  # No reader Job is created after delivery.
        calls.append('snapshot')
        return error
    monkeypatch.setattr(gate,'_sync_evidence',sync)
    monkeypatch.setattr(gate,'_write_status',lambda p,v,state,message,**kw: calls.append(state))
    gate._execute('GATK_mock',1,'step6_materialize')
    assert calls[-3:] == ['delivery','snapshot','success']
