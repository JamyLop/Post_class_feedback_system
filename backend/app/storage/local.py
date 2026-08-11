from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings


class LocalStorage:
    """开发期本地文件存储，替代 MinIO。文件经 /api/storage/files/... 访问。"""

    def __init__(self):
        self.root = Path(settings.local_storage_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, object_name: str) -> Path:
        p = (self.root / object_name).resolve()
        if not str(p).startswith(str(self.root)):
            raise HTTPException(status_code=400, detail="非法的存储路径")
        return p

    def upload_bytes(self, data: bytes, content_type: str, ext: str) -> str:
        key = f"{time.strftime('%Y%m%d')}/{uuid.uuid4().hex}{ext}"
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return key

    def presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        if not object_name:
            return ""
        return f"/api/storage/files/{object_name}"

    def download_bytes(self, object_name: str) -> bytes:
        return self._path(object_name).read_bytes()

    def file_response(self, object_name: str) -> FileResponse:
        p = self._path(object_name)
        if not p.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")
        return FileResponse(p)
