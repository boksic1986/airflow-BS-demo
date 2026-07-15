import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, QcMetric, Sample, SnakemakeRuleEvent


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def seed_operator_resources(session_factory, tmp_path) -> None:
    now = datetime.now(timezone.utc)
    runs = [
        (
            "PGTA_ALPHA_SUCCESS",
            "pgta",
            "success",
            now - timedelta(hours=3),
            now - timedelta(hours=3),
            now - timedelta(hours=2),
            {"project_name": "Alpha embryo batch", "target": "baseline_qc"},
            None,
        ),
        (
            "PGTA_BETA_FAILED",
            "pgta",
            "failed",
            now - timedelta(hours=2),
            now - timedelta(hours=2),
            now - timedelta(hours=1, minutes=50),
            {"project_name": "Beta retry batch", "target": "baseline_qc"},
            json.dumps(
                {
                    "return_code": 17,
                    "stderr_path": "/data/airflow-demo/runs/PGTA_BETA_FAILED/logs/snakemake.stderr.log",
                    "last_100_lines": ["Error in rule mapping", "samtools sort failed"],
                }
            ),
        ),
        (
            "NIPT_GAMMA_QC",
            "nipt_docker",
            "success",
            now - timedelta(hours=1),
            now - timedelta(hours=1),
            now - timedelta(minutes=55),
            {"project_name": "Gamma NIPT chip", "run_mode": "mount_smoke"},
            None,
        ),
    ]
    with session_factory() as session:
        for analysis_id, pipeline, status, created_at, started_at, ended_at, params, error_summary in runs:
            session.add(
                AnalysisRun(
                    analysis_id=analysis_id,
                    pipeline_name=pipeline,
                    dag_id="bio_pgta" if pipeline == "pgta" else "bio_nipt_docker",
                    dag_run_id=f"manual__{analysis_id}",
                    mode="new",
                    status=status,
                    sample_sheet_path=str(tmp_path / analysis_id / "config" / "samples.selected.tsv"),
                    workdir=str(tmp_path / analysis_id),
                    params_json=params,
                    created_at=created_at,
                    started_at=started_at,
                    ended_at=ended_at,
                    error_summary=error_summary,
                )
            )

        session.add_all(
            [
                Sample(
                    analysis_id="PGTA_ALPHA_SUCCESS",
                    sample_id="G10",
                    family_id="FAMILY-A",
                    fq1="/data/project/CNV/PGT-A/rawdata/alpha/G10_R1.fastq.gz",
                    fq2="/data/project/CNV/PGT-A/rawdata/alpha/G10_R2.fastq.gz",
                    metadata_json={"source_dir": "/data/project/CNV/PGT-A/rawdata/alpha"},
                    status="success",
                    qc_status="pass",
                ),
                Sample(
                    analysis_id="PGTA_BETA_FAILED",
                    sample_id="G20",
                    fq1="/data/project/CNV/PGT-A/rawdata/beta/G20_R1.fastq.gz",
                    fq2="/data/project/CNV/PGT-A/rawdata/beta/G20_R2.fastq.gz",
                    metadata_json={"source_dir": "/data/project/CNV/PGT-A/rawdata/beta"},
                    status="failed",
                    qc_status="unknown",
                ),
                Sample(
                    analysis_id="NIPT_GAMMA_QC",
                    sample_id="NC-01",
                    fq1="/opt/pipelines/NIPT/fastq/chip-gamma/NC-01.R1.clean.fastq.gz",
                    fq2="/opt/pipelines/NIPT/fastq/chip-gamma/NC-01.R2.clean.fastq.gz",
                    metadata_json={"source_dir": "/opt/pipelines/NIPT/fastq/chip-gamma"},
                    status="success",
                    qc_status="fail",
                ),
            ]
        )
        session.add(
            SnakemakeRuleEvent(
                analysis_id="PGTA_BETA_FAILED",
                rule="mapping",
                sample_id="G20",
                snakemake_jobid="9",
                status="failed",
                return_code=17,
                message="samtools sort failed",
            )
        )
        session.add(
            QcMetric(
                analysis_id="NIPT_GAMMA_QC",
                sample_id="NC-01",
                metric_name="fetal_ratio",
                metric_value="0.015",
                threshold=">=0.03",
                status="fail",
            )
        )
        session.commit()


def install_session(monkeypatch, session_factory) -> TestClient:
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    return TestClient(main.app)


