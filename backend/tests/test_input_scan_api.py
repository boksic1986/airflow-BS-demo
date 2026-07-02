from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main


def write_fastq_pair(sample_dir, stem: str) -> tuple[str, str]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    r1 = sample_dir / f"{stem}_R1.fastq.gz"
    r2 = sample_dir / f"{stem}_R2.fastq.gz"
    r1.write_text("r1\n", encoding="utf-8")
    r2.write_text("r2\n", encoding="utf-8")
    return str(r1.resolve()), str(r2.resolve())


def test_input_scan_endpoint_returns_discovered_candidates(tmp_path, monkeypatch) -> None:
    allowed_root = tmp_path / "rawdata"
    sample_dir = allowed_root / "run1" / "Sample_JZ26083055-G1-G1"
    r1, r2 = write_fastq_pair(sample_dir, "JZ26083055-G1-G1_combined")
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(input_scan_roots=[str(allowed_root)], container_shared_root=str(tmp_path / "shared")),
    )
    client = TestClient(main.app)

    response = client.post(
        "/api/input/scan",
        json={"pipeline": "pgta", "rawdata_root": str(allowed_root), "max_samples": 20},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline"] == "pgta"
    assert payload["rawdata_root"] == str(allowed_root.resolve())
    assert payload["truncated"] is False
    assert payload["items"] == [
        {
            "sample_id": "G1",
            "r1": r1,
            "r2": r2,
            "source_dir": str(sample_dir.resolve()),
            "r1_size": 3,
            "r2_size": 3,
            "r1_mtime": payload["items"][0]["r1_mtime"],
            "r2_mtime": payload["items"][0]["r2_mtime"],
            "discovery_method": "server_path_scan",
        }
    ]


def test_input_scan_endpoint_rejects_non_pgta_pipeline(tmp_path, monkeypatch) -> None:
    allowed_root = tmp_path / "rawdata"
    allowed_root.mkdir()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(input_scan_roots=[str(allowed_root)], container_shared_root=str(tmp_path / "shared")),
    )
    client = TestClient(main.app)

    response = client.post(
        "/api/input/scan",
        json={"pipeline": "wes_qsub", "rawdata_root": str(allowed_root)},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_PIPELINE"
