"""Page reads avoid expensive enrichment and never acquire execution claims."""
from functools import partial
import json
import re
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from app import gatk_step7_service, main, pipeline_registry_service, wgs_sample_projection
from app.models import (
    AnalysisRun, Base, PipelineStageExecution, Sample, WgsExecutionDispatch,
    WgsMaintenanceAction,
)
from app.run_service import list_runs
from app.wgs_execution_dispatch_service import ensure_execution_dispatch, project_execution_dispatch
from app.wgs_workspace_service import build_wgs_workspace


@pytest.fixture
def database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine, sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def settings(tmp_path):
    registry = tmp_path / "pipelines.yaml"
    registry.write_text("""version: 1
pipelines:
  wgs:
    display_name: WGS
    dag_id: bio_wgs
    version: 4.2.3
    adapter: wgs
    enabled: true
    submit_enabled: true
    capabilities: [submit, rules, qc, artifacts]
    execution_targets: [cce]
  gatk:
    display_name: GATK
    dag_id: bio_gatk
    version: 7.6.0
    adapter: gatk
    enabled: true
    submit_enabled: true
    capabilities: [submit, rules, artifacts]
    execution_targets: [cce]
""", encoding="utf-8")
    return SimpleNamespace(
        deployed_pipelines=("wgs", "gatk"), pipeline_registry_path=str(registry),
        gatk_execution_enabled=False, gatk_runtime_request_root=str(tmp_path / "runtime" / "requests"),
        wgs_heavy_slot_limit=25, wgs_heavy_slot_mode="monitor-only",
        wgs_evidence_root=str(tmp_path / "evidence"),
        wgs_local_node97_enabled=False, wgs_local_node96_enabled=False, wgs_sge_enabled=False,
    )


def _run(analysis_id, pipeline="wgs"):
    return AnalysisRun(
        analysis_id=analysis_id, pipeline_name=pipeline, dag_id=f"bio_{pipeline}",
        dag_run_id=f"{analysis_id}-a1", status="success", attempt=1,
        current_stage="step6_materialize", execution_mode="cce", workdir=f"/synthetic/{analysis_id}",
        params_json={"project_id": "SYNTHETIC", "project_name": "SYNTHETIC",
                     "analysis_batch": analysis_id, "batch": analysis_id},
    )


def _qc_file(tmp_path, analysis_id, status):
    batch = tmp_path / analysis_id
    (batch / "07_QC").mkdir(parents=True)
    (batch / "07_QC" / f"{batch.name}.QCstat.tsv").write_text(
        f"Sample_ID\tName\t是否通过质控\nSYN_DATA\t\t{status}\n", encoding="utf-8",
    )
    return batch


def _sample_selects(engine):
    statements = []

    @event.listens_for(engine, "before_cursor_execute")
    def observe(_connection, _cursor, statement, _parameters, _context, _many):
        normalized = " ".join(statement.lower().split())
        if normalized.startswith("select ") and re.search(r"\bfrom sample\b", normalized):
            statements.append(normalized)

    return statements


@pytest.mark.parametrize("source_status,expected", [
    ("Yes", "pass"), ("No", "fail"), ("SNV数量偏低", "warn"), ("", "unknown"),
])
def test_batch_qc_status_reads_only_status_and_preserves_selected_aliases(
    database, settings, tmp_path, monkeypatch, source_status, expected,
):
    _, sessions = database
    batch = _qc_file(tmp_path, "SYN_QC_STATUS", source_status)
    monkeypatch.setattr(wgs_sample_projection, "_batch_root", lambda **_: batch)

    def forbidden_enrichment(*_args, **_kwargs):
        raise AssertionError("status-only projection scanned rich QC inputs")

    for name in ("_qc_contexts", "_variant_count", "_multi_qc_row"):
        monkeypatch.setattr(wgs_sample_projection, name, forbidden_enrichment)
    monkeypatch.setattr(wgs_sample_projection.hashlib, "sha256", forbidden_enrichment)
    with sessions() as session:
        run = _run("SYN_QC_STATUS")
        session.add(run)
        session.add_all([
            Sample(analysis_id=run.analysis_id, sample_id="SYN_SELECTED", qc_status="pass",
                   metadata_json={"data_id": "SYN_DATA-WGS", "selection_decision": "selected", "selection_attempt": 1}),
            Sample(analysis_id=run.analysis_id, sample_id="SYN_EXCLUDED", qc_status="fail",
                   metadata_json={"selection_decision": "excluded", "selection_attempt": 1}),
            Sample(analysis_id=run.analysis_id, sample_id="SYN_STALE", qc_status="fail",
                   metadata_json={"selection_decision": "selected", "selection_attempt": 2}),
        ])
        session.commit()
        assert wgs_sample_projection.get_wgs_batch_qc_status(
            session=session, settings=settings, run=run,
        ) == expected


