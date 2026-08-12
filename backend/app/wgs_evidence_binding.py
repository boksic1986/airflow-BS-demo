from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from app.wgs_release_catalog import SnapshotCatalog


RUN_LABEL_PATTERN = re.compile(r"^wgs392-[0-9a-f]{16}$")


@dataclass(frozen=True)
class EvidenceBinding:
    analysis_id: str
    attempt: int
    pipeline_snapshot_id: str
    run_label: str
    evidence_path: str
    evidence_directory: Path
    source_path: Path


@dataclass(frozen=True)
class BindingDiagnostic:
    source_path: Path
    message: str


def load_evidence_bindings(
    binding_root: Path, evidence_root: Path, catalog: SnapshotCatalog
) -> tuple[list[EvidenceBinding], list[BindingDiagnostic]]:
    bindings: list[EvidenceBinding] = []
    diagnostics: list[BindingDiagnostic] = []
    approved = {snapshot.snapshot_id for snapshot in catalog.snapshots}
    root = evidence_root.resolve()
    try:
        paths = sorted(binding_root.glob("*.json"))
    except OSError as error:
        return [], [BindingDiagnostic(binding_root, f"cannot list bindings: {error}")]

    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("binding must be a JSON object")
            if str(payload.get("schema_version")) != "1":
                raise ValueError("unsupported binding schema_version")
            analysis_id = str(payload.get("analysis_id") or "").strip()
            if not analysis_id:
                raise ValueError("analysis_id is required")
            attempt = int(payload.get("attempt"))
            if attempt <= 0:
                raise ValueError("attempt must be positive")
            snapshot_id = str(payload.get("pipeline_snapshot_id") or "")
            if snapshot_id not in approved:
                raise ValueError("pipeline snapshot is not approved by catalog")
            run_label = str(payload.get("run_label") or "")
            if not RUN_LABEL_PATTERN.fullmatch(run_label):
                raise ValueError("invalid run_label")
            relative = Path(str(payload.get("evidence_path") or ""))
            if not str(relative) or relative.is_absolute() or ".." in relative.parts:
                raise ValueError("evidence_path must be relative and cannot escape")
            directory = (root / relative).resolve()
            if directory == root or root not in directory.parents:
                raise ValueError("evidence_path must resolve below evidence root")
            bindings.append(
                EvidenceBinding(
                    analysis_id=analysis_id,
                    attempt=attempt,
                    pipeline_snapshot_id=snapshot_id,
                    run_label=run_label,
                    evidence_path=relative.as_posix(),
                    evidence_directory=directory,
                    source_path=path,
                )
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            diagnostics.append(BindingDiagnostic(path, str(error)))
    return bindings, diagnostics
