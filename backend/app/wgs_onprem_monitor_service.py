"""Observe native files only: never prepare, launch, signal or resubmit work."""
from datetime import datetime, timezone
from pathlib import Path
import re

from pydantic import Field
from sqlalchemy import select

from app.models import AnalysisRun, WgsStageExecution
from app.wgs_onprem_execution_service import RegistrationConflict, StrictModel, _project_root
from app.wgs_onprem_terminal import consume_controller_exit


class NativeObservationRequest(StrictModel):
    attempt: int = Field(gt=0, strict=True)
    generation: int = Field(gt=0, strict=True)


def _time(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('Native timestamp lacks timezone')
    return parsed.astimezone(timezone.utc)


def _read(root, path):
    if path.is_symlink() or root not in path.resolve().parents:
        raise ValueError('Native evidence leaves project')
    with path.open('rb') as handle:
        data = handle.read(65537)
    if len(data) > 65536:
        raise ValueError('Native evidence exceeds metadata limit')
    return data.decode('utf-8')


def observe_native_execution(*, session, settings, analysis_id, execution_id, request):
    if (not getattr(settings, 'wgs_onprem_monitor_enabled', False)
            or 'wgs' not in getattr(settings, 'deployed_pipelines', ())):
        raise RegistrationConflict('Native monitoring is disabled')
    run = session.scalar(select(AnalysisRun).where(
        AnalysisRun.analysis_id == analysis_id).with_for_update())
    stage = session.scalar(select(WgsStageExecution).where(
        WgsStageExecution.execution_id == execution_id).execution_options(populate_existing=True))
    if (run is None or stage is None or not (run.params_json or {}).get('native_monitor_only')
            or stage.analysis_id != analysis_id or stage.stage_code != 'native_analysis'
            or run.attempt != request.attempt or stage.attempt != request.attempt
            or stage.generation != request.generation
            or run.params_json.get('current_native_execution_id') != execution_id):
        raise RegistrationConflict('Observation does not match the current native execution')
    initial = run.params_json['onprem_registration']
    if initial['platform_instance_id'] != getattr(settings, 'wgs_platform_instance_id', ''):
        raise RegistrationConflict('Observation platform instance mismatch')
    previous = (run.params_json.get('native_monitor') or {})
    if previous.get('execution_id') != execution_id:
        previous = {}
    result = {**previous, 'analysis_id': analysis_id, 'attempt': stage.attempt,
              'execution_id': execution_id, 'generation': stage.generation,
              'status': stage.status, 'done': stage.status in {'success', 'failed', 'canceled'},
              'monitoring_health': 'healthy', 'error_code': None,
              'checked_at': datetime.now(timezone.utc).isoformat()}
    if result['done']:
        # A terminal projector is separate; native .exitcode is not that authority.
        result['observation'] = 'terminal'
        return result
    result['observation'] = 'awaiting_claim' if stage.status == 'accepted' else 'awaiting_start'
    if stage.status != 'accepted':
        try:
            root = _project_root(settings, run.workdir, run.onprem_project_uuid,
                                 initial['platform_instance_id']).resolve()
            terminal = consume_controller_exit(session=session, settings=settings,
                run=run, stage=stage, root=root)
            if terminal is not None:
                result.update(terminal, status=stage.status, done=True, observation='terminal')
                run.params_json = {**run.params_json, 'native_monitor': result}
                session.commit()
                return result
            log = root / 'log'
            if log.is_symlink():
                raise ValueError('Native log directory is a symlink')
            native_id = f'{analysis_id}-a{stage.attempt}-g{stage.generation}-{execution_id}'
            prefix = log / f'step1.{native_id}'
            meta_path = Path(str(prefix) + '.metadata.tsv')
            try:
                raw = _read(root, meta_path)
            except FileNotFoundError:
                if stage.started_at is not None:
                    raise ValueError('Previously observed native metadata is missing')
                raw = None
            if raw is not None:
                # Ignore command entirely; it may contain credentials or clinical paths.
                meta = {}
                for line in raw.splitlines():
                    key, sep, value = line.partition('\t')
                    if key not in {'run_mode', 'started_at', 'finished_at'}:
                        continue
                    if not sep or key in meta:
                        raise ValueError('Ambiguous native metadata')
                    meta[key] = value
                if meta.get('run_mode') != initial['execution_mode']:
                    raise ValueError('Native execution mode differs from registration')
                started = _time(meta['started_at'])
                existing_start = stage.started_at
                if existing_start is not None:
                    if existing_start.tzinfo is None:
                        existing_start = existing_start.replace(tzinfo=timezone.utc)
                    if existing_start != started:
                        raise ValueError('Native start evidence changed')
                result.update(observation='running', native_started_at=started.isoformat())
                if meta.get('finished_at'):
                    finished = _time(meta['finished_at'])
                    if finished < started:
                        raise ValueError('Native timestamps are reversed')
                    code = _read(root, Path(str(prefix) + '.exitcode')).strip()
                    if not re.fullmatch(r'[0-9]{1,3}', code) or int(code) > 255:
                        raise ValueError('Native exitcode is invalid')
                    result.update(observation='native_result_reported', native_exitcode=int(code),
                                  native_finished_at=finished.isoformat(), controller_exit_confirmed=False)
                # Read succeeds before changing run state; collection errors never fail work.
                if existing_start is None:
                    run.progress_percent = 0
                    run.error_summary = None
                stage.status = 'running'
                stage.started_at = started
                stage.updated_at = datetime.now(timezone.utc)
                run.status = 'running'
                run.started_at = started
                run.ended_at = None
                run.pipeline_finished_at = None
                run.current_stage = 'native_analysis'
                result['status'] = 'running'
        except (ValueError, OSError, KeyError, UnicodeError):
            result.update(observation=previous.get('observation', 'unavailable'),
                          monitoring_health='degraded', error_code='NATIVE_EVIDENCE_UNAVAILABLE')
    run.params_json = {**run.params_json, 'native_monitor': result}
    session.commit()
    return result
