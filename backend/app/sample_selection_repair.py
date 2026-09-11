"""Explicit, idempotent current-attempt repair. Dry-run unless --apply is supplied."""
import argparse
import json
import re
from pathlib import Path
from sqlalchemy import select
from app.models import AnalysisRun, Sample
from app.sample_selection_scope import selected_clause
from app.wgs_platform_service import sync_prepare_handoff_decisions


def repair_sample_scope(*, session, runtime_root, analysis_id, attempt, apply=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', analysis_id) or attempt < 1:
        raise ValueError('invalid analysis identity')
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id).with_for_update())
    if run is None or run.pipeline_name != 'wgs' or run.attempt != attempt:
        raise ValueError('repair requires the current WGS attempt')
    root = Path(runtime_root).resolve()
    runs_root = root if root.name == 'runs' else root / 'runs'
    directory = runs_root / analysis_id / f'attempt-{attempt}' / 'prepare-handoff'
    receipts = []
    for stage in ('prepare_sampleinfo', 'prepare_analysis'):
        matches = list(directory.rglob(f'{stage}.receipt.json'))
        if len(matches) != 1:
            raise ValueError('repair requires one unambiguous current-attempt receipt per stage')
        path = matches[0]
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('unsafe receipt location')
        value = json.loads(path.read_text(encoding='utf-8'))
        if value.get('analysis_id') != analysis_id or value.get('attempt') != attempt:
            raise ValueError('receipt attempt mismatch')
        if value.get('generation') is not None:
            if path.parent.name != f"generation-{value['generation']}":
                raise ValueError('receipt generation mismatch')
            request_path = path.parent / 'handoff-request.json'
            request = json.loads(request_path.read_text(encoding='utf-8'))
            if any(request.get(key) != value.get(key) for key in ('analysis_id', 'attempt', 'generation', 'execution_id', 'request_hash')):
                raise ValueError('receipt does not match its accepted handoff request')
        receipts.append(value)
    preview, final = receipts
    if preview.get('schema_version') != 'wgs.prepare-sampleinfo.receipt.v1' or final.get('schema_version') != 'wgs.prepare-analysis.receipt.v1':
        raise ValueError('unsupported receipt schema')
    def identities(value, key):
        rows = value.get(key)
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not str(row.get('sample_id') or '').strip() for row in rows):
            raise ValueError('incomplete sample decision group')
        ids = [str(row['sample_id']).strip() for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate receipt identity')
        return set(ids)
    candidates = identities(preview, 'safe_candidates')
    groups = {key: identities(final, key) for key in ('selected', 'pending', 'excluded')}
    union = set().union(*groups.values())
    if union != candidates or sum(map(len, groups.values())) != len(union):
        raise ValueError('receipt sample sets are incomplete or overlapping')
    before = len(session.scalars(select(Sample).where(Sample.analysis_id == analysis_id, selected_clause())).all())
    result = {'analysis_id': analysis_id, 'attempt': attempt, 'before_selected': before,
              **{key: len(ids) for key, ids in groups.items()}, 'applied': bool(apply)}
    if apply:
        sync_prepare_handoff_decisions(session=session, run=run, receipt=final)
        session.commit()
    return result


def main():
    from app.config import get_settings
    from app.db import get_sessionmaker
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-id', required=True)
    parser.add_argument('--attempt', type=int, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with get_sessionmaker()() as session:
        print(json.dumps(repair_sample_scope(session=session, runtime_root=get_settings().wgs_runtime_run_root,
              analysis_id=args.analysis_id, attempt=args.attempt, apply=args.apply), sort_keys=True))


if __name__ == '__main__': main()
