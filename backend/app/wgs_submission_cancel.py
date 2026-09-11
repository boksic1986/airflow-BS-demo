"""Cancel only quiescent, pre-configuration manual submissions; never delete data."""
from datetime import datetime, timezone
from sqlalchemy import select
from app.models import AnalysisRun, Sample, RunAction, WgsExecutionDispatch

FENCED_PHASES = {'cancelling_submission', 'cancelled'}

def _load(session, analysis_id, attempt):
    run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==analysis_id).with_for_update().execution_options(populate_existing=True))
    if run is None or run.attempt != attempt:
        raise ValueError('提交 attempt 已变化，请刷新页面。')
    p=run.params_json or {}
    if run.pipeline_name!='wgs' or p.get('submission_mode')!='three_stage' or p.get('submission_phase') not in {'config_review', *FENCED_PHASES} or p.get('config_approved_at') or p.get('execution_approved_at'):
        raise ValueError('仅支持确认配置前取消；准备中或已经确认配置的任务不能使用此入口。')
    if p.get('submission_phase')=='config_review' and run.status not in {'created','submitted','queued','running'}:
        raise ValueError('任务已结束或状态变化，请刷新。')
    dispatch=session.scalar(select(WgsExecutionDispatch).where(WgsExecutionDispatch.analysis_id==analysis_id))
    if dispatch is not None and dispatch.dispatch_state in {'committed','running'}:
        raise ValueError('任务已经提交执行，不能取消提交。')
    if run.dag_id!='bio_wgs' or run.dag_run_id!=f'{analysis_id}-a{attempt}':
        raise ValueError('Airflow 运行身份不一致，取消已阻止。')
    return run

def _verify_waiting(client, run):
    tasks=client.list_task_instances(run.dag_id,run.dag_run_id)['task_instances']
    states={t['task_id']:t.get('state') for t in tasks}
    if any(states.get(t)!='success' for t in ('prepare_wgs_sampleinfo','wait_prepare_wgs_sampleinfo')) or 'wait_wgs_config_approval' not in states:
        raise ValueError('样本准备未确认完成，暂不允许取消。')
    before={'validate_request','choose_run_path','prepare_wgs_sampleinfo','wait_prepare_wgs_sampleinfo'}
    for task,state in states.items():
        if task=='wait_wgs_config_approval':
            if state not in {None,'scheduled','queued','running','up_for_reschedule','failed'}:
                raise ValueError('配置确认等待状态已变化。')
        elif task in before:
            if state!='success': raise ValueError('准备步骤尚未安全结束。')
        elif state not in {None,'skipped'}:
            raise ValueError('检测到后续任务已启动，取消已阻止。')

def preview_config_cancellation(*,session,airflow_client,analysis_id,attempt):
    run=_load(session,analysis_id,attempt)
    if run.params_json.get('submission_phase')!='cancelled' and not _already_stopped(airflow_client,run): _verify_waiting(airflow_client,run)
    return {'analysis_id':analysis_id,'attempt':attempt,'submission_phase':run.params_json['submission_phase'],
            'effects':['停止此 attempt 的 Airflow 配置等待，禁止继续提交。','本次候选样本标记取消，保留样本表、回执和审计记录。','不修改 pending 文件，不删除本地项目目录、原始数据、SFS 或 OBS 数据。']}

def _already_stopped(client,run):
    p=run.params_json or {}
    return p.get('submission_phase')=='cancelling_submission' and p.get('submission_cancel_attempt')==run.attempt and client.get_dag_run(run.dag_id,run.dag_run_id).get('state')=='failed'

def cancel_config_submission(*,session,airflow_client,analysis_id,attempt,requested_by):
    run=_load(session,analysis_id,attempt)
    if run.params_json.get('submission_phase')=='cancelled':
        return {'analysis_id':analysis_id,'attempt':attempt,'status':'cancelled'}
    already_stopped=_already_stopped(airflow_client,run)
    if not already_stopped: _verify_waiting(airflow_client,run)
    if run.params_json.get('submission_phase')!='cancelling_submission':
        run.params_json={**run.params_json,'submission_phase':'cancelling_submission','submission_cancel_attempt':attempt}
        run.status='cancel_requested'
        session.add(RunAction(analysis_id=analysis_id,action='cancel_submission',requested_by=requested_by,result_status='accepted',payload_json={'attempt':attempt,'retained_files':True}))
        session.commit()  # Durable approval fence before the remote request; safe to retry on timeout.
    if not already_stopped: airflow_client.stop_submission_dag(run.dag_id,run.dag_run_id)
    if airflow_client.get_dag_run(run.dag_id,run.dag_run_id).get('state')!='failed':
        raise ValueError('Airflow 尚未确认停止；保留取消中状态，请重试。')
    run=_load(session,analysis_id,attempt)
    run.status='cancelled';run.current_stage='submission_cancelled';run.ended_at=datetime.now(timezone.utc)
    run.params_json={**run.params_json,'submission_phase':'cancelled'}
    for sample in session.scalars(select(Sample).where(Sample.analysis_id==analysis_id)):
        m=sample.metadata_json or {}
        if m.get('selection_attempt')==attempt and m.get('selection_decision')=='candidate':
            sample.status='cancelled'
    for action in session.scalars(select(RunAction).where(RunAction.analysis_id==analysis_id,RunAction.action=='cancel_submission')):
        if (action.payload_json or {}).get('attempt')==attempt: action.result_status='cancelled'
    session.commit()
    return {'analysis_id':analysis_id,'attempt':attempt,'status':'cancelled'}
