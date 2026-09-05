"""存储统一入口：按配置分发到本地磁盘或 MinIO。"""

from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.storage.local import LocalStorage
from app.storage.minio import MinioStorage

_backend: LocalStorage | MinioStorage | None = None


def _get():
    """懒加载单例存储后端。"""
    global _backend
    if _backend is None:
        if settings.storage_backend == "local":
            _backend = LocalStorage()
        else:
            _backend = MinioStorage()
    return _backend


def upload_bytes(data: bytes, content_type: str, ext: str) -> str:
    """上传文件并返回对象名。"""
    return _get().upload_bytes(data, content_type, ext)


def presigned_url(object_name: str, expires_seconds: int = 3600) -> str:
    """生成预签名下载 URL（本地存储返回内部路由）。"""
    return _get().presigned_url(object_name, expires_seconds)


def download_bytes(object_name: str) -> bytes:
    """按对象名读取原始字节。"""
    return _get().download_bytes(object_name)


def serve_file(object_name: str):
    """响应文件内容：本地直接返回流，MinIO 重定向到预签名 URL。"""
    backend = _get()
    if isinstance(backend, LocalStorage):
        return backend.file_response(object_name)
    url = backend.presigned_url(object_name)
    if not url:
        raise HTTPException(status_code=404, detail="文件不存在或暂时无法访问")
    return RedirectResponse(url=url, status_code=307)
