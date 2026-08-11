from __future__ import annotations

import io
import time
import uuid
from datetime import timedelta

from minio import Minio

from app.core.config import settings


class MinioStorage:
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(settings.minio_bucket):
            self.client.make_bucket(settings.minio_bucket)

    def upload_bytes(self, data: bytes, content_type: str, ext: str) -> str:
        self._ensure_bucket()
        key = f"{time.strftime('%Y%m%d')}/{uuid.uuid4().hex}{ext}"
        self.client.put_object(
            settings.minio_bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return key

    def presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        if not object_name:
            return ""
        try:
            return self.client.presigned_get_object(
                settings.minio_bucket,
                object_name,
                expires=timedelta(seconds=expires_seconds),
            )
        except Exception:
            return ""

    def download_bytes(self, object_name: str) -> bytes:
        resp = self.client.get_object(settings.minio_bucket, object_name)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()
