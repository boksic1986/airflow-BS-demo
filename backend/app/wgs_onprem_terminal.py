"""Consume a fixed, identity-bound direct-child wait receipt; no process control."""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, StrictBool, UUID4, model_validator

from app.models import WgsOnpremExecutionSnapshot
from app.wgs_onprem_execution_service import StrictModel
from app.wgs_onprem_snapshot import digest


class ControllerExit(StrictModel):
    schema_version: Literal['wgs.onprem-controller-exit.v1']
    platform_instance_id: str
    project_uuid: UUID4
    analysis_id: str
    attempt: int = Field(gt=0, strict=True)
    execution_id: str
    generation: int = Field(gt=0, strict=True)
    operation_id: UUID4
    native_execution_id: str
    manifest_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    execution_mode: Literal['local', 'sge']
    execution_target: Literal['node-96', 'node-97', 'sge-default']
    execution_user: str = Field(min_length=1, max_length=128)
    execution_uid: int = Field(ge=0, strict=True)
    hostname: str = Field(min_length=1, max_length=255)
    started_at: datetime
    finished_at: datetime
    wait_returncode: int = Field(ge=-255, le=255, strict=True)
    controller_exit_confirmed: StrictBool
    evidence_method: Literal['direct_child_wait']

    @model_validator(mode='after')
    def waited(self):
        if (not self.controller_exit_confirmed or self.started_at.tzinfo is None
                or self.finished_at.tzinfo is None or self.finished_at < self.started_at):
            raise ValueError('Controller receipt lacks valid waited times')
        return self


def consume_controller_exit(*, session, settings, run, stage, root):
    relative = Path('.wgs-platform/executions') / stage.execution_id / f'g{stage.generation}/controller-exit.json'
    path = root / relative
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError('Controller receipt path is a symlink')
    try:
        with path.open('rb') as handle:
            raw = handle.read(65537)
    except FileNotFoundError:
        return None
    if len(raw) > 65536:
        raise ValueError('Controller receipt exceeds metadata limit')
    receipt = ControllerExit.model_validate_json(raw)
    snapshot = session.get(WgsOnpremExecutionSnapshot, stage.execution_id)
    if snapshot is None:
        raise ValueError('Controller snapshot is missing')
    directory = Path(snapshot.snapshot_path)
    base = Path(getattr(settings, 'wgs_onprem_snapshot_root', ''))
    manifest_path = directory / 'manifest.json'
    if (not base.is_absolute() or directory.is_symlink() or manifest_path.is_symlink()
            or directory.resolve().parent != base.resolve()):
        raise ValueError('Controller snapshot reference is invalid')
    with manifest_path.open('rb') as handle:
        manifest_raw = handle.read(2 * 1024 * 1024 + 1)
    if digest(manifest_raw) != snapshot.manifest_hash:
        raise ValueError('Controller snapshot hash differs')
    manifest = json.loads(manifest_raw)
    expected = {key: manifest[key] for key in ('platform_instance_id', 'project_uuid',
        'analysis_id', 'attempt', 'execution_id', 'generation', 'operation_id',
        'execution_mode', 'execution_target', 'execution_user', 'execution_uid')}
    expected.update(manifest_sha256=snapshot.manifest_hash,
        native_execution_id=f'{run.analysis_id}-a{stage.attempt}-g{stage.generation}-{stage.execution_id}')
    values = receipt.model_dump(mode='json')
    if any(values.get(key) != value for key, value in expected.items()):
        raise ValueError('Controller receipt identity differs from the frozen execution')
    rc = receipt.wait_returncode
    # A signal or abnormal SGE controller exit is not proof its jobs ended.
    eligible = rc >= 0 and (receipt.execution_mode == 'local' or rc == 0)
    terminal = dict(wait_returncode=rc, controller_exit_confirmed=True,
        evidence_method='direct_child_wait', completion_scope='requested_command',
        started_at=receipt.started_at.isoformat(), finished_at=receipt.finished_at.isoformat(),
        relaunch_eligible=eligible)
    ended = receipt.finished_at.astimezone(timezone.utc)
    stage.status = 'success' if rc == 0 else 'failed'
    stage.started_at = stage.started_at or receipt.started_at.astimezone(timezone.utc)
    stage.ended_at = ended
    stage.updated_at = datetime.now(timezone.utc)
    stage.receipt_hash = digest(raw)
    stage.evidence_type = 'native_controller_exit'
    stage.evidence_key = str(relative)
    stage.terminal_payload_json = {**(stage.terminal_payload_json or {}), 'controller_exit': terminal}
    run.status = stage.status
    run.started_at = stage.started_at
    run.ended_at = ended
    run.pipeline_finished_at = ended
    run.current_stage = 'native_analysis'
    if rc == 0:
        run.progress_percent = 100  # Requested command finished, not a QC assertion.
        run.error_summary = None
    else:
        run.error_summary = f'Native controller exited with code {rc}.'
    return terminal
