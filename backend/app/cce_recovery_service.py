"""Internal evidence-to-reservation bridge; no endpoint, dispatch or policy enable.

Future trusted adapters must populate the immutable Master binding from their
validated frozen handoff, not blindly copy it from an arbitrary terminal payload.
The original Step2 submit execution is deliberately distinct from Step3 monitor.
The caller owns the transaction and must roll it back on error, commit before
external actions, and recheck fences/quiescence at dispatch.
"""
from copy import deepcopy
from datetime import timedelta

from sqlalchemy import select

from app.cce_recovery_budget import ACTION, reserve_compute_recovery, _date
from app.cce_recovery_reader import read_recovery_evidence
from app.cce_recovery_evidence import validate_schema2_recovery_evidence
from app.models import AnalysisRun, PipelineStageExecution, RunAction, WgsStageExecution


def _payload(row):
    value = row.terminal_payload_json
    if not isinstance(value, dict):
        raise ValueError("missing trusted execution binding")
    return value


def reserve_monitored_recovery(*, session, analysis_id, attempt,
                               monitor_execution_id, evidence_root, now):
    """Bind trusted files to current DB lineage, reserve once, leave status alone.

evidence_root is configured by the adapter, not a request field. Missing stored
bindings in historical releases reject; no backfill or invented identity.
"""
    if type(attempt) is not int or attempt < 1:
        raise ValueError("invalid recovery attempt")
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        .with_for_update().execution_options(populate_existing=True))
    if run is None or run.attempt != attempt or run.execution_mode != "cce":
        raise ValueError("unknown current CCE attempt")
    # These are adapter-specific legacy storage models, not a shared API branch.
    if run.pipeline_name == "wgs":
        model = WgsStageExecution
        release = (run.params_json or {}).get("pipeline_release_id")
    elif run.pipeline_name == "gatk":
        model = PipelineStageExecution
        params = run.params_json or {}
        profile, revision = params.get("runtime_profile_id"), params.get("runtime_profile_revision")
        release = f"{profile}@{revision}" if profile and revision is not None else None
    else:
        raise ValueError("unsupported recovery adapter")
    if not release or run.current_stage != "step3_monitor":
        raise ValueError("recovery requires the frozen current analysis stage")
    conditions = [model.analysis_id == analysis_id, model.attempt == attempt]
    if model is PipelineStageExecution:
        conditions.append(model.pipeline_name == run.pipeline_name)

    def latest(stage):
        return session.scalar(select(model).where(*conditions, model.stage_code == stage)
            .order_by(model.generation.desc()).limit(1).with_for_update()
            .execution_options(populate_existing=True))

    monitor = latest("step3_monitor")
    if (monitor is None or monitor.execution_id != monitor_execution_id
            or monitor.status != "failed" or monitor.release_id != release):
        raise ValueError("recovery monitor is not the current failed generation")
    source_id = _payload(monitor).get("cce_master_submit_execution_id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("monitor has no trusted Master submit binding")
    source = session.scalar(select(model).where(*conditions, model.execution_id == source_id)
        .with_for_update().execution_options(populate_existing=True))
    if (source is None or source.stage_code not in {"step2_master", "step3_monitor"}
            or source.status not in {"success", "failed"} or source.release_id != release):
        raise ValueError("invalid Master submit execution binding")
    binding = _payload(source).get("cce_master_binding")
    if not isinstance(binding, dict):
        raise ValueError("missing or changed frozen Master binding")
    schema2 = binding.get('schema_version') == 2
    current_source = latest(source.stage_code)
    if current_source.execution_id != source_id:
        # A new observer does not become a new native producer. Only its verified
        # receipt can retain an older producer; accepted/running/new-Master rows
        # remain a superseding fence.
        if (not schema2 or current_source.status not in {'success','failed'}
                or current_source.release_id != release
                or _payload(current_source).get('cce_master_submit_execution_id') != source_id
                or _payload(current_source).get('cce_master_binding') != binding):
            raise ValueError('Master submit execution was superseded')
    if schema2:
        if _payload(monitor).get('cce_master_binding') != binding:
            raise ValueError('monitor selected a different native Master')
        platform = dict(pipeline=run.pipeline_name,analysis_id=analysis_id,attempt=attempt,
            stage=source.stage_code,execution_id=source.execution_id,generation=source.generation,
            request_hash=source.request_hash)
        validated = validate_schema2_recovery_evidence(binding=binding,
            evidence=_payload(monitor).get('cce_recovery_evidence'),expected_platform=platform,
            allow_active_workers=True)
    else:
        # Preserve the earlier fixed-scope internal contract; it cannot fall back
        # from a missing/mismatched schema2 receipt or invent new legacy evidence.
        if binding.get('workdir') != run.workdir:
            raise ValueError('missing or changed frozen Master binding')
        context = binding.get("context")
        identity = dict(pipeline=run.pipeline_name, analysis_id=analysis_id, attempt=str(attempt),
                        execution_id=source.execution_id, generation=source.generation,
                        request_hash=source.request_hash)
        if not isinstance(context, dict) or any(type(context.get(k)) is not type(v) or context[k] != v
                                                for k, v in identity.items()):
            raise ValueError("Master context differs from frozen submit execution")
        validated = read_recovery_evidence(root=evidence_root,
            relative_dir=binding.get("evidence_scope"), expected_context=context)
    evidence_binding = dict(monitor_execution_id=monitor.execution_id,
        monitor_generation=monitor.generation, monitor_request_hash=monitor.request_hash,
        submit_generation=source.generation, submit_request_hash=source.request_hash,
        release_id=release, category=validated["category"],
        evidence_key=validated["evidence_key"], evidence_sha256=validated["evidence_sha256"])
    if schema2:
        evidence_binding.update(native_binding_sha256=validated['native_binding_sha256'],workdir=run.workdir)
    prior_actions = session.scalars(select(RunAction).where(
        RunAction.analysis_id == analysis_id, RunAction.action == ACTION)).all()
    for prior in prior_actions:
        data = prior.payload_json
        if (isinstance(data, dict) and data.get("attempt") == attempt
                and data.get("source_execution_id") == source.execution_id):
            if (data.get("source_master_uid") != validated["source_master_uid"]
                    or data.get("evidence_binding") != evidence_binding):
                raise ValueError("reserved recovery evidence binding changed")
    receipt = reserve_compute_recovery(session=session, analysis_id=analysis_id, attempt=attempt,
        source_execution_id=source.execution_id, source_master_uid=validated["source_master_uid"], now=now)
    action = session.scalar(select(RunAction).where(RunAction.analysis_id == analysis_id,
        RunAction.action == ACTION).order_by(RunAction.id.desc()))
    # Resolve by persisted action identity, not by ordering of late callbacks.
    if action is None or action.payload_json.get("action_id") != receipt["action_id"]:
        action = next((item for item in prior_actions
                       if item.payload_json.get("action_id") == receipt["action_id"]), None)
    if action is None:
        raise ValueError("reserved recovery action is unavailable")
    action.payload_json = dict(action.payload_json, evidence_binding=evidence_binding)
    if validated.get('workers_active') and 'worker_wait' not in action.payload_json:
        action.payload_json = dict(action.payload_json, worker_wait=dict(state='waiting',
            started_at=now.isoformat(), deadline=min(now+timedelta(seconds=600),
                _date(receipt['original_deadline'])).isoformat()))
    session.flush()
    return deepcopy(action.payload_json)
