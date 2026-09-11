"""Attempt-fenced participation, separate from mutable execution status."""
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import aliased
from app.models import AnalysisRun, Sample


def selection_state(sample, run):
    meta=sample.metadata_json or {}
    decision=meta.get('selection_decision')
    if decision is None:
        return 'unresolved' if (getattr(run, 'params_json', None) or {}).get('sample_selection_scope') else 'legacy'
    if meta.get('selection_attempt') != run.attempt: return 'unresolved'
    return decision


def participates(sample, run):
    return selection_state(sample,run) in {'legacy','selected'}


def selected_clause(sample=Sample):
    """Portable SQL filter; aliased run prevents accidental outer correlation."""
    run=aliased(AnalysisRun)
    decision=sample.metadata_json['selection_decision'].as_string()
    legacy_run = select(run.analysis_id).where(run.analysis_id == sample.analysis_id,
        run.params_json['sample_selection_scope'].as_string().is_(None)).exists()
    return or_(and_(decision.is_(None), legacy_run), and_(decision=='selected', select(run.analysis_id).where(
        run.analysis_id==sample.analysis_id,
        run.attempt==sample.metadata_json['selection_attempt'].as_integer(),
    ).exists()))


def nonparticipating_status(sample,run):
    state=selection_state(sample,run)
    if state in {'legacy','selected'}: return None
    return 'skipped' if state=='excluded' else 'pending'


def scope_status(run):
    scope = (run.params_json or {}).get('sample_selection_scope')
    if not scope:
        return 'legacy'
    return 'ready' if scope.get('attempt') == run.attempt and scope.get('status') == 'ready' else 'preparing'
