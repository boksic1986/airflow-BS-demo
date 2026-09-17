"""Read existing terminal Step5 log packages; no export, subprocess or writes."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tarfile

from app.wgs_run_projection import load_wgs_runtime_binding, resolve_bound_wgs_batch_root


def _safe(root, relative):
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Invalid archive path')
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Indirect archive path')
    if root not in path.resolve().parents:
        raise ValueError('Archive outside registered root')
    return path


def wgs_log_archive_root(run, settings):
    from app.wgs_test_project import project_root
    _safe(settings.wgs_runtime_run_root, Path(run.analysis_id)/f'attempt-{run.attempt}'/'batch-binding.json')
    binding = load_wgs_runtime_binding(run_root=settings.wgs_runtime_run_root,
        analysis_id=run.analysis_id, attempt=run.attempt)
    test_root = project_root(settings, run)
    local_root = test_root or settings.host_results_root
    resolve_bound_wgs_batch_root(binding=binding,
        node_analysis_root=test_root or settings.wgs_results_host_root, local_analysis_root=local_root)
    batch = _safe(local_root, Path(binding['batch_root']).relative_to(test_root or settings.wgs_results_host_root))
    return batch/'cce', binding['run_id']


def gatk_log_archive_root(run, settings):
    root = Path(settings.gatk_runtime_request_root).resolve().parent
    path = _safe(root, Path('runs')/run.analysis_id/f'attempt-{run.attempt}'/'batch-binding.json')
    with path.open() as handle:
        binding = json.loads(handle.read(1024*1024))
    if (binding.get('schema_version') != 'gatk-runtime.batch-binding.v1'
            or binding.get('analysis_id') != run.analysis_id or binding.get('attempt') != run.attempt):
        raise ValueError('Archive binding mismatch')
    return path.parent/'cce', binding['run_id']


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


@lru_cache(maxsize=64)
def _validated(path_text, run_id, signature, checksum_signature):
    """Cache by immutable file version, never decompress logs on every UI poll."""
    path = Path(path_text)
    with os.fdopen(os.open(path.with_suffix('.gz.sha256'), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)) as sidecar:
        if not stat.S_ISREG(os.fstat(sidecar.fileno()).st_mode):
            raise ValueError('Archive checksum is not a file')
        fields = sidecar.read(1024).split()
        if len(fields)!=2 or fields[1]!=path.name or not re.fullmatch('[a-f0-9]{64}', fields[0]):
            raise ValueError('Archive checksum unavailable')
        if _signature(os.fstat(sidecar.fileno())) != checksum_signature:
            raise ValueError('Archive checksum changed')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('Archive is not a file')
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != fields[0]:
            raise ValueError('Archive checksum mismatch')
        stream.seek(0)
        manifest = None
        names = set()
        with tarfile.open(fileobj=stream, mode='r:gz') as pack:
            for member in pack:
                parts = member.name.split('/')
                if (not member.isfile() or '\\' in member.name or
                        any(part in {'', '.', '..'} for part in parts) or member.name in names):
                    raise ValueError('Unsafe archive member')
                names.add(member.name)
                if member.name == 'LOG_MANIFEST.json':
                    if member.size > 4*1024*1024:
                        raise ValueError('Invalid log manifest')
                    manifest = json.load(pack.extractfile(member))
                elif not ((parts[:2] == ['evidence', run_id] and len(parts)==3 and
                           (member.name.endswith('.log') or parts[-1] in {'RUN_COMPLETE.json', 'RUN_FAILED.json'}))
                          or (parts[:3] == ['work', '.snakemake', 'log'] and len(parts)==4 and member.name.endswith('.log'))):
                    raise ValueError('Not a log archive')
        if (not isinstance(manifest, dict) or manifest.get('schema_version')!=1
                or manifest.get('run_id')!=run_id or len(names)<2
                or {item['path'] for item in manifest.get('files', [])} != names-{'LOG_MANIFEST.json'}):
            raise ValueError('Log manifest identity mismatch')
        if _signature(os.fstat(stream.fileno()))!=signature:
            raise ValueError('Archive changed while reading')
    return digest


def _selection(run, settings, resolver):
    if resolver is None or run.execution_mode!='cce' or (run.params_json or {}).get('native_monitor_only'):
        raise ValueError('No CCE log archive')
    bundle, run_id = resolver(run, settings)
    if not isinstance(run_id, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]*', run_id):
        raise ValueError('Invalid archive run identity')
    # Check bundle itself as well as each child before trusting the archive.
    bundle = _safe(bundle.parent, Path(bundle.name))
    directory = _safe(bundle, Path('logs')/run_id)
    paths = [p for p in directory.glob('cce-log-*.tar.gz') if not p.is_symlink() and p.is_file()]
    if not paths:
        raise ValueError('No completed log archive')
    path = max(paths, key=lambda p:(p.stat().st_mtime_ns,p.name))
    path = _safe(bundle, path.relative_to(bundle))
    sidecar = _safe(bundle, path.with_suffix('.gz.sha256').relative_to(bundle))
    signature = _signature(path.stat())
    digest = _validated(str(path), run_id, signature, _signature(sidecar.stat()))
    key = hashlib.sha256(f'{run.analysis_id}:{run.attempt}:{run_id}:{path.name}:{digest}'.encode()).hexdigest()[:32]
    return path, key, signature


def log_archive_index(run, settings, resolver):
    try:
        path, key, signature = _selection(run, settings, resolver)
        return dict(available=True, key=key, filename=f'{run.analysis_id}-a{run.attempt}-logs.tar.gz', size_bytes=signature[2])
    except (OSError, ValueError, KeyError, TypeError, EOFError, tarfile.TarError):
        return dict(available=False, reason='日志包尚未就绪或不可校验；需 Master 结束并由 Step5 下载日志。')


def open_log_archive(run, settings, resolver, key):
    try:
        path, expected, signature = _selection(run, settings, resolver)
        if key!=expected:
            raise ValueError('Unknown log archive')
        stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb')
        if _signature(os.fstat(stream.fileno()))!=signature:
            stream.close()
            raise ValueError('Archive changed')
        return stream
    except (OSError, KeyError, TypeError, EOFError, tarfile.TarError) as exc:
        raise ValueError('Archive unavailable') from exc
