"""Idempotently attach observation, never claim or start native work."""
import httpx
from sqlalchemy import select

from app.models import AnalysisRun, AuditLog, WgsStageExecution, WgsOnpremExecutionSnapshot
from app.wgs_onprem_execution_service import RegistrationConflict


def attach_native_monitor(*, session, settings, execution_id, request, username, airflow):
    if (not getattr(settings, 'wgs_onprem_monitor_enabled', False)
            or 'wgs' not in getattr(settings, 'deployed_pipelines', ())
            or request.platform_instance_id != getattr(settings, 'wgs_platform_instance_id', '')):
        raise RegistrationConflict('Native monitoring is disabled or instance differs')
    run = session.scalar(select(AnalysisRun).join(WgsStageExecution,
        WgsStageExecution.analysis_id == AnalysisRun.analysis_id).where(
        WgsStageExecution.execution_id == execution_id).with_for_update(of=AnalysisRun))
    if run is None or not (run.params_json or {}).get('native_monitor_only'):
        raise RegistrationConflict('Native execution is not registered')
    if run.submitted_by != username:
        raise PermissionError('Native execution belongs to another operator')
    stage = session.scalar(select(WgsStageExecution).where(
        WgsStageExecution.execution_id == execution_id).execution_options(populate_existing=True))
    snapshot = session.get(WgsOnpremExecutionSnapshot, execution_id)
    if (snapshot is None or stage.stage_code != 'native_analysis' or stage.status == 'accepted'
            or stage.attempt != run.attempt or stage.generation != request.generation
            or snapshot.operation_id != str(request.operation_id)
            or snapshot.manifest_hash != request.manifest_sha256
            or run.params_json.get('current_native_execution_id') != execution_id):
        raise RegistrationConflict('Monitor attachment references an unclaimed or stale execution')
    dag_id = 'bio_wgs_native_monitor'
    dag_run_id = f'native__{execution_id}'
    conf = dict(pipeline='wgs', monitor_only=True, analysis_id=run.analysis_id,
                execution_id=execution_id, attempt=stage.attempt, generation=stage.generation)
    result = dict(schema_version='wgs.onprem-monitor-attachment.v1',
        analysis_id=run.analysis_id, attempt=stage.attempt, execution_id=execution_id,
        generation=stage.generation, dag_id=dag_id, dag_run_id=dag_run_id, monitor_attached=True)
    prior = (stage.terminal_payload_json or {}).get('monitor_binding')
    if prior:
        if prior != result:
            raise RegistrationConflict('Stored native monitor binding differs')
        return result
    try:
        remote = airflow.trigger_dag_run(dag_id, dag_run_id=dag_run_id, conf=conf)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 409:
            raise
        remote = airflow.get_dag_run(dag_id, dag_run_id)
    if remote.get('dag_run_id') != dag_run_id or remote.get('conf') != conf:
        raise RegistrationConflict('Existing Airflow monitor identity differs')
    stage.terminal_payload_json = {**(stage.terminal_payload_json or {}), 'monitor_binding': result}
    run.dag_id = dag_id
    run.dag_run_id = dag_run_id
    session.add(AuditLog(username=username, action='wgs.onprem.monitor.attach',
                        analysis_id=run.analysis_id, payload_json=result))
    session.commit()
    return result
