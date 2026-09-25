"""Default-off policy frozen only by the new-run creation paths."""
from datetime import timedelta
from pathlib import Path

from app.cce_recovery_budget import _date


def freeze_new_attempt(*, run, settings):
    params = dict(run.params_json or {})
    if 'cce_recovery_policy' in params or 'cce_recovery_budget' in params:
        raise ValueError('recovery policy is already frozen')
    enabled = (run.execution_mode == 'cce' and run.pipeline_name in {'wgs','gatk'}
        and getattr(settings,run.pipeline_name+'_cce_recovery_enabled',False) is True)
    seconds = None
    if enabled:
        if run.pipeline_name == 'wgs':
            if not getattr(settings,'wgs_contract_v2_enabled',False):
                raise ValueError('automatic WGS recovery requires contract v2')
            from app.wgs_stage_catalog import load_wgs_stage_contract
            seconds = load_wgs_stage_contract(Path(settings.wgs_stage_contract_path)).stages['step3_monitor'].timeout_seconds
        else:
            seconds = 72*3600  # Existing bio_gatk wait_step3_analysis timeout.
    params['cce_recovery_policy'] = dict(version=1,attempt=run.attempt,enabled=enabled,
        monitor_timeout_seconds=seconds,original_deadline=None)
    params['cce_recovery_budget'] = dict(attempt=run.attempt,count=0,original_deadline=None)
    run.params_json = params


def start_monitor_deadline(*, run, now):
    """Call only on first registered Step3; missing legacy state stays missing."""
    params = dict(run.params_json or {})
    policy = params.get('cce_recovery_policy')
    if not isinstance(policy,dict) or policy.get('enabled') is not True:
        return None
    budget = params.get('cce_recovery_budget')
    if (policy.get('version') != 1 or type(policy.get('attempt')) is not int
            or policy['attempt'] != run.attempt or not isinstance(budget,dict)
            or type(budget.get('attempt')) is not int or budget['attempt'] != run.attempt):
        raise ValueError('recovery policy/budget belongs to another attempt')
    if policy.get('original_deadline') is not None:
        if _date(policy['original_deadline']) != _date(budget.get('original_deadline')):
            raise ValueError('original monitor deadline changed')
        return policy['original_deadline']
    seconds = policy.get('monitor_timeout_seconds')
    if (type(seconds) is not int or seconds <= 0 or now.tzinfo is None
            or budget.get('original_deadline') is not None
            or type(budget.get('count')) is not int or budget['count'] != 0):
        raise ValueError('original monitor deadline cannot be initialized')
    deadline = (now+timedelta(seconds=seconds)).isoformat()
    run.params_json = dict(params,cce_recovery_policy=dict(policy,original_deadline=deadline),
        cce_recovery_budget=dict(budget,original_deadline=deadline))
    return deadline
