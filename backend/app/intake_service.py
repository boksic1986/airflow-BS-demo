from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.input_scanner import FastqCandidate, scan_fastq_candidates, scan_nipt_batch_candidates
from app.intake_config import load_intake_config
from app.models import AnalysisRun, IntakeDiscovery
from app.pgta_manifest_intake import PgtaManifestFailure, scan_pgta_manifest_request_results
from app.pipeline_config_service import get_pipeline_config_template, validate_pipeline_config
from app.run_service import create_nipt_docker_run, create_pgta_run, submit_run_to_airflow


@dataclass(frozen=True)
class BatchSnapshot:
    pipeline: str
    root_path: str
    batch_id: str
    source_dir: str
    items: list[FastqCandidate]
    fingerprint: str
    file_count: int
    total_bytes: int
    max_mtime: datetime | None
    run_rawdata_root: str | None = None
    project_name: str | None = None
    submitted_by: str | None = None
    source_manifest_path: str | None = None


@dataclass(frozen=True)
class IntakeScanFailure:
    pipeline: str
    root_path: str
    batch_id: str
    fingerprint: str
    source_manifest_path: str
    message: str


def scan_and_submit_intake(
    *,
    session: Session,
    settings,
    airflow_client,
    pipelines: list[str],
    bootstrap: bool = False,
    max_samples: int = 200,
) -> dict[str, object]:
    supported = {"pgta", "nipt_docker"}
    normalized_pipelines = [pipeline for pipeline in pipelines if pipeline in supported]
    if not normalized_pipelines:
        raise ValueError("pipelines must include pgta or nipt_docker.")

    items: list[dict[str, object]] = []
    for pipeline in normalized_pipelines:
        snapshots, errors = _scan_pipeline(settings=settings, pipeline=pipeline, max_samples=max_samples)
        for error in errors:
            items.append(_record_scan_error(session=session, error=error))
        for snapshot in snapshots:
            items.append(
                _record_snapshot(
                    session=session,
                    settings=settings,
                    airflow_client=airflow_client,
                    snapshot=snapshot,
                    bootstrap=bootstrap,
                )
            )
    return {"items": items}


def preview_intake_scan(
    *,
    session: Session,
    settings,
    pipelines: list[str],
    bootstrap: bool = False,
    max_samples: int = 200,
) -> dict[str, object]:
    supported = {"pgta", "nipt_docker"}
    normalized_pipelines = [pipeline for pipeline in pipelines if pipeline in supported]
    if not normalized_pipelines:
        raise ValueError("pipelines must include pgta or nipt_docker.")

    items: list[dict[str, object]] = []
    for pipeline in normalized_pipelines:
        snapshots, errors = _scan_pipeline(settings=settings, pipeline=pipeline, max_samples=max_samples)
        items.extend(_preview_scan_error(error) for error in errors)
        for snapshot in snapshots:
            items.append(_preview_snapshot(session=session, settings=settings, snapshot=snapshot, bootstrap=bootstrap))
    return {"items": items, "summary": _preview_summary(items)}