def seed_bs_wgs_failure(session_factory, tmp_path) -> None:
    now = datetime.now(timezone.utc)
    analysis_id = "WGS_OMEGA_FAILED"
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status="failed",
                sample_sheet_path=str(tmp_path / analysis_id / "config" / "samples.selected.tsv"),
                workdir=str(tmp_path / analysis_id),
                params_json={"project_name": "Omega WGS family", "wgs_stage": "full"},
                created_at=now,
                submitted_at=now,
                started_at=now,
                ended_at=now,
                error_summary="QualCal failed",
            )
        )
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="WGS-01",
                family_id="OMEGA",
                status="failed",
                qc_status="unknown",
            )
        )
        session.add(
            SnakemakeRuleEvent(
                analysis_id=analysis_id,
                rule="QualCal",
                sample_id="WGS-01",
                snakemake_jobid="7",
                status="failed",
                return_code=23,
                message="Sentieon QualCal failed",
            )
        )
        session.commit()


def test_runs_support_project_keyword_sort_and_pagination(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_operator_resources(session_factory, tmp_path)
    client = install_session(monkeypatch, session_factory)

    response = client.get("/api/runs?pipeline=pgta&keyword=alpha&sort=created_desc&limit=1&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["analysis_id"] == "PGTA_ALPHA_SUCCESS"
    assert payload["items"][0]["project_name"] == "Alpha embryo batch"


def test_runs_deployed_scope_excludes_historical_wes_and_uses_sql_pagination(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_operator_resources(session_factory, tmp_path)
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id="WES_HISTORY",
                pipeline_name="wes_qsub",
                dag_id="bio_wes_qsub",
                dag_run_id="manual__WES_HISTORY",
                mode="new",
                status="success",
                sample_sheet_path=None,
                workdir=str(tmp_path / "WES_HISTORY"),
                params_json={"project_name": "Historical WES"},
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    statements: list[str] = []
    event.listen(session_factory.kw["bind"], "before_cursor_execute", lambda _conn, _cursor, statement, _params, _context, _many: statements.append(statement))
    client = install_session(monkeypatch, session_factory)

    response = client.get("/api/runs?pipeline=deployed&limit=2&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert all(item["pipeline"] in {"pgta", "nipt_docker"} for item in payload["items"])
    assert any(" limit " in statement.lower() for statement in statements)


def test_bs_default_all_and_deployed_resources_share_one_nipt_wgs_page(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_operator_resources(session_factory, tmp_path)
    seed_bs_wgs_failure(session_factory, tmp_path)
    monkeypatch.setattr(
        main,
        "_deployment_guard_settings",
        lambda: SimpleNamespace(deployed_pipelines=("nipt_docker", "wgs")),
    )
    client = install_session(monkeypatch, session_factory)

    for pipeline_query in ("", "&pipeline=all", "&pipeline=deployed"):
        first_runs = client.get(f"/api/runs?sort=created_desc&limit=1&offset=0{pipeline_query}").json()
        second_runs = client.get(f"/api/runs?sort=created_desc&limit=1&offset=1{pipeline_query}").json()
        assert first_runs["total"] == 2
        assert first_runs["items"][0]["analysis_id"] == "WGS_OMEGA_FAILED"
        assert second_runs["items"][0]["analysis_id"] == "NIPT_GAMMA_QC"

        first_samples = client.get(f"/api/samples?limit=1&offset=0{pipeline_query}").json()
        second_samples = client.get(f"/api/samples?limit=1&offset=1{pipeline_query}").json()
        assert first_samples["total"] == 2
        assert first_samples["items"][0]["analysis_id"] == "WGS_OMEGA_FAILED"
        assert second_samples["items"][0]["analysis_id"] == "NIPT_GAMMA_QC"

        first_failures = client.get(f"/api/failures?kind=all&period=7d&limit=1&offset=0{pipeline_query}").json()
        second_failures = client.get(f"/api/failures?kind=all&period=7d&limit=1&offset=1{pipeline_query}").json()
        assert first_failures["total"] == 2
        assert first_failures["items"][0]["analysis_id"] == "WGS_OMEGA_FAILED"
        assert second_failures["items"][0]["analysis_id"] == "NIPT_GAMMA_QC"

        returned_ids = {
            first_runs["items"][0]["analysis_id"],
            second_runs["items"][0]["analysis_id"],
            first_samples["items"][0]["analysis_id"],
            second_samples["items"][0]["analysis_id"],
            first_failures["items"][0]["analysis_id"],
            second_failures["items"][0]["analysis_id"],
        }
        assert all(not analysis_id.startswith("PGTA_") for analysis_id in returned_ids)


def test_samples_resource_is_paginated_and_hides_absolute_paths(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_operator_resources(session_factory, tmp_path)
    client = install_session(monkeypatch, session_factory)
    statements: list[str] = []
    event.listen(session_factory.kw["bind"], "before_cursor_execute", lambda _conn, _cursor, statement, _params, _context, _many: statements.append(statement))

    response = client.get("/api/samples?pipeline=nipt_docker&qc_status=fail&keyword=NC-01&limit=25&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item == {
        "analysis_id": "NIPT_GAMMA_QC",
        "project_name": "Gamma NIPT chip",
        "pipeline": "nipt_docker",
        "sample_id": "NC-01",
        "family_id": None,
        "status": "success",
        "qc_status": "fail",
        "source_folder": "chip-gamma",
        "r1_name": "NC-01.R1.clean.fastq.gz",
        "r2_name": "NC-01.R2.clean.fastq.gz",
        "report_status": "available",
    }
    assert "/opt/pipelines" not in json.dumps(payload)
    assert any(" limit " in statement.lower() for statement in statements)


def test_failures_separate_workflow_and_qc_without_airflow_calls(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_operator_resources(session_factory, tmp_path)
    client = install_session(monkeypatch, session_factory)

    workflow = client.get("/api/failures?pipeline=all&kind=workflow&period=7d&limit=20&offset=0")
    qc = client.get("/api/failures?pipeline=all&kind=qc&period=7d&limit=20&offset=0")

    assert workflow.status_code == 200
    workflow_payload = workflow.json()
    assert workflow_payload["total"] == 1
    workflow_item = workflow_payload["items"][0]
    assert workflow_item["analysis_id"] == "PGTA_BETA_FAILED"
    assert workflow_item["failure_kind"] == "workflow"
    assert workflow_item["failure_layer"] == "pipeline_rule"
    assert workflow_item["failed_step"] == "mapping"
    assert workflow_item["failed_step_label"] == "Mapping reads"
    assert workflow_item["sample_id"] == "G20"
    assert workflow_item["return_code"] == 17
    assert "samtools sort failed" in workflow_item["stderr_excerpt"]
    assert workflow_item["can_resume"] is True
    assert workflow_item["can_rerun_stage"] is True

    assert qc.status_code == 200
    qc_payload = qc.json()
    assert qc_payload["total"] == 1
    qc_item = qc_payload["items"][0]
    assert qc_item["analysis_id"] == "NIPT_GAMMA_QC"
    assert qc_item["workflow_status"] == "success"
    assert qc_item["qc_status"] == "fail"
    assert qc_item["failure_kind"] == "qc"
    assert qc_item["failure_layer"] == "qc"
    assert qc_item["sample_id"] == "NC-01"
    assert qc_item["failed_step"] == "fetal_ratio"
    assert qc_item["can_resume"] is False
    assert qc_item["can_rerun_stage"] is False


def test_failures_keep_qc_alerts_for_failed_runs_and_redact_sensitive_paths(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_operator_resources(session_factory, tmp_path)
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == "PGTA_BETA_FAILED"))
        sample = session.scalar(select(Sample).where(Sample.analysis_id == "PGTA_BETA_FAILED"))
        assert run is not None and sample is not None
        sample.qc_status = "fail"
        run.error_summary = json.dumps({
            "last_100_lines": [
                "samtools failed at /data/private/patient-001/G20.sorted.bam token=secret-value",
                "Authorization: Bearer bearer-value AWS_SECRET_ACCESS_KEY=aws-value smtp_password=mail-value",
            ]
        })
        session.add(QcMetric(analysis_id=run.analysis_id, sample_id=sample.sample_id, metric_name="mapped_fragments", metric_value="10", threshold=">=100", status="fail"))
        session.commit()
    client = install_session(monkeypatch, session_factory)

    qc_payload = client.get("/api/failures?pipeline=all&kind=qc&period=7d&limit=20&offset=0").json()
    workflow_payload = client.get("/api/failures?pipeline=all&kind=workflow&period=7d&limit=20&offset=0").json()

    assert {item["analysis_id"] for item in qc_payload["items"]} == {"PGTA_BETA_FAILED", "NIPT_GAMMA_QC"}
    excerpt = workflow_payload["items"][0]["stderr_excerpt"]
    assert "/data/private" not in excerpt
    assert "secret-value" not in excerpt
    assert "bearer-value" not in excerpt
    assert "aws-value" not in excerpt
    assert "mail-value" not in excerpt
    assert "G20.sorted.bam" in excerpt
