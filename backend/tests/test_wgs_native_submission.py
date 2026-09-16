from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base
from app.wgs_submission_service import create_and_submit_run, create_automatic_wgs_run
from test_wgs_submission_service import RecordingAirflow


@pytest.mark.parametrize("automatic", [False, True])
def test_native_submission_is_opt_in_and_never_upgrades_existing_run(tmp_path, automatic):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = SimpleNamespace(
        wgs_project_catalog_path=str(Path(__file__).parents[2] / "config/wgs_projects.yaml"),
        wgs_release_catalog_path=str(Path(__file__).parents[2] / "config/wgs_releases.yaml"),
        host_results_root=str(tmp_path / "results"), container_shared_root=str(tmp_path / "shared"),
        wgs_native_prepare_enabled=False, wgs_contract_v2_enabled=True,
    )
    create = create_automatic_wgs_run if automatic else create_and_submit_run
    airflow = RecordingAirflow()
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        kwargs = dict(session=session, settings=settings, airflow_client=airflow,
                      username="operator", project_id="WGS_Clinical", platform="T7",
                      batch="20260901A", fastq_root_id="T7_Fastq")
        old = create(**kwargs)
        settings.wgs_native_prepare_enabled = True
        assert create(**kwargs)["analysis_id"] == old["analysis_id"]
        old_run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == old["analysis_id"]))
        assert "native_prepare_contract" not in old_run.params_json
        fresh = create(**{**kwargs, "batch": "20260902A"})
        new_run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == fresh["analysis_id"]))
        assert new_run.params_json["native_prepare_contract"] == 1
        frozen = new_run.params_json.get("prepare_execution")
        assert bool(frozen) == automatic
        if automatic:
            assert frozen["mode"] == "cce" and frozen["target"] == "cce"
            assert airflow.calls[-1]["conf"]["params"]["prepare_execution"] == frozen
        assert new_run.execution_mode == "cce"
        assert len(airflow.calls) == 2
