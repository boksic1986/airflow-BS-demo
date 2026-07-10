from __future__ import annotations

import stat
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import Base


PROFILE_YAML = """
version: 1
pipelines:
  pgta:
    default_profile: pgta-current
    profiles:
      pgta-current:
        label: PGT-A current
        pipeline_version: current
        config_version: "1"
        runtime:
          pipeline_root: /opt/pipelines/PGT_A
          snakemake_bin: /biosoftware/miniconda/envs/snakemake_env/bin/snakemake
          docker_image: should-never-reach-the-browser
        editable_defaults:
          core:
            wisecondorx:
              reference_prefilter:
                max_iterations: 3
        editable_schema:
          core.wisecondorx.reference_prefilter.max_iterations:
            type: integer
            minimum: 1
            maximum: 10
  nipt_docker:
    default_profile: niptpro-1.0.11
    profiles:
      niptpro-1.0.11:
        label: NIPTPro 1.0.11
        pipeline_version: 1.0.11
        config_version: v3.2.5.1
        runtime:
          docker_image: registry.example/niptpro:1.0.11
        editable_defaults:
          params:
            sexcutoff: 0.00007
            map_threads: 4
        editable_schema:
          params.sexcutoff:
            type: number
            minimum: 0
            maximum: 1
          params.map_threads:
            type: integer
            minimum: 1
            maximum: 40
"""


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def configure_client(tmp_path, monkeypatch) -> tuple[TestClient, object, object]:
    rawdata_root = tmp_path / "rawdata"
    rawdata_root.mkdir()
    shared_root = tmp_path / "shared"
    profile_path = tmp_path / "pipeline_profiles.yaml"
    profile_path.write_text(PROFILE_YAML, encoding="utf-8")
    session_factory = make_test_sessionmaker()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[str(rawdata_root)],
            pgta_input_scan_roots=[str(rawdata_root)],
            nipt_input_scan_roots=[str(rawdata_root)],
            container_shared_root=str(shared_root),
            pipeline_profile_config_path=str(profile_path),
            nipt_allow_heavy_run=False,
            nipt_docker_cores=40,
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    return TestClient(main.app), rawdata_root, shared_root


def write_fastq_pair(sample_dir, stem: str) -> tuple[str, str]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    r1 = sample_dir / f"{stem}_R1.fastq.gz"
    r2 = sample_dir / f"{stem}_R2.fastq.gz"
    r1.write_text("r1\n", encoding="utf-8")
    r2.write_text("r2\n", encoding="utf-8")
    return str(r1.resolve()), str(r2.resolve())


def test_config_template_returns_editable_yaml_without_runtime_details(tmp_path, monkeypatch) -> None:
    client, _, _ = configure_client(tmp_path, monkeypatch)

    response = client.get("/api/pipeline-config/template?pipeline=pgta&target=metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"] == {
        "id": "pgta-current",
        "label": "PGT-A current",
        "pipeline_version": "current",
        "config_version": "1",
    }
    assert payload["profiles"] == [payload["profile"]]
    assert "max_iterations: 3" in payload["editable_yaml"]
    serialized = response.text
    assert "runtime" not in serialized
    assert "docker_image" not in serialized
    assert "/biosoftware" not in serialized


