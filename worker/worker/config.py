import os
import re
from pydantic_settings import BaseSettings, SettingsConfigDict

# Definition of forbidden environment patterns for zero database credentials
FORBIDDEN_ENV_PATTERNS = [
    re.compile(r".*POSTGRES.*", re.IGNORECASE),  # forbidden regex check
    re.compile(r".*DATABASE_URL.*", re.IGNORECASE),  # forbidden regex check
    re.compile(r"^PG[A-Z0-9_]*$", re.IGNORECASE),  # forbidden regex check
]


def assert_zero_database_credentials() -> None:
    """Pre-flight check: assert zero database credentials exist in worker environment."""
    violations = []
    for key in os.environ.keys():
        for pattern in FORBIDDEN_ENV_PATTERNS:
            if pattern.match(key):
                violations.append(key)
    if violations:
        raise RuntimeError(
            f"FATAL SECURITY VIOLATION: Compute worker started with forbidden database credentials: {violations}. "
            "Compute workers must run in Zone 3 with zero database access!"
        )


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    celery_broker_url: str = "redis://:redis_secret_pw@localhost:6379/0"
    celery_result_backend: str = "redis://:redis_secret_pw@localhost:6379/1"
    log_level: str = "INFO"
    interactive_timeout_seconds: int = 10
    batch_timeout_seconds: int = 120


def get_worker_settings() -> WorkerSettings:
    assert_zero_database_credentials()
    return WorkerSettings()