def test_runs_page_reuses_one_selected_sample_query_for_all_qc_statuses(
    database, settings, tmp_path, monkeypatch,
):
    engine, sessions = database
    roots = {"SYN_LIST_PASS": _qc_file(tmp_path, "SYN_LIST_PASS", "Yes"),
             "SYN_LIST_FAIL": _qc_file(tmp_path, "SYN_LIST_FAIL", "No")}
    monkeypatch.setattr(wgs_sample_projection, "_batch_root", lambda run, **_: roots.get(run.analysis_id))
    with sessions.begin() as session:
        for analysis_id in ("SYN_LIST_PASS", "SYN_LIST_FAIL", "SYN_LIST_FALLBACK"):
            session.add(_run(analysis_id))
            session.add(Sample(analysis_id=analysis_id, sample_id="SYN_SELECTED", qc_status="warn",
                               metadata_json={"data_id": "SYN_DATA-WGS"}))
    statements = _sample_selects(engine)
    with sessions() as session:
        payload = list_runs(
            session=session, pipeline="wgs", limit=20,
            qc_status_projectors={"wgs": partial(
                pipeline_registry_service._project_wgs_dashboard_qc_statuses, settings=settings,
            )},
        )
    assert {row["analysis_id"]: (row["sample_count"], row["qc_status"]) for row in payload["items"]} == {
        "SYN_LIST_PASS": (1, "pass"), "SYN_LIST_FAIL": (1, "fail"), "SYN_LIST_FALLBACK": (1, "warn"),
    }
    assert len(statements) == 1, statements


def test_wgs_workspace_reuses_selected_samples_for_qc(database, settings, monkeypatch):
    engine, sessions = database
    monkeypatch.setattr(wgs_sample_projection, "_batch_root", lambda **_: None)
    with sessions.begin() as session:
        session.add(_run("SYN_WORKSPACE_QC"))
        session.add(Sample(analysis_id="SYN_WORKSPACE_QC", sample_id="SYN_SELECTED", qc_status="warn"))
    statements = _sample_selects(engine)
    with sessions() as session:
        run = session.scalar(select(AnalysisRun))
        result = build_wgs_workspace(session=session, run=run,
            run_payload={"analysis_id": run.analysis_id}, settings=settings)
    assert result["summary"]["sample_count"] == 1
    assert result["summary"]["batch_qc_status"] == "warn"
    assert len(statements) == 1, statements


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_workspace_read_opens_one_session_and_fetches_run_once(
    database, settings, monkeypatch, pipeline,
):
    engine, sessions = database
    analysis_id = f"SYN_WORKSPACE_{pipeline.upper()}"
    with sessions.begin() as session:
        session.add(_run(analysis_id, pipeline))
        session.add(Sample(analysis_id=analysis_id, sample_id="SYN_SELECTED"))
    opened = []
    run_queries = []

    def session_factory():
        opened.append(True)
        return sessions()

    @event.listens_for(engine, "before_cursor_execute")
    def observe(_connection, _cursor, statement, _parameters, _context, _many):
        normalized = " ".join(statement.lower().split())
        if normalized.startswith("select analysis_run."):
            run_queries.append(normalized)

    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_airflow_client", lambda: None)
    monkeypatch.setattr(wgs_sample_projection, "_batch_root", lambda **_: None)
    result = main.run_workspace(analysis_id)
    assert result["run"]["analysis_id"] == analysis_id
    assert result["run"]["sample_count"] == result["summary"]["sample_count"] == 1
    assert len(opened) == 1
    assert len(run_queries) == 1, run_queries


