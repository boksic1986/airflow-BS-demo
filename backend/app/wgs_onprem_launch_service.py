"""One-shot launch permission; this API never starts a native controller."""
from datetime import datetime, timezone
import json
from pathlib import Path

from pydantic import Field, UUID4
from sqlalchemy import select, update

from app.models import AnalysisRun, AuditLog, WgsOnpremExecutionSnapshot, WgsStageExecution
from app.wgs_onprem_execution_service import RegistrationConflict, StrictModel, _instance, _project_root
from app.wgs_onprem_snapshot import capture_inputs, digest


class NativeLaunchClaim(StrictModel):
    platform_instance_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    operation_id: UUID4
    generation: int = Field(gt=0, strict=True)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _validate_bound_arguments(argv):
    # The original entry remains unrestricted. This monitored protocol snapshots
    # fixed project inputs and cannot honestly accept another config or executor.
    blocked = ("--config", "--configfile", "--configfiles", "--directory", "--snakefile",
               "--profile", "--workflow-profile", "--executor", "--cluster", "--cluster-sync",
               "--drmaa", "--jobscript", "--background", "--worker")
    for argument in argv:
        flag = argument.split("=", 1)[0]
        if ((flag.startswith("--") and flag != "--" and any(option.startswith(flag) for option in blocked))
                or (not flag.startswith("--") and any(flag.startswith(short) for short in ("-C", "-s", "-d")))):
            raise ValueError("Monitored arguments cannot override the frozen project/config/profile/executor")


def claim_native_launch(*, session, settings, execution_id: str,
                        request: NativeLaunchClaim, username: str) -> dict:
    instance = _instance(settings, request.platform_instance_id)
    if not getattr(settings, "wgs_onprem_launch_enabled", False):
        raise RegistrationConflict("Native monitored launching is disabled")
    # Same project row is locked by registration. The conditional stage update is
    # the final once-only fence; no new file-lock service or lease timeout.
    run = session.scalar(select(AnalysisRun).join(WgsStageExecution,
        WgsStageExecution.analysis_id == AnalysisRun.analysis_id).where(
        WgsStageExecution.execution_id == execution_id).with_for_update(of=AnalysisRun))
    if run is None or not (run.params_json or {}).get("native_monitor_only"):
        raise RegistrationConflict("Native project execution is not registered")
    if run.submitted_by != username:
        raise PermissionError("Native project belongs to another platform account")
    stage = session.scalar(select(WgsStageExecution).where(
        WgsStageExecution.execution_id == execution_id).execution_options(populate_existing=True))
    snapshot = session.get(WgsOnpremExecutionSnapshot, execution_id)
    if (snapshot is None or stage.stage_code != "native_analysis" or stage.attempt != run.attempt
            or stage.generation != request.generation or snapshot.operation_id != str(request.operation_id)
            or snapshot.manifest_hash != request.manifest_sha256
            or run.params_json.get("current_native_execution_id") != execution_id):
        raise RegistrationConflict("Launch claim references a different or stale execution")
    if stage.status != "accepted":
        raise RegistrationConflict("Launch already claimed or execution closed; do not launch again")
    initial = run.params_json["onprem_registration"]
    root = _project_root(settings, run.workdir, run.onprem_project_uuid, instance)
    snapshot_root = Path(getattr(settings, "wgs_onprem_snapshot_root", ""))
    directory = Path(snapshot.snapshot_path)
    manifest_path = directory / "manifest.json"
    if (not snapshot_root.is_absolute() or directory.is_symlink() or manifest_path.is_symlink()
            or directory.resolve().parent != snapshot_root.resolve() or not manifest_path.is_file()):
        raise ValueError("Native execution snapshot is unavailable")
    with manifest_path.open("rb") as handle:
        raw = handle.read(2 * 1024 * 1024 + 1)
    if digest(raw) != snapshot.manifest_hash:
        raise RegistrationConflict("Native execution snapshot has changed")
    manifest = json.loads(raw)
    expected = {"schema_version": "wgs.onprem-execution-snapshot.v1",
                "project_uuid": run.onprem_project_uuid, "platform_instance_id": instance,
                "project_dir": str(root), "analysis_id": run.analysis_id, "attempt": run.attempt,
                "execution_id": execution_id, "generation": stage.generation,
                "operation_id": snapshot.operation_id, "execution_mode": initial["execution_mode"],
                "execution_target": initial["execution_target"]}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise RegistrationConflict("Native execution snapshot identity does not match the project")
    _validate_bound_arguments(manifest["argv"])
    _, current_refs, _ = capture_inputs(root, initial["execution_mode"], manifest["argv"])
    if current_refs != snapshot.file_refs_json or manifest.get("files") != snapshot.file_refs_json:
        raise RegistrationConflict("Native inputs changed after registration; cannot grant this launch")
    native_id = f"{run.analysis_id}-a{run.attempt}-g{stage.generation}-{execution_id}"
    log_root = root / "log"
    if log_root.is_symlink() or (log_root.exists() and root.resolve() not in log_root.resolve().parents):
        raise ValueError("Native log directory is outside the project")
    # No reuse of evidence under this fresh identity, even if a previous caller
    # bypassed the monitored entry. Existence is not interpreted as completion.
    for suffix in ("pid", "metadata.tsv", "exitcode"):
        marker = root / "log" / f"step1.{native_id}.{suffix}"
        if marker.exists() or marker.is_symlink():
            raise RegistrationConflict("Native execution identity already has runtime evidence")
    _project_root(settings, str(root), run.onprem_project_uuid, instance)
    now = datetime.now(timezone.utc)
    result = session.execute(update(WgsStageExecution).where(
        WgsStageExecution.execution_id == execution_id, WgsStageExecution.status == "accepted",
        WgsStageExecution.generation == request.generation).values(
        status="launching", updated_at=now,
        message="Launch permission consumed; awaiting native start evidence"))
    if result.rowcount != 1:
        raise RegistrationConflict("Launch permission was already consumed; do not launch again")
    session.add(AuditLog(username=username, action="wgs.onprem.execution.claim", analysis_id=run.analysis_id,
        payload_json={"execution_id": execution_id, "operation_id": snapshot.operation_id,
                      "native_execution_id": native_id}))
    session.commit()  # A lost response after commit must never cause another grant.
    return {"schema_version": "wgs.onprem-launch-claim-result.v1", "claim_granted": True,
            "analysis_id": run.analysis_id, "attempt": run.attempt, "execution_id": execution_id,
            "generation": stage.generation, "operation_id": snapshot.operation_id,
            "manifest_sha256": snapshot.manifest_hash, "files": snapshot.file_refs_json,
            "native_execution_id": native_id, "project_dir": str(root),
            "execution_mode": initial["execution_mode"], "execution_target": initial["execution_target"],
            "argv": manifest["argv"], "execution_user": manifest["execution_user"],
            "execution_uid": manifest["execution_uid"]}
