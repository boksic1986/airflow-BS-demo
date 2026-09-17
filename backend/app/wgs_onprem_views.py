"""Read native execution snapshots and one latest project QC; never launch work."""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import yaml

from sqlalchemy import select, func

from app.models import AnalysisRun, WgsOnpremExecutionSnapshot, WgsStageExecution
from app.wgs_onprem_execution_service import _project_root
from app.wgs_sample_projection import QC_FIELDS, _qc_status
from app.diagnostics_service import _tail_log_file, _search_log_file
from app.operator_resources_service import _sanitize_excerpt


def current_scope(session, run):
    snapshot = session.get(WgsOnpremExecutionSnapshot, (run.params_json or {}).get('current_native_execution_id', ''))
    return snapshot.sample_scope_json if snapshot and snapshot.analysis_id == run.analysis_id else []


def _summary(stage, snapshot):
    return dict(execution_id=stage.execution_id, generation=stage.generation,
        attempt=stage.attempt, status=stage.status, registered_by=snapshot.registered_by,
        sample_count=len(snapshot.sample_scope_json), created_at=stage.created_at,
        started_at=stage.started_at, ended_at=stage.ended_at)


def _configuration(settings, snapshot):
    try:
        base = Path(settings.wgs_onprem_snapshot_root)
        directory = Path(snapshot.snapshot_path)
        if directory.is_symlink() or directory.resolve().parent != base.resolve():
            raise ValueError('Snapshot outside configured storage')
        manifest_path = _file(directory, Path('manifest.json'))
        with manifest_path.open('rb') as handle:
            raw = handle.read(2 * 1024 * 1024 + 1)
        if hashlib.sha256(raw).hexdigest() != snapshot.manifest_hash:
            raise ValueError('Snapshot manifest changed')
        manifest = json.loads(raw)
        if manifest['analysis_id'] != snapshot.analysis_id or manifest['execution_id'] != snapshot.execution_id:
            raise ValueError('Snapshot identity differs')
        with _file(directory, Path('config.yaml')).open('rb') as handle:
            config_raw = handle.read(16 * 1024 * 1024 + 1)
        if hashlib.sha256(config_raw).hexdigest() != manifest['files']['config.yaml']['sha256']:
            raise ValueError('Snapshot configuration changed')
        config = yaml.safe_load(config_raw)
        parameters = {key: config[key] for key in ('algo', 'caller', 'use_reference', 'genome')
            if key in config and isinstance(config[key], (str, bool, int, float))
            and len(str(config[key])) <= 96 and '/' not in str(config[key])}
        return dict(health='available', parameters=parameters, execution_mode=manifest['execution_mode'],
            execution_target=manifest['execution_target'], execution_user=manifest['execution_user'],
            manifest_sha256=snapshot.manifest_hash)
    except (AttributeError, ValueError, KeyError, TypeError, OSError, yaml.YAMLError):
        return dict(health='unavailable', parameters={})


def _file(root, relative):
    path = root / relative
    if any(part.is_symlink() for part in [path, *path.parents] if part != root and root in part.parents):
        raise ValueError('Symlink evidence')
    if root not in path.resolve().parents or not path.is_file():
        raise ValueError('Evidence unavailable')
    return path


