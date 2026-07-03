from types import SimpleNamespace
import stat

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import Base


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def write_fastq_pair(sample_dir, stem: str) -> tuple[str, str]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    r1 = sample_dir / f"{stem}_R1.fastq.gz"
    r2 = sample_dir / f"{stem}_R2.fastq.gz"
    r1.write_text("r1\n", encoding="utf-8")
    r2.write_text("r2\n", encoding="utf-8")
    return str(r1.resolve()), str(r2.resolve())


def test_create_pgta_run_records_selected_paths_and_writes_manifest(tmp_path, monkeypatch) -> None:
    allowed_root = tmp_path / "rawdata"
    source_dir = allowed_root / "run1" / "Sample_JZ26083055-G1-G1"
    r1, r2 = write_fastq_pair(source_dir, "JZ26083055-G1-G1_combined")
    shared_root = tmp_path / "shared"
    session_factory = make_test_sessionmaker()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[str(allowed_root)],
            container_shared_root=str(shared_root),
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "pgta",
            "project_name": "demo project",
            "target": "metadata",
            "rawdata_root": str(allowed_root),
            "selected_samples": [
                {
                    "sample_id": "G1",
                    "r1": r1,
                    "r2": r2,
                    "source_dir": str(source_dir.resolve()),
                }
            ],
            "email_to": "demo@example.com",
            "note": "metadata smoke only",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["analysis_id"].startswith("PGTA_")
    assert payload["pipeline"] == "pgta"
    assert payload["dag_id"] == "bio_pgta"
    assert payload["dag_run_id"] is None
    assert payload["status"] == "created"
    assert payload["sample_count"] == 1

    manifest = shared_root / "runs" / payload["analysis_id"] / "config" / "samples.selected.tsv"
    request_json = shared_root / "runs" / payload["analysis_id"] / "config" / "request.json"
    workdir = shared_root / "runs" / payload["analysis_id"]
    assert stat.S_IMODE(workdir.stat().st_mode) & stat.S_IWGRP
    assert stat.S_IMODE(manifest.parent.stat().st_mode) & stat.S_IWGRP
    assert manifest.read_text(encoding="utf-8").splitlines() == [
        "sample_id\tR1\tR2\tsource_dir",
        f"G1\t{r1}\t{r2}\t{source_dir.resolve()}",
    ]
    assert request_json.exists()

    detail = client.get(f"/api/runs/{payload['analysis_id']}")
    assert detail.status_code == 200
    assert detail.json()["sample_sheet_path"] == str(manifest)
    assert detail.json()["params"]["input_mode"] == "server_path_scan"
    assert detail.json()["params"]["selected_count"] == 1

    samples = client.get(f"/api/runs/{payload['analysis_id']}/samples")
    assert samples.status_code == 200
    assert samples.json()["items"][0]["sample_id"] == "G1"
    assert samples.json()["items"][0]["fq1"] == r1
    assert samples.json()["items"][0]["fq2"] == r2


def test_create_pgta_run_accepts_controlled_pgta_targets(tmp_path, monkeypatch) -> None:
    allowed_root = tmp_path / "rawdata"
    source_dir = allowed_root / "run1" / "Sample_JZ26083055-G1-G1"
    r1, r2 = write_fastq_pair(source_dir, "JZ26083055-G1-G1_combined")
    shared_root = tmp_path / "shared"
    session_factory = make_test_sessionmaker()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[str(allowed_root)],
            container_shared_root=str(shared_root),
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    for target in ("dryrun_cnv", "invalid_target"):
        response = client.post(
            "/api/runs",
            json={
                "pipeline": "pgta",
                "project_name": f"{target} smoke",
                "target": target,
                "rawdata_root": str(allowed_root),
                "selected_samples": [
                    {
                        "sample_id": f"G1_{target}",
                        "r1": r1,
                        "r2": r2,
                        "source_dir": str(source_dir.resolve()),
                    }
                ],
            },
        )

        assert response.status_code == 201
        analysis_id = response.json()["analysis_id"]
        detail = client.get(f"/api/runs/{analysis_id}")
        assert detail.status_code == 200
        assert detail.json()["params"]["target"] == target
        request_json = shared_root / "runs" / analysis_id / "config" / "request.json"
        assert f'"target": "{target}"' in request_json.read_text(encoding="utf-8")


def test_create_pgta_run_rejects_uncontrolled_target(tmp_path, monkeypatch) -> None:
    allowed_root = tmp_path / "rawdata"
    source_dir = allowed_root / "run1" / "Sample_JZ26083055-G1-G1"
    r1, r2 = write_fastq_pair(source_dir, "JZ26083055-G1-G1_combined")
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[str(allowed_root)],
            container_shared_root=str(tmp_path / "shared"),
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: make_test_sessionmaker())
    client = TestClient(main.app)

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "pgta",
            "project_name": "unsupported target",
            "target": "baseline_qc",
            "rawdata_root": str(allowed_root),
            "selected_samples": [
                {
                    "sample_id": "G1",
                    "r1": r1,
                    "r2": r2,
                    "source_dir": str(source_dir.resolve()),
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "Unsupported PGT-A target" in response.json()["detail"]["message"]


def test_create_pgta_run_rejects_empty_selection(tmp_path, monkeypatch) -> None:
    allowed_root = tmp_path / "rawdata"
    allowed_root.mkdir()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[str(allowed_root)],
            container_shared_root=str(tmp_path / "shared"),
        ),
    )
    client = TestClient(main.app)

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "pgta",
            "project_name": "demo project",
            "target": "metadata",
            "rawdata_root": str(allowed_root),
            "selected_samples": [],
        },
    )

    assert response.status_code == 422


def test_run_list_returns_created_runs(tmp_path, monkeypatch) -> None:
    allowed_root = tmp_path / "rawdata"
    source_dir = allowed_root / "run1" / "Sample_JZ26083055-G1-G1"
    r1, r2 = write_fastq_pair(source_dir, "JZ26083055-G1-G1_combined")
    session_factory = make_test_sessionmaker()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[str(allowed_root)],
            container_shared_root=str(tmp_path / "shared"),
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)
    created = client.post(
        "/api/runs",
        json={
            "pipeline": "pgta",
            "project_name": "demo project",
            "target": "metadata",
            "rawdata_root": str(allowed_root),
            "selected_samples": [{"sample_id": "G1", "r1": r1, "r2": r2, "source_dir": str(source_dir.resolve())}],
        },
    ).json()

    response = client.get("/api/runs?pipeline=pgta")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["analysis_id"] == created["analysis_id"]
    assert response.json()["items"][0]["status"] == "created"
