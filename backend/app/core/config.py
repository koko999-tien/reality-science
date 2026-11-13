from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "REALITY SCIENCE API"
    environment: str = "development"
    log_level: str = "INFO"

    # PostgreSQL Database URL
    database_url: str = "postgresql+asyncpg://rs_app_user:app_secure_password@localhost:5432/reality_science"

    # Redis URL
    redis_url: str = "redis://:redis_secret_pw@localhost:6379/0"

    # Security & Tokens
    jwt_secret_key: str = "dev_jwt_secret_change_in_production_min_32_bytes_long"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    backend_cors_origins: List[str] = ["http://localhost:3000"]


settings = Settings()