def test_validate_config_normalizes_yaml_and_reports_changed_paths(tmp_path, monkeypatch) -> None:
    client, _, _ = configure_client(tmp_path, monkeypatch)
    template = client.get("/api/pipeline-config/template?pipeline=pgta&target=metadata").json()

    response = client.post(
        "/api/pipeline-config/validate",
        json={
            "pipeline": "pgta",
            "target": "metadata",
            "runtime_profile_id": "pgta-current",
            "config_template_hash": template["config_template_hash"],
            "snakemake_config_yaml": "core:\n  wisecondorx:\n    reference_prefilter:\n      max_iterations: 5\n",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["changed_paths"] == ["core.wisecondorx.reference_prefilter.max_iterations"]
    assert "max_iterations: 5" in payload["normalized_yaml"]
    assert payload["config_template_hash"] == template["config_template_hash"]


def test_validate_config_rejects_unknown_or_unsafe_yaml(tmp_path, monkeypatch) -> None:
    client, _, _ = configure_client(tmp_path, monkeypatch)
    template = client.get("/api/pipeline-config/template?pipeline=pgta&target=metadata").json()
    base = {
        "pipeline": "pgta",
        "target": "metadata",
        "runtime_profile_id": "pgta-current",
        "config_template_hash": template["config_template_hash"],
    }
    invalid_documents = (
        "biosoft:\n  python: /tmp/unsafe-python\n",
        "biosoft: {}\n",
        "core:\n  wisecondorx:\n    reference_prefilter:\n      max_iterations: 3\n      max_iterations: 4\n",
        "core:\n  wisecondorx:\n    reference_prefilter:\n      max_iterations: 11\n",
        "core:\n  wisecondorx:\n    reference_prefilter:\n      max_iterations: '3'\n",
        "shared: &shared\n  max_iterations: 3\ncore:\n  wisecondorx:\n    reference_prefilter: *shared\n",
        "core: !unsafe {}\n",
    )

    for document in invalid_documents:
        response = client.post(
            "/api/pipeline-config/validate",
            json={**base, "snakemake_config_yaml": document},
        )
        assert response.status_code == 400, document
        assert response.json()["detail"]["code"] == "CONFIG_VALIDATION_ERROR"


def test_validate_config_rejects_non_finite_numbers(tmp_path, monkeypatch) -> None:
    client, _, _ = configure_client(tmp_path, monkeypatch)
    template = client.get("/api/pipeline-config/template?pipeline=nipt_docker").json()

    response = client.post(
        "/api/pipeline-config/validate",
        json={
            "pipeline": "nipt_docker",
            "run_mode": "mount_smoke",
            "cores": 40,
            "runtime_profile_id": "niptpro-1.0.11",
            "config_template_hash": template["config_template_hash"],
            "snakemake_config_yaml": "params:\n  sexcutoff: .nan\n  map_threads: 4\n",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CONFIG_VALIDATION_ERROR"


def test_validate_config_rejects_utf8_payload_over_64k(tmp_path, monkeypatch) -> None:
    client, _, _ = configure_client(tmp_path, monkeypatch)
    template = client.get("/api/pipeline-config/template?pipeline=pgta").json()

    response = client.post(
        "/api/pipeline-config/validate",
        json={
            "pipeline": "pgta",
            "runtime_profile_id": "pgta-current",
            "config_template_hash": template["config_template_hash"],
            "snakemake_config_yaml": "note: '" + ("é" * 33000) + "'\n",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CONFIG_VALIDATION_ERROR"


def test_nipt_config_threads_cannot_exceed_requested_cores(tmp_path, monkeypatch) -> None:
    client, _, _ = configure_client(tmp_path, monkeypatch)
    template = client.get("/api/pipeline-config/template?pipeline=nipt_docker").json()

    response = client.post(
        "/api/pipeline-config/validate",
        json={
            "pipeline": "nipt_docker",
            "run_mode": "mount_smoke",
            "cores": 1,
            "runtime_profile_id": "niptpro-1.0.11",
            "config_template_hash": template["config_template_hash"],
            "snakemake_config_yaml": template["editable_yaml"],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CONFIG_VALIDATION_ERROR"


def test_create_run_persists_requested_config_and_waiting_provenance(tmp_path, monkeypatch) -> None:
    client, rawdata_root, shared_root = configure_client(tmp_path, monkeypatch)
    source_dir = rawdata_root / "batch" / "sample-G1"
    r1, r2 = write_fastq_pair(source_dir, "G1")
    template = client.get("/api/pipeline-config/template?pipeline=pgta&target=metadata").json()
    config_yaml = "core:\n  wisecondorx:\n    reference_prefilter:\n      max_iterations: 5\n"

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "pgta",
            "project_name": "config override smoke",
            "target": "metadata",
            "rawdata_root": str(rawdata_root),
            "selected_samples": [
                {
                    "sample_id": "G1",
                    "r1": r1,
                    "r2": r2,
                    "source_dir": str(source_dir.resolve()),
                }
            ],
            "runtime_profile_id": "pgta-current",
            "config_template_hash": template["config_template_hash"],
            "snakemake_config_yaml": config_yaml,
        },
    )

    assert response.status_code == 201
    analysis_id = response.json()["analysis_id"]
    config_dir = shared_root / "runs" / analysis_id / "config"
    assert config_dir.joinpath("snakemake.user.yaml").read_text(encoding="utf-8") == config_yaml
    provenance = config_dir.joinpath("config_provenance.json").read_text(encoding="utf-8")
    assert '"runtime_profile_id": "pgta-current"' in provenance
    assert '"state": "waiting_for_prepare"' in provenance
    assert '"runtime_profile_snapshot"' in provenance
    assert not config_dir.joinpath("snakemake.resolved.yaml").exists()
    assert stat.S_IMODE(config_dir.joinpath("snakemake.user.yaml").stat().st_mode) & stat.S_IWGRP
    assert stat.S_IMODE(config_dir.joinpath("config_provenance.json").stat().st_mode) & stat.S_IWGRP

    detail = client.get(f"/api/runs/{analysis_id}").json()
    assert detail["params"]["runtime_profile_id"] == "pgta-current"
    assert detail["params"]["config_changed_paths"] == [
        "core.wisecondorx.reference_prefilter.max_iterations"
    ]
    assert "snakemake_config_yaml" not in detail["params"]

    run_config = client.get(f"/api/runs/{analysis_id}/config")
    assert run_config.status_code == 200
    config_payload = run_config.json()
    assert config_payload["state"] == "waiting_for_prepare"
    assert config_payload["requested_yaml"] == config_yaml
    assert config_payload["resolved_yaml"] is None
    assert "runtime" not in run_config.text
    assert "compose" not in run_config.text.lower()


def test_run_config_rejects_symlinked_config_files(tmp_path, monkeypatch) -> None:
    client, rawdata_root, shared_root = configure_client(tmp_path, monkeypatch)
    source_dir = rawdata_root / "batch" / "sample-G1"
    r1, r2 = write_fastq_pair(source_dir, "G1")
    template = client.get("/api/pipeline-config/template?pipeline=pgta").json()
    created = client.post(
        "/api/runs",
        json={
            "pipeline": "pgta",
            "project_name": "symlink guard",
            "target": "metadata",
            "rawdata_root": str(rawdata_root),
            "selected_samples": [
                {"sample_id": "G1", "r1": r1, "r2": r2, "source_dir": str(source_dir.resolve())}
            ],
            "runtime_profile_id": "pgta-current",
            "config_template_hash": template["config_template_hash"],
            "snakemake_config_yaml": template["editable_yaml"],
        },
    ).json()
    requested = shared_root / "runs" / created["analysis_id"] / "config" / "snakemake.user.yaml"
    requested.unlink()
    requested.symlink_to(tmp_path / "pipeline_profiles.yaml")

    response = client.get(f"/api/runs/{created['analysis_id']}/config")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CONFIG_VALIDATION_ERROR"


def test_create_run_rejects_stale_profile_hash(tmp_path, monkeypatch) -> None:
    client, rawdata_root, _ = configure_client(tmp_path, monkeypatch)
    source_dir = rawdata_root / "batch" / "sample-G1"
    r1, r2 = write_fastq_pair(source_dir, "G1")

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "pgta",
            "project_name": "stale profile",
            "target": "metadata",
            "rawdata_root": str(rawdata_root),
            "selected_samples": [
                {"sample_id": "G1", "r1": r1, "r2": r2, "source_dir": str(source_dir.resolve())}
            ],
            "runtime_profile_id": "pgta-current",
            "config_template_hash": "stale",
            "snakemake_config_yaml": "core: {}\n",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PROFILE_CHANGED"
