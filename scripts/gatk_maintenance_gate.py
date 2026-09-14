"""Fence explicit Step7 against the immutable GATK attempt before native cleanup."""
import hashlib
import fcntl
import json
import importlib.util
import os
from contextlib import contextmanager
from pathlib import Path
import re
import subprocess

import yaml
FROZEN_FILES = {'BATCH_RUNTIME.yaml','cleanup-job.yaml','Step7_cleanup_sfs.sh','cce_batch_runtime.py'}


def _safe_bytes(path,root):
    if root not in path.parents or any(item.is_symlink() for item in (path,*path.parents) if item == root or root in item.parents):
        raise ValueError('symlink or escaping frozen cleanup path')
    if not path.is_file():
        raise ValueError('frozen cleanup file unavailable')
    return path.read_bytes()


@contextmanager
def maintenance_lock(payload,request_root):
    root=Path(request_root).resolve()
    directory=root/payload['analysis_id']/f'attempt-{payload["attempt"]}'
    if root not in directory.parents or any(p.is_symlink() for p in (directory,directory.parent)):
        raise ValueError('unsafe cleanup lock directory')
    fd=os.open(directory/'.maintenance.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'a') as handle:
        try:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('GATK maintenance lock is busy; no new worker accepted') from exc
        yield


def check_start(payload,request_root):
    with maintenance_lock(payload,request_root):
        cleanup_command(payload,request_root)


def execute_cleanup(payload, request_root, write_status):
    root = Path(request_root).resolve()
    request_dir = root/payload['analysis_id']/f'attempt-{payload["attempt"]}'
    with maintenance_lock(payload,root):
        status_path = request_dir/'step7_cleanup.request.status.json'
        if status_path.is_file():
            status = json.loads(_safe_bytes(status_path,root))
            if status.get('request_hash') == payload.get('request_hash') and status.get('status') == 'success':
                return
        try:
            command = cleanup_command(payload, root)
            verify_live_cleanup_target(payload)
            write_status('running', 'GATK guarded SFS cleanup started')
            subprocess.run(command, check=True, text=True, capture_output=True)
            write_status('success', 'GATK SFS cleanup completed; local results retained')
        except Exception:
            write_status('failed', 'GATK guarded cleanup failed; retained evidence requires review')
            raise


def cleanup_command(payload, request_root):
    aid, attempt = payload.get('analysis_id'), payload.get('attempt')
    if not isinstance(aid, str) or not re.fullmatch(r'GATK_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}', aid):
        raise ValueError('invalid GATK cleanup identity')
    if not isinstance(attempt, int) or attempt < 1:
        raise ValueError('invalid GATK cleanup attempt')
    if not re.fullmatch(r'gatk-step7-[a-f0-9]{12}', str(payload.get('maintenance_action_id') or '')):
        raise ValueError('missing explicit GATK cleanup authorization')
    unsigned = {k:v for k,v in payload.items() if k != 'request_hash'}
    digest = hashlib.sha256(json.dumps(unsigned, sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest != payload.get('request_hash'):
        raise ValueError('cleanup request hash mismatch')
    root = Path(request_root).resolve()
    workdir = root.parent/'runs'/aid/f'attempt-{attempt}'
    if (Path(payload.get('runtime_workdir','')).resolve() != workdir.resolve()
        or workdir.is_symlink() or workdir.parent.is_symlink()
        or root.parent not in workdir.resolve().parents):
        raise ValueError('cleanup workdir escapes exact attempt')
    binding_path = workdir/'batch-binding.json'
    if hashlib.sha256(_safe_bytes(binding_path,root.parent)).hexdigest() != payload.get('binding_sha256'):
        raise ValueError('cleanup frozen binding changed')
    binding = json.loads(_safe_bytes(binding_path,root.parent))
    bundle = workdir/'cce'
    if bundle.is_symlink() or Path(payload.get('cce_bundle','')).resolve() != bundle.resolve():
        raise ValueError('cleanup bundle mismatch')
    hashes=payload.get('bundle_hashes')
    if not isinstance(hashes,dict) or not FROZEN_FILES.issubset(hashes):
        raise ValueError('frozen cleanup bundle hashes unavailable')
    for name,expected_hash in hashes.items():
        if Path(name).name != name or hashlib.sha256(_safe_bytes(bundle/name,root.parent)).hexdigest() != expected_hash:
            raise ValueError('frozen cleanup bundle changed')
    prepare=root/aid/f'attempt-{attempt}'/'prepare.request.json'
    if hashlib.sha256(_safe_bytes(prepare,root)).hexdigest() != payload.get('prepare_sha256'):
        raise ValueError('approved prepare request changed')
    run_id = f'{aid}-a{attempt}'
    if any(binding.get(k) != v for k,v in {'analysis_id':aid,'attempt':attempt,'run_id':run_id}.items()):
        raise ValueError('cleanup binding identity mismatch')
    predecessor = root/aid/f'attempt-{attempt}'/'step6_materialize.request.status.json'
    receipt = json.loads(_safe_bytes(predecessor,root))
    receipt_body = {k:v for k,v in receipt.items() if k != 'receipt_hash'}
    receipt_hash = hashlib.sha256(json.dumps(receipt_body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if receipt.get('receipt_hash') and receipt['receipt_hash'] != receipt_hash:
        raise ValueError('cleanup predecessor receipt hash is invalid')
    if (receipt.get('status') != 'success' or receipt.get('analysis_id') != aid
        or receipt.get('attempt') != attempt or receipt.get('stage') != 'step6_materialize'
        or receipt.get('execution_id') != payload.get('predecessor_execution_id')
        or receipt.get('generation') != payload.get('predecessor_generation')
        or receipt_hash != payload.get('predecessor_receipt_hash')):
        raise ValueError('cleanup requires exact successful Step6 receipt')
    runtime = yaml.safe_load(_safe_bytes(bundle/'BATCH_RUNTIME.yaml',root.parent))
    identity = runtime.get('identity') or {}
    kube = runtime.get('kubernetes') or {}
    if (identity.get('run_id') != run_id or not identity.get('project') or not identity.get('batch')
        or identity.get('project') != payload.get('approved_project')
        or identity.get('batch') != payload.get('approved_batch')
        or kube.get('namespace') != binding.get('namespace')
        or kube.get('master_job') != binding.get('master_job')):
        raise ValueError('cleanup frozen runtime identity mismatch')
    script = bundle/'Step7_cleanup_sfs.sh'
    if not script.is_file() or script.is_symlink():
        raise ValueError('frozen Step7 is unavailable')
    # Native Step7 enforces verified Step5/6, inactive Master and zero active
    # workers including history. Never pass --allow-unverified-cleanup.
    confirm = f'DELETE-SFS:{identity["project"]}/{identity["batch"]}/{run_id}'
    return ['bash',str(script),'--confirm',confirm]


def verify_live_cleanup_target(payload):
    """Check the frozen cleanup manifest and fresh Jobs/Pods before native Step7."""
    bundle = Path(payload['cce_bundle'])
    runtime = yaml.safe_load((bundle/'BATCH_RUNTIME.yaml').read_text())
    binding = json.loads((bundle.parent/'batch-binding.json').read_text())
    manifest = yaml.safe_load((bundle/'cleanup-job.yaml').read_text())
    identity = runtime['identity']
    project, batch = str(identity['project']), str(identity['batch'])
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value) for value in (project,batch)):
        raise ValueError('unsafe cleanup project or batch')
    metadata = manifest.get('metadata') or {}
    if (metadata.get('name') != runtime['kubernetes'].get('cleanup_job')
        or metadata.get('namespace') != binding.get('namespace')
        or (metadata.get('annotations') or {}).get('cce-pipeline/run-id') != identity['run_id']
        or (metadata.get('labels') or {}).get('cce.biosan.cn/run-id') != binding.get('run_label')):
        raise ValueError('cleanup Job manifest identity mismatch')
    pod_spec = manifest['spec']['template']['spec']
    if pod_spec.get('initContainers') or pod_spec.get('hostPID') or pod_spec.get('hostIPC'):
        raise ValueError('unapproved cleanup Pod privileges')
    containers = pod_spec.get('containers') or []
    if len(containers) != 1:
        raise ValueError('unexpected cleanup containers')
    container = containers[0]
    if container.get('args') or container.get('command') != ['/bin/bash','/opt/cce-pipeline/scripts/run_cce_cleanup_job.sh']:
        raise ValueError('unapproved cleanup command')
    if not re.search(r'@sha256:[a-f0-9]{64}$', str(container.get('image') or '')):
        raise ValueError('cleanup image must be immutable')
    env = {row['name']:row.get('value') for row in container.get('env') or []}
    expected = {'CCE_PROJECT':project,'CCE_BATCH':batch,'CCE_RUN_ID':identity['run_id'],
        'CCE_RUN_BASE':'/workspace/gatk-cloud/runs','CCE_LINKAGE_BASE':'/workspace/wgs-obs-sync',
        'CCE_RESULT_PREFIX':'Project_result',
        'CCE_RUN_ROOT':f'/workspace/gatk-cloud/runs/{project}/{batch}',
        'CCE_LINKAGE_ROOT':f'/workspace/wgs-obs-sync/Project_result/{project}/{batch}'}
    if any(env.get(key) != value for key,value in expected.items()):
        raise ValueError('cleanup scope is not frozen GATK SFS run/linkage')
    if any(key.startswith('CCE_') and key not in {*expected, 'CCE_PIPELINE_DIR'} for key in env):
        raise ValueError('unapproved cleanup environment override')
    spec = importlib.util.spec_from_file_location('_gatk_cleanup_runtime',bundle/'cce_batch_runtime.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    contract, config, _ = module._load(bundle,None)
    def query(*args,list_result=False):
        command = module._kubectl(config,'--request-timeout=15s','get',*args,
            *([] if list_result else ['--ignore-not-found']),'-o','json')
        completed = subprocess.run(command,check=True,capture_output=True,text=True,timeout=30)
        result=json.loads(completed.stdout) if completed.stdout.strip() else None
        if list_result and (not isinstance(result,dict) or not isinstance(result.get('items'),list)):
            raise ValueError('cleanup Pod inventory unavailable')
        return result
    def terminal(job):
        status = job.get('status') or {}
        return not status.get('active') and any(row.get('status') == 'True'
            and row.get('type') in {'Complete','Failed'} for row in status.get('conditions') or [])
    for name in (contract['kubernetes']['master_job'],contract['kubernetes']['cleanup_job']):
        job = query('job',name)
        if job:
            if not terminal(job) or (job.get('metadata') or {}).get('deletionTimestamp'):
                raise ValueError('cleanup blocked by nonterminal Job')
            if ((job.get('metadata') or {}).get('labels') or {}).get('cce.biosan.cn/run-id') != binding['run_label']:
                raise ValueError('cleanup Job belongs to another run')
            if name == contract['kubernetes']['master_job']:
                handoff = module._read_master_handoff(bundle,contract)
                if not handoff or handoff.get('job_uid') != job['metadata'].get('uid'):
                    raise ValueError('cleanup Master UID does not match frozen handoff')
    pods = query('pods','-l','cce.biosan.cn/run-id='+binding['run_label'],list_result=True)
    if any((pod.get('metadata') or {}).get('deletionTimestamp') or
        (pod.get('status') or {}).get('phase') not in {'Succeeded','Failed'} for pod in pods.get('items') or []):
        raise ValueError('cleanup blocked by live run Pod')
