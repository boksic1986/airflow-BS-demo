from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, Sample, SnakemakeRuleEvent
from app.run_service import list_runs


def test_run_list_builds_workflow_stage_summaries_with_one_rule_query() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all(
            [
                AnalysisRun(
                    analysis_id="PGTA_SUMMARY",
                    pipeline_name="pgta",
                    dag_id="bio_pgta",
                    status="running",
                    workdir="/tmp/pgta",
                    submitted_by="jiucheng",
                    params_json={"target": "predict", "project_name": "PGTA summary"},
                ),
                AnalysisRun(
                    analysis_id="NIPT_SUMMARY",
                    pipeline_name="nipt_docker",
                    dag_id="bio_nipt_docker",
                    status="failed",
                    workdir="/tmp/nipt",
                    params_json={"run_mode": "full_run", "project_name": "NIPT summary"},
                ),
                Sample(analysis_id="PGTA_SUMMARY", sample_id="P1", status="running", qc_status="unknown"),
                Sample(analysis_id="NIPT_SUMMARY", sample_id="N1", status="failed", qc_status="unknown"),
                SnakemakeRuleEvent(analysis_id="PGTA_SUMMARY", rule="fastp_bwa", sample_id="P1", snakemake_jobid="1", status="success"),
                SnakemakeRuleEvent(analysis_id="PGTA_SUMMARY", rule="wisecondorx_qc_for_predict", sample_id="P1", snakemake_jobid="2", status="running"),
                SnakemakeRuleEvent(analysis_id="NIPT_SUMMARY", rule="map", sample_id="N1", snakemake_jobid="1", status="success"),
                SnakemakeRuleEvent(analysis_id="NIPT_SUMMARY", rule="aneuscreen_predict", sample_id="N1", snakemake_jobid="2", status="failed"),
            ]
        )
        session.commit()

        statements: list[str] = []
        event.listen(engine, "before_cursor_execute", lambda _c, _cu, statement, _p, _ctx, _many: statements.append(statement))
        payload = list_runs(session=session, pipeline="deployed", limit=20, offset=0)

    by_id = {item["analysis_id"]: item for item in payload["items"]}
    assert by_id["PGTA_SUMMARY"]["submitted_by"] == "jiucheng"
    assert [(item["label"], item["status"]) for item in by_id["PGTA_SUMMARY"]["workflow_summary"]] == [
        ("Mapping", "success"),
        ("Metadata", "pending"),
        ("CNV QC", "running"),
        ("CNV prediction", "pending"),
    ]
    assert [(item["label"], item["status"]) for item in by_id["NIPT_SUMMARY"]["workflow_summary"]] == [
        ("Input QC", "pending"),
        ("Mapping", "success"),
        ("CNV", "pending"),
        ("T21 classifier", "failed"),
        ("Fetal fraction", "pending"),
        ("Final QC", "pending"),
    ]
    rule_selects = [statement for statement in statements if "FROM snakemake_rule_event" in statement]
    assert len(rule_selects) == 1
