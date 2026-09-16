"""Existing sampleinfo input for the ordinary, confirmed CCE prepare flow."""
import csv
import hashlib
import io
import os
from pathlib import Path
import re
import stat
import tempfile

from sqlalchemy import select

from app.models import WgsInputSnapshot
from app.wgs_cloud_consumer import SAMPLEINFO_ORDER


MAX_BYTES = 512 * 1024


def read_sampleinfo_path(settings, value: str) -> str:
    source = Path(value)
    if not source.is_absolute() or '..' in source.parts or source.suffix.lower() not in {'.tsv', '.txt'}:
        raise ValueError('Sampleinfo must be an absolute TSV/TXT file path')
    container_root = Path(settings.wgs_analysis_project_container_root)
    node_root = Path(settings.wgs_analysis_project_node200_root)
    if node_root in source.parents:
        source = container_root / source.relative_to(node_root)
    roots = [container_root, *map(Path, getattr(settings, 'wgs_config_roots', [])),
             *map(Path, getattr(settings, 'wgs_onprem_project_roots', []))]
    try:
        resolved = source.resolve(strict=True)
        if not any(root.is_absolute() and root.resolve() in resolved.parents for root in roots):
            raise ValueError('Sampleinfo is outside configured WGS input roots')
        fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError('Sampleinfo must be a regular file')
            raw = handle.read(MAX_BYTES + 1)
        if not raw or len(raw) > MAX_BYTES:
            raise ValueError('Sampleinfo must be non-empty, at most 512 KiB')
        return raw.decode('utf-8')
    except (OSError, UnicodeError) as exc:
        raise ValueError('Sampleinfo file is unavailable or is not UTF-8') from exc


def validate_table(content: str, batch: str) -> tuple[bytes, int, str]:
    if not content or len(content.encode('utf-8')) > MAX_BYTES or '\x00' in content:
        raise ValueError('Sampleinfo must be non-empty UTF-8 TSV, at most 512 KiB')
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')), delimiter='\t')
    # Match native _load_input_sampleinfo: the last three columns are optional.
    required = set(SAMPLEINFO_ORDER[:-3])
    if not required.issubset(reader.fieldnames or []) or len(set(reader.fieldnames or [])) != len(reader.fieldnames or []):
        raise ValueError('Sampleinfo is missing required columns or has duplicate columns')
    rows = list(reader)
    if not rows or len(rows) > 10000 or any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError('Sampleinfo requires complete TSV rows (1 to 10000)')
    for field in ('样本编号', '数据编号'):
        values = [row[field].strip() for row in rows]
        if len(set(values)) != len(values) or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', item) for item in values):
            raise ValueError('Sampleinfo sample/data IDs must be safe, non-empty and unique')
    old_batches = {row['分析批次'].strip() for row in rows}
    if len(old_batches) != 1 or '' in old_batches or batch in old_batches:
        raise ValueError('Use a new analysis batch different from the source sampleinfo batch')
    sequencing = [row['上机批次'].strip() for row in rows if row['上机批次'].strip()]
    if not sequencing or any(not re.fullmatch(r'[0-9]{8}[A-Z]', item) for item in sequencing):
        raise ValueError('Sampleinfo sequencing batches must use YYYYMMDDX format')
    # Native analysis derives the directory from this column. Change only the
    # uploaded copy's analysis batch; retain sequencing and all other metadata.
    for row in rows:
        row['分析批次'] = batch
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames, delimiter='\t', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8'), len(rows), sequencing[0]


def create_uploaded_run(*, session, settings, airflow_client, username, spec,
                        sampleinfo_text, selected_options, sampleinfo_path=None):
    from app.wgs_platform_service import run_payload, submit_wgs_run
    from app.wgs_submission_service import _create_catalog_run_record

    if not getattr(settings, 'wgs_contract_v2_enabled', False):
        raise ValueError('Uploaded sampleinfo requires WGS contract v2')
    content, count, sequencing = validate_table(sampleinfo_text, spec.analysis_batch)
    base = Path(settings.wgs_analysis_project_container_root)
    target = base / spec.batch_no
    if not base.is_absolute() or '..' in base.parts or not base.is_dir():
        raise ValueError('Configured WGS analysis root is unavailable')
    if any(path.is_symlink() for path in (target, *target.parents)):
        raise ValueError('Output directory cannot contain symlinks')
    snapshot = session.scalar(select(WgsInputSnapshot).where(WgsInputSnapshot.batch_no == spec.batch_no))
    if snapshot is None and target.exists():
        raise ValueError('Analysis batch directory already exists; overwriting is forbidden')
    if snapshot is not None and snapshot.fq_path != spec.node_root:
        raise ValueError('Analysis batch already exists with another input source')
    descriptor = {'sha256': hashlib.sha256(content).hexdigest(), 'row_count': count,
                  'source_sha256': hashlib.sha256(sampleinfo_text.encode('utf-8')).hexdigest()}
    run, existed = _create_catalog_run_record(session=session, settings=settings, username=username, spec=spec)
    if run.submitted_by != username:
        raise ValueError('Batch submission belongs to another owner')
    previous = (run.params_json or {}).get('sampleinfo_upload')
    if existed:
        if previous != descriptor or run.params_json.get('submission_options') != selected_options:
            raise ValueError('Analysis batch already exists with different frozen inputs or options')
        if run.dag_run_id or run.status != 'created':
            return run_payload(session, run)
    folder = Path(settings.wgs_runtime_request_root) / run.analysis_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o2770)
    if folder.is_symlink():
        raise ValueError('Upload storage is invalid')
    shared_gid = getattr(settings, 'wgs_runtime_shared_gid', None)
    if shared_gid is not None:
        if shared_gid < 1:
            raise ValueError('Shared runtime group id must be positive')
        if folder.stat().st_gid != shared_gid:
            os.chown(folder, -1, shared_gid)
    folder.chmod(0o2770)
    target = folder / 'sampleinfo-upload.tsv'
    fd, temporary_name = tempfile.mkstemp(prefix='.sampleinfo-', suffix='.partial', dir=folder)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, 'wb') as handle:
            os.fchmod(handle.fileno(), 0o640)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target)  # Atomic publication, never overwrite.
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != content:
                raise ValueError('Existing uploaded sampleinfo differs from this request')
    finally:
        temporary.unlink(missing_ok=True)
    params = {**run.params_json, 'sampleinfo_upload': descriptor, 'sequencing_batch': sequencing,
              'submission_mode': 'three_stage', 'submission_phase': 'preparing_sampleinfo',
              'config_approved_at': None, 'execution_approved_at': None, 'resource_set': 'default'}
    params.pop('native_prepare_contract', None)
    if sampleinfo_path is not None:
        params['sampleinfo_source_path'] = sampleinfo_path
        params['prepared_project_path'] = str(Path(settings.wgs_analysis_project_node200_root) / spec.batch_no)
    if selected_options is not None:
        params.update(submission_options=selected_options, algo=selected_options['algo'])
    run.params_json = params
    session.commit()
    return submit_wgs_run(session=session, airflow_client=airflow_client, analysis_id=run.analysis_id)
