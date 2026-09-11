from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.models import Base, AnalysisRun, Sample, WgsIntakeBatch
from app.wgs_dashboard_attention import project_wgs_dashboard_attention

@pytest.mark.parametrize('status', ['cancelled', 'canceled'])
def test_cancelled_runs_emit_no_attention_but_audit_and_other_alerts_remain(status):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        runs = []
        for aid, state, batch in [('CANCEL', status, '20000101A'), ('ACTIVE', 'failed', '20000102B')]:
            run = AnalysisRun(analysis_id=aid, pipeline_name='wgs', dag_id='bio_wgs',
                status=state, attempt=2, mode='resume', workdir='/synthetic', params_json={'analysis_batch': batch})
            session.add(run); runs.append(run)
            session.add(Sample(analysis_id=aid, sample_id='SYNTHETIC', family_id='FAMILY',
                qc_status='failed', metadata_json={'estimated_report_date':'2000-01-01'}))
        session.add(WgsIntakeBatch(source_path='/synthetic/cancel', chip_id='cancel-chip',
            sequencing_batch='20000101A', analysis_id='CANCEL', state='needs_review', pair_issue_count=1))
        session.add(WgsIntakeBatch(source_path='/synthetic/new', chip_id='new-chip',
            sequencing_batch='20000103C', state='needs_review', pair_issue_count=1))
        session.commit()
        items = project_wgs_dashboard_attention(session=session, runs=runs,
            now=datetime(2026,9,11,tzinfo=timezone.utc))
        assert not [item for item in items if item.get('analysis_id') == 'CANCEL']
        assert not [item for item in items if item['category'] == 'duplicate_family']
        assert {'workflow_failed', 'qc_failed', 'report_delivery_overdue'} <= {
            item['category'] for item in items if item.get('analysis_id') == 'ACTIVE'}
        assert any(item['category']=='intake_pair_issue' and item['analysis_id'] is None for item in items)
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 2
