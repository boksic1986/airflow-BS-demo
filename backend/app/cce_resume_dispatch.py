"""Shared durable Resume dispatch, independent of pipeline stage storage."""
import httpx
from sqlalchemy import select
from app.models import AnalysisRun, RunAction


def recovery_action(session, run, action_id):
    action = session.scalar(select(RunAction).where(RunAction.analysis_id == run.analysis_id,
        RunAction.action == 'resume_stage').order_by(RunAction.id.desc()).limit(1))
    if not action or action.payload_json.get('action_id') != action_id or action.payload_json.get('attempt') != run.attempt:
        raise ValueError('recovery action does not match the current attempt')
    if (run.params_json or {}).get('resume_action_id') != action_id:
        raise ValueError('recovery action has been superseded')
    return action


def authorize_recovery_stage(*, session, run, action_id, dag_run_id, stage):
    """Fence all recovery registrations, including slot acquire and finalize."""
    action = recovery_action(session, run, action_id)
    data = action.payload_json
    if (not dag_run_id or dag_run_id != run.dag_run_id or dag_run_id != data.get('dag_run_id')
            or action.result_status not in {'reserved', 'uncertain', 'queued'}):
        raise ValueError('stage registration requires the current recovery DagRun')
    # Airflow may start before its POST response reaches us. Only an already
    # persisted POST intent (or a confirmed legacy action) authorizes that DAG.
    if action.result_status != 'queued' and data.get('dispatch_state') != 'post_intent':
        raise ValueError('recovery dispatch has not been authorized')
    if (not stage.startswith('release_') and run.status in {'pause_requested', 'paused',
            'cancel_requested', 'canceled', 'cancelled', 'terminated', 'delete_requested', 'deleted'}):
        raise ValueError('recovery stage blocked by current control state')
    required = {'acquire_input_transfer_slot': 'step1_upload',
                'release_input_transfer_slot': 'step1_upload',
                'acquire_result_transfer_slot': 'step5_download',
                'release_result_transfer_slot': 'step5_download'}.get(stage, stage)
    # Finalize still validates the existing Step6 receipt in the endpoint; that
    # successful stage may deliberately be absent from resume_stages.
    if stage not in {'release_leases', 'finalize_run'} and required not in data['resume_stages']:
        raise ValueError('stage is outside the recovery action')
    return action


def dispatch_recovery(*, session, run, action, airflow_client, latest_execution):
    """One durable POST intent; an uncertain action is reconciled by GET only."""
    analysis_id, action_pk = run.analysis_id, action.id
    def refresh():
        current = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            .with_for_update().execution_options(populate_existing=True))
        row = session.scalar(select(RunAction).where(RunAction.id == action_pk)
            .with_for_update().execution_options(populate_existing=True))
        data = row.payload_json
        if (current.attempt != data['attempt'] or current.dag_run_id != data['dag_run_id']
                or (current.params_json or {}).get('resume_action_id') != data['action_id']):
            raise ValueError('recovery action has been superseded')
        return current, row

    run, action = refresh()
    if action.result_status == 'rejected':
        raise ValueError(action.message or 'recovery dispatch was rejected')
    if action.result_status == 'queued':
        return action
    data = action.payload_json
    outcome, message = 'uncertain', 'Recovery dispatch is unconfirmed; reconcile the same action'
    try:
        try:
            found = airflow_client.get_dag_run(run.dag_id, data['dag_run_id'])
        except httpx.HTTPStatusError as error:
            if error.response.status_code != 404:
                raise
            # Old reserved/uncertain records have no proof that POST never ran.
            if data.get('dispatch_state') != 'not_started':
                raise
            action.payload_json = dict(data, dispatch_state='post_intent')
            session.commit()  # Survives process death and response loss before POST.
            run, action = refresh()
            if action.result_status == 'queued':
                return action
            if run.status in {'success', 'pause_requested', 'paused', 'cancel_requested',
                              'canceled', 'cancelled', 'terminated', 'delete_requested', 'deleted'}:
                raise ValueError('recovery dispatch blocked by current control state')
            data = action.payload_json
            try:
                found = airflow_client.trigger_dag_run(run.dag_id, dag_run_id=data['dag_run_id'], conf=data['conf'])
            except httpx.HTTPStatusError as error:
                if error.response.status_code not in {408, 409, 429} and error.response.status_code < 500:
                    raise
                found = airflow_client.get_dag_run(run.dag_id, data['dag_run_id'])
            except httpx.TransportError:
                found = airflow_client.get_dag_run(run.dag_id, data['dag_run_id'])
        if (not isinstance(found, dict) or found.get('dag_run_id') != data['dag_run_id']
                or found.get('conf') != data['conf']):
            raise ValueError('existing recovery DagRun identity differs')
        outcome, message = 'queued', None
    except httpx.HTTPStatusError as error:
        code = error.response.status_code
        if code not in {404, 408, 429} and not 500 <= code < 600:
            outcome = 'rejected'
            message = f'Airflow rejected recovery dispatch (HTTP {code}); correct authorization or parameters before a new action'
    except httpx.TransportError:
        pass
    except ValueError as error:
        message = str(error)
    # Never let a slow response overwrite newer control/progress or a confirmed
    # replay. All callers use the same refreshed run -> action lock order.
    run, action = refresh()
    if action.result_status != 'queued':
        action.result_status, action.message = outcome, message
        if outcome == 'queued':
            action.payload_json = dict(action.payload_json, dispatch_state='confirmed')
            current = latest_execution(session, run, action.payload_json['stage'])
            failures = session.scalars(select(RunAction).where(RunAction.analysis_id == analysis_id,
                RunAction.action == 'airflow_dag_failed')).all()
            dag_failed = any((item.payload_json or {}).get('attempt') == run.attempt
                and (item.payload_json or {}).get('dag_run_id') == run.dag_run_id for item in failures)
            if (run.status in {'failed', 'needs_recovery'} and run.current_stage == action.payload_json['stage']
                    and not dag_failed and found.get('state') in {'queued', 'running'}
                    and current and current.status == 'accepted'
                    and current.generation == action.payload_json['generation']):
                run.status = 'queued'
                run.ended_at = run.pipeline_finished_at = None
                run.error_summary = None
        session.commit()
    if action.result_status == 'rejected':
        raise ValueError(action.message)
    return action
