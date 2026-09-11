from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.models import Base, AnalysisRun
from app.dashboard_service import get_dashboard_runs

def test_default_excludes_cancelled_before_pagination_but_history_retains_both_spellings():
    engine=create_engine('sqlite:///:memory:');Base.metadata.create_all(engine)
    with Session(engine) as s:
        for i,status in enumerate(['cancelled','canceled','created']):
            s.add(AnalysisRun(analysis_id=f'MOCK{i}',pipeline_name='wgs',dag_id='bio_wgs',status=status,workdir='/synthetic'))
        s.commit()
        def read(status=None):return get_dashboard_runs(session=s,airflow_client=None,pipeline='wgs',status=status,keyword=None,limit=1,offset=0)
        normal=read();assert normal['total']==1;assert normal['items'][0]['analysis_id']=='MOCK2'
        history=read('cancelled');assert history['total']==2
        assert s.scalar(select(func.count()).select_from(AnalysisRun))==3
