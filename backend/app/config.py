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
    host_results_root: str
    wgs_host_owner: str
    input_scan_roots: list[str]
    pgta_input_scan_roots: list[str]
    nipt_input_scan_roots: list[str]
    wgs_config_roots: list[str]
    wgs_validation_roots: list[str]
    intake_config_path: str | None
    pipeline_profile_config_path: str | None
    nipt_allow_heavy_run: bool
    nipt_docker_cores: int
    internal_service_token: str
    deployed_pipelines: tuple[str, ...]
    platform_environment: str
    public_airflow_url: str
    auth_required: bool
    session_cookie_secure: bool
    session_ttl_hours: int
    wgs_evidence_root: str


def get_cors_origins() -> list[str]:
    raw = os.getenv("BACKEND_CORS_ORIGINS", "*")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


def get_internal_service_token() -> str:
    return os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()


@lru_cache
def get_settings() -> Settings:
    legacy_scan_roots = _parse_list(os.getenv("INPUT_SCAN_ROOTS", "/data/project/CNV/PGT-A/rawdata"))
    pgta_scan_roots = _parse_list(os.getenv("PGTA_INPUT_SCAN_ROOTS") or ",".join(legacy_scan_roots))
    nipt_scan_roots = _parse_list(os.getenv("NIPT_INPUT_SCAN_ROOTS") or "/opt/pipelines/NIPT/fastq")
    wgs_config_roots = _parse_list(os.getenv("WGS_CONFIG_ROOTS") or "/data/wgs-intake")
    wgs_validation_roots = _parse_list(os.getenv("WGS_VALIDATION_ROOTS") or "/data/wgs-validation")
    deployed_pipelines = tuple(_parse_list(os.getenv("DEPLOYED_PIPELINES", "wgs")))
    unsupported = sorted(set(deployed_pipelines) - {"wgs"})
    if unsupported:
        raise RuntimeError(f"Unsupported DEPLOYED_PIPELINES values: {', '.join(unsupported)}")
    if not deployed_pipelines:
        raise RuntimeError("DEPLOYED_PIPELINES must contain at least one pipeline")
    return Settings(
        database_url=_required_env("DATABASE_URL"),
        airflow_base_url=os.getenv("AIRFLOW_BASE_URL", "http://airflow-api-server:8080"),
        airflow_api_username=os.getenv("AIRFLOW_API_USERNAME", "admin"),
        airflow_api_password=_required_env("AIRFLOW_API_PASSWORD"),
        container_shared_root=os.getenv("CONTAINER_SHARED_ROOT", "/data/airflow-demo"),
        host_results_root=os.getenv("HOST_RESULTS_ROOT", os.getenv("CONTAINER_SHARED_ROOT", "/data/airflow-demo")),
        wgs_host_owner=os.getenv("WGS_HOST_OWNER", "").strip(),
        input_scan_roots=pgta_scan_roots,
        pgta_input_scan_roots=pgta_scan_roots,
        nipt_input_scan_roots=nipt_scan_roots,
        wgs_config_roots=wgs_config_roots,
        wgs_validation_roots=wgs_validation_roots,
        intake_config_path=os.getenv("INTAKE_CONFIG_PATH", "/app/config/intake.yaml"),
        pipeline_profile_config_path=os.getenv(
            "PIPELINE_PROFILE_CONFIG_PATH",
            "/app/config/pipeline_profiles.yaml",
        ),
        nipt_allow_heavy_run=_parse_bool(os.getenv("NIPT_ALLOW_HEAVY_RUN", "false")),
        nipt_docker_cores=_parse_int(os.getenv("NIPT_DOCKER_CORES", "32"), default=32),
        internal_service_token=get_internal_service_token(),
        deployed_pipelines=deployed_pipelines,
        platform_environment=os.getenv("PLATFORM_ENVIRONMENT", "Demo").strip() or "Demo",
        public_airflow_url=os.getenv("PUBLIC_AIRFLOW_URL", "").strip(),
        auth_required=_parse_bool(os.getenv("AUTH_REQUIRED", "true")),
        session_cookie_secure=_parse_bool(os.getenv("SESSION_COOKIE_SECURE", "true")),
        session_ttl_hours=_parse_int(os.getenv("SESSION_TTL_HOURS", "8"), default=8),
        wgs_evidence_root=os.getenv("WGS_EVIDENCE_ROOT", "/data/wgs-evidence"),
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
