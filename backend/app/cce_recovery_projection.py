"""Read-only UI projection of existing CCE actions and scoped runtime evidence.

No filesystem, remote calls, reservations or state changes on a dashboard read.
Only allowlisted labels leave this module, never action conf or raw errors.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from app.models import RunAction, WgsStageExecution, PipelineStageExecution
from app.cce_recovery_budget import ACTION, STOPPED, _date
from app.cce_monitor_observation import KEY as MONITOR_KEY


def _object(value):
    return value if isinstance(value, dict) else {}


def _time(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()
    try:
        return _date(value).isoformat()
    except (ValueError, TypeError, AttributeError):
        return None


def recovery_views(*, session, runs, now=None):
    now = now or datetime.now(timezone.utc)
    supported = {r.analysis_id:r for r in runs
        if r.pipeline_name in {'wgs','gatk'} and r.execution_mode == 'cce'
        and not (r.params_json or {}).get('native_monitor_only')}
    if not supported:
        return {}
    # Batch reads for Tracker; never one action/evidence query per table row.
    actions = {}
    for a in session.scalars(select(RunAction).where(RunAction.analysis_id.in_(supported),
            RunAction.action.in_({ACTION,'cce_publish_dispatch'})).order_by(RunAction.id)):
        data = _object(a.payload_json)
        if type(data.get('attempt')) is int and data['attempt'] == supported[a.analysis_id].attempt:
            actions[(a.analysis_id,a.action)] = a
    latest = {}
    for pipeline, model in (('wgs',WgsStageExecution),('gatk',PipelineStageExecution)):
        ids = [r.analysis_id for r in supported.values() if r.pipeline_name == pipeline]
        if not ids: continue
        query = select(model).where(model.analysis_id.in_(ids)).order_by(model.generation)
        if pipeline == 'gatk': query = query.where(model.pipeline_name == pipeline)
        for row in session.scalars(query):
            if row.attempt == supported[row.analysis_id].attempt:
                latest[(row.analysis_id,row.stage_code)] = row
    result = {}
    for run in supported.values():
        stage = run.current_stage
        row = latest.get((run.analysis_id,'step3_monitor' if run.status == 'success' else stage))
        action = actions.get((run.analysis_id,'cce_publish_dispatch' if stage == 'step4_publish' else ACTION))
        value = _view(run,row,action if stage in {'step3_monitor','step4_publish'} else None,now)
        if value is not None: result[run.analysis_id] = value
    return result


def _view(run, row, action, now):
    if run.status in STOPPED - {'success'}: return None
    payload = _monitor_payload(row)
    health = payload.get('monitoring_health')
    stamp = _time(payload.get('last_success_at'))
    base = dict(stage_code=run.current_stage,last_confirmed_at=stamp,
        generation=row.generation if row else None,ordinal=None,limit=2,next_retry_at=None)
    def output(state,message,reason=None,**fields):
        return dict(base,state=state,message=message,reason=reason,**fields)
    if run.status == 'success':
        return output('completed_degraded','分析完成，日志采集异常') if health in {'degraded','error'} else None
    if action:
        data = _object(action.payload_json)
        if data.get('pipeline') != run.pipeline_name or data.get('workdir') != run.workdir:
            return output('stale','恢复记录与当前执行不一致，需人工核对')
        ordinal = data.get('ordinal') if action.action == ACTION else data.get('sequence')
        base['ordinal'] = ordinal if type(ordinal) is int and 0 <= ordinal <= 2 else None
        # Do not revive an older action after a manual recovery in the same attempt.
        current_id = (run.params_json or {}).get('resume_action_id')
        if action.action == ACTION and current_id and current_id != data.get('action_id'):
            return None
        if data.get('dag_run_id') and data['dag_run_id'] != run.dag_run_id:
            return output('stale','恢复记录与当前执行不一致，需人工核对')
        if row and data.get('generation') is not None and row.generation != data['generation']:
            return output('stale','恢复记录与当前执行不一致，需人工核对')
        if action.action != ACTION and (not row or any(data.get(k) != getattr(row,k)
                for k in ('execution_id','generation','request_hash'))):
            return output('stale','恢复记录与当前执行不一致，需人工核对')
        if (row and row.status == 'success') or data.get('compute_terminal') == 'success':
            action = None
        else:
            deadline = _time(data.get('original_deadline') if action.action == ACTION else data.get('deadline'))
            wait = _object(data.get('worker_wait'))
            wait_deadline = _time(wait.get('deadline')) if wait.get('state') == 'waiting' else None
            if (action.result_status in {'rejected','failed','exhausted','expired','stopped','canceled','cancelled'}
                    or not deadline or now >= _date(deadline)
                    or wait_deadline and now >= _date(wait_deadline)
                    or data.get('compute_terminal') == 'failed'):
                return output('needs_attention','自动续跑停止，需人工处理',
                    '当前执行已失败' if data.get('compute_terminal') == 'failed' else '执行状态待确认')
            if action.result_status == 'uncertain':
                return output('checking','正在核对原执行，勿重复提交','执行状态待确认')
            if action.action != ACTION and action.result_status == 'running' and data.get('started_observed') is True:
                action = None  # Reattached original publish, not a new execution.
            elif action.action == ACTION and _master_started(run,row,data):
                if health not in {'degraded','error'}:
                    return output('recovering',f'自动续跑中（{base["ordinal"]}/2）')
                action = None
            else:
                base['next_retry_at'] = _time(data.get('next_retry_at')) if action.result_status in {'reserved','waiting'} else None
                reason = '等待现有 Worker 自然结束' if wait.get('state') == 'waiting' else '等待当前恢复执行确认启动'
                label = '发布派发等待中' if action.action != ACTION else '自动续跑等待中'
                suffix = f'（{ordinal}/2）' if type(ordinal) is int and 1 <= ordinal <= 2 else ''
                return output('waiting',label+suffix,reason)
    if health in {'degraded','error'}:
        return output('stale','监控中断，执行状态待确认','保留最后确认进度；不表示分析失败')
    return None


def _master_started(run,row,data):
    if not row or row.status != 'running': return False
    binding = _object(_monitor_payload(row).get('cce_master_binding'))
    platform = _object(binding.get('platform_execution'))
    native = _object(binding.get('native'))
    expected = dict(pipeline=run.pipeline_name,analysis_id=run.analysis_id,attempt=run.attempt,
        stage=row.stage_code,execution_id=row.execution_id,generation=row.generation,request_hash=row.request_hash)
    return (binding.get('schema_version') == 2 and platform == expected
        and bool(native.get('job_uid')) and bool(native.get('pod_uid'))
        and native['job_uid'] != data.get('source_master_uid')
        and _object(native.get('recovery_context')).get('action') == data.get('action_id'))


def _monitor_payload(row):
    payload = _object(row.terminal_payload_json) if row else {}
    return _object(payload[MONITOR_KEY]) if MONITOR_KEY in payload else payload
