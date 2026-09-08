from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, Sample, WgsIntakeBatch
from app.dashboard_service import get_dashboard_overview
from app.wgs_dashboard_attention import project_wgs_dashboard_attention
from app.wgs_platform_service import masked_order_number


def make_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_order_number_mask_is_fixed_and_never_returns_the_source_value() -> None:
    assert masked_order_number("ORDER-12345678") == "****5678"
    assert masked_order_number("123") == "****"
    assert masked_order_number("") is None


def test_wgs_dashboard_attention_is_actionable_and_privacy_safe() -> None:
    sessions = make_sessionmaker()
    now = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    old = now - timedelta(days=3)
    runs = [
        AnalysisRun(
            analysis_id="WGS_FAILED",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            status="failed",
            workdir="/private/failed",
            params_json={"batch_no": "20260901A", "project_name": "WGS_Clinical"},
            created_at=old,
            pipeline_finished_at=old,
        ),
        AnalysisRun(
            analysis_id="WGS_RERUN",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            status="success",
            workdir="/private/rerun",
            params_json={"batch_no": "20260902A", "project_name": "WGS_Clinical"},
            mode="rerun_failed",
            attempt=2,
            parent_analysis_id="WGS_PARENT",
            created_at=old,
            pipeline_finished_at=old,
        ),
        AnalysisRun(
            analysis_id="WGS_OTHER",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            status="success",
            workdir="/private/other",
            params_json={"batch_no": "20260903A", "project_name": "WGS_Clinical"},
            created_at=old,
            pipeline_finished_at=old,
        ),
    ]
    with sessions.begin() as session:
        session.add_all(runs)
        session.add_all(
            [
                Sample(
                    analysis_id="WGS_RERUN",
                    sample_id="S1",
                    family_id="FAM-PRIVATE",
                    status="success",
                    qc_status="fail",
                    metadata_json={
                        "estimated_report_date": "2026-09-05",
                        "order_number_masked": "****5678",
                    },
                ),
                Sample(
                    analysis_id="WGS_OTHER",
                    sample_id="S2",
                    family_id="FAM-PRIVATE",
                    status="success",
                    qc_status="pass",
                    metadata_json={},
                ),
            ]
        )
        session.add(
            WgsIntakeBatch(
                source_path="/private/t7/2244th_20260904A_SECRET",
                chip_id="2244th_20260904A_PUBLIC",
                sequencing_batch="20260904A",
                state="needs_review",
                excluded_addon_pair_count=2,
                pair_issue_count=1,
                last_scanned_at=now,
            )
        )

    with sessions() as session:
        items = project_wgs_dashboard_attention(
            session=session,
            runs=session.query(AnalysisRun).all(),
            since=now - timedelta(days=7),
            now=now,
        )

    categories = {item["category"] for item in items}
    assert {
        "workflow_failed",
        "qc_failed",
        "intake_addon_excluded",
        "intake_pair_issue",
        "reanalysis",
        "duplicate_family",
        "sfs_cleanup_overdue",
        "report_delivery_overdue",
    }.issubset(categories)
    rendered = repr(items)
    assert "FAM-PRIVATE" not in rendered
    assert "/private/" not in rendered
    assert "ORDER-12345678" not in rendered


def test_dashboard_attention_respects_the_selected_pipeline() -> None:
    sessions = make_sessionmaker()
    calls: list[str] = []

    def wgs_projector(**_kwargs):
        calls.append("wgs")
        return [{"category": "should_not_render"}]

    with sessions() as session:
        payload = get_dashboard_overview(
            session=session,
            pipeline="gatk",
            period="7d",
            deployed_pipelines=("wgs", "gatk"),
            attention_projectors={"wgs": wgs_projector},
        )

    assert calls == []
    assert payload["attention_items"] == []


def test_dashboard_attention_failure_does_not_break_overview() -> None:
    sessions = make_sessionmaker()

    def failing_projector(**_kwargs):
        raise RuntimeError("projection unavailable")

    with sessions() as session:
        payload = get_dashboard_overview(
            session=session,
            pipeline="wgs",
            period="7d",
            deployed_pipelines=("wgs",),
            attention_projectors={"wgs": failing_projector},
        )

    assert payload["attention_items"] == []
    assert payload["totals"]["runs"] == 0
