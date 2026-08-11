from __future__ import annotations

from fastapi import HTTPException

from app.core.config import settings
from app.storage.local import LocalStorage
from app.storage.minio import MinioStorage

_backend: LocalStorage | MinioStorage | None = None


def _get():
    global _backend
    if _backend is None:
        if settings.storage_backend == "local":
            _backend = LocalStorage()
        else:
            _backend = MinioStorage()
    return _backend


def upload_bytes(data: bytes, content_type: str, ext: str) -> str:
    return _get().upload_bytes(data, content_type, ext)


def presigned_url(object_name: str, expires_seconds: int = 3600) -> str:
    return _get().presigned_url(object_name, expires_seconds)


def download_bytes(object_name: str) -> bytes:
    return _get().download_bytes(object_name)


def serve_file(object_name: str):
    backend = _get()
    if isinstance(backend, LocalStorage):
        return backend.file_response(object_name)
    raise HTTPException(status_code=404, detail="存储后端不支持直读文件")