def list_intake_status(
    *,
    session: Session,
    pipeline: str | None = None,
    state: str | None = None,
    keyword: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, object]:
    query = select(IntakeDiscovery)
    if pipeline:
        query = query.where(IntakeDiscovery.pipeline_name == pipeline)
    if state:
        query = query.where(_intake_state_condition(state))
    if keyword and keyword.strip():
        keyword_value = keyword.strip().lower()
        query = query.where(
            or_(
                func.lower(IntakeDiscovery.batch_id).contains(keyword_value, autoescape=True),
                func.lower(func.coalesce(IntakeDiscovery.analysis_id, "")).contains(
                    keyword_value,
                    autoescape=True,
                ),
            )
        )

    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    page = session.scalars(
        query.order_by(IntakeDiscovery.last_seen_at.desc(), IntakeDiscovery.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [_row_payload(row) for row in page],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _intake_state_condition(state: str):
    ready = IntakeDiscovery.ready_state
    submit = IntakeDiscovery.submit_state
    if state == "error":
        return or_(ready == "error", submit == "error")
    if state == "disabled":
        return and_(ready != "error", submit != "error", or_(ready == "disabled", submit == "disabled"))
    if state == "submitted":
        return and_(ready.notin_(["error", "disabled"]), submit == "submitted")
    if state == "bootstrap":
        return and_(ready.notin_(["error", "disabled"]), submit == "bootstrap")
    if state == "ready":
        return and_(
            ready == "ready",
            submit.notin_(["submitted", "error", "disabled", "bootstrap"]),
        )
    return and_(
        ready == "observed",
        submit.notin_(["submitted", "error", "disabled", "bootstrap"]),
    )


def _scan_pipeline(
    *, settings, pipeline: str, max_samples: int
) -> tuple[list[BatchSnapshot], list[IntakeScanFailure]]:
    config = _load_config(settings)
    pipeline_config = config.pipelines.get(pipeline)
    intake = dict(pipeline_config.intake if pipeline_config else {})
    if pipeline == "pgta" and intake.get("mode") == "manifest_ready":
        inbox_root = str(intake.get("inbox_root") or "").strip()
        data_root = str(intake.get("data_root") or "").strip()
        if not inbox_root or not data_root:
            raise ValueError("PGT-A manifest intake requires inbox_root and data_root.")
        snapshots: list[BatchSnapshot] = []
        scan_result = scan_pgta_manifest_request_results(inbox_root=inbox_root, data_root=data_root)
        for request in scan_result.requests:
            if len(request.samples) > max_samples:
                raise ValueError(f"PGT-A manifest {request.request_id} exceeds max_samples={max_samples}.")
            source_dir = str((Path(data_root) / request.source_batch).resolve())
            snapshots.append(
                BatchSnapshot(
                    pipeline="pgta",
                    root_path=str(Path(inbox_root).resolve()),
                    batch_id=request.request_id,
                    source_dir=source_dir,
                    items=request.samples,
                    fingerprint=request.fingerprint,
                    file_count=len(request.samples) * 2,
                    total_bytes=sum(item.r1_size + item.r2_size for item in request.samples),
                    max_mtime=_max_mtime(request.samples),
                    run_rawdata_root=source_dir,
                    project_name=request.project_id,
                    submitted_by=request.operator,
                    source_manifest_path=request.manifest_path,
                )
            )
        return snapshots, [
            _manifest_scan_failure(error=error, inbox_root=inbox_root)
            for error in scan_result.errors
        ]
    roots = _roots_for_pipeline(settings, pipeline)
    snapshots: list[BatchSnapshot] = []
    for root in roots:
        if pipeline == "nipt_docker":
            result = scan_nipt_batch_candidates(rawdata_root=root, allowed_roots=roots, max_samples=max_samples)
        else:
            result = scan_fastq_candidates(rawdata_root=root, allowed_roots=roots, max_samples=max_samples)
        snapshots.extend(_group_scan_result(pipeline=pipeline, root_path=result.rawdata_root, items=result.items))
    return snapshots, []


def _manifest_scan_failure(*, error: PgtaManifestFailure, inbox_root: str) -> IntakeScanFailure:
    return IntakeScanFailure(
        pipeline="pgta",
        root_path=str(Path(inbox_root).resolve()),
        batch_id=error.request_id,
        fingerprint=error.fingerprint,
        source_manifest_path=error.manifest_path,
        message=error.message,
    )


def _record_scan_error(*, session: Session, error: IntakeScanFailure) -> dict[str, object]:
    row = session.scalar(
        select(IntakeDiscovery).where(
            IntakeDiscovery.pipeline_name == error.pipeline,
            IntakeDiscovery.root_path == error.root_path,
            IntakeDiscovery.batch_id == error.batch_id,
        )
    )
    now = datetime.now(timezone.utc)
    if row is None:
        row = IntakeDiscovery(
            pipeline_name=error.pipeline,
            root_path=error.root_path,
            batch_id=error.batch_id,
            fingerprint=error.fingerprint,
            file_count=0,
            total_bytes=0,
            ready_state="error",
            submit_state="error",
            source_manifest_path=error.source_manifest_path,
            last_error=error.message,
            stable_observation_count=0,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(row)
    else:
        row.fingerprint = error.fingerprint
        row.ready_state = "error"
        row.submit_state = "error"
        row.source_manifest_path = error.source_manifest_path
        row.last_error = error.message
        row.stable_observation_count = 0
        row.last_seen_at = now
    session.commit()
    return _row_payload(row, auto_submit_enabled=False, reason="manifest_validation_error")


def _preview_scan_error(error: IntakeScanFailure) -> dict[str, object]:
    return {
        "pipeline": error.pipeline,
        "root_path": error.root_path,
        "batch_id": error.batch_id,
        "fingerprint": error.fingerprint,
        "file_count": 0,
        "total_bytes": 0,
        "ready_state": "error",
        "submit_state": "error",
        "source_manifest_path": error.source_manifest_path,
        "last_error": error.message,
        "stable_observation_count": 0,
        "would_transition_to": "error",
        "would_create_run": False,
        "would_submit": False,
        "auto_submit_enabled": False,
        "reason": "manifest_validation_error",
    }


def _record_snapshot(
    *,
    session: Session,
    settings,
    airflow_client,
    snapshot: BatchSnapshot,
    bootstrap: bool,
) -> dict[str, object]:
    auto_submit_enabled = _auto_submit_enabled(settings, snapshot.pipeline)
    row = session.scalar(
        select(IntakeDiscovery).where(
            IntakeDiscovery.pipeline_name == snapshot.pipeline,
            IntakeDiscovery.root_path == snapshot.root_path,
            IntakeDiscovery.batch_id == snapshot.batch_id,
        )
    )
    now = datetime.now(timezone.utc)
    if row is None:
        row = IntakeDiscovery(
            pipeline_name=snapshot.pipeline,
            root_path=snapshot.root_path,
            batch_id=snapshot.batch_id,
            fingerprint=snapshot.fingerprint,
            file_count=snapshot.file_count,
            total_bytes=snapshot.total_bytes,
            max_mtime=snapshot.max_mtime,
            ready_state="observed",
            analysis_id=None,
            submit_state="bootstrap" if bootstrap else "not_submitted",
            source_manifest_path=snapshot.source_manifest_path,
            stable_observation_count=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(row)
        session.commit()
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="bootstrap_protected" if bootstrap else "new_batch_observed")

    if row.fingerprint != snapshot.fingerprint:
        if (
            snapshot.source_manifest_path
            and row.ready_state == "error"
            and row.submit_state == "error"
            and not row.analysis_id
        ):
            row.fingerprint = snapshot.fingerprint
            row.file_count = snapshot.file_count
            row.total_bytes = snapshot.total_bytes
            row.max_mtime = snapshot.max_mtime
            row.ready_state = "observed"
            row.submit_state = "not_submitted"
            row.source_manifest_path = snapshot.source_manifest_path
            row.stable_observation_count = 1
            row.last_error = None
            row.last_seen_at = now
            session.commit()
            return _row_payload(
                row,
                auto_submit_enabled=auto_submit_enabled,
                reason="corrected_manifest_observed",
            )
        if snapshot.source_manifest_path:
            row.ready_state = "error"
            row.submit_state = "error"
            row.source_manifest_path = snapshot.source_manifest_path
            row.last_error = (
                "READY manifest or resolved FASTQ fingerprint changed after its first observation; "
                "create a new request_id instead of modifying an observed request."
            )
            row.stable_observation_count = 0
            row.last_seen_at = now
            session.commit()
            return _row_payload(
                row,
                auto_submit_enabled=False,
                reason="manifest_changed_after_observation",
            )
        row.fingerprint = snapshot.fingerprint
        row.file_count = snapshot.file_count
        row.total_bytes = snapshot.total_bytes
        row.max_mtime = snapshot.max_mtime
        row.ready_state = "observed"
        row.analysis_id = None
        row.submit_state = "bootstrap" if bootstrap else "not_submitted"
        row.source_manifest_path = snapshot.source_manifest_path
        row.stable_observation_count = 1
        row.last_error = None
        row.last_seen_at = now
        session.commit()
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="fingerprint_changed")

    row.file_count = snapshot.file_count
    row.total_bytes = snapshot.total_bytes
    row.max_mtime = snapshot.max_mtime
    row.last_seen_at = now
    row.stable_observation_count = int(row.stable_observation_count or 0) + 1
    if row.submit_state in {"submitted", "bootstrap"} or bootstrap:
        session.commit()
        reason = "already_submitted" if row.submit_state == "submitted" else "bootstrap_protected"
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason=reason)

    stable_scans = _stable_scans(settings, snapshot.pipeline)
    if row.stable_observation_count < stable_scans:
        session.commit()
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="waiting_for_stable_scan")
    row.ready_state = "ready"
    if not auto_submit_enabled:
        session.commit()
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="auto_submit_disabled")

    analysis_id = str(row.analysis_id or "") if row.submit_state == "created" else ""
    if not analysis_id and snapshot.source_manifest_path:
        recovered = _find_manifest_run(session=session, snapshot=snapshot)
        if recovered is not None:
            analysis_id = recovered.analysis_id
            row.analysis_id = analysis_id
            row.submit_state = "submitted" if recovered.dag_run_id else "created"
            session.commit()
            if recovered.dag_run_id:
                return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="already_submitted")
    if not analysis_id:
        if snapshot.pipeline == "nipt_docker":
            run_mode = _auto_submit_param(settings, snapshot.pipeline, "run_mode") or "mount_smoke"
            created = create_nipt_docker_run(
                session=session,
                settings=settings,
                project_name=f"NIPT auto {snapshot.batch_id}",
                rawdata_root=snapshot.root_path,
                selected_samples=snapshot.items,
                run_mode=str(run_mode),
                cores=None,
                note="auto intake stable scan",
            )
        else:
            target = _auto_submit_param(settings, snapshot.pipeline, "target") or "metadata"
            created = create_pgta_run(
                session=session,
                settings=settings,
                project_name=snapshot.project_name or f"PGT-A auto {snapshot.batch_id}",
                target=str(target),
                rawdata_root=snapshot.run_rawdata_root or snapshot.root_path,
                selected_samples=snapshot.items,
                submitted_by=snapshot.submitted_by,
                note="auto intake stable scan",
                pipeline_config=_auto_pipeline_config(settings=settings, pipeline="pgta", snapshot=snapshot),
                intake_request_id=snapshot.batch_id,
                intake_fingerprint=snapshot.fingerprint,
                source_manifest_path=snapshot.source_manifest_path,
            )
        analysis_id = str(created["analysis_id"])
        row.analysis_id = analysis_id
        row.submit_state = "created"
        session.commit()

    submit_run_to_airflow(session=session, airflow_client=airflow_client, analysis_id=analysis_id, settings=settings)
    row.submit_state = "submitted"
    row.ready_state = "ready"
    row.last_seen_at = datetime.now(timezone.utc)
    session.commit()
    return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="auto_submitted")


