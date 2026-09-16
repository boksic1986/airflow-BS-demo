"""Opt-in registration of native prepared projects; never schedules analysis."""
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import secrets
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, UUID4, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import AnalysisRun, AuditLog, RunAttempt, WgsStageExecution, WgsOnpremExecutionSnapshot


class RegistrationConflict(ValueError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PreparedFile(StrictModel):
    relative_path: str = Field(min_length=1, max_length=512)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def relative_reference(self):
        path = PurePosixPath(self.relative_path)
        if path.is_absolute() or ".." in path.parts or "\\" in self.relative_path or str(path) != self.relative_path:
            raise ValueError("Prepared file reference must be normalized and project-relative")
        return self


class PrepareSummary(StrictModel):
    selected_count: int = Field(gt=0, strict=True)
    pending_count: int = Field(ge=0, strict=True)
    version: str = Field(min_length=1, max_length=32)
    source_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    prepared_at: datetime
    files: dict[Literal["config", "sampleinfo", "step1"], PreparedFile]

    @model_validator(mode="after")
    def complete_summary(self):
        if set(self.files) != {"config", "sampleinfo", "step1"}:
            raise ValueError("Prepared summary requires config, sampleinfo and step1 references")
        if self.prepared_at.tzinfo is None:
            raise ValueError("Preparation time must include timezone")
        return self


class OnpremProjectRegistration(StrictModel):
    schema_version: Literal["wgs.onprem-project-registration.v1"]
    project_uuid: UUID4
    platform_instance_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    project_dir: str = Field(min_length=1, max_length=2048)
    batch_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    execution_mode: Literal["local", "sge"]
    execution_target: Literal["node-96", "node-97", "sge-default"]
    prepare_summary: PrepareSummary

    @model_validator(mode="after")
    def matching_target(self):
        expected = "sge" if self.execution_target == "sge-default" else "local"
        if self.execution_mode != expected:
            raise ValueError("Native mode and configured target differ")
        return self


def _response(run: AnalysisRun, instance: str) -> dict:
    return dict(schema_version="wgs.onprem-project-registration-result.v1",
                project_uuid=run.onprem_project_uuid, platform_instance_id=instance,
                analysis_id=run.analysis_id, attempt=1, status="created",
                registration_status="registered", execution_status="not_started")


def _instance(settings, requested: str) -> str:
    if not getattr(settings, "wgs_onprem_registration_enabled", False):
        raise RegistrationConflict("Native project registration is disabled")
    if "wgs" not in getattr(settings, "deployed_pipelines", ()):
        raise RegistrationConflict("WGS is not deployed")
    instance = getattr(settings, "wgs_platform_instance_id", "")
    if not instance or requested != instance:
        raise RegistrationConflict("Platform instance mismatch")
    return instance


def _read_binding(root: Path) -> dict:
    binding = root / ".wgs-platform/project.json"
    if (binding.parent.is_symlink() or binding.is_symlink() or not binding.is_file()
            or root.resolve() not in binding.resolve().parents or binding.stat().st_size > 32768):
        raise ValueError("Native project binding is missing or invalid")
    identity = json.loads(binding.read_text(encoding="utf-8"))
    if not isinstance(identity, dict) or identity.get("schema_version") != "wgs.platform-project.v1":
        raise ValueError("Native project binding cannot be read")
    return identity


def _project_root(settings, directory: str, project_uuid: str, instance: str) -> Path:
    root = Path(directory)
    if not root.is_absolute() or ".." in root.parts or root.is_symlink() or not root.is_dir():
        raise ValueError("Native project directory must be an existing normalized absolute directory")
    allowed = [Path(value).resolve() for value in getattr(settings, "wgs_onprem_project_roots", ())]
    if not any(base in root.resolve().parents for base in allowed):
        raise ValueError("Native project is outside configured registration roots")
    identity = _read_binding(root)
    if identity.get("project_uuid") != project_uuid or identity.get("platform_instance_id") != instance:
        raise RegistrationConflict("Native project binding identity mismatch")
    return root


def register_project(*, session, settings, request: OnpremProjectRegistration, username: str) -> dict:
    instance = _instance(settings, request.platform_instance_id)
    project_uuid = str(request.project_uuid)
    initial_request = request.model_dump(mode="json")

    def existing_response(run):
        if run.submitted_by != username:
            raise PermissionError("Project registration belongs to another account")
        if (run.params_json or {}).get("onprem_registration") != initial_request:
            raise RegistrationConflict("Project UUID already has a different registration; do not rerun prepare")
        return _response(run, instance)

    existing = session.scalar(select(AnalysisRun).where(AnalysisRun.onprem_project_uuid == project_uuid))
    if existing is not None:
        return existing_response(existing)
    # Validate only the known project identity, not mutable prepare output hashes.
    root = _project_root(settings, request.project_dir, project_uuid, instance)
    run = AnalysisRun(
        analysis_id=f"WGS_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{secrets.token_hex(3).upper()}",
        onprem_project_uuid=project_uuid, pipeline_name="wgs", dag_id="bio_wgs",
        execution_mode=request.execution_mode, status="created", attempt=1,
        current_stage="awaiting_native_start", workdir=str(root), submitted_by=username,
        params_json={"native_monitor_only": True, "onprem_registration": initial_request,
                     "project_id": project_uuid, "project_name": "WGS Local / SGE",
                     "batch_no": request.batch_name, "execution_target": request.execution_target,
                     "wgs_version": request.prepare_summary.version,
                     "prepare_summary_source": "reported_by_authenticated_prepare"},
    )
    try:
        with session.begin_nested():
            session.add(run)
            session.flush()
    except IntegrityError:
        existing = session.scalar(select(AnalysisRun).where(AnalysisRun.onprem_project_uuid == project_uuid))
        if existing is None:
            raise
        return existing_response(existing)
    session.add(RunAttempt(analysis_id=run.analysis_id, attempt=1,
                           execution_mode=request.execution_mode, status="created"))
    session.add(AuditLog(username=username, action="wgs.onprem.register", analysis_id=run.analysis_id,
                         payload_json={"project_uuid": project_uuid, "execution_target": request.execution_target}))
    session.commit()
    return _response(run, instance)


class OnpremExecutionRegistration(StrictModel):
    schema_version: Literal["wgs.onprem-execution-registration.v1"]
    platform_instance_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    operation_id: UUID4
    project_dir: str = Field(min_length=1, max_length=2048)
    execution_mode: Literal["local", "sge"]
    execution_target: Literal["node-96", "node-97", "sge-default"]
    argv: list[str] = Field(max_length=256)
    execution_user: str = Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
    execution_uid: int = Field(ge=0, strict=True)


def _execution_response(stage, snapshot):
    # A stable registration receipt, not status evidence or permission to launch.
    return {"schema_version": "wgs.onprem-execution-registration-result.v1",
            "analysis_id": stage.analysis_id, "attempt": stage.attempt,
            "execution_id": stage.execution_id, "generation": stage.generation,
            "operation_id": snapshot.operation_id, "registration_status": "registered",
            "manifest_sha256": snapshot.manifest_hash, "files": snapshot.file_refs_json,
            "launch_allowed": False}


def register_execution(*, session, settings, project_uuid: str,
                       request: OnpremExecutionRegistration, username: str) -> dict:
    from app.wgs_onprem_snapshot import capture_inputs, persist_snapshot, digest

    instance = _instance(settings, request.platform_instance_id)
    # Serialize only this project's registration transaction, not native analysis.
    run = session.scalar(select(AnalysisRun).where(
        AnalysisRun.onprem_project_uuid == project_uuid).with_for_update())
    if run is None or not (run.params_json or {}).get("native_monitor_only"):
        raise RegistrationConflict("Native project is not registered")
    if run.submitted_by != username:
        raise PermissionError("Native project belongs to another platform account")
    initial = run.params_json["onprem_registration"]
    if (initial["platform_instance_id"] != instance or initial["execution_mode"] != request.execution_mode
            or initial["execution_target"] != request.execution_target):
        raise RegistrationConflict("Native project mode, target or platform differs from registration")
    request_hash = digest(json.dumps(request.model_dump(mode="json"), sort_keys=True).encode())
    existing = session.scalar(select(WgsOnpremExecutionSnapshot).where(
        WgsOnpremExecutionSnapshot.analysis_id == run.analysis_id,
        WgsOnpremExecutionSnapshot.operation_id == str(request.operation_id)))
    if existing is not None:
        stage = session.scalar(select(WgsStageExecution).where(WgsStageExecution.execution_id == existing.execution_id))
        if stage.request_hash != request_hash:
            raise RegistrationConflict("Operation already registered with different execution inputs")
        return _execution_response(stage, existing)
    latest = session.scalar(select(WgsStageExecution).where(
        WgsStageExecution.analysis_id == run.analysis_id,
        WgsStageExecution.stage_code == "native_analysis").order_by(WgsStageExecution.generation.desc()).limit(1))
    if latest is not None and latest.status not in {"success", "failed", "canceled"}:
        raise RegistrationConflict("Native execution is active or its terminal state is unknown")
    if latest is not None and (latest.terminal_payload_json or {}).get('controller_exit', {}).get('relaunch_eligible') is False:
        raise RegistrationConflict("Native controller exited abnormally; verify remaining jobs before another execution")
    root = _project_root(settings, request.project_dir, project_uuid, instance)
    old_root = Path(run.workdir)
    if str(root) != str(old_root):
        if old_root.is_symlink():
            raise RegistrationConflict("Previous project location is a symlink; review its identity")
        if old_root.exists():
            old_binding = _read_binding(old_root)  # Unreadable is not proof of a move.
            if (old_binding.get("project_uuid") == project_uuid
                    or old_binding.get("platform_instance_id") != instance):
                raise RegistrationConflict("Project binding exists at two locations; cannot infer a move")
    contents, refs, scope = capture_inputs(root, request.execution_mode, request.argv)
    stage = WgsStageExecution(execution_id=f"wse_{secrets.token_hex(12)}", analysis_id=run.analysis_id,
        attempt=run.attempt, stage_code="native_analysis", generation=1 if latest is None else latest.generation + 1,
        status="accepted", request_hash=request_hash,
        release_id=f"reported:{initial['prepare_summary']['version']}")
    manifest = {"schema_version": "wgs.onprem-execution-snapshot.v1",
        "project_uuid": project_uuid, "platform_instance_id": instance,
        "analysis_id": run.analysis_id, "attempt": run.attempt,
        "execution_id": stage.execution_id, "generation": stage.generation,
        **request.model_dump(mode="json", exclude={"schema_version", "platform_instance_id"}),
        "registered_by": username, "execution_user_source": "reported_by_authenticated_launcher",
        "scope_source": "config.sample_data_ids_joined_to_sample_info",
        "scope_semantics": "configured_not_proof_of_scheduled_or_completed_work",
        "prepare_release_summary": initial["prepare_summary"]["version"],
        "release_source": "initial_prepare_report_not_observed_runtime", "files": refs}
    snapshot_path, manifest_hash = persist_snapshot(settings, root, stage.execution_id, contents, manifest)
    # Recheck binding after collection; don't commit a snapshot against another project.
    _project_root(settings, str(root), project_uuid, instance)
    snapshot = WgsOnpremExecutionSnapshot(execution_id=stage.execution_id, analysis_id=run.analysis_id,
        operation_id=str(request.operation_id), snapshot_path=str(snapshot_path), manifest_hash=manifest_hash,
        file_refs_json=refs, sample_scope_json=scope, registered_by=username)
    session.add(stage)
    session.flush()
    session.add(snapshot)
    run.workdir = str(root)
    run.params_json = {**run.params_json, "current_native_execution_id": stage.execution_id}
    session.add(AuditLog(username=username, action="wgs.onprem.execution.register", analysis_id=run.analysis_id,
        payload_json={"execution_id": stage.execution_id, "operation_id": str(request.operation_id),
                      "previous_project_dir": str(old_root), "project_dir": str(root)}))
    session.commit()
    return _execution_response(stage, snapshot)
