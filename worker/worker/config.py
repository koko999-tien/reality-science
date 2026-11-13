"""
REALITY SCIENCE — Compute Worker Configuration & Anti-Database Guard (Zone 3)
Approved Decision 2 (ADR-002: Private Scientific Compute Infrastructure)
Mandate: Strict Zero-Database Invariant. Zero database credentials injected into worker.
"""

import os
import re
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Definition of forbidden environment patterns for zero database credentials
# Exhaustively blocks PostgreSQL, MySQL, SQLite, MongoDB, MariaDB, CockroachDB,
# Oracle, MSSQL, SQL_*, and DB_* credential injection attempts.
FORBIDDEN_ENV_PATTERNS: List[re.Pattern] = [
    # Full connection strings and database-specific engine keys
    re.compile(r".*(POSTGRES|DATABASE|MYSQL|MONGO|MARIADB|SQLITE|COCKROACH|ORACLE|MSSQL).*", re.IGNORECASE),
    # Prefixed database variables (DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DB_NAME, DB_URI, etc.)
    re.compile(r".*DB_.*", re.IGNORECASE),
    # SQL query or credential variables (SQL_USER, SQL_PASSWORD, SQL_HOST, SQL_PORT, etc.)
    re.compile(r".*SQL_.*", re.IGNORECASE),
    # Standard PostgreSQL libpq environment variables (PGHOST, PGPORT, PGUSER, PGPASSWORD, etc.)
    re.compile(r"^PG[A-Z0-9_]*$", re.IGNORECASE),
]


def assert_zero_database_credentials() -> None:
    """Pre-flight check: assert zero database credentials exist in worker environment.

    Raises:
        RuntimeError: If any environment variable matches any pattern in FORBIDDEN_ENV_PATTERNS.
    """
    violations = []
    for key in os.environ.keys():
        for pattern in FORBIDDEN_ENV_PATTERNS:
            if pattern.match(key):
                violations.append(key)
                break
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
    """Instantiates worker settings after asserting zero database credentials."""
    assert_zero_database_credentials()
    return WorkerSettings()
