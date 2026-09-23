"""Restricted-runner recovery using the original bundle's low-level CCE runtime."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

import yaml


def _regular(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('necessary frozen recovery input is missing or symlinked')
    return path


def _runtime(bundle):
    spec = importlib.util.spec_from_file_location('wgs_frozen_resume_runtime', _regular(bundle / 'cce_batch_runtime.py'))
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    return runtime


def _query(runtime, config, *arguments):
    reader = getattr(runtime, '_recovery_query', None)
    return reader(config, *arguments) if callable(reader) else runtime._kubectl_json(config, *arguments)


def _subset(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and _subset(value, actual[key]) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(_subset(a, b) for a, b in zip(expected, actual))
    return expected == actual


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix('.partial')
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(value, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def _delete_master(runtime, config, names, options):
    url = f"/apis/batch/v1/namespaces/{names['namespace']}/jobs/{names['master_job']}"
    subprocess.run(runtime._kubectl(config, 'delete', '--raw', url, '-f', '-'),
        input=json.dumps(options).encode(), check=True, capture_output=True, timeout=60)


def _require_inactive_master_pods(runtime, config, names, uid):
    pods = _query(runtime, config, 'pods', '-l', 'job-name=' + names['master_job'], '--chunk-size=0')
    if (not isinstance(pods, dict) or pods.get('kind') not in {'List', 'PodList'}
            or not isinstance(pods.get('items'), list)
            or not isinstance(pods.get('metadata', {}), dict)
            or pods.get('metadata', {}).get('continue')
            or pods.get('metadata', {}).get('remainingItemCount', 0) != 0
            or any(not isinstance(pod, dict) for pod in pods['items'])):
        raise RuntimeError('Master Pod inventory is unavailable')
    for pod in pods['items']:
        metadata = pod.get('metadata') or {}
        owners = metadata.get('ownerReferences') or []
        if not any(owner.get('uid') == uid for owner in owners):
            raise RuntimeError('Master Pod has an unknown owner')
        if metadata.get('deletionTimestamp') or (pod.get('status') or {}).get('phase') not in {'Succeeded', 'Failed'}:
            raise RuntimeError('Master Pod is still active or unknown')


def _submit_frozen_master(runtime, config, bundle):
    # The caller always queries after an uncertain create response.
    return runtime._create_job_from_path(config, bundle / 'master-job.yaml')


def _finish_handoff(runtime, bundle, contract, config, job):
    uid = job['metadata']['uid']
    manifest = yaml.safe_load(_regular(bundle / 'master-job.yaml').read_text())
    if manifest.get('metadata', {}).get('annotations', {}).get('cce-pipeline/handoff-version') == '2':
        finish = getattr(runtime, '_finish_master_handoff', None)
        if not callable(finish):
            raise RuntimeError('compatible Master confirmation reader is unavailable')
        # The producer retains the original deadline, binds Job/Pod/digests,
        # and reconciles START_SENT without retransmission.
        return finish(bundle, contract, config, uid)
    name = contract['kubernetes']['master_job']
    pod = runtime._wait_pod(config, name, uid)
    start = runtime._run(runtime._kubectl(config, 'exec', pod, '--', 'test', '-f', '/tmp/cce-batch-input/START'), check=False, capture=True)
    if start.returncode == 0:
        return
    if start.returncode != 1:
        raise RuntimeError('Master START state is unavailable')
    runtime._write_master_handoff(bundle, contract, job_name=name, job_uid=uid, state='POD_READY')
    runtime._prepare_worker_manifest(bundle, contract, config, pod)
    fastq = contract['paths']['fastq_mount_dir']
    for target in ['FASTQ_UPLOAD_COMPLETE', *[item['target'] for item in contract['transfer_sources']]]:
        runtime._run(runtime._kubectl(config, 'exec', pod, '--', 'test', '-s', f'{fastq}/{target}'))
    payload = yaml.safe_load(_regular(bundle / 'PAYLOAD.yaml').read_text())
    if not isinstance(payload, dict) or payload.get('schema_version') != 1:
        raise RuntimeError('frozen payload contract is invalid')
    metadata = {'BATCH_RUNTIME.yaml': bundle / 'BATCH_RUNTIME.yaml', 'PAYLOAD.yaml': bundle / 'PAYLOAD.yaml'}
    for item in payload.get('files') or []:
        target, source = Path(str(item.get('target') or '')), Path(str(item.get('bundle_path') or ''))
        if not target.parts or target.is_absolute() or '..' in target.parts or not source.parts or source.parts[0] != 'payload' or source.is_absolute() or '..' in source.parts:
            raise RuntimeError('unsafe frozen payload path')
        metadata[str(target)] = bundle / source
    for name, source in metadata.items():
        runtime._run(runtime._kubectl(config, 'exec', '-i', pod, '--', 'sh', '-c',
            'umask 077; mkdir -p "$(dirname "$1")"; cat > "$1.partial" && mv -f "$1.partial" "$1"',
            'sh', f'/tmp/cce-batch-input/{name}'), input_bytes=_regular(source).read_bytes())
    # Replaying touch after a lost response is idempotent and cannot resubmit a Job.
    runtime._run(runtime._kubectl(config, 'exec', pod, '--', 'touch', '/tmp/cce-batch-input/START'))
    runtime._write_master_handoff(bundle, contract, job_name=contract['kubernetes']['master_job'], job_uid=uid, state='START_SENT')


def resume_master(*, payload, binding, runtime=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(payload.get('resume_action_id') or '')):
        raise RuntimeError('invalid recovery action identity')
    bundle = Path(binding['cce_bundle'])
    runtime = runtime or _runtime(bundle)
    required = ('_load', '_kubectl_json', '_claim_batch_lock', '_require_no_active_workers',
        '_create_job_from_path', '_wait_pod', '_run', '_kubectl', '_write_master_handoff', '_prepare_worker_manifest')
    if any(not callable(getattr(runtime, name, None)) for name in required):
        raise RuntimeError('frozen CCE runtime lacks a necessary recovery primitive')
    contract, config, _ = runtime._load(bundle, None)
    names = contract['kubernetes']
    expected = f"{payload['analysis_id']}-a{payload['attempt']}"
    if binding.get('run_id') != expected or contract['identity']['run_id'] != expected or any(names.get(key) != binding.get(key) for key in ('namespace', 'master_job')):
        raise RuntimeError('frozen recovery identity differs')
    if any(not re.fullmatch(r'[a-z0-9][-a-z0-9.]{0,252}', names[key]) for key in ('namespace', 'master_job')):
        raise RuntimeError('unsafe Kubernetes identity')
    manifest = yaml.safe_load(_regular(bundle / 'master-job.yaml').read_text())
    metadata = manifest.get('metadata', {})
    if manifest.get('kind') != 'Job' or metadata.get('name') != names['master_job'] or metadata.get('namespace', names['namespace']) != names['namespace'] or metadata.get('labels', {}).get('cce.biosan.cn/run-id') != binding.get('run_label'):
        raise RuntimeError('frozen Master manifest differs from binding')
    journal_path = Path(payload['control_workdir']) / ('recovery-' + payload['resume_action_id'] + '.json')
    journal = json.loads(_regular(journal_path).read_text()) if journal_path.exists() else {}
    job = _query(runtime, config, 'job', names['master_job'])
    if job and not _subset(manifest, job):
        raise RuntimeError('live Master differs from frozen manifest/image')
    v2 = metadata.get('annotations', {}).get('cce-pipeline/handoff-version') == '2'
    if v2 and (not job or fence_master_status({}, job, expected_uid=job['metadata']['uid'])['master_state'] == 'FAILED'):
        raise RuntimeError('missing or failed v2 Master requires a bound next-generation recovery view before replacement')
    runtime._claim_batch_lock(contract, config)  # Native same-run lock inheritance.
    mode = 'reused'
    if job:
        status = fence_master_status({}, job, expected_uid=job['metadata']['uid'])['master_state']
        if job['metadata'].get('deletionTimestamp'):
            raise RuntimeError('Master deletion is still in progress')
        if status == 'SUCCEEDED':
            success = getattr(runtime, '_recovery_native_success', None)
            if not callable(success):
                raise RuntimeError('compatible native success reader is unavailable')
            terminal = success(bundle, contract, job['metadata']['uid'])
            if not isinstance(terminal, dict) or terminal.get('state') != 'SUCCEEDED' or terminal.get('job_uid') != job['metadata']['uid']:
                raise RuntimeError('native success identity is unverified')
            return {'mode': 'reused', 'master_uid': job['metadata']['uid']}
        if status == 'FAILED':
            # CREATE may have succeeded while its response and first GET were
            # lost. A delayed failed Job is not permission to restart this action.
            if journal.get('state') == 'submitting':
                raise RuntimeError('submitted Master outcome requires reconciliation; no replacement submitted')
            if int((job.get('status') or {}).get('active') or 0):
                raise RuntimeError('failed Master still has active Pods')
            uid = job['metadata']['uid']
            if journal.get('replacement_uid') == uid:
                raise RuntimeError('replacement failed; an explicit new recovery action is required')
            _require_inactive_master_pods(runtime, config, names, uid)
            # Retain the failed Job and native mirror before a new Master can refresh them.
            archive = journal_path.with_suffix('')
            archive.mkdir(parents=True, exist_ok=True)
            _save(archive / 'failed-master.json', job)
            if hasattr(runtime, '_mirror_dir'):
                mirror = runtime._mirror_dir(bundle, expected)
                if mirror.is_dir():
                    for source in mirror.iterdir():
                        if source.is_file() and not source.is_symlink() and not (archive / source.name).exists():
                            shutil.copy2(source, archive / source.name)
            runtime._require_no_active_workers(bundle, contract, config, job, allow_prestart_manifest_absence=True)
            rechecked = _query(runtime, config, 'job', names['master_job'])
            if (not rechecked or rechecked.get('metadata', {}).get('uid') != uid
                    or rechecked['metadata'].get('resourceVersion') != job['metadata']['resourceVersion']
                    or rechecked['metadata'].get('deletionTimestamp')
                    or not _subset(manifest, rechecked)):
                raise RuntimeError('Master UID/resourceVersion changed before deletion')
            journal.update(old_uid=uid, state='deleting')
            _save(journal_path, journal)
            options = {'apiVersion': 'v1', 'kind': 'DeleteOptions', 'propagationPolicy': 'Foreground',
                'preconditions': {'uid': uid, 'resourceVersion': job['metadata']['resourceVersion']}}
            try:
                _delete_master(runtime, config, names, options)
            except (RuntimeError, subprocess.SubprocessError):
                # Never retry a DELETE blindly; observe the exact name below.
                pass
            for _ in range(30):
                observed = _query(runtime, config, 'job', names['master_job'])
                if observed is None:
                    job = None
                    break
                if observed['metadata']['uid'] != uid:
                    raise RuntimeError('Master identity changed during deletion')
                time.sleep(1)
            else:
                raise RuntimeError('Master deletion is not confirmed')
            journal['state'] = 'deleted'
            _save(journal_path, journal)
    if job is None:
        # Once CREATE may have been transmitted, even a later successful 404
        # cannot establish that no Master ran. Reconcile evidence, never POST again.
        if journal and journal.get('state') not in {'deleting', 'deleted'}:
            raise RuntimeError('missing submitted Master requires evidence reconciliation; no replacement submitted')
        if payload['stage'] != 'step2_master' and journal.get('state') not in {'deleting', 'deleted'}:
            raise RuntimeError('missing Master without a recorded recovery deletion')
        if not journal and callable(getattr(runtime, '_read_master_handoff', None)) and runtime._read_master_handoff(bundle, contract):
            raise RuntimeError('previously submitted Master is missing; its outcome must be reconciled')
        journal['state'] = 'submitting'
        _save(journal_path, journal)
        try:
            _submit_frozen_master(runtime, config, bundle)
        except (RuntimeError, subprocess.SubprocessError):
            pass
        job = _query(runtime, config, 'job', names['master_job'])
        if not job or not _subset(manifest, job) or job['metadata']['uid'] == journal.get('old_uid'):
            raise RuntimeError('replacement submission outcome is unverified')
        journal.update(state='created', replacement_uid=job['metadata']['uid'])
        _save(journal_path, journal)
        mode = 'replaced'
    _finish_handoff(runtime, bundle, contract, config, job)
    journal.update(state='started', replacement_uid=job['metadata']['uid'])
    _save(journal_path, journal)
    return {'mode': mode, 'master_uid': job['metadata']['uid']}


def fence_master_status(snapshot, live, *, expected_uid):
    if not live or live.get('metadata', {}).get('uid') != expected_uid:
        raise RuntimeError('current Master identity is unavailable or changed')
    status = live.get('status') or {}
    conditions = {item.get('type') for item in status.get('conditions') or [] if item.get('status') == 'True'}
    terminal = conditions & {'Complete', 'Failed'}
    if (len(terminal) > 1 or (terminal and any(type(status.get(k, 0)) is not int or status.get(k, 0) != 0
                                              for k in ('active', 'terminating')))):
        raise RuntimeError('Master terminal state is ambiguous or still active')
    state = 'SUCCEEDED' if 'Complete' in conditions else 'FAILED' if 'Failed' in conditions else 'RUNNING'
    return {**snapshot, 'master_state': state, 'master_uid': expected_uid,
        'message': snapshot.get('message', '') if snapshot.get('master_uid') == expected_uid else 'Current Master ' + state.lower()}


def run_resume_stage(payload, *, gate):
    stage = payload['stage']
    binding = gate._load_binding(payload)
    if stage in {'step1_upload', 'step5_download'}:
        gate._run_transfer_stage(payload)
    elif stage == 'step6_materialize':
        subprocess.run(gate._step_command(payload, stage), check=True)
    elif stage in {'step2_master', 'step3_monitor'}:
        result = resume_master(payload=payload, binding=binding)
        payload['resume_master_uid'] = result['master_uid']
        if stage == 'step3_monitor':
            gate._monitor_step3(payload)
    elif stage == 'step4_publish':
        gate._wait_step4(payload)
    else:
        raise RuntimeError('recovery supports canonical Step1–6 only')
