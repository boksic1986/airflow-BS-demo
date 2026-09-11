"""Existing WGS project inputs -> independent, explicitly confirmed test run.

Only sampleinfo is copied by the restricted node gate. Results are never copied.
"""
from datetime import datetime, timedelta, timezone
import csv
import hashlib
import json
from pathlib import Path
import re
import secrets

import yaml
from sqlalchemy import select, text

from app.models import AnalysisRun, PipelineSubmissionDraft
from app.wgs_release_catalog import load_wgs_release_catalog, submission_options
from app.wgs_platform_service import create_wgs_platform_run, run_payload, submit_wgs_run

TEST_ROOT = Path('/sg2/50.ctapa/project/HWcloud/WGS_test')
FASTQ_ROOTS = (Path('/bi/fastq/T7_Fastq'), Path('/sg2/T7new/result1/OutputFq'), Path('/sg2/T7/result6/OutputFq/T7'))
SAFE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')


def require_test(settings):
    if str(settings.platform_environment).lower() not in {'test', 'bs10610-test'}:
        raise ValueError('Independent WGS projects require the test environment')
    if not getattr(settings, 'wgs_test_project_enabled', False):
        raise ValueError('Independent WGS project gate is disabled')


def project_root(settings, run) -> str | None:
    data=(run.params_json or {}).get('test_project')
    if not data: return None
    require_test(settings)
    root=Path(data['output_root'])
    if TEST_ROOT not in root.parents or '..' in root.parts or root.is_symlink():
        raise ValueError('Test project root is invalid')
    return str(root)


def target_path(root: Path, child: str) -> Path:
    if not child or any(not SAFE.fullmatch(part) for part in child.split('/')):
        raise ValueError('Output must be a safe relative child directory')
    target = root
    for part in child.split('/'):
        target = target / part
        if target.is_symlink():
            raise ValueError('Output symlinks are forbidden')
    if target.exists():
        raise ValueError('Output target already exists; overwriting is forbidden')
    resolved = target.resolve()
    if root.resolve() not in resolved.parents:
        raise ValueError('Output escapes test root')
    return resolved


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def read_source(source: Path, root: Path) -> dict:
    if not source.is_absolute() or '..' in source.parts or source.is_symlink():
        raise ValueError('Source must be an absolute real project directory')
    source=source.resolve(strict=True)
    if root.resolve(strict=True) not in source.parents or not source.is_dir():
        raise ValueError('Source must be inside the approved test root')
    for path in [source/'sampleinfo.tsv',source/'config.yaml']:
        if path.is_symlink() or not path.is_file(): raise ValueError(f'Required source input is missing: {path.name}')
    config=yaml.safe_load((source/'config.yaml').read_text())
    fastq_root=Path(str(config.get('fastqPath') or '')) if isinstance(config,dict) else Path('.')
    if not fastq_root.is_absolute() or '..' in fastq_root.parts:
        raise ValueError('Source config must declare an absolute fastqPath')
    resolved_fastq_root=fastq_root.resolve(strict=True)
    approved=[root.resolve(strict=True),*(path.resolve() for path in FASTQ_ROOTS)]
    if not any(resolved_fastq_root==base or base in resolved_fastq_root.parents for base in approved):
        raise ValueError('Config-declared FASTQ root is not an approved test input root')
    with (source/'sampleinfo.tsv').open(encoding='utf-8-sig',newline='') as handle:
        rows=list(csv.DictReader(handle,delimiter='\t'))
    if not rows or len(rows)>10000: raise ValueError('Source sample table is empty or exceeds 10000 rows')
    samples=[str(row.get('样本编号') or '').strip() for row in rows]
    data_ids=[str(row.get('数据编号') or '').strip() for row in rows]
    if any(not SAFE.fullmatch(item) for item in samples+data_ids) or len(set(samples))!=len(samples) or len(set(data_ids))!=len(data_ids):
        raise ValueError('Sample and data IDs must be safe and unique')
    batches={str(row.get('分析批次') or '').strip() for row in rows}
    if len(batches)!=1 or not re.fullmatch(r'[0-9]{8}[A-Z]',next(iter(batches))):
        raise ValueError('Source must identify one YYYYMMDDX analysis batch')
    files=[]
    for sample,data_id in zip(samples,data_ids):
        for read in ['R1','R2']:
            path=source/'raw'/f'{data_id}.{read}.fq.gz'
            resolved=path.resolve(strict=True)
            if not resolved.is_file(): raise ValueError('FASTQ pair member is not a regular file')
            # FASTQ may resolve outside source only below the config-declared root.
            if fastq_root.resolve() not in resolved.parents and source not in resolved.parents:
                raise ValueError('FASTQ escapes the config-declared source root')
            stat=resolved.stat()
            files.append({'sample_id':sample,'data_id':data_id,'read':read,'path':str(resolved),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns})
    result={'source':str(source),'sampleinfo_sha256':sha(source/'sampleinfo.tsv'),'config_sha256':sha(source/'config.yaml'),'samples':samples,'batch':next(iter(batches)),'fastq_root':str(fastq_root),'fastq':files}
    result['fingerprint']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result


