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


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=_required_env("DATABASE_URL"),
        airflow_base_url=os.getenv("AIRFLOW_BASE_URL", "http://airflow-api-server:8080"),
        airflow_api_username=os.getenv("AIRFLOW_API_USERNAME", "admin"),
        airflow_api_password=_required_env("AIRFLOW_API_PASSWORD"),
    )