def _latest_qc(session, run, root):
    previous = (run.params_json or {}).get('native_latest_qc')
    try:
        # Native QC.smk uses config["batch"], not the (possibly renamed) directory.
        with _file(root, Path('config.yaml')).open('rb') as handle:
            config_raw = handle.read(16 * 1024 * 1024 + 1)
        if len(config_raw) > 16 * 1024 * 1024:
            raise ValueError('Config exceeds limit')
        config = yaml.safe_load(config_raw)
        batch = config.get('batch') if isinstance(config, dict) else None
        if not isinstance(batch, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,255}', batch):
            raise ValueError('QC batch is unavailable')
        path = _file(root, Path('07_QC') / f'{batch}.QCstat.tsv')
        before = path.stat()
        with path.open('rb') as handle:
            raw = handle.read(2 * 1024 * 1024 + 1)
        after = path.stat()
        if (len(raw) > 2 * 1024 * 1024 or not raw.endswith(b'\n')
                or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
            raise ValueError('QC incomplete')
        table = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')), delimiter='\t')
        if not {'Sample_ID', '是否通过质控'}.issubset(table.fieldnames or []):
            raise ValueError('QC header incomplete')
        items, seen = [], set()
        for row in table:
            identifier = row.get('Sample_ID')
            if not identifier or identifier in seen or None in row or any(value is None for value in row.values()):
                raise ValueError('QC row incomplete or duplicate')
            seen.add(identifier)
            items.append(dict(sample_id=identifier, qc_status=_qc_status(row['是否通过质控']),
                qc_metrics={public: row[key] for key, public in QC_FIELDS.items() if row.get(key)}))
        if not items:
            raise ValueError('QC not ready')
        result = dict(scope='run_latest', items=items, sha256=hashlib.sha256(raw).hexdigest(),
            updated_at=datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat())
        if result != previous:
            run.params_json = {**run.params_json, 'native_latest_qc': result}
            session.flush()
        return {**result, 'health': 'available'}
    except (ValueError, OSError, UnicodeError, csv.Error, yaml.YAMLError):
        return {**(previous or dict(scope='run_latest', items=[], updated_at=None)),
                'health': 'stale' if previous else 'unavailable'}


def _rules(path, scope):
    rows, incomplete, _ = _rule_evidence(path, scope)
    return rows, incomplete


def _rule_evidence(path, scope):
    # Scan line-by-line: verbose alignment logs exceed 8 MiB long before the
    # next completion. Keep memory bounded without discarding later evidence.
    with path.open('r', encoding='utf-8', errors='replace') as handle:
        return _parse_rule_lines(handle, scope)


def _parse_rule_lines(lines, scope):
    # Text is evidence of declarations/completions, not a complete scheduled DAG.
    incomplete = False
    identities = {item['data_id']: item for item in scope}
    result, latest, current = [], {}, None
    timestamp = None
    total, completed = None, None
    in_stats = False
    for number, line in enumerate(lines):
        if not line.endswith('\n'):
            incomplete = True
            continue  # Ignore only the unfinished line, not earlier measurements.
        line = line.rstrip('\r\n')
        stamp = re.fullmatch(r'\[(\w{3} \w{3} +\d{1,2} \d{2}:\d{2}:\d{2} \d{4})\]', line.strip())
        if stamp:
            timestamp = stamp[1]  # Native local time; do not silently invent a timezone.
            continue
        if line.strip() == 'Job stats:':
            in_stats = True
        stats = re.fullmatch(r'total\s+(\d+)', line.strip()) if in_stats else None
        if stats:
            total, completed, in_stats = int(stats[1]), 0, False
        progress = re.fullmatch(r'(\d+) of (\d+) steps \(\d+(?:\.\d+)?%\) done', line.strip())
        if progress and 0 <= int(progress[1]) <= int(progress[2]):
            completed, total = int(progress[1]), int(progress[2])
        rule = re.fullmatch(r'(?:local)?rule ([A-Za-z0-9_]+):', line.strip())
        failed_rule = re.fullmatch(r'Error in rule ([A-Za-z0-9_]+):', line.strip())
        if failed_rule:
            current = dict(rule=failed_rule[1], status='failed', failure_block=True)
            continue
        if rule:
            current = dict(rule=rule[1], job_id=None, sample_id=None, family_id=None,
                           status='running' if timestamp else 'unknown', source_line=number + 1,
                           rule_instance_id=f'line:{number + 1}', sequence=len(result) + 1,
                           timing_provenance='native_log_local_time' if timestamp else 'not_collected',
                           native_started_at=timestamp, native_ended_at=None,
                           message=f'Native log line {number + 1}', origin='native_step1_log')
            timestamp = None
            continue
        finished = re.fullmatch(r'Finished job(?:id:)? (\d+)(?:\.| \(Rule: [A-Za-z0-9_]+\))', line.strip())
        if finished:
            if finished[1] in latest:
                latest[finished[1]]['status'] = 'success'
                latest[finished[1]]['native_ended_at'] = timestamp
            timestamp = None
            current = None
            continue
        if current is not None:
            job = re.fullmatch(r'\s+jobid: (\d+)\s*', line)
            if job:
                if current.get('failure_block'):
                    prior = latest.get(job[1])
                    if prior and prior['rule'] == current['rule']:
                        prior['status'] = 'failed'
                        prior['native_ended_at'] = timestamp
                    current = None
                    continue
                current['job_id'] = job[1]
                current['snakemake_jobid'] = job[1]
                result.append(current)
                latest[job[1]] = current
            wildcards = re.fullmatch(r'\s+wildcards: (.*)', line)
            if wildcards:
                values = dict(item.strip().split('=', 1) for item in wildcards[1].split(',') if '=' in item)
                identity = identities.get(values.get('sample'))
                if identity:
                    current.update(sample_id=identity['sample_id'], family_id=identity.get('family_id'))
            if not line.strip():
                current = None
    available = bool(total and completed is not None)
    return result, incomplete, dict(available=available,
        percent=round(completed / total * 100, 2) if available else None,
        completed_units=completed, total_units=total, unit='rules', source='native_step1_log',
        observed_rules=len(result))


def native_rule_evidence(settings, run, stage, scope):
    """One bounded, execution-specific file supplies rule rows and measured progress."""
    initial = run.params_json['onprem_registration']
    root = _project_root(settings, run.workdir, run.onprem_project_uuid, initial['platform_instance_id']).resolve()
    relative = Path('log') / f'step1.{run.analysis_id}-a{stage.attempt}-g{stage.generation}-{stage.execution_id}.log'
    return _rule_evidence(_file(root, relative), scope)


def _snakemake_log(root, metadata_relative, stage):
    """Select the unique Snakemake log within this execution's recorded interval."""
    with _file(root, metadata_relative).open('r') as handle:
        raw = handle.read(65537)
    if len(raw) > 65536:
        raise ValueError('Metadata too large')
    meta = dict(line.split('\t', 1) for line in raw.splitlines() if '\t' in line)
    started = datetime.fromisoformat(meta['started_at'])
    recorded = stage.started_at
    if recorded and recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=timezone.utc)
    if started.tzinfo is None or recorded != started:
        raise ValueError('Unconfirmed native start')
    ended = datetime.fromisoformat(meta['finished_at']) if meta.get('finished_at') else stage.ended_at
    if ended and ended.tzinfo is None:
        ended = ended.replace(tzinfo=timezone.utc)
    upper = (ended or datetime.now(timezone.utc)).astimezone(started.tzinfo).replace(tzinfo=None)
    lower = started.replace(tzinfo=None)
    directory = root / '.snakemake' / 'log'
    if directory.is_symlink() or directory.parent.is_symlink():
        raise ValueError('Symlink log directory')
    matches = []
    for path in directory.glob('*.snakemake.log'):
        try:
            stamp = datetime.strptime(path.name, '%Y-%m-%dT%H%M%S.%f.snakemake.log')
        except ValueError:
            continue
        if lower <= stamp <= upper:
            matches.append(_file(root, path.relative_to(root)))
    if len(matches) != 1:
        raise ValueError('No unique Snakemake log for this execution')
    return matches[0]


