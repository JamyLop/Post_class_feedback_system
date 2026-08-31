"""应用配置：读取 .env 环境变量（含默认值）。"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str:
    """从常见位置定位 .env 文件（当前目录/上级/项目根）。"""
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
    """集中配置项：应用/数据库/Redis/存储/AI/OCR。"""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "一生一案学业发展管理系统"
    app_env: str = "dev"
    debug: bool = True
    log_dir: str = "logs"
    api_prefix: str = "/api"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 1440
    cors_origins: List[str] = ["*"]

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
    ocr_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ocr_api_key: str = ""
    ocr_model: str = "qwen-vl-ocr"
    ocr_timeout_seconds: int = 60
    ocr_max_retries: int = 1

    wx_appid: str = ""
    wx_secret: str = ""
    wx_mock: bool = False


settings = Settings()
