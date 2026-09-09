from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, Sample
from app.wgs_platform_service import sync_prepare_handoff_decisions


def test_analysis_handoff_imports_safe_pending_reason_without_clinical_fields() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as session:
        run = AnalysisRun(
            analysis_id="WGS_20260909_010203_A1B2C3",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            mode="new",
            execution_mode="cce",
            attempt=1,
            status="running",
            sample_sheet_path="/runs/sampleinfo.tsv",
            workdir="/runs/WGS_20260909_010203_A1B2C3",
            params_json={},
            submitted_by="operator",
        )
        session.add(run)
        session.flush()

        imported = sync_prepare_handoff_decisions(
            session=session,
            run=run,
            receipt={
                "schema_version": "wgs.prepare-analysis.receipt.v1",
                "selected": [{
                    "sample_id": "S1",
                    "family_id": "F1",
                    "data_id": "S1-WGS",
                    "family_relation": "proband",
                    "sample_type": "blood",
                    "sex": "female",
                    "decision": "selected",
                    "reason_code": "selected",
                    "reason_message": "",
                }],
                "pending": [{
                    "sample_id": "S2",
                    "family_id": "F2",
                    "data_id": "S2-WGS",
                    "family_relation": "proband",
                    "sample_type": "blood",
                    "sex": "male",
                    "decision": "pending",
                    "reason_code": "family_incomplete",
                    "reason_message": "Family members are incomplete",
                }],
            },
        )

        rows = session.scalars(select(Sample).order_by(Sample.sample_id)).all()
        assert imported == 2
        assert [row.status for row in rows] == ["running", "pending"]
        assert rows[1].metadata_json["status_reason"] == "Family members are incomplete"
        assert "patient_name" not in rows[1].metadata_json
