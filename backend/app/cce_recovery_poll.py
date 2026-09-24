"""One existing Airflow sensor poll -> durable recovery action; never a loop."""
from sqlalchemy import select

from app.models import AnalysisRun, RunAction
from app.cce_recovery_budget import ACTION, FINISHED_ACTIONS, STOPPED
from app.cce_recovery_service import reserve_monitored_recovery
from app.cce_compute_dispatch import dispatch_due_recovery


def poll_compute_recovery(*, session, settings, airflow_client, analysis_id, attempt,
                          pipeline, dag_run_id, resume_action_id, now):
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==analysis_id)
        .with_for_update().execution_options(populate_existing=True))
    if (not run or run.attempt!=attempt or run.pipeline_name!=pipeline
            or pipeline not in {'wgs','gatk'} or run.execution_mode!='cce' or not dag_run_id):
        raise ValueError('unknown recovery polling identity')
    actions = session.scalars(select(RunAction).where(RunAction.analysis_id==analysis_id,
        RunAction.action==ACTION).order_by(RunAction.id.desc()).with_for_update()
        .execution_options(populate_existing=True)).all()
    actions = [a for a in actions if (a.payload_json or {}).get('attempt')==attempt]
    action = actions[0] if actions else None
    # The old sensor may only reconcile the action it originally requested.
    old_caller = bool(action and action.payload_json.get('original_dag_run_id')==dag_run_id
        and action.payload_json.get('original_resume_action_id')==resume_action_id)
    if dag_run_id != run.dag_run_id:
        if not old_caller:
            return dict(status='superseded')
        if action.result_status=='queued':
            return dict(status='delegated',action_id=action.payload_json['action_id'])
        if action.result_status in FINISHED_ACTIONS:
            return dict(status='needs_attention')
    elif (run.params_json or {}).get('resume_action_id')!=resume_action_id:
        return dict(status='superseded')
    if pipeline=='wgs':
        from app.wgs_resume_service import _latest as latest
    else:
        from app.gatk_runtime_service import _latest_gatk as latest
    monitor = latest(session,run,'step3_monitor')
    current_action = next((a for a in actions if a.payload_json.get('action_id')==resume_action_id),None)
    if current_action and monitor and dag_run_id==run.dag_run_id:
        data = current_action.payload_json
        if (monitor.status in {'success','failed'} and monitor.generation==data.get('generation')
                and data.get('dag_run_id')==dag_run_id and current_action.result_status=='queued'):
            # The same action still authorizes downstream after successful
            # compute; only the automatic budget/manual fence considers it done.
            current_action.payload_json = dict(data,compute_terminal=monitor.status)
            session.flush()
    if monitor and monitor.status=='success' and dag_run_id==run.dag_run_id:
        session.commit()
        return dict(status='complete')
    policy = (run.params_json or {}).get('cce_recovery_policy')
    if not isinstance(policy,dict) or policy.get('enabled') is not True or policy.get('attempt')!=attempt:
        session.commit()
        return dict(status='not_eligible')
    pending = bool(action and action.result_status in {'reserved','uncertain'}
        and not action.payload_json.get('compute_terminal'))
    try:
        if not pending:
            if (run.status in STOPPED or run.current_stage!='step3_monitor'
                    or not monitor or monitor.status!='failed' or dag_run_id!=run.dag_run_id):
                return dict(status='not_eligible')
            receipt = reserve_monitored_recovery(session=session,analysis_id=analysis_id,attempt=attempt,
                monitor_execution_id=monitor.execution_id,evidence_root=None,now=now)
            action = session.scalar(select(RunAction).where(RunAction.analysis_id==analysis_id,
                RunAction.action==ACTION).order_by(RunAction.id.desc()).limit(1))
            if action.payload_json['action_id']!=receipt['action_id']:
                raise ValueError('automatic reservation was superseded')
        if 'original_dag_run_id' not in action.payload_json:
            action.payload_json = dict(action.payload_json,original_dag_run_id=dag_run_id,
                original_resume_action_id=resume_action_id)
        session.commit()  # Sensor reschedule/process restart sees exactly this action.
        result = dispatch_due_recovery(session=session,settings=settings,airflow_client=airflow_client,
            analysis_id=analysis_id,attempt=attempt,action_id=action.payload_json['action_id'],now=now)
        if result['status']=='queued':
            return dict(result,status='delegated')
        return result
    except ValueError:
        # Preserve an ambiguous POST for GET-only reconciliation. A proven
        # untransmitted action can terminate so manual intervention is possible.
        if action and action.result_status in {'reserved','uncertain'}:
            if action.payload_json.get('dispatch_state') not in {'post_intent','confirmed'}:
                action.result_status='rejected'
                action.message='Automatic recovery requires manual review'
        session.commit()
        return dict(status='needs_attention')
