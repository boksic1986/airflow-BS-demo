"""Classify a trusted native FINAL and fresh complete live inventory.

Internal restricted reader only. The returned evidence is not permission to
dispatch; policy, budget, current generation, writer and user-control fences
remain mandatory. Never infer zero errors from missing logger events.
"""
import hashlib
import json
from pathlib import Path

if __package__:
    from .cce_recovery_inventory import lineage_workers
    from .cce_recovery_workloads import probe_final_workloads
else:
    from cce_recovery_inventory import lineage_workers
    from cce_recovery_workloads import probe_final_workloads


def _require(ok):
    if not ok:
        raise ValueError('automatic recovery requires complete unmixed bound failure evidence')


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def collect_failure_evidence(*, runtime, selected, contract, config, run_label, binding, history_bundles=()):
    selected = Path(selected)
    _require(binding.get('schema_version') == 2 and binding.get('selected_bundle') == str(selected))
    native = binding['native']
    value = runtime._recovery_final_evidence(selected, contract, native['job_uid'])
    final, snapshot = value['terminal'], value['snapshot']
    master = snapshot['master']
    _require(final['state'] == 'FAILED' and final.get('submission_inventory_complete') is True
        and master.get('platform_execution') == binding.get('platform_execution')
        and final.get('platform_execution') == binding.get('platform_execution')
        and native.get('namespace') == contract['kubernetes']['namespace']
        and all(type(master.get(k)) is type(v) and master[k] == v for k,v in native.items() if k != 'namespace'))
    failed_phase = final.get('failed_stage')
    _require(failed_phase in {'preflight','analysis'} and type(final.get('exit_code')) is int and final['exit_code'] > 0)
    chosen = None
    for name, phase in snapshot['phases'].items():
        if not phase['started']:
            _require(name == 'analysis' and failed_phase == 'preflight')
            continue
        audit = phase.get('failure_summary')
        _require(isinstance(audit, dict) and audit.get('schema') == 'cce.master-failure-summary.v1'
            and audit.get('context') == phase['context'] and audit.get('closed') is True
            and audit.get('complete') is True and type(audit.get('workflow_started')) is int
            and audit['workflow_started'] == 1)
        counts, shutdown = audit.get('counts'), audit.get('shutdown')
        _require(isinstance(counts,dict) and set(counts)=={'submission','control','rule','other'}
            and all(type(v) is int and v>=0 for v in counts.values())
            and isinstance(shutdown,dict) and set(shutdown)=={'scheduler','workflow'}
            and all(type(v) is int and v in (0,1) for v in shutdown.values())
            and shutdown['workflow'] <= shutdown['scheduler'])
        _require(counts['rule'] == counts['other'] == 0)
        if name != failed_phase:
            _require(phase['exit_code'] == 0 and not any(counts.values())
                and not any(shutdown.values()) and not phase['candidates'])
            continue
        _require(phase['exit_code'] == final['exit_code'] and len(phase['candidates']) == 1)
        filename, candidate = next(iter(phase['candidates'].items()))
        control = filename == 'executor-control-failure.json'
        source = 'control' if control else 'submission'
        _require(counts[source] > 0 and counts['submission' if control else 'control'] == 0
            and isinstance(candidate.get('failures'),list) and len(candidate['failures']) == counts[source])
        chosen = phase, candidate, counts, control
    _require(chosen is not None)
    # Native validation verifies FINAL hash and inputs; these existing validators
    # independently cover all phases, retained ancestors and live Jobs/Pods.
    workers = lineage_workers(runtime, contract, selected, value, history_bundles)
    _require(all(worker['terminal_state'] != 'FAILED' for worker in workers))
    observed = probe_final_workloads(runtime=runtime, config=config,
        namespace=native['namespace'],run_label=run_label,master_job=native['job_name'],
        master_job_uid=native['job_uid'],master_state=final['state'],workers=workers)
    _require(observed['workers_inactive'] is True
        and all(worker['job_state'] in {'Complete','absent'} for worker in observed['workers']))
    phase, candidate, counts, control = chosen
    seal = dict(phase['context'], schema='cce.master-terminal.v1',
        plugin_failure_sha256=_digest(candidate), sealed=True, complete=True,
        worker_inventory_complete=True, worker_ownership_verified=True, submissions_reconciled=True,
        master_state='failed',master_pod_state='terminated',exit_code=phase['exit_code'],
        fatal_source='executor_control' if control else 'executor_submission',
        rule_failure_count=counts['rule'],other_failure_count=counts['other'],
        executor_failure_count=counts['control']+counts['submission'],
        active_worker_jobs=0,active_worker_pods=0,unresolved_submissions=0,
        submission_snapshot_sha256=final['submission_snapshot_sha256'])
    return dict(schema_version=2,binding=json.loads(json.dumps(binding)),phase=failed_phase,
        candidate=candidate,terminal=seal)
