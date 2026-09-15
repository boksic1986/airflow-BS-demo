from datetime import datetime, timezone

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Base
from app import wgs_submission_service as service


def test_incomplete_page_filters_before_count_and_exposes_only_card_fields():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for aid, pipeline, status, phase, mode in [
            ('A', 'wgs', 'running', 'config_review', 'three_stage'),
            ('B', 'wgs', 'submitted', 'preparing_sampleinfo', None),
            ('C', 'wgs', 'running', 'execution_review', 'auto_dispatch'),
            ('D', 'wgs', 'failed', 'config_review', 'three_stage'),
            ('E', 'gatk', 'running', 'config_review', 'manual'),
            ('F', 'wgs', 'running', 'approved', 'three_stage'),
            ('G', 'wgs', 'cancel_requested', 'cancelling_submission', 'three_stage'),
        ]:
            session.add(AnalysisRun(analysis_id=aid, pipeline_name=pipeline, dag_id='bio_'+pipeline,
                status=status, attempt=2, workdir='/synthetic', created_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
                params_json={'submission_phase':phase, 'submission_mode':mode, 'batch_no':'SYNTH',
                             'config_approved_at':None, 'private_path':'/not-for-api', 'clinical_text':'synthetic-private'}))
        session.commit()
        first = service.list_incomplete_submissions(session=session, limit=2, offset=0)
        second = service.list_incomplete_submissions(session=session, limit=2, offset=2)
        assert first['total'] == second['total'] == 3
        assert [r['analysis_id'] for r in first['items'] + second['items']] == ['G', 'B', 'A']
        assert first['items'][0]['attempt'] == 2
        assert first['items'][0]['params']['submission_phase'] == 'cancelling_submission'
        assert 'private_path' not in str(first) and 'clinical_text' not in str(first)
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 7


def test_incomplete_page_retains_current_attempt_and_returns_empty_past_end():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(AnalysisRun(analysis_id='SYNTH', pipeline_name='wgs', dag_id='bio_wgs', status='created',
            attempt=3, workdir='/synthetic', params_json={'submission_phase':'preparing_analysis', 'batch_no':'SYNTH'}))
        session.commit()
        assert service.list_incomplete_submissions(session=session, limit=100, offset=0)['items'][0]['attempt'] == 3
        assert service.list_incomplete_submissions(session=session, limit=100, offset=100)['items'] == []
