import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from test_wgs_runtime_gate import load_gate
from test_wgs_420_handoff_gate import payload, write_source, write_all_pending_receipt


def test_release_runtime_uses_only_server_pins(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('release_runtime', Path(__file__).parents[1] / 'wgs_release_runtime.py')
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    monkeypatch.setenv('WGS_RELEASE_RUNTIMES_JSON', '{}')
    assert runtime.select_release_runtime({'pipeline_release_id': 'legacy'}, default_cli='/original/cli') == '/original/cli'
    paths = [tmp_path / 'runtime' / name for name in ('python', 'cce-pipeline')]
    paths[0].parent.mkdir()
    for path in paths:
        path.write_text('synthetic executable')
        path.chmod(0o700)
    monkeypatch.setenv('WGS_RELEASE_RUNTIME_ROOT', str(tmp_path))
    monkeypatch.setenv('WGS_RELEASE_RUNTIMES_JSON', json.dumps({'current': {
        'python': str(paths[0]), 'cce_pipeline': str(paths[1]), 'version': '0.8.5'}}))
    monkeypatch.setattr(runtime.sys, 'executable', str(paths[0]))
    request = {'pipeline_release_id': 'current', 'cce_pipeline_version': '0.8.5'}
    assert runtime.select_release_runtime(request, default_cli='/original/cli') == str(paths[1])
    with pytest.raises(RuntimeError, match='pin is invalid'):
        runtime.select_release_runtime({**request, 'cce_pipeline_version': '0.8.4'}, default_cli='/original/cli')


def test_prepare_config_and_check_override_are_release_pinned(tmp_path, monkeypatch):
    gate = load_gate()
    profile = tmp_path / 'profile.yaml'
    profile.write_text('schema_version: 1\n')
    config = tmp_path / 'prepare.yaml'
    config.write_text(yaml.safe_dump({'cce': {'profile_file': str(profile)}}))
    monkeypatch.setattr(gate, 'WGS_PREPARE_CONFIG_ROOT', tmp_path)
    monkeypatch.setenv('WGS_RELEASE_PREPARE_CONFIGS_JSON', json.dumps({'current': {
        'path': str(config), 'sha256': hashlib.sha256(config.read_bytes()).hexdigest()}}))
    request = {'pipeline_release_id': 'current', 'node200_profile_path': str(profile),
        'profile_sha256': hashlib.sha256(profile.read_bytes()).hexdigest(), 'sequencing_batch': 'BATCH1'}
    assert gate.validate_prepare_config(request) == config
    monkeypatch.setenv('WGS_PREPARE_CHECK_OVERRIDES_JSON', '{"current:BATCH1":true}')
    assert gate._skip_prepare_checks(request)
    assert not gate._skip_prepare_checks({**request, 'sequencing_batch': 'BATCH2'})
    profile.write_text('changed')
    with pytest.raises(RuntimeError, match='pinned prepare'):
        gate.validate_prepare_config(request)


def test_receipt_allows_other_batches_pending_without_losing_current_identity(tmp_path, monkeypatch):
    gate = load_gate()
    monkeypatch.setattr(gate, 'RUNTIME_RUN_ROOT', str(tmp_path / 'runtime'))
    source = write_source(tmp_path)
    request = payload(tmp_path, generation=1)
    request_path = gate._prepare_handoff_request(request)
    private = write_all_pending_receipt(gate, request_path, source)
    with private.open('a') as handle:
        handle.write(private.read_text().splitlines()[1].replace('SAMPLE-1', 'OLD-SAMPLE') + '\n')
    receipt_path = request_path.parent / 'prepare_analysis.receipt.json'
    receipt = json.loads(receipt_path.read_text())
    receipt['private_pending_payload'].update(row_count=2, sha256=gate._sha256_file(private))
    receipt_path.write_text(json.dumps(receipt))
    assert len(gate._validated_prepare_receipt(request, request_path)['pending']) == 1