def native_view(*, session, settings, analysis_id, execution_id=None, section='samples',
                offset=0, limit=25, history_offset=0, query='', match_index=0,
                rule_status='', sample_id='', family_id='', phase=''):
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id).with_for_update())
    if (run is None or not (run.params_json or {}).get('native_monitor_only')
            or 'wgs' not in getattr(settings, 'deployed_pipelines', ())):
        return None
    stmt = select(WgsStageExecution, WgsOnpremExecutionSnapshot).join(
        WgsOnpremExecutionSnapshot, WgsOnpremExecutionSnapshot.execution_id == WgsStageExecution.execution_id).where(
        WgsStageExecution.analysis_id == analysis_id, WgsStageExecution.stage_code == 'native_analysis')
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    pairs = session.execute(stmt.order_by(WgsStageExecution.id.desc()).offset(history_offset).limit(50)).all()
    selected_id = execution_id or run.params_json.get('current_native_execution_id')
    pair = session.execute(stmt.where(WgsStageExecution.execution_id == selected_id)).first() if selected_id else None
    if selected_id and pair is None:
        return None
    result = dict(analysis_id=analysis_id, current_execution_id=run.params_json.get('current_native_execution_id'),
        executions=[_summary(*row) for row in pairs], history_total=total, history_offset=history_offset,
        selected=_summary(*pair) if pair else None, samples=[], sample_total=0, rules=[], rule_total=0,
        rules_incomplete=False, phase_summaries=[], log=None, log_error=None,
        qc=dict(scope='run_latest', items=[], health='unavailable'),
        evidence_health='available', offset=offset, limit=limit,
        progress=dict(available=False, percent=None, observed_rules=0),
        monitoring=run.params_json.get('native_monitor'), configured_scope_only=True)
    scope = pair[1].sample_scope_json if pair else []
    result.update(samples=scope[offset:offset + limit], sample_total=len(scope))
    result['configuration'] = _configuration(settings, pair[1]) if pair else None
    if pair:
        try:
            rows, truncated, progress = native_rule_evidence(settings, run, pair[0], scope)
            result.update(progress=progress, rules_incomplete=truncated)
            if section == 'rules':
                from app.workflow_phases import wgs_phase_for_rule, run_phase_release, PINNED_WGS_PHASES
                for row in rows:
                    release = run_phase_release(run)
                    # Native registration may lack a cloud release ID. Use the
                    # shared exact-name catalog for display, not runtime attestation.
                    row['phase'] = (PINNED_WGS_PHASES['rules'].get(row['rule'], 'Unknown')
                        if release == 'unavailable' else wgs_phase_for_rule(row['rule'], release_id=release))
                from app.workflow_phases import summarize_rule_events, phase_order
                labels = {row['rule']: row['phase'] for row in rows}
                summaries = summarize_rule_events(rows, phase_projector=lambda rule, **_: labels[rule])['phases']
                for summary in summaries:
                    summary.update(canceled=0, status='failed' if summary['failed'] else
                        'running' if summary['running'] else
                        'success' if summary['success'] == summary['total'] else 'unknown')
                result['phase_summaries'] = sorted(summaries, key=lambda item: phase_order(item['phase'], pipeline_name='wgs'))
                rows = [row for row in rows if (not rule_status or row['status'] == rule_status)
                    and (not phase or row['phase'] == phase)
                    and (not sample_id or row['sample_id'] == sample_id)
                    and (not family_id or row['family_id'] == family_id)]
                result.update(rules=rows[offset:offset + limit], rule_total=len(rows))
        except (OSError, ValueError, KeyError):
            result['evidence_health'] = 'unavailable'
    try:
        initial = run.params_json['onprem_registration']
        root = _project_root(settings, run.workdir, run.onprem_project_uuid, initial['platform_instance_id']).resolve()
    except (ValueError, OSError, KeyError):
        root = None
        result['evidence_health'] = 'unavailable'
    # QC belongs to the run, never to selected execution or renamed sample metadata.
    if section in {'samples', 'qc'}:
        result['qc'] = _latest_qc(session, run, root) if root else {
            **(run.params_json.get('native_latest_qc') or result['qc']), 'health': 'stale' if run.params_json.get('native_latest_qc') else 'unavailable'}
    if pair and section in {'logs', 'rules'}:
        stage = pair[0]
        relative = Path('log') / f'step1.{analysis_id}-a{stage.attempt}-g{stage.generation}-{stage.execution_id}.log'
        result['log'] = dict(analysis_id=analysis_id, stream='stdout', path=relative.as_posix(), lines=[], truncated=False, query=query)
        try:
            if root is None:
                raise ValueError('Project binding unavailable')
            path = _file(root, relative)
            if section == 'logs':
                path = _snakemake_log(root, relative.with_suffix('.metadata.tsv'), stage)
                result['log']['path'] = path.relative_to(root).as_posix()
                if query:
                    result['log'].update(_search_log_file(path, query=query, match_index=match_index, limit=200, max_bytes=8 * 1024 * 1024))
                else:
                    lines, truncated, size = _tail_log_file(path, tail=200, max_bytes=1024 * 1024)
                    result['log'].update(lines=lines, truncated=truncated, file_size=size)
                result['log']['lines'] = [_sanitize_excerpt(line) for line in result['log']['lines']]
        except (OSError, ValueError, KeyError):
            if section == 'logs':
                result['log_error'] = '本次执行的 Snakemake 日志尚不可确认。'
            else:
                result['evidence_health'] = 'unavailable'
    session.commit()  # Only the last-good, allowlisted QC cache may have changed.
    return result
