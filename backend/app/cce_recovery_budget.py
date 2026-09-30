"""Internal CCE recovery reservations; deliberately no dispatch or public route.

Call only after bound runtime evidence validation, inside a caller transaction.
The caller must commit before any external side effect and recheck control fences
at dispatch. Policy AND a zero-count budget must be frozen for a new attempt;
absence of historical state never grants a fresh budget. PostgreSQL serializes
reservations on the existing AnalysisRun row, shared with control operations.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from uuid import uuid4

from sqlalchemy import select

from app.models import AnalysisRun, ObserverRunState, PipelineStageExecution, RunAction, WgsMaintenanceAction, WgsStageExecution


ACTION = "cce_compute_recovery"
DELAYS = (60, 180)
STOPPED = {"success", "cancel_requested", "cancelled", "canceled", "terminated",
           "paused", "pause_requested", "delete_requested", "deleted"}
FINISHED_ACTIONS = {"success", "failed", "rejected", "cancelled", "canceled"}
CONTROL_ACTIONS = {"resume_stage", "resume", "rerun_failed", "cancel_submission",
                   "pause", "cancel", "delete", "terminate"}
NATIVE_STAGES = frozenset({"step1_upload", "step2_master", "step3_monitor",
                           "step4_publish", "step5_download", "step6_materialize"})
_CLEANUP_STAGE = {"release_input_transfer_slot": "step1_upload",
                  "release_result_transfer_slot": "step5_download",
                  "observer_deactivate": "step3_monitor"}


def bound_compute_terminal(*, session, run, action, settings=None,
                           native_stage_observation=None):
    """Return only a terminal bound to this queued action and its frozen Step3.

    A fresh native observation may establish the durable compute-only permit.
    Later budget checks use that exact persisted binding, while the queued
    action continues to authorize its downstream stages.
    """
    data = action.payload_json if action is not None else None
    if (action is None or action.action not in {ACTION, 'resume_stage'}
            or action.result_status != 'queued'
            or not isinstance(data, dict) or data.get('attempt') != run.attempt
            or data.get('stage') != 'step3_monitor' or data.get('dispatch_state') != 'confirmed'
            or type(data.get('generation')) is not int or data['generation'] < 1
            or not isinstance(data.get('action_id'), str) or not data['action_id']
            or not isinstance(data.get('dag_run_id'), str) or not data['dag_run_id']
            or not isinstance(data.get('resume_stages'), list)
            or 'step3_monitor' not in data['resume_stages']):
        return None
    conf = data.get('conf')
    if (not isinstance(conf, dict) or conf.get('analysis_id') != run.analysis_id
            or conf.get('attempt') != run.attempt or conf.get('pipeline') != run.pipeline_name
            or conf.get('execution_mode') != 'cce' or conf.get('workdir') != run.workdir
            or conf.get('resume_stage') != 'step3_monitor'
            or conf.get('resume_action_id') != data['action_id']):
        return None
    params = run.params_json
    if not isinstance(params, dict):
        return None
    if run.pipeline_name == 'wgs':
        release = params.get('pipeline_release_id')
    else:
        profile, revision = params.get('runtime_profile_id'), params.get('runtime_profile_revision')
        if not profile or not revision:
            return None
        release = f'{profile}@{revision}'
    if not isinstance(release, str) or not release:
        return None
    model = WgsStageExecution if run.pipeline_name == 'wgs' else PipelineStageExecution
    conditions = [model.analysis_id == run.analysis_id, model.attempt == run.attempt,
                  model.stage_code == 'step3_monitor', model.generation == data['generation']]
    if model is PipelineStageExecution:
        conditions.append(model.pipeline_name == run.pipeline_name)
    row = session.scalar(select(model).where(*conditions))
    if (row is None or row.status not in {'success', 'failed'} or row.release_id != release
            or not isinstance(row.request_hash, str)
            or re.fullmatch(r'[a-f0-9]{64}', row.request_hash) is None
            or not isinstance(row.receipt_hash, str)
            or re.fullmatch(r'[a-f0-9]{64}', row.receipt_hash) is None):
        return None
    if row.status == 'failed':
        payload = row.terminal_payload_json
        if not isinstance(payload, dict):
            return None
        source_id = payload.get('cce_master_submit_execution_id')
        binding = payload.get('cce_master_binding')
        if not isinstance(source_id, str) or not isinstance(binding, dict):
            return None
        source_conditions = [model.analysis_id == run.analysis_id, model.attempt == run.attempt,
                             model.execution_id == source_id]
        if model is PipelineStageExecution:
            source_conditions.append(model.pipeline_name == run.pipeline_name)
        source = session.scalar(select(model).where(*source_conditions))
        source_payload = source.terminal_payload_json if source is not None else None
        if (source is None or source.stage_code not in {'step2_master', 'step3_monitor'}
                or source.status not in {'success', 'failed'} or source.release_id != release
                or not isinstance(source_payload, dict)
                or source_payload.get('cce_master_binding') != binding):
            return None
        expected_platform = dict(pipeline=run.pipeline_name, analysis_id=run.analysis_id,
            attempt=run.attempt, stage=source.stage_code, execution_id=source.execution_id,
            generation=source.generation, request_hash=source.request_hash)
        from app.cce_recovery_evidence import validate_schema2_recovery_evidence
        try:
            validate_schema2_recovery_evidence(binding=binding,
                evidence=payload.get('cce_recovery_evidence'), expected_platform=expected_platform,
                allow_active_workers=True)
        except ValueError:
            return None
    state = 'succeeded' if row.status == 'success' else 'failed'
    saved = data.get('compute_terminal_binding')
    if data.get('compute_terminal') == row.status and isinstance(saved, dict):
        expected_saved = dict(execution_id=row.execution_id, generation=row.generation,
            request_hash=row.request_hash, receipt_hash=row.receipt_hash,
            registration_sha256=saved.get('registration_sha256'), state=state,
            action_id=data['action_id'], dag_run_id=data['dag_run_id'])
        if (saved == expected_saved and isinstance(saved['registration_sha256'], str)
                and re.fullmatch(r'[a-f0-9]{64}', saved['registration_sha256'])):
            return dict(state=row.status, binding=saved)
    if (native_stage_observation is None or settings is None or run.status in STOPPED
            or data.get('compute_terminal') not in {None, row.status}
            or run.dag_run_id != data['dag_run_id']
            or params.get('resume_action_id') != data['action_id']):
        return None
    latest_conditions = [model.analysis_id == run.analysis_id, model.attempt == run.attempt,
                         model.stage_code == 'step3_monitor']
    if model is PipelineStageExecution:
        latest_conditions.append(model.pipeline_name == run.pipeline_name)
    latest = session.scalar(select(model).where(*latest_conditions)
        .order_by(model.generation.desc()).limit(1))
    if latest is None or latest.execution_id != row.execution_id:
        return None
    try:
        if run.pipeline_name == 'wgs':
            from app.wgs_stage_execution_service import require_frozen_request_digest
            path = (Path(settings.wgs_runtime_request_root) / run.analysis_id /
                    f'attempt-{run.attempt}' / 'step3_monitor.json')
            if not path.is_file() or path.is_symlink():
                return None
            frozen = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(frozen, dict):
                return None
            require_frozen_request_digest(frozen, row)
        else:
            from app.gatk_runtime_service import _request_path, _validate_recovery_request
            path = _request_path(settings, run.analysis_id, run.attempt, 'step3_monitor')
            if not path.is_file() or path.is_symlink():
                return None
            frozen = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(frozen, dict):
                return None
            _validate_recovery_request(run, row, frozen)
        from app.stage_execution_contract import STAGE_EXECUTION_EXTENSION, require_native_stage_terminal
        if (frozen.get('stage_execution') != STAGE_EXECUTION_EXTENSION
                or frozen.get('resume_action_id') != data['action_id']):
            return None
        validated = require_native_stage_terminal(native_stage_observation,
            pipeline=run.pipeline_name, analysis_id=run.analysis_id, attempt=run.attempt,
            stage='step3_monitor', execution_id=row.execution_id, generation=row.generation,
            request_hash=row.request_hash, evidence_ref=row.receipt_hash,
            expected_state=state)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
    proof = dict(execution_id=row.execution_id, generation=row.generation,
        request_hash=row.request_hash, receipt_hash=row.receipt_hash,
        registration_sha256=validated['execution_ref']['registration_sha256'], state=state,
        action_id=data['action_id'], dag_run_id=data['dag_run_id'])
    return dict(state=row.status, binding=proof)


def compute_finished(action, *, session, run):
    if action.result_status in FINISHED_ACTIONS:
        return True
    terminal = bound_compute_terminal(session=session, run=run, action=action)
    data = action.payload_json or {}
    return bool(terminal and data.get('compute_terminal') == terminal['state']
                and data.get('compute_terminal_binding') == terminal['binding'])


def _current_native_stage_row(*, session, run, cleanup_stage=None):
    """Choose the current registered execution from trusted run/route state."""
    if run.pipeline_name not in {"wgs", "gatk"}:
        return None
    model = WgsStageExecution if run.pipeline_name == "wgs" else PipelineStageExecution
    filters = [model.analysis_id == run.analysis_id, model.attempt == run.attempt]
    if model is PipelineStageExecution:
        filters.append(model.pipeline_name == run.pipeline_name)
    stage = _CLEANUP_STAGE.get(cleanup_stage)
    if stage is None and run.current_stage in NATIVE_STAGES:
        stage = run.current_stage
    if stage is None and cleanup_stage != "release_leases" and run.current_stage not in {
            "finalize_run", "release_input_transfer_slot", "release_result_transfer_slot",
            "release_leases"}:
        return None
    if stage is not None:
        filters.append(model.stage_code == stage)
    else:
        filters.append(model.stage_code.in_(NATIVE_STAGES))
    return session.scalar(select(model).where(*filters).order_by(model.id.desc()).limit(1))


def _marked_native_terminal(*, session, run, settings, native_stage_observation,
                            cleanup_stage=None):
    """Return None for legacy, or (confirmed, row) for a marked current stage.

    A service-token caller supplies a fresh read-only observation. The database
    row and version-correct frozen request determine the expected identity;
    neither the caller's stage name nor UI monitoring health grants authority.
    """
    if (run.execution_mode != "cce" or
            (run.params_json or {}).get("orchestration_contract_version") != 2):
        return None
    row = _current_native_stage_row(session=session, run=run, cleanup_stage=cleanup_stage)
    if row is None:
        # A frozen marked request can exist before its registration is visible.
        # In particular, a Step2 submit terminal cannot drain Step3's observer.
        if cleanup_stage == "observer_deactivate":
            observer = session.scalar(select(ObserverRunState).where(
                ObserverRunState.analysis_id == run.analysis_id,
                ObserverRunState.attempt == run.attempt,
            ))
            if observer is None or observer.lifecycle_status == "stopped":
                return None  # Existing observer drain is an idempotent no-op.
            return False, None
        stage = _CLEANUP_STAGE.get(cleanup_stage)
        if stage is None and run.current_stage in NATIVE_STAGES:
            stage = run.current_stage
        if stage is not None and settings is not None:
            try:
                if run.pipeline_name == "wgs":
                    path = (Path(settings.wgs_runtime_request_root) / run.analysis_id /
                            f"attempt-{run.attempt}" / f"{stage}.json")
                else:
                    from app.gatk_runtime_service import _request_path
                    path = _request_path(settings, run.analysis_id, run.attempt, stage)
                if path.is_symlink():
                    return False, None
                if path.is_file():
                    frozen = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(frozen, dict) or frozen.get("stage_execution") is not None:
                        return False, None
            except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError):
                return False, None
        return None
    if settings is None:
        if row.stage_code == "step3_monitor":
            from app.cce_monitor_observation import query_unconfirmed
            if query_unconfirmed(row):
                return None  # Preserve the existing legacy diagnostic reason.
        return False, row
    if cleanup_stage == "release_leases" and row.stage_code == "step2_master":
        # Step2 is only a Master handoff; it does not prove the compute stopped.
        return False, row
    params = run.params_json or {}
    if run.pipeline_name == "wgs":
        release = params.get("pipeline_release_id")
    else:
        profile, revision = params.get("runtime_profile_id"), params.get("runtime_profile_revision")
        release = f"{profile}@{revision}" if profile and revision else None
    if not isinstance(release, str) or not release or row.release_id != release:
        return False, row
    try:
        if run.pipeline_name == "wgs":
            from app.wgs_stage_execution_service import require_frozen_request_digest
            path = (Path(settings.wgs_runtime_request_root) / run.analysis_id /
                    f"attempt-{run.attempt}" / f"{row.stage_code}.json")
            if not path.is_file() or path.is_symlink():
                return False, row
            frozen = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(frozen, dict):
                return False, row
            require_frozen_request_digest(frozen, row)
            marker = frozen.get("stage_execution")
        else:
            from app.gatk_runtime_service import _registration_payload, _request_path
            if _request_path(settings, run.analysis_id, run.attempt, row.stage_code).is_symlink():
                return False, row
            marker = _registration_payload(row, settings).get("stage_execution")
        if marker is None:
            return None
        from app.stage_execution_contract import STAGE_EXECUTION_EXTENSION, require_native_stage_terminal
        if marker != STAGE_EXECUTION_EXTENSION:
            return False, row
        expected_state = {"success": "succeeded", "failed": "failed",
                          "canceled": "canceled", "cancelled": "canceled"}.get(row.status)
        if expected_state is None:
            return False, row
        require_native_stage_terminal(
            native_stage_observation, pipeline=run.pipeline_name,
            analysis_id=run.analysis_id, attempt=run.attempt,
            stage=row.stage_code, execution_id=row.execution_id,
            generation=row.generation, request_hash=row.request_hash,
            evidence_ref=row.receipt_hash, expected_state=expected_state,
        )
    except (AttributeError, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False, row
    return True, row


def _failed_step3_workers_quiet(*, session, run, row):
    """Reuse the current schema2 FINAL/Worker proof before draining Step3."""
    payload = row.terminal_payload_json
    if not isinstance(payload, dict):
        return False
    source_id = payload.get("cce_master_submit_execution_id")
    binding = payload.get("cce_master_binding")
    if not isinstance(source_id, str) or not isinstance(binding, dict):
        return False
    model = WgsStageExecution if run.pipeline_name == "wgs" else PipelineStageExecution
    filters = [model.analysis_id == run.analysis_id, model.attempt == run.attempt,
               model.execution_id == source_id]
    if model is PipelineStageExecution:
        filters.append(model.pipeline_name == run.pipeline_name)
    source = session.scalar(select(model).where(*filters))
    source_payload = source.terminal_payload_json if source is not None else None
    if (source is None or source.stage_code not in {"step2_master", "step3_monitor"}
            or source.status not in {"success", "failed"}
            or source.release_id != row.release_id
            or not isinstance(source_payload, dict)
            or source_payload.get("cce_master_binding") != binding):
        return False
    expected = dict(pipeline=run.pipeline_name, analysis_id=run.analysis_id,
        attempt=run.attempt, stage=source.stage_code,
        execution_id=source.execution_id, generation=source.generation,
        request_hash=source.request_hash)
    from app.cce_recovery_evidence import validate_schema2_recovery_evidence
    try:
        result = validate_schema2_recovery_evidence(
            binding=binding, evidence=payload.get("cce_recovery_evidence"),
            expected_platform=expected, allow_active_workers=False,
        )
    except (ValueError, TypeError, KeyError):
        return False
    return result.get("workers_active") is False


def dag_failure_fence_reason(*, session, run, dag_run_id,
                             native_stage_observation=None, settings=None,
                             cleanup_stage=None, for_cleanup=False):
    """Return why a failure callback cannot project; caller holds refreshed run lock.

    A waiting reservation has no replacement DagRun authority. Once dispatch is
    persisted, only its exact current DagRun may report its own failure. Retain
    the legacy identity-less callback only where no current recovery exists.
    Marked native stages additionally require the current frozen request,
    business receipt and same-state native terminal. This does not authorize
    dispatch or replace the downstream transfer/Worker quiet checks.
    """
    if dag_run_id is not None and dag_run_id != run.dag_run_id:
        return 'superseded_dag_run'
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
        if not compute_finished(action, session=session, run=run):
            if (action.result_status not in {'queued', 'uncertain'}
                    or data.get('dag_run_id') != dag_run_id):
                return 'pending_compute_recovery'
    native = _marked_native_terminal(
        session=session, run=run, settings=settings,
        native_stage_observation=native_stage_observation,
        cleanup_stage=cleanup_stage,
    )
    if native is not None:
        if not native[0]:
            return 'native_stage_unconfirmed'
        if not for_cleanup and native[1].status not in {'failed', 'canceled', 'cancelled'}:
            return 'native_stage_not_failed'
        return None
    if run.current_stage == 'step3_monitor' and run.status not in STOPPED:
        from app.cce_monitor_observation import query_unconfirmed
        row = _current_native_stage_row(session=session, run=run)
        if row is not None and query_unconfirmed(row):
            return 'monitor_execution_unconfirmed'
    return None


def require_current_dag_cleanup(*, session, analysis_id, attempt, pipeline,
                                dag_run_id, resume_action_id=None,
                                native_stage_observation=None, settings=None,
                                cleanup_stage=None):
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
    reason = dag_failure_fence_reason(
        session=session, run=run, dag_run_id=dag_run_id,
        native_stage_observation=native_stage_observation, settings=settings,
        cleanup_stage=cleanup_stage, for_cleanup=True,
    )
    if reason:
        raise ValueError(f'DagRun cleanup rejected: {reason}')
    if cleanup_stage in {'observer_deactivate', 'release_leases'}:
        native = _marked_native_terminal(
            session=session, run=run, settings=settings,
            native_stage_observation=native_stage_observation,
            cleanup_stage=cleanup_stage,
        )
        if native is not None and not native[0]:
            raise ValueError('DagRun cleanup rejected: native_stage_unconfirmed')
        if (native is not None and native[1].stage_code == 'step3_monitor'
                and native[1].status in {'failed', 'canceled', 'cancelled'}
                and not _failed_step3_workers_quiet(
                    session=session, run=run, row=native[1],
                )):
            raise ValueError('DagRun cleanup rejected: step3_worker_quiet_unconfirmed')
    recovery_id = (run.params_json or {}).get('resume_action_id')
    if recovery_id and (not dag_run_id or dag_run_id != run.dag_run_id or resume_action_id != recovery_id):
        raise ValueError('DagRun cleanup requires the current recovery identity')
    return run


def require_no_pending_compute_recovery(*, session, run, monitor_handoff=None):
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
        if monitor_handoff is not None and action.id == monitor_handoff.id:
            continue  # Exact confirmed, ended observer; caller binds its successor atomically.
        if compute_finished(action, session=session, run=run):
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
        elif action.action in CONTROL_ACTIONS and not compute_finished(action, session=session, run=run):
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
    if any(not compute_finished(action, session=session, run=run) for action in journal):
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