@pytest.fixture
def gatk_ready(database, settings):
    _, sessions = database
    settings.gatk_execution_enabled = True
    with sessions() as session:
        run = _run("SYN_GATK_CLEANUP", "gatk")
        session.add(run)
        for stage in ("step5_download", "step6_materialize"):
            session.add(PipelineStageExecution(
                execution_id=f"{run.analysis_id}-{stage}", pipeline_name="gatk",
                analysis_id=run.analysis_id, attempt=1, stage_code=stage, generation=1,
                status="success", request_hash="a" * 64, receipt_hash="b" * 64, release_id="gatk@synthetic",
            ))
        session.commit()
        from pathlib import Path
        root = Path(settings.gatk_runtime_request_root).parent
        binding = root / "runs" / run.analysis_id / "attempt-1" / "batch-binding.json"
        binding.parent.mkdir(parents=True)
        binding.write_text(json.dumps({"schema_version": "gatk-runtime.batch-binding.v1",
            "analysis_id": run.analysis_id, "attempt": 1, "run_id": run.dag_run_id}))
        bundle = binding.parent / "cce"
        bundle.mkdir()
        (bundle / "BATCH_RUNTIME.yaml").write_text(json.dumps({"identity": {
            "project": "SYNTHETIC", "batch": run.analysis_id, "run_id": run.dag_run_id}}))
        for filename in ("cleanup-job.yaml", "Step7_cleanup_sfs.sh", "cce_batch_runtime.py"):
            (bundle / filename).write_text("# synthetic\n")
        prepare = {"analysis_id": run.analysis_id, "attempt": 1,
                   "project_name": "SYNTHETIC", "batch": run.analysis_id}
        prepare["request_hash"] = gatk_step7_service._canonical_hash(prepare)
        prepare_path = root / "requests" / run.analysis_id / "attempt-1" / "prepare.request.json"
        prepare_path.parent.mkdir(parents=True)
        prepare_path.write_text(json.dumps(prepare))
        yield session, run, settings, bundle


def test_gatk_public_detail_does_not_scan_frozen_bundle_or_runtime_terminal(gatk_ready, monkeypatch):
    session, run, settings, _ = gatk_ready
    session.add(WgsMaintenanceAction(action_id="synthetic-failed-cleanup", analysis_id=run.analysis_id,
        attempt=1, action_type=gatk_step7_service.ACTION, generation=1, status="failed",
        requested_by="synthetic-admin", linkage_group="sfs", target_snapshot_json={},
        error_message="synthetic cleanup failure"))
    session.commit()
    reads = []
    terminals = []
    safe_bytes = gatk_step7_service._safe_bytes
    runtime_terminal = gatk_step7_service._runtime_terminal

    def observe_bytes(path, root):
        reads.append(path.name)
        return safe_bytes(path, root)

    def observe_terminal(*args):
        terminals.append(True)
        return runtime_terminal(*args)

    monkeypatch.setattr(gatk_step7_service, "_safe_bytes", observe_bytes)
    monkeypatch.setattr(gatk_step7_service, "_runtime_terminal", observe_terminal)
    result = pipeline_registry_service._project_gatk_run_detail(session=session, settings=settings, run=run)
    assert result["step7_cleanup"]["latest_action"]["status"] == "failed"
    assert result["step7_cleanup"]["latest_action"]["error_message"] == "synthetic cleanup failure"
    assert reads == []
    assert terminals == []


def test_gatk_default_capability_and_cleanup_post_still_verify_frozen_identity(gatk_ready):
    session, run, settings, bundle = gatk_ready
    (bundle / "BATCH_RUNTIME.yaml").write_text(json.dumps({"identity": {
        "project": "SYNTHETIC", "batch": "SYN_WRONG_BATCH", "run_id": run.dag_run_id}}))
    result = gatk_step7_service.capability(session=session, settings=settings, run=run)
    assert result["available"] is False
    assert result["reason"] == "approved_runtime_identity_mismatch"
    with pytest.raises(ValueError, match="approved_runtime_identity_mismatch"):
        gatk_step7_service.request_cleanup(
            session=session, settings=settings, airflow_client=None, analysis_id=run.analysis_id,
            batch_confirmation=run.analysis_id, requested_by="synthetic-admin",
        )
    assert session.scalar(select(func.count()).select_from(WgsMaintenanceAction)) == 0


def test_execution_dispatch_read_does_not_create_or_commit_missing_claim(database, settings):
    _, sessions = database
    with sessions() as session:
        run = _run("SYN_DISPATCH_READ")
        session.add(run)
        session.commit()
        commits = []
        event.listen(session, "after_commit", lambda _session: commits.append(True))
        projected = project_execution_dispatch(session=session, settings=settings, run=run)
        assert commits == []
        assert projected is None
        assert session.scalar(select(func.count()).select_from(WgsExecutionDispatch)) == 0
        # The operation-owned initializer still creates the exact claim explicitly.
        claim = ensure_execution_dispatch(session=session, run=run)
        session.commit()
        assert claim.analysis_id == run.analysis_id
        assert session.scalar(select(func.count()).select_from(WgsExecutionDispatch)) == 1
