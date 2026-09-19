"""应用配置：读取 .env 环境变量（含默认值）。"""

from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
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
    """集中配置项：应用、数据库与微信登录。"""

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
    backend_port: int = 8000
    # 开发环境可以使用默认值；生产环境必须通过 SECRET_KEY 显式注入随机密钥。
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 1440
    cors_origins: List[str] = ["http://localhost:5173"]

    database_url: str = "postgresql+psycopg://pfs:pfs@localhost:5432/pfs"

    # 打卡附件仍需兼容历史本地文件及当前 OSS 对象；缺少这些字段会让照片读取链路在运行时失败。
    storage_backend: str = "local"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "pfs"
    minio_secret_key: str = "pfs123456"
    minio_bucket: str = "submissions"
    minio_secure: bool = False
    local_storage_dir: str = "local_storage"
    max_upload_bytes: int = 10 * 1024 * 1024

    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_endpoint: str = "oss-cn-beijing.aliyuncs.com"
    oss_bucket: str = "xueshengyian"

    wx_appid: str = ""
    wx_secret: str = ""
    wx_mock: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """兼容 JSON 数组及部署平台常用的逗号分隔环境变量。"""
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_security(self):
        """生产进程启动即拒绝不安全的认证或跨域配置，避免带病上线。"""
        # 白名单反转：仅 dev/test 放行，其他一律按生产校验，防止 APP_ENV 拼写错误绕过。
        if self.app_env.lower() in {"dev", "development", "test", "testing"}:
            return self
        if self.debug:
            raise ValueError("生产环境必须设置 DEBUG=false")
        if self.secret_key in {"", "dev-secret-change-me", "change-me-in-production-please"} or len(self.secret_key) < 32:
            raise ValueError("生产环境必须设置至少 32 位的随机 SECRET_KEY")
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("生产环境 CORS_ORIGINS 必须是明确的受信任域名列表，不能包含 *")
        return self


settings = Settings()
