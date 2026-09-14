from sqlalchemy import select
from test_gatk_runtime_service import _sessions, _run, ANALYSIS_ID
from app.models import Sample, RuleState
from app.wgs_observer import ingest_bound_pipeline_evidence_once


def test_bound_gatk_ingestion_enriches_registered_sample_from_log(tmp_path):
    sessions=_sessions()
    directory=tmp_path/'run';(directory/'mirror').mkdir(parents=True)
    (directory/'mirror'/'analysis.log').write_text('rule fastp_clean:\n    jobid: 165\n    wildcards: sample=SYNTHETIC-01\nrule fastp_clean:\n    jobid: 166\n    wildcards: sample=NOT-REGISTERED\n')
    with sessions() as s:
        s.add_all([_run(),Sample(analysis_id=ANALYSIS_ID,sample_id='SYNTHETIC-01',status='running')])
        for job in ('165','166'):
            s.add(RuleState(analysis_id=ANALYSIS_ID,attempt=1,rule_instance_id=job,rule_name='fastp_clean',snakemake_jobid=job,status='success'))
        s.commit()
    for _ in range(2):
        ingest_bound_pipeline_evidence_once(session_factory=sessions,analysis_id=ANALYSIS_ID,attempt=1,pipeline_release_id='synthetic',run_label='synthetic-a1',evidence_root=tmp_path,evidence_directory=directory)
        with sessions() as s:
            rows=s.scalars(select(RuleState).order_by(RuleState.snakemake_jobid)).all()
            assert rows[0].sample_id=='SYNTHETIC-01'
            assert rows[1].sample_id is None
