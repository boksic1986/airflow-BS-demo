from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.input_scanner import FastqCandidate, scan_fastq_candidates, scan_nipt_batch_candidates
from app.intake_config import load_intake_config
from app.models import IntakeDiscovery
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
        for snapshot in _scan_pipeline(settings=settings, pipeline=pipeline, max_samples=max_samples):
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
        for snapshot in _scan_pipeline(settings=settings, pipeline=pipeline, max_samples=max_samples):
            items.append(_preview_snapshot(session=session, settings=settings, snapshot=snapshot, bootstrap=bootstrap))
    return {"items": items, "summary": _preview_summary(items)}


def list_intake_status(*, session: Session, pipeline: str | None = None, limit: int = 50) -> dict[str, object]:
    stmt = select(IntakeDiscovery).order_by(IntakeDiscovery.last_seen_at.desc(), IntakeDiscovery.id.desc()).limit(limit)
    if pipeline:
        stmt = (
            select(IntakeDiscovery)
            .where(IntakeDiscovery.pipeline_name == pipeline)
            .order_by(IntakeDiscovery.last_seen_at.desc(), IntakeDiscovery.id.desc())
            .limit(limit)
        )
    return {"items": [_row_payload(row) for row in session.scalars(stmt).all()]}


def _scan_pipeline(*, settings, pipeline: str, max_samples: int) -> list[BatchSnapshot]:
    roots = _roots_for_pipeline(settings, pipeline)
    snapshots: list[BatchSnapshot] = []
    for root in roots:
        if pipeline == "nipt_docker":
            result = scan_nipt_batch_candidates(rawdata_root=root, allowed_roots=roots, max_samples=max_samples)
        else:
            result = scan_fastq_candidates(rawdata_root=root, allowed_roots=roots, max_samples=max_samples)
        snapshots.extend(_group_scan_result(pipeline=pipeline, root_path=result.rawdata_root, items=result.items))
    return snapshots


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
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(row)
        session.commit()
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="bootstrap_protected" if bootstrap else "new_batch_observed")

    if row.fingerprint != snapshot.fingerprint:
        row.fingerprint = snapshot.fingerprint
        row.file_count = snapshot.file_count
        row.total_bytes = snapshot.total_bytes
        row.max_mtime = snapshot.max_mtime
        row.ready_state = "observed"
        row.analysis_id = None
        row.submit_state = "bootstrap" if bootstrap else "not_submitted"
        row.last_seen_at = now
        session.commit()
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="fingerprint_changed")

    row.file_count = snapshot.file_count
    row.total_bytes = snapshot.total_bytes
    row.max_mtime = snapshot.max_mtime
    row.last_seen_at = now
    if row.submit_state in {"submitted", "bootstrap"} or bootstrap:
        session.commit()
        reason = "already_submitted" if row.submit_state == "submitted" else "bootstrap_protected"
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason=reason)

    row.ready_state = "ready"
    if not auto_submit_enabled:
        session.commit()
        return _row_payload(row, auto_submit_enabled=auto_submit_enabled, reason="auto_submit_disabled")

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
            project_name=f"PGT-A auto {snapshot.batch_id}",
            target=str(target),
            rawdata_root=snapshot.root_path,
            selected_samples=snapshot.items,
            note="auto intake stable scan",
        )
    row = session.scalar(
        select(IntakeDiscovery).where(
            IntakeDiscovery.pipeline_name == snapshot.pipeline,
            IntakeDiscovery.root_path == snapshot.root_path,
            IntakeDiscovery.batch_id == snapshot.batch_id,
        )
    )
    assert row is not None
    row.analysis_id = str(created["analysis_id"])
    row.submit_state = "created"
    session.commit()
    submit_run_to_airflow(session=session, airflow_client=airflow_client, analysis_id=row.analysis_id, settings=settings)
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
        "errors": 0,
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
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
    }
    if auto_submit_enabled is not None:
        payload["auto_submit_enabled"] = auto_submit_enabled
    if reason is not None:
        payload["reason"] = reason
    return payload