def _preview_snapshot(*, session: Session, settings, snapshot: BatchSnapshot, bootstrap: bool) -> dict[str, object]:
    row = session.scalar(
        select(IntakeDiscovery).where(
            IntakeDiscovery.pipeline_name == snapshot.pipeline,
            IntakeDiscovery.root_path == snapshot.root_path,
            IntakeDiscovery.batch_id == snapshot.batch_id,
        )
    )
    auto_submit_enabled = _auto_submit_enabled(settings, snapshot.pipeline)
    existing_ready_state = row.ready_state if row else None
    existing_submit_state = row.submit_state if row else None
    existing_analysis_id = row.analysis_id if row else None
    fingerprint_changed = bool(row and row.fingerprint != snapshot.fingerprint)

    would_transition_to = "observed"
    would_create_run = False
    would_submit = False
    reason = "new_batch_observed"

    if bootstrap:
        reason = "bootstrap_protected"
    elif row is None:
        reason = "new_batch_observed"
    elif fingerprint_changed:
        reason = "fingerprint_changed"
    elif row.submit_state == "submitted":
        would_transition_to = row.ready_state
        reason = "already_submitted"
    elif row.submit_state == "bootstrap":
        would_transition_to = row.ready_state
        reason = "bootstrap_protected"
    else:
        would_transition_to = "ready"
        if auto_submit_enabled:
            would_create_run = row.analysis_id is None
            would_submit = True
            reason = "auto_submit_enabled"
        else:
            reason = "auto_submit_disabled"

    return {
        "pipeline": snapshot.pipeline,
        "root_path": snapshot.root_path,
        "batch_id": snapshot.batch_id,
        "source_dir": snapshot.source_dir,
        "fingerprint": snapshot.fingerprint,
        "file_count": snapshot.file_count,
        "total_bytes": snapshot.total_bytes,
        "max_mtime": snapshot.max_mtime.isoformat() if snapshot.max_mtime else None,
        "existing_ready_state": existing_ready_state,
        "existing_submit_state": existing_submit_state,
        "existing_analysis_id": existing_analysis_id,
        "would_transition_to": would_transition_to,
        "would_create_run": would_create_run,
        "would_submit": would_submit,
        "auto_submit_enabled": auto_submit_enabled,
        "reason": reason,
    }


