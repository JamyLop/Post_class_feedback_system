"""本地存储文件直读：小程序 <image> 无法携带 Authorization，用预签名直链访问时会走到这里。

统一要求登录鉴权后再 serve_file，避免打卡照片被未登录用户遍历下载。
前端 Web 走鉴权 blob 下载，不受此路由影响。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.storage import serve_file

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/files/{object_name:path}")
def read_storage_file(
    object_name: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按对象名返回文件内容（本地直接返回流，OSS/MinIO 重定向到预签名 URL）。"""
    return serve_file(object_name)
