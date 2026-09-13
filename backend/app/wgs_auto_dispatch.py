from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, text

from app.models import AnalysisRun, WgsIntakeBatch, WgsInputSnapshot
from app.wgs_platform_service import submit_wgs_run
from app.wgs_run_projection import wgs_params_match_batch
from app.wgs_submission_service import create_automatic_wgs_run
from app.wgs_project_catalog import load_wgs_projects
from pathlib import Path
import stat
from app.wgs_t7_intake import inspect_chip_directory


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
        samplelist = row.discovery_mode == "samplelist_batches"
        if samplelist and not getattr(settings, "wgs_intake_scan_enabled", False):
            continue
        # Linked ownership is authoritative even after failure/cancellation.
        if row.analysis_id:
            linked = next((run for run in runs if run.analysis_id == row.analysis_id), None)
            if (samplelist and linked is not None and linked.status == "created"
                    and not _compatible_run_root(session, row, linked, settings)):
                _ownership_review(session, row)
                continue
            if (linked is not None and linked.status == "created"
                    and dict(linked.params_json or {}).get("submission_mode") == "auto_dispatch"
                    and (not samplelist or _bound_ready(row, settings))):
                submit_wgs_run(session=session, airflow_client=airflow_client, analysis_id=linked.analysis_id)
            result["already_registered"] = int(result["already_registered"]) + 1
            result["analysis_ids"].append(row.analysis_id)
            continue
        if samplelist and not _bound_ready(row, settings):
            continue
        candidates = [run for run in runs if wgs_params_match_batch(run.params_json, row.sequencing_batch)]
        if samplelist:
            scoped = [run for run in candidates if dict(run.params_json or {}).get("project_id") == row.project_id
                      and dict(run.params_json or {}).get("platform") == row.platform_id]
            unknown = [run for run in candidates if not dict(run.params_json or {}).get("project_id")
                       or not dict(run.params_json or {}).get("platform")]
            if len(scoped) > 1 or unknown:
                row.state, row.reason_code = "needs_review", "ambiguous_analysis_owner"
                session.commit()
                continue
            existing = scoped[0] if scoped else None
        else:
            existing = _find_batch_run(runs, row.sequencing_batch)
        if existing is not None:
            if samplelist and not _compatible_run_root(session, row, existing, settings):
                _ownership_review(session, row)
                continue
            if not _link_intake_row(session, row, existing.analysis_id):
                _ownership_review(session, row)
                continue
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
        claimed = False
        def claim_actual_run(run):
            nonlocal claimed
            if not _bound_ready(row, settings) or not _compatible_run_root(session, row, run, settings):
                return False
            claimed = _link_intake_row(session, row, run.analysis_id, commit=False)
            return claimed
        payload = create_automatic_wgs_run(
            session=session,
            settings=settings,
            airflow_client=airflow_client,
            username="wgs-intake-scanner",
            project_id=row.project_id if samplelist else "WGS_Clinical",
            platform=row.platform_id if samplelist else "T7",
            batch=row.sequencing_batch,
            fastq_root_id=row.root_id if samplelist else "T7_Fastq",
            use_reference="all",
            **({"before_submit_guard": claim_actual_run} if samplelist else {}),
        )
        analysis_id = str(payload["analysis_id"])
        if samplelist and not claimed:
            _ownership_review(session, row)
            continue
        if not _link_intake_row(session, row, analysis_id):
            _ownership_review(session, row)
            continue
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


def _link_intake_row(session, row: WgsIntakeBatch, analysis_id: str, *, commit: bool = True) -> bool:
    if row.analysis_id is not None:
        return row.analysis_id == analysis_id
    # Lock the retained run identity before the ownership query. A missing owner
    # row alone cannot provide a row lock for competing Intake claims.
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id).with_for_update())
    if run is None:
        return False
    owner = session.scalar(
        select(WgsIntakeBatch).where(
            WgsIntakeBatch.analysis_id == analysis_id,
            WgsIntakeBatch.id != row.id,
        )
    )
    if owner is None:
        row.analysis_id = analysis_id
        row.updated_at = datetime.now(timezone.utc)
        session.flush()
        if commit:
            session.commit()
        return True
    return False


def _ownership_review(session, row):
    row.state = "needs_review"
    row.reason_code = "incompatible_analysis_owner"
    row.last_error = row.reason_code
    session.commit()


def _compatible_run_root(session, row, run, settings):
    params = dict(run.params_json or {})
    if (params.get("project_id") != row.project_id or params.get("platform") != row.platform_id
            or params.get("sequencing_batch") != row.sequencing_batch):
        return False
    try:
        project = next(item for item in load_wgs_projects(settings.wgs_project_catalog_path) if item.project_id == row.project_id)
        expected_root = project.fastq_root(row.root_id)["node200_path"]
    except (OSError, ValueError, StopIteration):
        return False
    snapshot = session.scalar(select(WgsInputSnapshot).where(
        WgsInputSnapshot.analysis_id == run.analysis_id, WgsInputSnapshot.attempt == run.attempt))
    return (params.get("fastq_root") == expected_root and params.get("fq_path") == expected_root
            and snapshot is not None and snapshot.fq_path == expected_root)


def _bound_ready(row, settings):
    if not (row.source_path and row.chip_id and row.bound_directory_identity
            and row.project_id and row.platform_id and row.root_id and row.eligible_fingerprint):
        return False
    try:
        project = next(item for item in load_wgs_projects(settings.wgs_project_catalog_path) if item.project_id == row.project_id)
        project.platform(row.platform_id)
        root = Path(project.fastq_root(row.root_id)["control_plane_path"])
        path = Path(row.source_path)
        if path.parent != root or path.name != row.chip_id or any(part.is_symlink() for part in (path, *path.parents)):
            return False
        value = path.lstat()
        if not stat.S_ISDIR(value.st_mode) or f"{value.st_dev}:{value.st_ino}" != row.bound_directory_identity:
            return False
        observation = inspect_chip_directory(path, sequencing_batch=row.sequencing_batch)
        return (observation.barcode_present and observation.eligible_pair_count > 0
                and observation.pair_issue_count == 0 and observation.fingerprint == row.eligible_fingerprint)
    except (OSError, ValueError, StopIteration):
        return False


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
