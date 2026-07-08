from dataclasses import dataclass
from functools import lru_cache
import os


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    airflow_base_url: str
    airflow_api_username: str
    airflow_api_password: str
    container_shared_root: str
    input_scan_roots: list[str]
    pgta_input_scan_roots: list[str]
    nipt_input_scan_roots: list[str]
    nipt_allow_heavy_run: bool
    nipt_docker_cores: int


def get_cors_origins() -> list[str]:
    raw = os.getenv("BACKEND_CORS_ORIGINS", "*")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


@lru_cache
def get_settings() -> Settings:
    legacy_scan_roots = _parse_list(os.getenv("INPUT_SCAN_ROOTS", "/data/project/CNV/PGT-A/rawdata"))
    pgta_scan_roots = _parse_list(os.getenv("PGTA_INPUT_SCAN_ROOTS") or ",".join(legacy_scan_roots))
    nipt_scan_roots = _parse_list(os.getenv("NIPT_INPUT_SCAN_ROOTS") or "/opt/pipelines/NIPT/fastq")
    return Settings(
        database_url=_required_env("DATABASE_URL"),
        airflow_base_url=os.getenv("AIRFLOW_BASE_URL", "http://airflow-api-server:8080"),
        airflow_api_username=os.getenv("AIRFLOW_API_USERNAME", "admin"),
        airflow_api_password=_required_env("AIRFLOW_API_PASSWORD"),
        container_shared_root=os.getenv("CONTAINER_SHARED_ROOT", "/data/airflow-demo"),
        input_scan_roots=pgta_scan_roots,
        pgta_input_scan_roots=pgta_scan_roots,
        nipt_input_scan_roots=nipt_scan_roots,
        nipt_allow_heavy_run=_parse_bool(os.getenv("NIPT_ALLOW_HEAVY_RUN", "false")),
        nipt_docker_cores=_parse_int(os.getenv("NIPT_DOCKER_CORES", "40"), default=40),
    )


def _parse_list(value: str | None) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _parse_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, *, default: int) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default
