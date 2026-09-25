"""Internal CCE recovery reservations; deliberately no dispatch or public route.

Call only after bound runtime evidence validation, inside a caller transaction.
The caller must commit before any external side effect and recheck control fences
at dispatch. Policy AND a zero-count budget must be frozen for a new attempt;
absence of historical state never grants a fresh budget. PostgreSQL serializes
reservations on the existing AnalysisRun row, shared with control operations.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.models import AnalysisRun, RunAction, WgsMaintenanceAction


ACTION = "cce_compute_recovery"
DELAYS = (60, 180)
STOPPED = {"success", "cancel_requested", "cancelled", "canceled", "terminated",
           "paused", "pause_requested", "delete_requested", "deleted"}
FINISHED_ACTIONS = {"success", "failed", "rejected", "cancelled", "canceled"}
CONTROL_ACTIONS = {"resume_stage", "resume", "rerun_failed", "cancel_submission",
                   "pause", "cancel", "delete", "terminate"}


def compute_finished(action):
    return (action.result_status in FINISHED_ACTIONS or
        (action.result_status=='queued' and isinstance(action.payload_json,dict)
         and action.payload_json.get('compute_terminal') in {'success','failed'}))


def dag_failure_fence_reason(*, session, run, dag_run_id):
    """Return why a failure callback cannot project; caller holds refreshed run lock.

    A waiting reservation has no replacement DagRun authority. Once dispatch is
    persisted, only its exact current DagRun may report its own failure. Retain
    the legacy identity-less callback only where no current recovery exists.
    This does not validate runtime failure evidence or authorize any dispatch.
    """
    if dag_run_id is not None and dag_run_id != run.dag_run_id:
        return 'superseded_dag_run'
    if run.current_stage == 'step3_monitor' and run.status not in STOPPED:
        from app.models import WgsStageExecution, PipelineStageExecution
        from app.cce_monitor_observation import query_unconfirmed
        model = WgsStageExecution if run.pipeline_name == 'wgs' else PipelineStageExecution
        query = select(model).where(model.analysis_id == run.analysis_id,
            model.attempt == run.attempt, model.stage_code == 'step3_monitor')
        if model is PipelineStageExecution:
            query = query.where(model.pipeline_name == run.pipeline_name)
        row = session.scalar(query.order_by(model.generation.desc()).limit(1))
        if row is not None and query_unconfirmed(row):
            return 'monitor_execution_unconfirmed'
    actions = session.scalars(select(RunAction).where(
        RunAction.analysis_id == run.analysis_id, RunAction.action == ACTION)).all()
    for action in actions:
        data = action.payload_json
        if not isinstance(data, dict) or type(data.get('attempt')) is not int:
            return 'ambiguous_recovery_identity'
        if data['attempt'] != run.attempt:
            continue
        if not dag_run_id:
            return 'recovery_callback_identity_required'
        if not compute_finished(action):
            if (action.result_status not in {'queued', 'uncertain'}
                    or data.get('dag_run_id') != dag_run_id):
                return 'pending_compute_recovery'
    return None


def require_current_dag_cleanup(*, session, analysis_id, attempt, pipeline,
                                dag_run_id, resume_action_id=None):
    """Fence external DagRun cleanup under the run lock, without committing.

    Trusted runtime terminal ingestion keeps its existing receipt/lease guards;
    this check is only for Airflow release and observer-deactivate requests.
    """
    run = session.scalar(select(AnalysisRun).where(
        AnalysisRun.analysis_id == analysis_id,
        AnalysisRun.pipeline_name == pipeline).with_for_update()
        .execution_options(populate_existing=True))
    if run is None or run.attempt != attempt:
        raise ValueError('unknown current cleanup attempt')
    reason = dag_failure_fence_reason(session=session, run=run, dag_run_id=dag_run_id)
    if reason:
        raise ValueError(f'DagRun cleanup rejected: {reason}')
    recovery_id = (run.params_json or {}).get('resume_action_id')
    if recovery_id and (not dag_run_id or dag_run_id != run.dag_run_id or resume_action_id != recovery_id):
        raise ValueError('DagRun cleanup requires the current recovery identity')
    return run


def require_no_pending_compute_recovery(*, session, run):
    """Manual retry fence; caller holds/refreshed the same AnalysisRun row lock.

    Stop/cancel paths must not use this fence: user stop keeps priority. Missing
    attempt identity is ambiguous and blocks; completed history is preserved.
    """
    from app.cce_publish_recovery import ACTION as PUBLISH_ACTION, TERMINAL as PUBLISH_TERMINAL
    for action in session.scalars(select(RunAction).where(
            RunAction.analysis_id==run.analysis_id,RunAction.action==PUBLISH_ACTION)):
        data=action.payload_json or {}
        if data.get('attempt') in {None,run.attempt} and (
                action.result_status not in PUBLISH_TERMINAL or data.get('in_flight')):
            raise ValueError('pending publish dispatch must be reconciled before manual resume')
    actions = session.scalars(select(RunAction).where(
        RunAction.analysis_id == run.analysis_id, RunAction.action == ACTION)).all()
    for action in actions:
        if compute_finished(action):
            continue
        data = action.payload_json
        if (not isinstance(data, dict) or type(data.get('attempt')) is not int
                or data['attempt'] == run.attempt):
            raise ValueError('pending automatic recovery must be reconciled before manual resume')


def _date(value):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError) as error:
        raise ValueError("invalid recovery deadline") from error


def reserve_compute_recovery(*, session, analysis_id, attempt,
                             source_execution_id, source_master_uid, now):
    """Reserve/replay an action, never commit, sleep, dispatch or change run state."""
    if type(attempt) is not int or attempt < 1:
        raise ValueError("invalid recovery attempt")
    if any(not isinstance(value, str) or not value.strip() or len(value) > 256
           for value in (source_execution_id, source_master_uid)):
        raise ValueError("recovery source identity is required")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("timezone-aware recovery time required")
    now = now.astimezone(timezone.utc)
    run = session.scalar(select(AnalysisRun).where(
        AnalysisRun.analysis_id == analysis_id).with_for_update()
        .execution_options(populate_existing=True))
    if run is None or run.attempt != attempt:
        raise ValueError("unknown current recovery attempt")
    if run.pipeline_name not in {"wgs", "gatk"} or run.execution_mode != "cce":
        raise ValueError("recovery requires WGS/GATK CCE")
    if run.status in STOPPED:
        raise ValueError("recovery stopped by terminal or user control state")
    params = dict(run.params_json or {})
    policy = params.get("cce_recovery_policy")
    if (not isinstance(policy, dict) or type(policy.get("version")) is not int
            or policy["version"] != 1 or type(policy.get("attempt")) is not int
            or policy["attempt"] != attempt or policy.get("enabled") is not True):
        raise ValueError("missing, disabled or mismatched recovery policy")
    budget = params.get("cce_recovery_budget")
    if (not isinstance(budget, dict) or type(budget.get("attempt")) is not int
            or budget["attempt"] != attempt or type(budget.get("count")) is not int
            or not 0 <= budget["count"] <= len(DELAYS)
            or not isinstance(budget.get("original_deadline"), str)):
        raise ValueError("missing or invalid recovery budget")
    deadline = _date(budget.get("original_deadline"))
    if deadline != _date(policy.get("original_deadline")) or now >= deadline:
        raise ValueError("recovery deadline changed or exhausted")

    actions = session.scalars(select(RunAction).where(
        RunAction.analysis_id == analysis_id).order_by(RunAction.id)).all()
    journal = []
    for action in actions:
        data = action.payload_json
        if action.action == ACTION:
            if not isinstance(data, dict) or type(data.get("attempt")) is not int:
                raise ValueError("invalid recovery budget journal")
            if data["attempt"] != attempt:
                continue
            journal.append(action)
        elif action.action in CONTROL_ACTIONS and action.result_status not in FINISHED_ACTIONS:
            if not isinstance(data, dict) or data.get("attempt") in {None, attempt}:
                raise ValueError("active control action blocks recovery")
    maintenance = session.scalars(select(WgsMaintenanceAction).where(
        WgsMaintenanceAction.analysis_id == analysis_id,
        WgsMaintenanceAction.attempt == attempt)).all()
    if any(action.status not in FINISHED_ACTIONS for action in maintenance):
        raise ValueError("active maintenance blocks recovery")
    if len(journal) != budget["count"]:
        raise ValueError("recovery budget disagrees with durable journal")
    for ordinal, action in enumerate(journal, 1):
        data = action.payload_json
        if (data.get("ordinal") != ordinal or data.get("pipeline") != run.pipeline_name
                or data.get("workdir") != run.workdir or not data.get("action_id")
                or _date(data.get("original_deadline")) != deadline):
            raise ValueError("recovery budget journal identity differs")
    # Replay never consumes a second slot, including a late callback after slot 2.
    for action in journal:
        data = action.payload_json
        if data.get("source_execution_id") == source_execution_id and data.get("source_master_uid") == source_master_uid:
            return deepcopy(data)
        if data.get("source_master_uid") == source_master_uid:
            raise ValueError("recovery source identity differs for the same Master")
    if any(not compute_finished(action) for action in journal):
        raise ValueError("another recovery action is active")
    count = budget["count"]
    if count >= len(DELAYS):
        raise ValueError("automatic recovery budget exhausted")
    retry_at = now + timedelta(seconds=DELAYS[count])
    if retry_at >= deadline:
        raise ValueError("recovery wait exceeds original deadline")
    data = dict(action_id="cce_recovery_" + uuid4().hex, policy_version=1,
                pipeline=run.pipeline_name, attempt=attempt, workdir=run.workdir,
                source_execution_id=source_execution_id, source_master_uid=source_master_uid,
                ordinal=count + 1, next_retry_at=retry_at.isoformat(),
                original_deadline=deadline.isoformat())
    session.add(RunAction(analysis_id=analysis_id, action=ACTION,
        requested_by="internal-cce-recovery", result_status="reserved",
        payload_json=data, created_at=now))
    run.params_json = dict(params, cce_recovery_budget=dict(budget, count=count + 1))
    session.flush()
    return deepcopy(data)
