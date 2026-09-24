"""Operator-pinned runtime selection shared by restricted WGS/GATK entries.

Absence of activation keeps legacy behavior. Invalid activation never falls
back to a frozen copy, and no request/environment field selects executable code.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

POLICY_PATH = Path('/etc/cce-pipeline/writers-v2.json')
TRUST_ROOT = Path('/etc/cce-pipeline')
TRUSTED_UID = 0
PLATFORM_SOURCE = Path(__file__).resolve()
COMMANDS = dict(step1_upload='step1-upload', step2_master='step2-run',
    step3_monitor='step3-status', step4_publish='step4-publish',
    step5_download='step5-download', step6_materialize='step6-materialize')


def _operator_path(path):
    path = Path(path)
    if not path.is_absolute():
        raise RuntimeError('paired runtime path must be absolute')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != TRUSTED_UID or info.st_mode & 0o022:
        raise RuntimeError('paired runtime files must be operator-owned')
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != TRUSTED_UID or info.st_mode & 0o022:
            raise RuntimeError('paired runtime ancestry must be operator-owned')
        if parent == TRUST_ROOT:
            break
    return path


def _pin(pin):
    if not isinstance(pin, dict) or set(pin) != {'path','sha256'}:
        raise RuntimeError('invalid paired runtime pin')
    path = _operator_path(pin['path'])
    if path.stat().st_size > 16*1024*1024 or hashlib.sha256(path.read_bytes()).hexdigest() != pin['sha256']:
        raise RuntimeError('paired runtime source pin changed')
    return path


def _operator_python(value):
    path = _operator_path(value)
    if not os.access(path, os.X_OK):
        raise RuntimeError('paired runtime Python is unavailable')
    return str(path)


def selected_runtime():
    try:
        POLICY_PATH.lstat()
    except FileNotFoundError:
        return None
    path = _operator_path(POLICY_PATH)
    if path.stat().st_size > 16*1024*1024:
        raise RuntimeError('paired runtime policy is too large')
    policy = json.loads(path.read_bytes())
    if (not isinstance(policy, dict) or policy.get('schema_version') != 2
            or set(policy.get('writers', {})) != {'cli','platform'}):
        raise RuntimeError('invalid paired runtime activation')
    source = _pin(policy['writers']['cli'])
    platform = _pin(policy['writers']['platform'])
    guard = _pin(policy.get('runtime_guard'))
    if platform != PLATFORM_SOURCE or guard != source.with_name('cce_writer_guard.py'):
        raise RuntimeError('unpaired platform or guard entry')
    return source, _operator_python(policy['operator_python'])


def stage_command(bundle, stage, *arguments):
    if stage not in COMMANDS:
        return None  # Prepare/Step7/maintenance remain outside this rollout.
    selected = selected_runtime()
    if selected is None:
        return None
    source, python = selected
    return [python, str(source), COMMANDS[stage], '--bundle', str(bundle), *arguments]


def load_runtime():
    selected = selected_runtime()
    if selected is None:
        return None
    source, _ = selected
    name = '_cce_operator_paired_runtime'
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module
