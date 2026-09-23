#!/usr/bin/env python3
"""Operator-only same-attempt GATK resume. Dry-run unless --execute is given.

Never use Step0. This helper preserves workflow versions and existing SFS/OBS
outputs; the replacement Master resumes its original workdir. It does not
change Airflow state. Invoke under the approved runtime identity/environment.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import yaml


class ResumeGuardError(RuntimeError):
    """Only fixed privacy-safe guard messages may be exposed by the CLI."""


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _regular(path):
    if path.is_symlink() or not path.is_file():
        raise ResumeGuardError('missing or symlinked frozen file')
    return path


def _subset(expected, observed):
    if isinstance(expected, dict):
        return isinstance(observed, dict) and all(
            key in observed and _subset(value, observed[key])
            for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(observed, list) and len(expected) == len(observed) and all(
            _subset(a, b) for a, b in zip(expected, observed))
    return expected == observed


def _save(path, value, *, create=False):
    # Private, fsynced journal. Never truncate an existing journal in place.
    target = path if create else path.with_suffix('.partial')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    with os.fdopen(descriptor, 'w') as handle:
        json.dump(value, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    if not create:
        os.replace(target, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _runtime(bundle):
    source = _regular(bundle/'cce_batch_runtime.py')
    spec = importlib.util.spec_from_file_location('gatk_frozen_runtime', source)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    return runtime


def _query(runtime, config, *arguments):
    reader = getattr(runtime, '_recovery_query', None)
    return reader(config, *arguments) if callable(reader) else runtime._kubectl_json(config, *arguments)


def _master_pods(runtime, config, master_job):
    # The native --ignore-not-found helper may turn an empty List into None.
    # Query a List explicitly: only a successful, valid items=[] proves empty.
    if callable(getattr(runtime, '_recovery_query', None)):
        return runtime._recovery_query(config, 'pods', '-l', 'job-name='+master_job, '--chunk-size=0')
    try:
        completed = subprocess.run(
            runtime._kubectl(config, 'get', 'pods', '-l', 'job-name='+master_job, '--chunk-size=0', '-o', 'json'),
            check=True, capture_output=True, timeout=30)
        if completed.returncode:
            raise ResumeGuardError('Master Pod inventory command failed')
        value = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        raise ResumeGuardError('Master Pod inventory unavailable or invalid') from None
    if (not isinstance(value, dict) or value.get('kind') not in {'List', 'PodList'}
            or not isinstance(value.get('items'), list)
            or not isinstance(value.get('metadata', {}), dict)
            or value.get('metadata', {}).get('continue')
            or value.get('metadata', {}).get('remainingItemCount', 0) != 0
            or any(not isinstance(item, dict) for item in value['items'])):
        raise ResumeGuardError('Master Pod inventory is not a valid List')
    return value


def _guard(runtime, bundle, contract, config, modules, job, archived_workers=None):
    names = contract['kubernetes']
    if job:
        status = job.get('status') or {}
        failed = any(item.get('type') == 'Failed' and item.get('status') == 'True'
                     for item in status.get('conditions') or [])
        if not failed or int(status.get('active') or 0) or job['metadata'].get('deletionTimestamp'):
            raise ResumeGuardError('Master is not an inactive terminal failed Job')
    pods = _master_pods(runtime, config, names['master_job'])
    if any(p.get('metadata', {}).get('deletionTimestamp') or
           p.get('status', {}).get('phase') not in {'Succeeded', 'Failed'}
           for p in pods['items']):
        raise ResumeGuardError('Master Pod is active or terminating')
    # Native guard includes historical workers; it refreshes retained evidence.
    runtime._require_no_active_workers(bundle, contract, config, job, include_history=True)
    if archived_workers is not None:
        records = runtime._parse_jobs_ndjson(archived_workers, since_epoch=None, strict=True)
        states = runtime._query_worker_states(config, records)
        # Absence is not terminal proof: a reclaimed Job needs exact persisted
        # terminal evidence before the compatible recovery consumer can allow it.
        if any(item.get('state') not in {'SUCCEEDED', 'FAILED'} for item in states):
            raise ResumeGuardError('archived Worker Job is active or uncertain')
    _guard_maintenance_and_obs(runtime,contract,config,modules)


def _guard_maintenance_and_obs(runtime,contract,config,modules):
    names=contract['kubernetes']
    for key in ('cleanup_job', 'reset_job', 'repair_job'):
        if not names.get(key):
            raise ResumeGuardError('frozen maintenance Job identity missing')
        other = _query(runtime, config, 'job', names[key])
        if other:
            status = other.get('status') or {}
            terminal = {c.get('type') for c in status.get('conditions') or []
                        if c.get('type') in {'Complete','Failed'} and c.get('status')=='True'}
            if (len(terminal)!=1 or any(type(status.get(k,0)) is not int or status.get(k,0)!=0
                                       for k in ('active','terminating')) or other.get('metadata',{}).get('deletionTimestamp')):
                raise ResumeGuardError('maintenance Job is active or uncertain')
    identity = contract['identity']
    observed = modules[0].inspect_reset_obs(
        obsutil=config['obs']['obsutil_bin'], obsutil_config=config['obs']['config_file'],
        project_name=identity['project'], batch=identity['batch'],
        fastq_uri=contract['paths']['fastq_upload_uri'],
        result_uri=contract['paths']['result_upload_uri'])
    if observed.get('result_count') != 0:
        raise ResumeGuardError('OBS results exist or their absence is unverified')


def resume(*, analysis_id, attempt, expected_job_uid, expected_binding_sha256,
           expected_contract_sha256, execute=False, runtime=None, recovery=None):
    if not re.fullmatch(r'GATK_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}', analysis_id):
        raise ResumeGuardError('invalid analysis identity')
    if type(attempt) is not int or attempt < 1:
        raise ResumeGuardError('invalid attempt')
    if not re.fullmatch(r'[a-zA-Z0-9-]{1,64}', expected_job_uid):
        raise ResumeGuardError('invalid expected Job UID')
    if any(not re.fullmatch(r'[0-9a-f]{64}', value)
           for value in (expected_binding_sha256, expected_contract_sha256)):
        raise ResumeGuardError('explicit frozen SHA256 values required')
    configured = os.environ.get('GATK_RUNTIME_REQUEST_ROOT', '')
    if not configured or not Path(configured).is_absolute():
        raise ResumeGuardError('approved GATK_RUNTIME_REQUEST_ROOT must be set')
    request_root = Path(configured).resolve(strict=True)
    request_dir = request_root/analysis_id/f'attempt-{attempt}'
    bundle = request_root.parent/'runs'/analysis_id/f'attempt-{attempt}'/'cce'
    for path in (request_dir, bundle):
        if not path.is_dir() or path.resolve() != path:
            raise ResumeGuardError('attempt directory missing or symlinked')
    binding_path = _regular(bundle.parent/'batch-binding.json')
    contract_path = _regular(bundle/'BATCH_RUNTIME.yaml')
    manifest_path = _regular(bundle/'master-job.yaml')
    lock_fd = os.open(request_dir/'.maintenance.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if _hash(binding_path) != expected_binding_sha256 or _hash(contract_path) != expected_contract_sha256:
            raise ResumeGuardError('frozen binding or contract SHA256 changed')
        binding = json.loads(binding_path.read_text())
        run_id = f'{analysis_id}-a{attempt}'
        if any(binding.get(k) != v for k, v in {
            'schema_version':'gatk-runtime.batch-binding.v1', 'analysis_id':analysis_id,
            'attempt':attempt, 'run_id':run_id, 'cce_bundle':str(bundle)}.items()):
            raise ResumeGuardError('binding identity mismatch')
        runtime = runtime or _runtime(bundle)
        contract, config, modules = runtime._load(bundle, None)
        names = contract['kubernetes']
        if contract['identity']['run_id'] != run_id or any(names.get(k) != binding.get(k) for k in ('namespace', 'master_job')):
            raise ResumeGuardError('frozen runtime identity mismatch')
        if any(not re.fullmatch(r'[a-z0-9][-a-z0-9.]{0,252}', names[k]) for k in ('namespace', 'master_job')):
            raise ResumeGuardError('unsafe Kubernetes identity')
        manifest = yaml.safe_load(manifest_path.read_text())
        if manifest.get('kind') != 'Job' or manifest.get('metadata', {}).get('name') != names['master_job']:
            raise ResumeGuardError('frozen Master manifest mismatch')
        if manifest['metadata'].get('namespace', names['namespace']) != names['namespace']:
            raise ResumeGuardError('frozen Master namespace mismatch')
        if manifest['metadata'].get('labels', {}).get('cce.biosan.cn/run-id') != binding.get('run_label'):
            raise ResumeGuardError('frozen Master run label mismatch')
        if not manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers'):
            raise ResumeGuardError('frozen Master containers missing')
        hashes = {'binding_sha256':expected_binding_sha256,
                  'contract_sha256':expected_contract_sha256, 'manifest_sha256':_hash(manifest_path)}
        journal_path = request_dir/f'resume-{expected_job_uid}.json'
        journal = json.loads(_regular(journal_path).read_text()) if journal_path.exists() else None
        identity = {'analysis_id':analysis_id, 'attempt':attempt, 'run_id':run_id,
                    'expected_job_uid':expected_job_uid, **hashes}
        if journal and any(journal.get(k) != v for k, v in identity.items()):
            raise ResumeGuardError('resume journal identity mismatch')
        v2 = manifest['metadata'].get('annotations', {}).get('cce-pipeline/handoff-version') == '2'
        if recovery is not None:
            from scripts.cce_recovery_inventory import RecoveryCapability
            if (not isinstance(recovery,RecoveryCapability) or recovery.bundle!=bundle
                    or recovery.expected_job_uid!=expected_job_uid):
                raise ResumeGuardError('internal verified recovery capability required')
            recovery.bind(runtime,contract,config,run_label=binding['run_label'],pipeline='gatk',
                analysis_id=analysis_id,attempt=attempt,action=recovery.context['action'])
            def check():
                observed=recovery.inspect()
                if observed['terminal']['state']=='FAILED':
                    _guard_maintenance_and_obs(runtime,contract,config,modules)
                return observed
            journal=journal or dict(identity)
            result=runtime._advance_recovery_view(bundle,contract,config,context=recovery.context,
                expected_job_uid=expected_job_uid,destination=request_dir/('resume-'+expected_job_uid+'-view'),
                journal=journal,save_journal=lambda value:_save(journal_path,value),check=check,
                claim=recovery.claim,authorize=recovery._authorized,
                before_handoff=lambda:_guard_maintenance_and_obs(runtime,contract,config,modules),execute=execute,
                platform_execution=recovery.platform_execution)
            return {**identity,**result,'replacement_job_uid':result['master_uid'],
                    'status':'succeeded' if result['mode']=='succeeded' else 'ready' if result['mode']=='ready' else 'completed'}
        job = _query(runtime, config, 'job', names['master_job'])
        if job and job['metadata']['uid'] != expected_job_uid:
            if not v2 and journal and journal.get('status') == 'completed' and journal.get('replacement_job_uid') == job['metadata']['uid'] and _subset(manifest, job):
                return journal
            raise ResumeGuardError('different Master UID; ambiguous replacement must not be deleted')
        if job and not _subset(manifest, job):
            raise ResumeGuardError('live Master does not match frozen manifest/image')
        if v2 and not job:
            raise ResumeGuardError('missing v2 Master requires a bound next-generation recovery view before replacement')
        if v2 and job:
            conditions = {c.get('type') for c in job.get('status', {}).get('conditions', [])
                          if c.get('status') == 'True'}
            terminal = conditions & {'Complete', 'Failed'}
            if (job['metadata'].get('deletionTimestamp') or len(terminal) > 1
                    or (terminal and any(type(job.get('status', {}).get(k, 0)) is not int
                                         or job.get('status', {}).get(k, 0) != 0 for k in ('active', 'terminating')))):
                raise ResumeGuardError('Master terminal state is ambiguous, active or deleting')
            if 'Failed' in conditions:
                raise ResumeGuardError('failed v2 Master requires a bound next-generation recovery view before replacement')
            if 'Complete' in conditions:
                success = getattr(runtime, '_recovery_native_success', None)
                if not callable(success):
                    raise ResumeGuardError('compatible native success reader is unavailable')
                terminal = success(bundle, contract, expected_job_uid)
                if not isinstance(terminal, dict) or terminal.get('state') != 'SUCCEEDED' or terminal.get('job_uid') != expected_job_uid:
                    raise ResumeGuardError('native success identity is unverified')
                return {**identity, 'status':'succeeded', 'master_uid':expected_job_uid}
            finish = getattr(runtime, '_finish_master_handoff', None)
            if not callable(finish):
                raise ResumeGuardError('compatible Master confirmation reader is unavailable')
            if execute:
                runtime._claim_batch_lock(contract, config)
                finish(bundle, contract, config, expected_job_uid)
            return {**identity, 'status':'reused' if execute else 'ready', 'master_uid':expected_job_uid}
        if not job and (not journal or journal.get('status') not in {'deleting', 'deleted'}):
            raise ResumeGuardError('Master absent without a matching deletion journal')
        # Archive old worker evidence before native refresh overwrites snapshots.
        archived = {}
        if not journal:
            mirror = runtime._mirror_dir(bundle, run_id) if hasattr(runtime, '_mirror_dir') else None
            if mirror and mirror.is_dir():
                for name in ('jobs.ndjson', 'run-state.json', 'MASTER_HANDOFF.json'):
                    source = mirror/name if name != 'MASTER_HANDOFF.json' else mirror.parent/name
                    if source.is_file() and not source.is_symlink():
                        content = source.read_bytes()
                        archive = request_dir/f'resume-{expected_job_uid}-{name}'
                        if archive.exists():
                            # Preserve the first pre-refresh snapshot on dry-run
                            # replay; never replace it with a later observation.
                            archived[name] = _hash(_regular(archive))
                        else:
                            fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                            with os.fdopen(fd, 'wb') as handle:
                                handle.write(content); handle.flush(); os.fsync(handle.fileno())
                            archived[name] = hashlib.sha256(content).hexdigest()
        worker_archive = request_dir/f'resume-{expected_job_uid}-jobs.ndjson'
        archived_workers = _regular(worker_archive).read_text() if worker_archive.exists() else None
        _guard(runtime, bundle, contract, config, modules, job, archived_workers)
        if not execute:
            return {**identity, 'status':'ready', 'expected_resource_version':job['metadata']['resourceVersion'] if job else journal['expected_resource_version']}
        if not journal:
            journal = {**identity, 'status':'prepared', 'expected_resource_version':job['metadata']['resourceVersion'],
                       'old_job_status':job.get('status', {}), 'archived_evidence':archived}
            _save(journal_path, journal, create=True)
        runtime._claim_batch_lock(contract, config)
        if job:
            rechecked = _query(runtime, config, 'job', names['master_job'])
            if not rechecked or rechecked['metadata'].get('uid') != expected_job_uid or rechecked['metadata'].get('resourceVersion') != journal['expected_resource_version']:
                raise ResumeGuardError('Master UID/resourceVersion changed before deletion')
            journal['status'] = 'deleting'; _save(journal_path, journal)
            delete_options = {'apiVersion':'v1', 'kind':'DeleteOptions', 'propagationPolicy':'Foreground',
                              'preconditions':{'uid':expected_job_uid, 'resourceVersion':journal['expected_resource_version']}}
            path = f'/apis/batch/v1/namespaces/{names["namespace"]}/jobs/{names["master_job"]}'
            subprocess.run(runtime._kubectl(config, 'delete', '--raw', path, '-f', '-'),
                           input=json.dumps(delete_options).encode(), check=True, capture_output=True, timeout=60)
        for _ in range(30):
            if _query(runtime, config, 'job', names['master_job']) is None:
                break
            time.sleep(1)
        else:
            raise ResumeGuardError('Master deletion not confirmed; no replacement submitted')
        journal['status'] = 'deleted'; _save(journal_path, journal)
        _guard(runtime, bundle, contract, config, modules, None, archived_workers)
        if any(_hash(path) != digest for path, digest in ((binding_path, hashes['binding_sha256']), (contract_path, hashes['contract_sha256']), (manifest_path, hashes['manifest_sha256']))):
            raise ResumeGuardError('frozen files changed before replacement')
        journal['status'] = 'submitting'; _save(journal_path, journal)
        runtime.step2(bundle, contract, config, modules)
        replacement = _query(runtime, config, 'job', names['master_job'])
        if not replacement or replacement['metadata'].get('uid') == expected_job_uid or not _subset(manifest, replacement):
            raise ResumeGuardError('replacement identity is unverified; manual reconciliation required')
        journal.update(status='completed', replacement_job_uid=replacement['metadata']['uid'])
        _save(journal_path, journal)
        return journal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-id', required=True)
    parser.add_argument('--attempt', type=int, required=True)
    parser.add_argument('--expected-job-uid', required=True)
    parser.add_argument('--expected-binding-sha256', required=True)
    parser.add_argument('--expected-contract-sha256', required=True)
    parser.add_argument('--execute', action='store_true')
    arguments = vars(parser.parse_args())
    try:
        result = resume(**arguments)
    except Exception as error:
        # Native OBS/Kubernetes exceptions may contain private configuration.
        reason = str(error) if isinstance(error, ResumeGuardError) else 'native_resume_requires_reconciliation'
        print(json.dumps({'status':'blocked', 'reason':reason,
                          'error_type':type(error).__name__}), file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps({k:result[k] for k in ('analysis_id', 'attempt', 'status', 'expected_job_uid', 'replacement_job_uid') if k in result}))


if __name__ == '__main__':
    main()
