from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Base, WgsMaintenanceAction
from app.pipeline_registry_service import ADAPTERS
from app.run_service import list_runs


def test_gatk_release_list_uses_latest_cleanup_in_current_attempt():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for name, attempt in (("released", 1), ("new_attempt", 2), ("pending", 1)):
            session.add(AnalysisRun(analysis_id=name, pipeline_name="gatk",
                dag_id="bio_gatk", status="success", execution_mode="cce",
                attempt=attempt, workdir=f"/runs/{name}", params_json={}))
        session.flush()
        for name, generation, status in (("released", 1, "failed"),
                ("released", 2, "success"), ("new_attempt", 1, "success"),
                ("pending", 1, "queued")):
            session.add(WgsMaintenanceAction(action_id=f"{name}-{generation}",
                analysis_id=name, attempt=1, generation=generation,
                action_type="gatk_cleanup_step7_sfs", status=status,
                requested_by="operator"))
        session.commit()
        payload = list_runs(session=session, pipeline="gatk",
            lifecycle_projectors={"gatk": ADAPTERS["gatk"].project_dashboard_lifecycles})
    rows = {row["analysis_id"]: row for row in payload["items"]}
    assert rows["released"]["lifecycle"] is not None
    assert rows["released"]["lifecycle"]["cloud_release"]["status"] == "success"
    assert rows["new_attempt"]["lifecycle"]["cloud_release"]["status"] == "not_started"
    assert rows["pending"]["lifecycle"]["cloud_release"]["status"] == "pending"
    assert rows["released"]["lifecycle"]["workflow"]["status"] == "success"
    assert rows["released"]["lifecycle"]["downstream_release"]["status"] == "not_started"