def _group_scan_result(*, pipeline: str, root_path: str, items: list[FastqCandidate]) -> list[BatchSnapshot]:
    by_source: dict[str, list[FastqCandidate]] = {}
    for item in items:
        by_source.setdefault(item.source_dir, []).append(item)

    snapshots: list[BatchSnapshot] = []
    root = Path(root_path).resolve()
    for source_dir, batch_items in sorted(by_source.items()):
        source = Path(source_dir).resolve()
        snapshots.append(
            BatchSnapshot(
                pipeline=pipeline,
                root_path=str(root),
                batch_id=_relative_id(source, root),
                source_dir=str(source),
                items=batch_items,
                fingerprint=_fingerprint(batch_items),
                file_count=len(batch_items) * 2,
                total_bytes=sum(int(item.r1_size or 0) + int(item.r2_size or 0) for item in batch_items),
                max_mtime=_max_mtime(batch_items),
            )
        )
    return snapshots


def _roots_for_pipeline(settings, pipeline: str) -> list[str]:
    config = _load_config(settings)
    roots = config.roots_for_pipeline(pipeline)
    if roots:
        return roots
    if pipeline == "nipt_docker":
        return list(getattr(settings, "nipt_input_scan_roots", []) or [])
    return list(getattr(settings, "pgta_input_scan_roots", None) or getattr(settings, "input_scan_roots", []) or [])


