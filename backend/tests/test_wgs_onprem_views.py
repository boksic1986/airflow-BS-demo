"""Native history stays isolated; QC is the latest project result, not per execution."""
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.models import AnalysisRun, WgsStageExecution
from test_wgs_onprem_registration import context, write_binding
from test_wgs_onprem_execution import setup_execution, inputs


def history(context, tmp_path):
    client, factory, _, data = context
    url, body, _ = setup_execution(context, tmp_path)
    config = Path(data['project_dir']) / 'config.yaml'
    config.write_text(config.read_text() + 'batch: SYN_QC_BATCH\n')
    first = client.post(url, json=body).json()
    with factory() as session:
        session.scalar(select(WgsStageExecution)).status = 'success'
        session.commit()
    inputs(data['project_dir'], sample='SYN_NEW', family='SYN_F2', caller='dnascope')
    config.write_text(config.read_text() + 'batch: SYN_QC_BATCH\n')
    second = client.post(url, json={**body, 'operation_id': str(uuid4())}).json()
    return first, second, f"/api/runs/{first['analysis_id']}/native-view"


def test_current_and_history_scope_share_latest_qc_not_current_names(context, tmp_path):
    client, factory, _, data = context
    first, second, url = history(context, tmp_path)
    root = Path(data['project_dir'])
    (root / '07_QC').mkdir()
    qc = root / '07_QC' / 'SYN_QC_BATCH.QCstat.tsv'
    qc.write_text('Sample_ID\t是否通过质控\tAverage_Depth\nSYN_A\tPASS\t32\n')
    result = client.get(url)
    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload['selected']['execution_id'] == second['execution_id']
    assert payload['configuration']['parameters']['caller'] == 'dnascope'
    assert [row['data_id'] for row in payload['samples']] == ['SYN_NEW']
    assert payload['qc']['scope'] == 'run_latest'
    assert payload['qc']['items'][0]['sample_id'] == 'SYN_A'
    old = client.get(url, params={'execution_id': first['execution_id']}).json()
    assert [row['data_id'] for row in old['samples']] == ['SYN_A']
    assert old['configuration']['parameters']['caller'] == 'haplotyper'
    assert old['qc'] == payload['qc']
    qc.write_text('Sample_ID\t是否通过质控\tAverage_Depth\nSYN_NEW\tPASS\t41\n')
    updated = client.get(url, params={'execution_id': first['execution_id']}).json()
    assert updated['qc']['items'][0]['sample_id'] == 'SYN_NEW'
    assert updated['qc']['items'][0]['qc_metrics']['average_depth'] == '41'
    qc.write_text('Sample_ID\t是否通过质控\tAverage_Depth\nSYN_NEW\t')
    unavailable = client.get(url).json()
    assert unavailable['qc']['items'] == updated['qc']['items']
    assert unavailable['qc']['health'] == 'stale'
    assert client.get(url, params={'execution_id': 'OTHER_RUN_EXECUTION'}).status_code == 404
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).attempt == 1


def test_exact_log_and_rule_inventory_never_reads_reused_project(context, tmp_path):
    client, _, _, data = context
    first, second, url = history(context, tmp_path)
    root = Path(data['project_dir'])
    (root / 'log').mkdir()
    native_id = f"{first['analysis_id']}-a1-g1-{first['execution_id']}"
    (root / 'log' / f'step1.{native_id}.log').write_text(
        'rule pre_process_mapping:\n    jobid: 3\n    wildcards: sample=SYN_A\n\n'
        'Finished job 3.\nrule other:\n    jobid: 4\n    wildcards: sample=SYN_NEW\n\n')
    old = client.get(url, params={'execution_id': first['execution_id'], 'section': 'rules'} )
    assert old.status_code == 200, old.text
    assert old.json()['rules'][0]['sample_id'] == 'SYN_METADATA'
    assert old.json()['rules'][0]['status'] == 'success'
    assert old.json()['rules'][1]['sample_id'] is None
    assert old.json()['rules'][1]['status'] == 'unknown'
    log = client.get(url, params={'execution_id': first['execution_id'], 'section': 'logs', 'query': 'MAPPING'}).json()
    assert log['log']['match_count'] == 1
    assert 'mapping' in log['log']['lines'][log['log']['match_line']]
    assert '    jobid: 3' in log['log']['lines']
    next_match = client.get(url, params={'execution_id': first['execution_id'], 'section': 'logs', 'query': 'rule', 'match_index': 1}).json()['log']
    assert next_match['match_index'] == 1
    assert next_match['lines'][next_match['match_line']] == 'rule other:'
    write_binding({**data, 'project_uuid': str(uuid4())})
    blocked = client.get(url, params={'execution_id': first['execution_id'], 'section': 'logs'}).json()
    assert blocked['log']['lines'] == [] and blocked['evidence_health'] == 'unavailable'
    assert blocked['samples'][0]['data_id'] == 'SYN_A'


def test_native_workspace_is_read_only_without_cloud_controls(context, tmp_path):
    client, _, _, _ = context
    first, _, _ = history(context, tmp_path)
    response = client.get(f"/api/runs/{first['analysis_id']}/workspace")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['run']['params']['native_monitor_only'] is True
    assert payload['summary']['sample_count'] == 1
    assert payload['slot_usage'] is None and payload['active_transfer'] is None
    assert not payload['run'].get('step7_cleanup')


def test_native_list_uses_current_configured_scope_without_cloud_phases(context, tmp_path):
    from app.run_service import list_runs
    from app.pipeline_registry_service import _project_wgs_workflows
    client, factory, _, _ = context
    first, _, _ = history(context, tmp_path)
    with factory() as session:
        result = list_runs(session=session, workflow_projectors={'wgs': _project_wgs_workflows})
    assert result['total'] == 1
    row = result['items'][0]
    assert row['analysis_id'] == first['analysis_id']
    assert row['batch_no'] == 'SYN_BATCH'
    assert row['sample_count'] == 1
    assert row['workflow_summary'] == []