def preview(*,session,settings,username,source_project_dir,output_child,algo,use_reference):
    require_test(settings)
    target=target_path(TEST_ROOT,output_child)
    source=read_source(Path(source_project_dir),TEST_ROOT)
    release=load_wgs_release_catalog(settings.wgs_release_catalog_path).release
    supported=submission_options(release)
    if algo not in {item['value'] for item in supported['callers']} or use_reference not in supported['reference_values']:
        raise ValueError('Unsupported release options')
    now=datetime.now(timezone.utc)
    namespace='WGS_TEST_'+secrets.token_hex(8).upper()
    analysis_batch=source['batch']
    data={**source,'output_child':output_child,'target_root':str(target),'project_namespace':namespace,'output_root':str(target/namespace),'analysis_batch':analysis_batch,'algo':algo,'use_reference':use_reference,'release_id':release.release_id}
    draft=PipelineSubmissionDraft(draft_id=f'wgs-test-{secrets.token_hex(12)}',pipeline_name='wgs',owner_username=username,input_root=source['source'],input_fingerprint=source['fingerprint'],preview_json=data,status='previewed',created_at=now,updated_at=now,expires_at=now+timedelta(hours=2))
    session.add(draft);session.commit()
    return {'draft_id':draft.draft_id,'preview_hash':draft.input_fingerprint,'samples':source['samples'],'batch':source['batch'],'analysis_batch':analysis_batch,'output_child':output_child+'/'+namespace,'sample_count':len(source['samples']),'fastq_file_count':len(source['fastq']),'algo':algo,'use_reference':use_reference,'release_id':release.release_id,'write_check':'Restricted test node checks write access at preparation; no fallback output root','expires_at':draft.expires_at.isoformat()}


def confirm(*,session,settings,airflow_client,username,draft_id,preview_hash):
    require_test(settings)
    draft=session.scalar(select(PipelineSubmissionDraft).where(PipelineSubmissionDraft.draft_id==draft_id).with_for_update())
    if draft is None or draft.pipeline_name!='wgs' or draft.owner_username!=username or not draft_id.startswith('wgs-test-'):
        raise ValueError('Unknown test project draft')
    if draft.input_fingerprint != preview_hash: raise ValueError('Preview fingerprint mismatch')
    if draft.analysis_id:
        run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==draft.analysis_id))
        if run is None: raise ValueError('Draft run binding is missing')
        return submit_wgs_run(session=session,airflow_client=airflow_client,analysis_id=run.analysis_id) if run.status=='created' else run_payload(session,run)
    if draft.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc): raise ValueError('Test project draft expired')
    data=dict(draft.preview_json)
    if session.get_bind().dialect.name == 'postgresql':
        lock_key=int.from_bytes(hashlib.sha256(data['target_root'].encode()).digest()[:8],byteorder='big',signed=True)
        session.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock_key})
    others=session.scalars(select(PipelineSubmissionDraft).where(PipelineSubmissionDraft.pipeline_name=='wgs',PipelineSubmissionDraft.analysis_id.is_not(None),PipelineSubmissionDraft.draft_id!=draft_id)).all()
    if any((row.preview_json or {}).get('target_root')==data['target_root'] for row in others):
        raise ValueError('Output target is already reserved by another test project')
    target_path(TEST_ROOT,data['output_child'])
    if read_source(Path(draft.input_root),TEST_ROOT)['fingerprint']!=draft.input_fingerprint: raise ValueError('Source inputs changed after preview')
    release=load_wgs_release_catalog(settings.wgs_release_catalog_path).release
    if release.release_id!=data['release_id']: raise ValueError('Release changed after preview')
    created=create_wgs_platform_run(session=session,settings=settings,project_name=data['project_namespace'],execution_mode='cce',batch_no=f"WGS_{data['analysis_batch']}_T7Hg38{release.version}",fq_path=data['output_root'],submitted_by=username,commit=False,validate_input=False,platform='T7',sequencing_batch=data['batch'],analysis_batch=data['analysis_batch'],fastq_root=data['fastq_root'],use_reference=data['use_reference'])
    run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==created['analysis_id']))
    # Different destinations are independent projects, never implicit resumes.
    if (run.params_json or {}).get('test_project'):
        raise ValueError('Source already bound to another test project; use its existing draft')
    run.params_json={**run.params_json,'test_project':data,'algo':data['algo'],'submission_options':{'algo':data['algo'],'use_reference':data['use_reference'],'release_id':release.release_id},'submission_mode':'three_stage','submission_phase':'preparing_sampleinfo','resource_set':'default','config_approved_at':None,'execution_approved_at':None}
    draft.analysis_id=run.analysis_id;draft.status='submitted'
    session.commit()
    return submit_wgs_run(session=session,airflow_client=airflow_client,analysis_id=run.analysis_id)
