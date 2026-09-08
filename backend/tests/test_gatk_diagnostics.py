from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.diagnostics_service import (
    get_gatk_run_log,
    list_gatk_run_artifacts,
    list_gatk_run_logs,
)
from app.models import AnalysisRun, Base


def test_gatk_diagnostics_expose_only_registered_safe_entries(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    analysis_id = "GATK_20260908_120000_A1B2C3"
    request_root = tmp_path / "runtime" / "requests"
    attempt_request = request_root / analysis_id / "attempt-1"
    attempt_run = request_root.parent / "runs" / analysis_id / "attempt-1"
    evidence = tmp_path / "evidence" / analysis_id / "attempt-1"
    attempt_request.mkdir(parents=True)
    attempt_run.mkdir(parents=True)
    (evidence / "mirror").mkdir(parents=True)
    (attempt_request / "step3_monitor.worker.log").write_text(
        "worker line\n", encoding="utf-8"
    )
    (evidence / "mirror" / "analysis.log").write_text(
        "analysis line\n", encoding="utf-8"
    )
    (attempt_run / "prepare.receipt.json").write_text("{}\n", encoding="utf-8")
    (attempt_run / "batch-binding.json").write_text("{}\n", encoding="utf-8")
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="gatk",
                dag_id="bio_gatk",
                workdir=str(attempt_run),
                attempt=1,
                params_json={},
            )
        )
        session.commit()
        settings = SimpleNamespace(
            gatk_runtime_request_root=str(request_root),
            gatk_evidence_root=str(tmp_path / "evidence"),
        )
        logs = list_gatk_run_logs(
            session=session, analysis_id=analysis_id, settings=settings
        )
        artifacts = list_gatk_run_artifacts(
            session=session, analysis_id=analysis_id, settings=settings
        )
        analysis = next(item for item in logs["items"] if item["source"] == "master_analysis")
        content = get_gatk_run_log(
            session=session,
            analysis_id=analysis_id,
            stream="stdout",
            tail=20,
            settings=settings,
            key=analysis["key"],
        )

    assert content["lines"] == ["analysis line"]
    assert content["path"] == "evidence/mirror/analysis.log"
    assert all(str(tmp_path) not in str(item) for item in logs["items"])
    assert {item["key"] for item in artifacts["items"]} == {
        "gatk_prepare_receipt",
        "gatk_batch_binding",
    }
    assert all(str(tmp_path) not in str(item) for item in artifacts["items"])
