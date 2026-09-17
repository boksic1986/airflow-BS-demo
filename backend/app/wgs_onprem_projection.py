"""Read-only presentation of native runs; no native work or Sample writes."""
import re
from datetime import datetime, timezone


def native_batch(params):
    value = str(params.get('batch_no') or (params.get('onprem_registration') or {}).get('batch_name') or '')
    # Recognize the native generated name only. Preserve arbitrary custom batch labels.
    match = re.fullmatch(r'WGS_(.+)_T7Hg38V\d+(?:\.\d+)+', value)
    return match[1] if match else value


def current_native_stage(session, run):
    from sqlalchemy import select
    from app.models import WgsStageExecution
    return session.scalar(select(WgsStageExecution).where(
        WgsStageExecution.execution_id == (run.params_json or {}).get('current_native_execution_id'),
        WgsStageExecution.analysis_id == run.analysis_id,
        WgsStageExecution.attempt == run.attempt,
        WgsStageExecution.stage_code == 'native_analysis'))


def native_progress(run, stage):
    monitor = (run.params_json or {}).get('native_monitor') or {}
    if monitor.get('execution_id') != (run.params_json or {}).get('current_native_execution_id'):
        monitor = {}
    progress = monitor.get('progress') or {}
    target = (run.params_json or {}).get('execution_target')
    mode = 'SGE' if run.execution_mode == 'sge' else {'node-96':'node96', 'node-97':'node97'}.get(target, 'Local')
    status = stage.status if stage and stage.status in {'running', 'success', 'failed', 'canceled'} else 'created'
    return dict(stage_label=f'{mode} analysis' if stage and stage.started_at else f'Awaiting {mode} start',
        stage_code='native_analysis', stage_status=status, not_in_airflow=False,
        progress_available=bool(progress.get('available')),
        progress_percent=progress.get('percent'), completed_units=progress.get('completed_units'),
        total_units=progress.get('total_units'), unit='rules', progress_source='native_step1_log',
        stage_updated_at=monitor.get('checked_at'),
        note=('监控异常，保留最后采集进度' if monitor.get('monitoring_health') == 'degraded'
              else f"已采集 {progress.get('observed_rules', 0)} 条 Rule；仅显示本次日志证据"))


def native_tracker_row(session, run):
    from app.wgs_onprem_views import current_scope
    stage = current_native_stage(session, run)
    p = native_progress(run, stage)
    started = stage.started_at if stage else None
    ended = stage.ended_at if stage else None
    utc = lambda value: value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value
    elapsed = max(0, int(((utc(ended) or datetime.now(timezone.utc)) - utc(started)).total_seconds())) if started else None
    return dict(analysis_id=run.analysis_id, project_name='WGS_Clinical', batch_no=native_batch(run.params_json),
        execution_target=(run.params_json or {}).get('execution_target'),
        pipeline='wgs', status=p['stage_status'], display_status=p['stage_status'], execution_mode=run.execution_mode,
        native_monitor_only=True, sample_count=len(current_scope(session, run)), sample_scope_status='ready',
        submitted_by=run.submitted_by, run_source='manual', started_at=started, submitted_at=run.submitted_at,
        ended_at=ended, pipeline_finished_at=ended, elapsed_seconds=elapsed,
        estimated_remaining_seconds=None, current_stage_label=p['stage_label'], stage_status=p['stage_status'],
        not_in_airflow=False, note=p['note'], percent=p['progress_percent'],
        stage_progress=dict(available=p['progress_available'], percent=p['progress_percent'],
            completed_units=p['completed_units'], total_units=p['total_units'], unit='rules',
            source=p['progress_source'], updated_at=p['stage_updated_at']))
