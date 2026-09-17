"""Existing Step5 archives only: never start export or accept a caller path."""
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models import AnalysisRun


def archive(path, run_id, *, member='work/.snakemake/log/synthetic.log'):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = b'synthetic rule completed\n'
    manifest = dict(schema_version=1, run_id=run_id, terminal={'run_id': run_id},
        files=[dict(path=member, size=len(content), sha256=hashlib.sha256(content).hexdigest())])
    with tarfile.open(path, 'w:gz') as pack:
        for name, data in [(member, content), ('LOG_MANIFEST.json', json.dumps(manifest).encode())]:
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            pack.addfile(entry, io.BytesIO(data))
    path.with_suffix('.gz.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n')
    return path


def setup(tmp_path, pipeline):
    aid = 'WGS_20260917_120000_AAAAAA' if pipeline == 'wgs' else 'GATK_20260917_120000_AAAAAA'
    run = AnalysisRun(analysis_id=aid, pipeline_name=pipeline, execution_mode='cce',
        attempt=1, status='success', params_json={}, dag_id='bio_'+pipeline, workdir='/unused')
    settings = SimpleNamespace(wgs_runtime_run_root=str(tmp_path/'runtime/runs'),
        gatk_runtime_request_root=str(tmp_path/'runtime/requests'),
        gatk_evidence_root=str(tmp_path/'evidence'),
        wgs_results_host_root='/node/results', host_results_root=str(tmp_path/'results'))
    binding_dir = tmp_path/'runtime/runs'/aid/'attempt-1'
    binding_dir.mkdir(parents=True)
    rid = aid+'-a1'
    binding = dict(schema_version='gatk-runtime.batch-binding.v1', analysis_id=aid, attempt=1,
        batch_root='/node/results/SYN_BATCH', run_id=rid)
    (binding_dir/'batch-binding.json').write_text(json.dumps(binding))
    bundle = (tmp_path/'results/SYN_BATCH' if pipeline=='wgs' else binding_dir)/'cce'
    return run, settings, archive(bundle/'logs'/rid/'cce-log-synthetic.tar.gz', rid)


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
def test_download_exact_current_attempt_and_deny_old_key(tmp_path, pipeline):
    from app.log_archive_service import log_archive_index, open_log_archive
    from app.pipeline_registry_service import ADAPTERS
    run, settings, path = setup(tmp_path, pipeline)
    resolver = ADAPTERS[pipeline].log_archive_root
    index = log_archive_index(run, settings, resolver)
    assert index['available'] and index['size_bytes'] == path.stat().st_size
    assert str(tmp_path) not in str(index)
    with open_log_archive(run, settings, resolver, index['key']) as stream:
        assert stream.read() == path.read_bytes()
    run.attempt = 2
    assert not log_archive_index(run, settings, resolver)['available']
    with pytest.raises(ValueError):
        open_log_archive(run, settings, resolver, index['key'])


@pytest.mark.parametrize('fault', ['manifest', 'checksum', 'checksum_fifo', 'truncated', 'symlink', 'unsafe_member', 'native'])
def test_untrusted_or_non_cce_archive_is_not_downloadable(tmp_path, fault):
    from app.log_archive_service import log_archive_index
    from app.pipeline_registry_service import ADAPTERS
    run, settings, path = setup(tmp_path, 'gatk')
    if fault=='manifest': archive(path, 'OTHER_RUN')
    elif fault=='checksum': path.with_suffix('.gz.sha256').write_text('0'*64+'  '+path.name)
    elif fault=='checksum_fifo':
        path.with_suffix('.gz.sha256').unlink()
        os.mkfifo(path.with_suffix('.gz.sha256'))
    elif fault=='truncated':
        path.write_bytes(path.read_bytes()[:50])
        path.with_suffix('.gz.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name)
    elif fault=='symlink':
        moved = path.with_name('outside.tar.gz')
        path.rename(moved)
        path.symlink_to(moved)
    elif fault=='unsafe_member': archive(path, run.analysis_id+'-a1', member='../config.yaml')
    else: run.execution_mode='local'
    assert not log_archive_index(run, settings, ADAPTERS['gatk'].log_archive_root)['available']


def test_archive_http_auth_and_attachment(context, tmp_path, monkeypatch):
    from app import main
    from app.pipeline_registry_service import ADAPTERS
    client, factory, _, _ = context
    run, settings, path = setup(tmp_path/'download', 'gatk')
    settings.auth_required = True
    settings.internal_service_token = 'synthetic-internal'
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    monkeypatch.setattr(main, 'require_pipeline', lambda *args: SimpleNamespace(adapter=ADAPTERS['gatk']))
    with factory() as session:
        session.add(run)
        session.commit()
    index = client.get(f'/api/runs/{run.analysis_id}/logs/index').json()['archive']
    url=f'/api/runs/{run.analysis_id}/logs/archive?key={index["key"]}'
    result=client.get(url)
    assert result.status_code==200 and result.content==path.read_bytes()
    assert 'attachment;' in result.headers['content-disposition']
    assert result.headers['cache-control']=='private, no-store'
    assert client.get(url.replace(index['key'], '0'*32)).status_code==404
    client.cookies.clear()
    assert client.get(url).status_code==401


from test_wgs_onprem_registration import context
