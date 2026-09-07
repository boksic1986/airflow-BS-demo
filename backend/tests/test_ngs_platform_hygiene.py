from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent


def _source_path(relative: str) -> Path:
    path = REPOSITORY_ROOT / relative
    if path.exists() or not relative.startswith("backend/"):
        return path
    return BACKEND_ROOT / relative.removeprefix("backend/")


def test_retired_pipeline_assets_are_absent():
    retired = [
        "backend/app/nipt_yaml_intake.py",
        "backend/app/pgta_manifest_intake.py",
        "dags/bio_nipt_docker.py",
        "dags/bio_pgta.py",
        "dags/bio_pgta_airflow.py",
        "dags/bio_wes_qsub.py",
        "dags/nipt_docker_runner.py",
        "dags/pgta_airflow_runner.py",
        "dags/pgta_metadata_runner.py",
        "dags/wes_qsub_runner.py",
        "pipelines/pgta_s9",
        "pipelines/wes",
        "nipt_s9_image",
        "docker-compose.bs-nipt.yaml",
    ]

    remaining = []
    for relative in retired:
        candidate = _source_path(relative)
        if candidate.is_file() or (
            candidate.is_dir() and any(item.is_file() for item in candidate.rglob("*"))
        ):
            remaining.append(relative)
    assert remaining == []


def test_pipeline_registry_is_the_only_deployment_catalog():
    source = (BACKEND_ROOT / "app/main.py").read_text(encoding="utf-8")

    assert "pgta" not in source.lower()
    assert "nipt_docker" not in source.lower()
    assert "wes_qsub" not in source.lower()
    assert 'return ("wgs",)' not in source
    assert "get_pipeline_registry" in source


def test_shared_projection_services_do_not_dispatch_on_pipeline_names():
    for relative in (
        "backend/app/dashboard_service.py",
        "backend/app/progress_service.py",
        "backend/app/rule_event_service.py",
        "backend/app/diagnostics_service.py",
        "backend/app/operator_resources_service.py",
        "backend/app/workflow_phases.py",
    ):
        source = _source_path(relative).read_text(encoding="utf-8")
        assert 'pipeline_name == "wgs"' not in source
        assert 'pipeline_name != "wgs"' not in source
