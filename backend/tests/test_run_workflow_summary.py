from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, RuleState, Sample, SnakemakeRuleEvent
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
                AnalysisRun(
                    analysis_id="WGS_SUMMARY",
                    pipeline_name="wgs",
                    dag_id="bio_wgs",
                    status="running",
                    workdir="/tmp/wgs",
                    current_stage="wait_step3_analysis",
                    submitted_by="jiucheng",
                    params_json={"stage": "full", "project_name": "WGS summary"},
                ),
                Sample(analysis_id="PGTA_SUMMARY", sample_id="P1", status="running", qc_status="unknown"),
                Sample(analysis_id="NIPT_SUMMARY", sample_id="N1", status="failed", qc_status="unknown"),
                Sample(analysis_id="WGS_SUMMARY", sample_id="W1", status="running", qc_status="unknown"),
                SnakemakeRuleEvent(analysis_id="PGTA_SUMMARY", rule="fastp_bwa", sample_id="P1", snakemake_jobid="1", status="success"),
                SnakemakeRuleEvent(analysis_id="PGTA_SUMMARY", rule="wisecondorx_qc_for_predict", sample_id="P1", snakemake_jobid="2", status="running"),
                SnakemakeRuleEvent(analysis_id="NIPT_SUMMARY", rule="map", sample_id="N1", snakemake_jobid="1", status="success"),
                SnakemakeRuleEvent(analysis_id="NIPT_SUMMARY", rule="aneuscreen_predict", sample_id="N1", snakemake_jobid="2", status="failed"),
                RuleState(analysis_id="WGS_SUMMARY", attempt=1, rule_instance_id="w1", rule_name="Preall", phase="Pre-calling", sequence=1, status="success"),
                RuleState(analysis_id="WGS_SUMMARY", attempt=1, rule_instance_id="w2", rule_name="mapping", phase="Pre-calling", sequence=2, sample_id="W1", status="success"),
                RuleState(analysis_id="WGS_SUMMARY", attempt=1, rule_instance_id="w3", rule_name="QualCal", phase="Pre-calling", sequence=3, sample_id="W1", status="running"),
                RuleState(analysis_id="WGS_SUMMARY", attempt=1, rule_instance_id="w4", rule_name="SNV_Annotation", phase="Variant analysis", sequence=4, sample_id="W1", status="running"),
                RuleState(analysis_id="WGS_SUMMARY", attempt=1, rule_instance_id="w5", rule_name="mergeMTQC", phase="QC", sequence=5, sample_id="W1", status="success"),
                RuleState(analysis_id="WGS_SUMMARY", attempt=1, rule_instance_id="w6", rule_name="all", phase="QC", sequence=6, status="success"),
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
    assert [(item["label"], item["status"]) for item in by_id["WGS_SUMMARY"]["workflow_summary"]] == [
        ("Uploading FASTQ", "success"),
        ("Starting WGS workflow", "success"),
        ("WGS workflow running", "running"),
        ("Publishing WGS results", "pending"),
        ("Downloading WGS results", "pending"),
        ("Materializing local results", "pending"),
    ]
    rule_selects = [statement for statement in statements if "FROM snakemake_rule_event" in statement]
    assert len(rule_selects) == 1
    wgs_rule_selects = [statement for statement in statements if "FROM rule_state" in statement]
    assert len(wgs_rule_selects) == 0


def test_successful_wgs_run_list_uses_six_project_steps_not_rule_phases() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        run = AnalysisRun(
            analysis_id="WGS_SUCCESS_STAGES",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status="success",
            workdir="/data/wgs-results/runs/WGS_SUCCESS_STAGES",
            current_stage="Workflow complete",
            params_json={"project_name": "WGS", "batch_no": "BATCH-1"},
        )
        session.add_all(
            [
                run,
                RuleState(
                    analysis_id=run.analysis_id,
                    attempt=1,
                    rule_instance_id="stale-final",
                    rule_name="cloud_finalize_delivery",
                    status="running",
                ),
            ]
        )
        session.commit()

        payload = list_runs(session=session, pipeline="deployed", limit=20, offset=0)

    stages = payload["items"][0]["workflow_summary"]
    assert [item["key"] for item in stages] == [
        "step1_upload",
        "step2_master",
        "step3_monitor",
        "step4_publish",
        "step5_download",
        "step6_materialize",
    ]
    assert {item["status"] for item in stages} == {"success"}