def _fingerprint(items: list[FastqCandidate]) -> str:
    digest = hashlib.sha256()
    for item in sorted(items, key=lambda sample: sample.sample_id):
        digest.update(
            "\t".join(
                [
                    item.sample_id,
                    item.r1,
                    item.r2,
                    str(item.r1_size),
                    str(item.r2_size),
                    str(item.r1_mtime),
                    str(item.r2_mtime),
                ]
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def _max_mtime(items: list[FastqCandidate]) -> datetime | None:
    mtimes = [mtime for item in items for mtime in (item.r1_mtime, item.r2_mtime) if mtime is not None]
    if not mtimes:
        return None
    return datetime.fromtimestamp(max(mtimes), tz=timezone.utc)


def _relative_id(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix() or path.name
    except ValueError:
        return path.name


def _load_config(settings):
    return load_intake_config(
        path=getattr(settings, "intake_config_path", None),
        fallback_pgta_roots=list(getattr(settings, "pgta_input_scan_roots", None) or getattr(settings, "input_scan_roots", []) or []),
        fallback_nipt_roots=list(getattr(settings, "nipt_input_scan_roots", []) or []),
    )


def _auto_submit_enabled(settings, pipeline: str) -> bool:
    return _load_config(settings).auto_submit_enabled(pipeline)


def _auto_submit_param(settings, pipeline: str, key: str) -> object | None:
    config = _load_config(settings)
    item = config.pipelines.get(pipeline)
    if item is None:
        return None
    return item.auto_submit.get(key)


def _preview_summary(items: list[dict[str, object]]) -> dict[str, int]:
    return {
        "total_batches": len(items),
        "new_observed": sum(1 for item in items if item["reason"] == "new_batch_observed"),
        "stable_ready": sum(1 for item in items if item["would_transition_to"] == "ready"),
        "bootstrap_protected": sum(1 for item in items if item["reason"] == "bootstrap_protected"),
        "would_create": sum(1 for item in items if item["would_create_run"]),
        "would_submit": sum(1 for item in items if item["would_submit"]),
        "blocked_auto_submit": sum(1 for item in items if item["reason"] == "auto_submit_disabled"),
        "errors": sum(1 for item in items if item["reason"] == "manifest_validation_error"),
    }


def _row_payload(row: IntakeDiscovery, *, auto_submit_enabled: bool | None = None, reason: str | None = None) -> dict[str, object]:
    payload = {
        "pipeline": row.pipeline_name,
        "root_path": row.root_path,
        "batch_id": row.batch_id,
        "fingerprint": row.fingerprint,
        "file_count": row.file_count,
        "total_bytes": row.total_bytes,
        "ready_state": row.ready_state,
        "analysis_id": row.analysis_id,
        "submit_state": row.submit_state,
        "source_manifest_path": row.source_manifest_path,
        "last_error": row.last_error,
        "stable_observation_count": row.stable_observation_count,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
    }
    if auto_submit_enabled is not None:
        payload["auto_submit_enabled"] = auto_submit_enabled
    if reason is not None:
        payload["reason"] = reason
    return payload


def _stable_scans(settings, pipeline: str) -> int:
    config = _load_config(settings)
    pipeline_config = config.pipelines.get(pipeline)
    value = (pipeline_config.intake if pipeline_config else {}).get("stable_scans")
    return max(1, int(value or config.defaults.stable_scans))


def _auto_pipeline_config(*, settings, pipeline: str, snapshot: BatchSnapshot):
    profile_id = str(_auto_submit_param(settings, pipeline, "runtime_profile_id") or "").strip() or None
    template = get_pipeline_config_template(settings=settings, pipeline=pipeline, profile_id=profile_id)
    return validate_pipeline_config(
        settings=settings,
        pipeline=pipeline,
        profile_id=str(template["profile"]["id"]),
        template_hash=str(template["config_template_hash"]),
        config_yaml=str(template["editable_yaml"]),
    )


def _find_manifest_run(*, session: Session, snapshot: BatchSnapshot) -> AnalysisRun | None:
    matches = session.scalars(
        select(AnalysisRun)
        .where(
            AnalysisRun.pipeline_name == "pgta",
            AnalysisRun.params_json["intake_request_id"].as_string() == snapshot.batch_id,
            AnalysisRun.params_json["intake_fingerprint"].as_string() == snapshot.fingerprint,
        )
        .order_by(AnalysisRun.created_at.desc())
    ).all()
    if len(matches) > 1:
        raise ValueError(
            f"Multiple PGT-A runs already exist for intake request {snapshot.batch_id}; manual review is required."
        )
    return matches[0] if matches else None
