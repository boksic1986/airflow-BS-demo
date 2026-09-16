"""One opt-in owner-source controller -> actual platform receipt-consumer check."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import select

from app import main
from app.models import AnalysisRun
from test_wgs_onprem_registration import context
from test_wgs_onprem_execution import setup_execution


def test_owner_controller_receipt_matches_real_platform_snapshot(context, tmp_path, monkeypatch):
    source = os.environ.get('WGS_CONTROLLER_SOURCE')
    if not source:
        pytest.skip('Requires explicitly mounted WGS owner candidate; no download or native WGS')
    import pwd
    client, factory, settings, data = context
    url, registration, analysis_id = setup_execution(context, tmp_path)
    root = Path(data['project_dir'])
    # Synthetic no-analysis entry, with the native static assignment contract.
    (root / 'Step1_run.sh').write_text(
        f'#!/bin/bash\nPROJECT_DIR="{root}"\nRUN_MODE=local\n'
        'PROFILE_DIR="${PROJECT_DIR}/pipeline/cfg/profiles/${RUN_MODE}"\nexit 0\n')
    (root / 'pipeline/cfg/profiles/local/config.yaml').write_text('executor: local\njobs: 1\n')
    registration.update(execution_user=pwd.getpwuid(os.geteuid()).pw_name, execution_uid=os.geteuid())
    response = client.post(url, json=registration)
    assert response.status_code == 200, response.text
    registered = response.json()
    settings.wgs_onprem_launch_enabled = True
    claim = client.post(f"/api/wgs/onprem/executions/{registered['execution_id']}/claim", json={
        'platform_instance_id': data['platform_instance_id'], 'operation_id': registration['operation_id'],
        'generation': registered['generation'], 'manifest_sha256': registered['manifest_sha256']})
    assert claim.status_code == 200, claim.text
    grant = claim.json()
    identity = ('analysis_id', 'attempt', 'execution_id', 'generation', 'operation_id',
        'native_execution_id', 'manifest_sha256', 'execution_mode', 'execution_target',
        'execution_user', 'execution_uid', 'files', 'argv', 'project_dir')
    payload = {key: grant[key] for key in identity}
    payload.update(platform_instance_id=data['platform_instance_id'], project_uuid=data['project_uuid'],
        binding=json.loads((root / '.wgs-platform/project.json').read_text()))
    result = subprocess.run([sys.executable, source], input=json.dumps(payload), text=True,
                            capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    settings.wgs_onprem_monitor_enabled = True
    monkeypatch.setattr(main, 'get_internal_service_token', lambda: 'synthetic-internal')
    client.headers['X-Airflow-Demo-Token'] = 'synthetic-internal'
    observed = client.post(f"/api/internal/wgs/onprem/runs/{analysis_id}/executions/{registered['execution_id']}/observe",
                           json={'attempt': 1, 'generation': 1})
    assert observed.status_code == 200, observed.text
    assert observed.json()['done'] is True and observed.json()['status'] == 'success'
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'success'
