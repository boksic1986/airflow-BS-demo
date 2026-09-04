from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, text

from app.models import AnalysisRun, WgsIntakeBatch
from app.wgs_platform_service import submit_wgs_run
from app.wgs_run_projection import wgs_params_match_batch
from app.wgs_submission_service import create_automatic_wgs_run


DISPATCH_ADVISORY_LOCK_ID = 743_701_143_830


def dispatch_ready_wgs_intake(
    *, session, settings, airflow_client, now: datetime | None = None, limit: int = 20
) -> dict[str, object]:
    """Submit newly-ready T7 batches exactly once through the normal WGS DAG."""
    result: dict[str, object] = {
        "enabled": bool(getattr(settings, "wgs_auto_dispatch_enabled", False)),
        "examined": 0,
        "submitted": 0,
        "already_registered": 0,
        "baseline_skipped": 0,
        "analysis_ids": [],
    }
    if not result["enabled"]:
        return result
    not_before = _activation_watermark(settings)
    current = _aware(now or datetime.now(timezone.utc))
    if not _acquire_dispatch_lock(session):
        result["lock_busy"] = True
        return result

    rows = session.scalars(
        select(WgsIntakeBatch)
        .where(WgsIntakeBatch.state == "ready")
        .order_by(WgsIntakeBatch.ready_at.asc(), WgsIntakeBatch.id.asc())
        .limit(max(1, min(int(limit), 100)))
        .with_for_update(skip_locked=True)
    ).all()
    runs = session.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.pipeline_name == "wgs")
        .order_by(AnalysisRun.created_at.desc())
    ).all()

    for row in rows:
        result["examined"] = int(result["examined"]) + 1
        existing = _find_batch_run(runs, row.sequencing_batch)
        if existing is not None:
            _link_intake_row(session, row, existing.analysis_id)
            if (
                existing.status == "created"
                and dict(existing.params_json or {}).get("submission_mode") == "auto_dispatch"
            ):
                submit_wgs_run(
                    session=session,
                    airflow_client=airflow_client,
                    analysis_id=existing.analysis_id,
                )
            result["already_registered"] = int(result["already_registered"]) + 1
            cast_ids = result["analysis_ids"]
            assert isinstance(cast_ids, list)
            cast_ids.append(existing.analysis_id)
            continue
        ready_at = _aware(row.ready_at or row.first_seen_at)
        if ready_at < not_before:
            result["baseline_skipped"] = int(result["baseline_skipped"]) + 1
            continue
        payload = create_automatic_wgs_run(
            session=session,
            settings=settings,
            airflow_client=airflow_client,
            username="wgs-intake-scanner",
            project_id="WGS_Clinical",
            platform="T7",
            batch=row.sequencing_batch,
            fastq_root_id="T7_Fastq",
            use_reference="all",
        )
        analysis_id = str(payload["analysis_id"])
        _link_intake_row(session, row, analysis_id)
        session.commit()
        result["submitted"] = int(result["submitted"]) + 1
        cast_ids = result["analysis_ids"]
        assert isinstance(cast_ids, list)
        cast_ids.append(analysis_id)
        created_run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        if created_run is not None:
            runs.insert(0, created_run)

    result["evaluated_at"] = current.isoformat()
    return result


def _find_batch_run(runs: list[AnalysisRun], batch: str) -> AnalysisRun | None:
    for run in runs:
        if wgs_params_match_batch(run.params_json, batch):
            return run
    return None


def _link_intake_row(session, row: WgsIntakeBatch, analysis_id: str) -> None:
    owner = session.scalar(
        select(WgsIntakeBatch).where(
            WgsIntakeBatch.analysis_id == analysis_id,
            WgsIntakeBatch.id != row.id,
        )
    )
    if owner is None:
        row.analysis_id = analysis_id
        row.updated_at = datetime.now(timezone.utc)
        session.commit()


def _activation_watermark(settings) -> datetime:
    value = str(getattr(settings, "wgs_auto_dispatch_not_before", "") or "").strip()
    if not value:
        raise ValueError(
            "WGS_AUTO_DISPATCH_NOT_BEFORE is required when automatic dispatch is enabled"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("WGS_AUTO_DISPATCH_NOT_BEFORE must be an ISO-8601 timestamp") from exc
    return _aware(parsed)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _acquire_dispatch_lock(session) -> bool:
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return True
    return bool(
        session.scalar(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": DISPATCH_ADVISORY_LOCK_ID},
        )
    )
