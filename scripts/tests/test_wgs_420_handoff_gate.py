import csv
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest
import yaml


ROOT = Path(__file__).parents[1]


def load_gate():
    if sys.platform == "win32" and "fcntl" not in sys.modules:
        sys.modules["fcntl"] = types.SimpleNamespace(
            LOCK_EX=1,
            flock=lambda *_args, **_kwargs: None,
        )
    spec = importlib.util.spec_from_file_location(
        "wgs_runtime_gate_420_test", ROOT / "wgs_runtime_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def payload(tmp_path: Path, *, generation: int) -> dict[str, object]:
    runtime_root = tmp_path / "runtime"
    return {
        "analysis_id": "WGS_20260909_010203_A1B2C3",
        "attempt": 1,
        "stage": "prepare_analysis",
        "pipeline_release_id": "wgs-4.2.0-b067c72",
        "wgs_version": "V4.2.0",
        "wgs_source_commit": "b067c72eed795e59b724b13324b0d380ae8b7e94",
        "control_workdir": str(
            runtime_root / "runs" / "WGS_20260909_010203_A1B2C3" / "attempt-1"
        ),
        "analysis_project_root": str(tmp_path / "WGS_Clinical"),
        "expected_batch_root": str(tmp_path / "WGS_Clinical" / "20260909A"),
        "project_name": "WGS_Clinical",
        "batch_no": "20260909A",
        "fq_path": "/bi/fastq/T7_Fastq",
        "sequencing_batch": "20260909A",
        "analysis_batch": "20260909A",
        "execution_id": f"wse-analysis-g{generation}",
        "generation": generation,
        "request_hash": str(generation) * 64,
    }


def write_source(tmp_path: Path) -> Path:
    source = tmp_path / "WGS_Clinical" / "sampleinfo" / "20260909A.sampleinfo.txt"
    source.parent.mkdir(parents=True)
    source.write_text(
        "上机批次\t分析批次\t家系编号\t样本编号\t数据编号\t样本类型\t家系关系\t性别\n"
        "20260909A\t20260909A\tFAMILY-1\tSAMPLE-1\tDATA-1\tWGS\tproband\tM\n",
        encoding="utf-8",
    )
    return source


def safe_pending_row() -> dict[str, str]:
    return {
        "sequencing_batch": "20260909A",
        "analysis_batch": "20260909A",
        "family_id": "FAMILY-1",
        "sample_id": "SAMPLE-1",
        "data_id": "DATA-1",
        "sample_type": "WGS",
        "family_relation": "proband",
        "sex": "M",
        "decision": "pending",
        "reason_code": "pending",
        "reason_message": "FASTQ pair is incomplete",
    }


def write_all_pending_receipt(gate, request_path: Path, source: Path) -> Path:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    root = request_path.parent
    private = root / "private-pending-output.tsv"
    pending_manifest = json.loads(
        Path(request["pending_input"]["manifest_path"]).read_text(encoding="utf-8")
    )
    input_payload = Path(pending_manifest["payload"]["path"])
    header = next(csv.reader(input_payload.open(encoding="utf-8"), delimiter="\t"))
    with private.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerow(
            [
                "20260909A",
                "20260909A",
                "FAMILY-1",
                "SAMPLE-1",
                "DATA-1",
                "WGS",
                "proband",
                "M",
                "FASTQ pair is incomplete",
                "2026-09-09T00:00:00Z",
                "20260909A",
                str(source),
            ]
        )
    receipt = {
        "schema_version": "wgs.prepare-analysis.receipt.v1",
        **{key: request[key] for key in (
            "analysis_id", "attempt", "execution_id", "generation", "request_hash", "release_id"
        )},
        "source_sampleinfo_snapshot_id": request["source_sampleinfo"]["snapshot_id"],
        "source_sampleinfo_sha256": gate._sha256_file(source),
        "pending_input_revision": request["pending_input"]["revision"],
        "pending_input_sha256": pending_manifest["payload"]["sha256"],
        "final_sampleinfo": {
            "artifact_key": request["artifact_keys"]["final_sampleinfo"],
            "sha256": None,
            "row_count": 0,
        },
        "private_pending_payload": {
            "artifact_key": request["artifact_keys"]["private_pending_payload"],
            "sha256": gate._sha256_file(private),
            "row_count": 1,
        },
        "selected": [],
        "pending": [safe_pending_row()],
        "excluded": [],
    }
    receipt_path = root / "prepare_analysis.receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return private


def test_analysis_handoff_uses_wgs_artifact_name_and_carries_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    monkeypatch.setattr(gate, "RUNTIME_RUN_ROOT", str(tmp_path / "runtime"))
    source = write_source(tmp_path)
    first = payload(tmp_path, generation=1)
    first_request = gate._prepare_handoff_request(first)
    assert first_request is not None
    first_payload = json.loads(first_request.read_text(encoding="utf-8"))
    assert first_payload["artifact_keys"]["private_pending_payload"] == (
        "private-pending-output.tsv"
    )
    previous_private = write_all_pending_receipt(gate, first_request, source)

    second_request = gate._prepare_handoff_request(payload(tmp_path, generation=2))
    assert second_request is not None
    second = json.loads(second_request.read_text(encoding="utf-8"))
    second_manifest = json.loads(
        Path(second["pending_input"]["manifest_path"]).read_text(encoding="utf-8")
    )
    carried = Path(second_manifest["payload"]["path"])
    assert carried.read_bytes() == previous_private.read_bytes()
    assert second_manifest["payload"]["row_count"] == 1


def test_receipt_rejects_source_sampleinfo_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    monkeypatch.setattr(gate, "RUNTIME_RUN_ROOT", str(tmp_path / "runtime"))
    source = write_source(tmp_path)
    request = gate._prepare_handoff_request(payload(tmp_path, generation=1))
    assert request is not None
    source.write_text(source.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    write_all_pending_receipt(gate, request, source)

    with pytest.raises(RuntimeError, match="input identity mismatch"):
        gate._validated_prepare_receipt(payload(tmp_path, generation=1), request)


def test_release_runtime_evidence_is_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    profile_root = tmp_path / "profiles"
    profile_root.mkdir()
    profile = profile_root / "wgs-4.2.0-r1.yaml"
    profile.write_text(
        yaml.safe_dump(
            {
                "profile_id": "wgs-4.2.0",
                "revision": "r1",
                "pipeline": {
                    "build_sha256": "b" * 64,
                    "resource_manifest_sha256": "c" * 64,
                },
            }
        ),
        encoding="utf-8",
    )
    prepare_config = tmp_path / "prepare-config.yaml"
    prepare_config.write_text(
        yaml.safe_dump({"cce": {"profile_file": str(profile)}}), encoding="utf-8"
    )
    executable = tmp_path / "cce-pipeline"
    executable.write_text("test", encoding="utf-8")
    monkeypatch.setattr(gate, "CCE_PROFILE_ROOT", profile_root)
    monkeypatch.setattr(gate, "CCE_PIPELINE_BIN", str(executable))
    monkeypatch.setattr(gate, "validate_prepare_config", lambda _payload: prepare_config)
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *_args, **_kwargs: types.SimpleNamespace(stdout="cce-pipeline 0.8.3\n"),
    )
    request = {
        "cce_pipeline_version": "0.8.3",
        "profile_id": "wgs-4.2.0",
        "profile_revision": "r1",
        "profile_sha256": gate._sha256_file(profile),
        "node200_profile_path": str(profile),
        "pipeline_build_sha256": "b" * 64,
        "resource_manifest_sha256": "c" * 64,
    }

    gate.validate_release_runtime(request)
    request["profile_sha256"] = "d" * 64
    with pytest.raises(RuntimeError, match="profile"):
        gate.validate_release_runtime(request)
