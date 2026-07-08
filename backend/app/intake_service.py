from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.input_scanner import FastqCandidate, scan_fastq_candidates, scan_nipt_batch_candidates
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
        return _row_payload(row)

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
        return _row_payload(row)

    row.file_count = snapshot.file_count
    row.total_bytes = snapshot.total_bytes
    row.max_mtime = snapshot.max_mtime
    row.last_seen_at = now
    if row.submit_state in {"submitted", "bootstrap"} or bootstrap:
        session.commit()
        return _row_payload(row)

    row.ready_state = "ready"
    if snapshot.pipeline == "nipt_docker":
        created = create_nipt_docker_run(
            session=session,
            settings=settings,
            project_name=f"NIPT auto {snapshot.batch_id}",
            rawdata_root=snapshot.root_path,
            selected_samples=snapshot.items,
            run_mode="mount_smoke",
            cores=None,
            note="auto intake stable scan",
        )
    else:
        created = create_pgta_run(
            session=session,
            settings=settings,
            project_name=f"PGT-A auto {snapshot.batch_id}",
            target="metadata",
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
    return _row_payload(row)


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


def _row_payload(row: IntakeDiscovery) -> dict[str, object]:
    return {
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
