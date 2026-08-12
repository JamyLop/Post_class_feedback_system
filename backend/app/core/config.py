from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str:
    cwd = Path.cwd()
    candidates = [
        cwd / ".env",
        cwd.parent / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(cwd / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "课后反馈系统"
    app_env: str = "dev"
    debug: bool = True
    log_dir: str = "logs"
    api_prefix: str = "/api"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 1440
    cors_origins: List[str] = ["http://localhost:5173"]

    database_url: str = "postgresql+psycopg://pfs:pfs@localhost:5432/pfs"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    storage_backend: str = "local"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "pfs"
    minio_secret_key: str = "pfs123456"
    minio_bucket: str = "submissions"
    minio_secure: bool = False
    local_storage_dir: str = "local_storage"
    max_upload_bytes: int = 10 * 1024 * 1024

    llm_provider: str = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 1

    ocr_provider: str = "mock"


settings = Settings()
