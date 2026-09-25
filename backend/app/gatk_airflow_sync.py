"""Attempt-fenced GATK orchestration reconciliation, not workflow recovery.

Only the authenticated Airflow client supplies DAG state. Runtime generations
remain authoritative for computation; a task clear cannot resurrect failed
compute, and a successful DAG cannot substitute for successful materialization.
"""
from datetime import datetime, timezone

from sqlalchemy import select

from app.diagnostics_service import (
    MissingDagRunError, _parse_airflow_datetime, _run_payload, sync_sample_statuses,
)
from app.models import AnalysisRun, PipelineStageExecution, RunAction


def sync_gatk_airflow_status(*, session, airflow_client, analysis_id, settings):
    run = session.scalar(select(AnalysisRun).where(
        AnalysisRun.analysis_id == analysis_id,
        AnalysisRun.pipeline_name == 'gatk').with_for_update())
    if run is None:
        return None
    if run.dag_id != 'bio_gatk' or run.dag_run_id != f'{analysis_id}-a{run.attempt}':
        raise MissingDagRunError('GATK current attempt has no matching DagRun identity')
    payload = airflow_client.get_dag_run(run.dag_id, run.dag_run_id)
    if (payload.get('dag_id'), payload.get('dag_run_id')) != (run.dag_id, run.dag_run_id):
        raise ValueError('GATK Airflow response identity mismatch')
    state = payload.get('state')
    if state not in {'running', 'queued', 'success', 'failed'}:
        raise ValueError('GATK Airflow response has no authoritative state')
    # Successful/cancelled runs are immutable to delayed orchestration snapshots.
    if run.status in {'success', 'cancelled', 'canceled', 'cancel_requested'}:
        return _run_payload(run)
    if state == 'failed':
        from app.cce_recovery_budget import dag_failure_fence_reason
        if dag_failure_fence_reason(session=session, run=run, dag_run_id=run.dag_run_id):
            return _run_payload(run)

    executions = session.scalars(select(PipelineStageExecution).where(
        PipelineStageExecution.analysis_id == analysis_id,
        PipelineStageExecution.pipeline_name == 'gatk',
        PipelineStageExecution.attempt == run.attempt,
    ).order_by(PipelineStageExecution.generation.desc())).all()
    latest = {}
    for execution in executions:
        latest.setdefault(execution.stage_code, execution)
    now = datetime.now(timezone.utc)
    was_failed = run.status == 'failed'
    if state in {'running', 'queued'}:
        # Check every latest stage: an old successful Step2 cannot hide failed
        # Step3. Historical failed generations do not veto an explicit reopen.
        if any(row.status in {'failed', 'canceled', 'cancelled'} for row in latest.values()):
            return _run_payload(run)
        current = latest.get(run.current_stage)
        if was_failed and (state != 'running' or current is None or current.status not in {
            'accepted', 'queued', 'running', 'success',
        }):
            return _run_payload(run)
        run.status = 'running' if state == 'running' else 'submitted'
        run.started_at = _parse_airflow_datetime(payload.get('start_date')) or run.started_at
        run.ended_at = None
        run.pipeline_finished_at = None
        run.error_summary = None
        if was_failed:
            session.add(RunAction(analysis_id=analysis_id,
                action='gatk_airflow_reconciled', requested_by='airflow-observer',
                payload_json={'attempt': run.attempt, 'dag_run_id': run.dag_run_id,
                    'stage': current.stage_code, 'generation': current.generation,
                    'execution_id': current.execution_id}, result_status='running',
                message='Current DagRun resumed; existing runtime and output retained.'))
    elif state == 'success':
        materialize = latest.get('step6_materialize')
        if (materialize is None or materialize.status != 'success'
            or any(row.status in {'failed', 'canceled', 'cancelled'} for row in latest.values())):
            return _run_payload(run)
        run.status = 'success'
        run.ended_at = _parse_airflow_datetime(payload.get('end_date')) or now
        run.pipeline_finished_at = run.ended_at
        run.error_summary = None
        run.progress_percent = 100
        run.progress_updated_at = run.ended_at
    else:
        run.status = 'failed'
        run.ended_at = _parse_airflow_datetime(payload.get('end_date')) or run.ended_at or now
        run.pipeline_finished_at = run.pipeline_finished_at or run.ended_at
        run.error_summary = run.error_summary or 'GATK Airflow run failed; inspect task logs.'
    sync_sample_statuses(session=session, analysis_id=analysis_id, run_status=run.status)
    session.commit()
    session.refresh(run)
    return _run_payload(run)
