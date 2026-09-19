"""阿里云 OSS 对象存储实现。"""

from __future__ import annotations

import time
import uuid

import oss2

from app.core.config import settings


class AliyunOSSStorage:
    """阿里云 OSS 对象存储。"""

    def __init__(self):
        auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        self.bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)

    def upload_bytes(self, data: bytes, content_type: str, ext: str) -> str:
        key = f"{time.strftime('%Y%m%d')}/{uuid.uuid4().hex}{ext}"
        headers = {"Content-Type": content_type}
        self.bucket.put_object(key, data, headers=headers)
        return key

    def presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        if not object_name:
            return ""
        try:
            return self.bucket.sign_url("GET", object_name, expires_seconds)
        except Exception:
            return ""

    def download_bytes(self, object_name: str) -> bytes:
        return self.bucket.get_object(object_name).read()
